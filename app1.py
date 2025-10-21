# ----------------------------------------------------------
# COM682 Coursework 1: Flask + MongoDB Healthcare API
# Author: <Your Name>
# ----------------------------------------------------------

from flask import Flask, jsonify, request, make_response, render_template
from pymongo import MongoClient
from bson import ObjectId
from flask_cors import CORS
from functools import wraps
import re
import jwt
import datetime
import bcrypt
import os
from flasgger import Swagger
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ----------------------------------------------------------
# App Setup
# ----------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mysecret')
CORS(app)
Swagger(app)
limiter = Limiter(app=app, key_func=get_remote_address)

# ----------------------------------------------------------
# MongoDB Connection
# ----------------------------------------------------------
client = MongoClient('mongodb://localhost:27017/')
db = client['healthcareDB']
patients = db['patients']
users = db['users']
blacklist = db['blacklist']

# ----------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------
def is_valid_objectid(id):
    return bool(re.fullmatch(r"[0-9a-fA-F]{24}", id))

def validate_patient_data(data):
    try:
        age = int(data.get("age", -1))
        if age < 0 or age > 120:
            return "Age must be between 0 and 120"
    except ValueError:
        return "Age must be a number"
    if not all(k in data for k in ("name", "age", "gender", "condition")):
        return "Missing required fields"
    return None

# ----------------------------------------------------------
# JWT Decorators
# ----------------------------------------------------------
def jwt_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return make_response(jsonify({'error': 'Token missing'}), 401)
        if blacklist.find_one({"token": token}):
            return make_response(jsonify({'error': 'Token blacklisted'}), 401)
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
        except jwt.ExpiredSignatureError:
            return make_response(jsonify({'error': 'Token expired'}), 401)
        except Exception:
            return make_response(jsonify({'error': 'Token invalid'}), 401)
        return func(*args, **kwargs)
    return wrapper

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('x-access-token')
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms="HS256")
        if data.get("admin"):
            return func(*args, **kwargs)
        return make_response(jsonify({'error': 'Admin access required'}), 401)
    return wrapper

# ----------------------------------------------------------
# Default Admin
# ----------------------------------------------------------
def create_default_user():
    if users.find_one({'username': 'admin'}) is None:
        hashed_pw = bcrypt.hashpw(b'admin123', bcrypt.gensalt())
        users.insert_one({'username': 'admin', 'password': hashed_pw, 'admin': True})
        print("Default admin user created: admin/admin123")

create_default_user()

# ----------------------------------------------------------
# Authentication Routes
# ----------------------------------------------------------
@app.route('/api/v1.0/login', methods=['GET'])
def login():
    """Authenticate user using Basic Auth and issue JWT"""
    auth = request.authorization
    if not auth:
        return make_response(jsonify({'error': 'Authentication required'}), 401)
    user = users.find_one({'username': auth.username})
    if not user or not bcrypt.checkpw(bytes(auth.password, 'utf-8'), user['password']):
        return make_response(jsonify({'error': 'Invalid credentials'}), 401)

    token = jwt.encode({
        'user': auth.username,
        'admin': user.get('admin', False),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=45)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return make_response(jsonify({'token': token}), 200)

@app.route('/api/v1.0/logout', methods=['GET'])
@jwt_required
def logout():
    """Invalidate the current JWT by adding it to blacklist"""
    token = request.headers['x-access-token']
    blacklist.insert_one({"token": token})
    return jsonify({'message': 'Logged out successfully'})

# ----------------------------------------------------------
# Frontend route (optional)
# ----------------------------------------------------------
@app.route("/")
def index():
    return render_template("index1.html")

# ----------------------------------------------------------
# Patient CRUD
# ----------------------------------------------------------
@app.route("/api/v1.0/patients", methods=["GET"])
@jwt_required
@limiter.limit("30/minute")
def get_patients():
    """Paginated patient list with optional filters"""
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    condition_filter = request.args.get('condition')

    query = {}
    if condition_filter:
        query['condition'] = {"$regex": condition_filter, "$options": "i"}

    data = []
    for p in patients.find(query).skip((page - 1) * limit).limit(limit):
        p['_id'] = str(p['_id'])
        for sub in p.get('appointments', []):
            sub['_id'] = str(sub['_id'])
        data.append(p)
    return jsonify({'count': len(data), 'patients': data})

@app.route("/api/v1.0/patients", methods=["POST"])
@jwt_required
def add_patient():
    """Add a new patient"""
    error = validate_patient_data(request.form)
    if error:
        return make_response(jsonify({'error': error}), 400)

    new_patient = {
        "name": request.form["name"],
        "age": int(request.form["age"]),
        "gender": request.form["gender"],
        "condition": request.form["condition"],
        "image_url": request.form.get("image_url", None),
        "appointments": [],
        "prescriptions": []
    }
    inserted = patients.insert_one(new_patient)
    return jsonify({
        "message": "Patient added",
        "url": f"/api/v1.0/patients/{inserted.inserted_id}"
    }), 201

@app.route("/api/v1.0/patients/<string:id>", methods=["GET"])
@jwt_required
def get_patient(id):
    """Get patient by ID"""
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid patient ID'}), 400
    patient = patients.find_one({'_id': ObjectId(id)})
    if not patient:
        return jsonify({'error': 'Not found'}), 404
    patient['_id'] = str(patient['_id'])
    return jsonify(patient)

@app.route("/api/v1.0/patients/<string:id>", methods=["PUT"])
@jwt_required
def update_patient(id):
    """Update patient details"""
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid ID'}), 400
    error = validate_patient_data(request.form)
    if error:
        return jsonify({'error': error}), 400
    result = patients.update_one(
        {"_id": ObjectId(id)},
        {"$set": {
            "name": request.form["name"],
            "age": int(request.form["age"]),
            "gender": request.form["gender"],
            "condition": request.form["condition"],
            "image_url": request.form.get("image_url")
        }}
    )
    if result.matched_count == 0:
        return jsonify({'error': 'Patient not found'}), 404
    return jsonify({'message': 'Patient updated successfully'})

@app.route("/api/v1.0/patients/<string:id>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_patient(id):
    """Admin only: delete patient"""
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid ID'}), 400
    result = patients.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        return jsonify({'error': 'Patient not found'}), 404
    return jsonify({'message': 'Patient deleted'})

# ----------------------------------------------------------
# Appointment Sub-Documents
# ----------------------------------------------------------
@app.route("/api/v1.0/patients/<string:id>/appointments", methods=["POST"])
@jwt_required
def add_appointment(id):
    """Add appointment to patient"""
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid patient ID'}), 400
    required = ("doctor", "date", "notes", "status")
    if not all(k in request.form for k in required):
        return jsonify({'error': 'Missing appointment data'}), 400
    appointment = {
        "_id": ObjectId(),
        "doctor": request.form["doctor"],
        "date": request.form["date"],
        "notes": request.form["notes"],
        "status": request.form["status"]
    }
    result = patients.update_one({"_id": ObjectId(id)}, {"$push": {"appointments": appointment}})
    if result.matched_count == 0:
        return jsonify({'error': 'Patient not found'}), 404
    return jsonify({"message": "Appointment added", "appointment_id": str(appointment["_id"])}), 201

@app.route("/api/v1.0/patients/<string:id>/appointments", methods=["GET"])
@jwt_required
def list_appointments(id):
    """Fetch all appointments"""
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid ID'}), 400
    patient = patients.find_one({"_id": ObjectId(id)}, {"appointments": 1, "_id": 0})
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404
    for a in patient.get("appointments", []):
        a["_id"] = str(a["_id"])
    return jsonify(patient)

@app.route("/api/v1.0/patients/<string:pid>/appointments/<string:aid>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_appointment(pid, aid):
    """Admin delete appointment"""
    if not (is_valid_objectid(pid) and is_valid_objectid(aid)):
        return jsonify({'error': 'Invalid ID'}), 400
    result = patients.update_one(
        {"_id": ObjectId(pid)},
        {"$pull": {"appointments": {"_id": ObjectId(aid)}}}
    )
    if result.modified_count == 0:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'message': 'Appointment deleted'})

# ----------------------------------------------------------
# Advanced Query Endpoints
# ----------------------------------------------------------
@app.route("/api/v1.0/search", methods=["GET"])
@jwt_required
def search_patients():
    """Search patients by name or condition"""
    q = request.args.get("q", "")
    results = patients.find({
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"condition": {"$regex": q, "$options": "i"}}
        ]
    })
    data = [{**p, "_id": str(p["_id"])} for p in results]
    return jsonify({'results': data, 'count': len(data)})

@app.route("/api/v1.0/stats/appointments", methods=["GET"])
@jwt_required
def appointment_stats():
    """Aggregation: count appointments per doctor"""
    pipeline = [
        {"$unwind": "$appointments"},
        {"$group": {"_id": "$appointments.doctor", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    stats = list(patients.aggregate(pipeline))
    return jsonify(stats)

# ----------------------------------------------------------
# Error Handling
# ----------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Server error"}), 500

# ----------------------------------------------------------
# Run App
# ----------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
