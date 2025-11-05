# COM682 Coursework 1: Flask + MongoDB Healthcare API
# Author: Paul Johnston (B00888517)
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
client = MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017/'))
db_name = os.environ.get('MONGO_DB', 'syntheaDB')
db = client[db_name]
patients = db['patients']
users = db['users']
blacklist = db['blacklist']

# ----------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------
def is_valid_objectid(id):
    return bool(re.fullmatch(r"[0-9a-fA-F]{24}", id))

def incoming_data():
    """Accept either JSON or form-encoded bodies."""
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form or {}

def validate_patient_data(data):
    try:
        age = int(data.get("age", -1))
        if age < 0 or age > 120:
            return "Age must be between 0 and 120"
    except (ValueError, TypeError):
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
    if not user:
        return make_response(jsonify({'error': 'Invalid credentials'}), 401)

    stored_hash = user['password']

    if hasattr(stored_hash, 'as_bytes'):
        stored_hash_bytes = stored_hash.as_bytes()
    elif isinstance(stored_hash, bytes):
        stored_hash_bytes = stored_hash
    elif isinstance(stored_hash, str):
        stored_hash_bytes = stored_hash.encode('utf-8')
    else:
        return make_response(jsonify({'error': 'Unrecognized password format'}), 500)

    if not bcrypt.checkpw(auth.password.encode('utf-8'), stored_hash_bytes):
        return make_response(jsonify({'error': 'Invalid credentials'}), 401)

    token = jwt.encode({
        'user': auth.username,
        'admin': user.get('admin', False),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=45)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({'token': token})

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
    """Paginated summary of patients (clean output with safe name cleanup)."""
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = max(1, min(50, int(request.args.get("limit", 10))))
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    condition_filter = request.args.get("condition")
    query = {}
    if condition_filter:
        query["condition"] = {"$regex": condition_filter, "$options": "i"}

    # Use list() to materialize the cursor safely before looping
    docs = list(patients.find(query).skip((page - 1) * limit).limit(limit))
    total = patients.count_documents(query)

    data = []
    for p in docs:
        # Clean name safely
        raw_name = p.get("name", "")
        if not isinstance(raw_name, str):
            raw_name = str(raw_name)
        clean_name = re.sub(r"\d+", "", raw_name).strip().title()

        summary = {
            "id": str(p["_id"]),
            "name": clean_name,
            "age": p.get("age"),
            "gender": p.get("gender"),
            "condition": p.get("condition"),
            "appointment_count": len(p.get("appointments", [])),
            "prescription_count": len(p.get("prescriptions", [])),
            "careplan_count": len(p.get("careplans", [])),
        }
        data.append(summary)

    return jsonify({
        "page": page,
        "count": len(data),
        "total": total,
        "patients": data
    })


@app.route("/api/v1.0/patients", methods=["POST"])
@jwt_required
def add_patient():
    """Add a new patient"""
    body = incoming_data()
    error = validate_patient_data(body)
    if error:
        return make_response(jsonify({'error': error}), 400)

    new_patient = {
        "name": body["name"],
        "age": int(body["age"]),
        "gender": body["gender"],
        "condition": body["condition"],
        "image_url": body.get("image_url"),
        "appointments": [],
        "prescriptions": [],
        "careplans": []
    }
    inserted = patients.insert_one(new_patient)
    return jsonify({
        "message": "Patient added",
        "url": f"/api/v1.0/patients/{inserted.inserted_id}"
    }), 201

@app.route("/api/v1.0/patients/<string:id>", methods=["GET"])
@jwt_required
def get_patient(id):
    """Get detailed patient by ID"""
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid patient ID'}), 400
    patient = patients.find_one({'_id': ObjectId(id)})
    if not patient:
        return jsonify({'error': 'Not found'}), 404

    patient['_id'] = str(patient['_id'])
    for sublist in ['appointments', 'prescriptions', 'careplans']:
        for sub in patient.get(sublist, []):
            if isinstance(sub.get('_id'), ObjectId):
                sub['_id'] = str(sub['_id'])
    return jsonify(patient)

@app.route("/api/v1.0/patients/<string:id>", methods=["PUT"])
@jwt_required
def update_patient(id):
    """Update patient details"""
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid ID'}), 400
    body = incoming_data()
    error = validate_patient_data(body)
    if error:
        return jsonify({'error': error}), 400

    result = patients.update_one(
        {"_id": ObjectId(id)},
        {"$set": {
            "name": body["name"],
            "age": int(body["age"]),
            "gender": body["gender"],
            "condition": body["condition"],
            "image_url": body.get("image_url")
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


@app.route("/api/v1.0/patients/<string:id>/appointments", methods=["POST"])
@jwt_required
@admin_required
def add_appointment(id):
    """Admin only: Add appointment to an existing patient"""
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid patient ID'}), 400

    patient = patients.find_one({"_id": ObjectId(id)})
    if not patient:
        return jsonify({'error': 'Patient not found'}), 404

    body = incoming_data()
    required = ("doctor", "date", "notes", "status")
    if not all(k in body for k in required):
        return jsonify({'error': 'Missing appointment data'}), 400

    appointment = {
        "_id": ObjectId(),
        "doctor": body["doctor"],
        "date": body["date"],
        "notes": body["notes"],
        "status": body["status"]
    }

    result = patients.update_one(
        {"_id": ObjectId(id)},
        {"$push": {"appointments": appointment}}
    )

    if result.modified_count == 0:
        return jsonify({'error': 'Failed to add appointment'}), 500

    return jsonify({
        "message": "Appointment added successfully",
        "appointment_id": str(appointment["_id"])
    }), 201

@app.route("/api/v1.0/patients/<string:pid>/appointments/<string:aid>", methods=["GET"])
@jwt_required
def get_appointment(pid, aid):
    """Retrieve a single appointment by its ID for a given patient"""
    if not (is_valid_objectid(pid) and is_valid_objectid(aid)):
        return jsonify({'error': 'Invalid ID format'}), 400

    patient = patients.find_one(
        {"_id": ObjectId(pid), "appointments._id": ObjectId(aid)},
        {"appointments.$": 1, "_id": 0}
    )

    if not patient or "appointments" not in patient:
        return jsonify({'error': 'Appointment not found'}), 404

    appointment = patient["appointments"][0]
    appointment["_id"] = str(appointment["_id"])
    return jsonify(appointment)


@app.route("/api/v1.0/patients/<string:pid>/appointments/<string:aid>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_appointment(pid, aid):
    """Admin only: Delete appointment"""
    if not (is_valid_objectid(pid) and is_valid_objectid(aid)):
        return jsonify({'error': 'Invalid ID'}), 400
    result = patients.update_one(
        {"_id": ObjectId(pid)},
        {"$pull": {"appointments": {"_id": ObjectId(aid)}}}
    )
    if result.modified_count == 0:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'message': 'Appointment deleted'})

@app.route("/api/v1.0/patients/<string:id>/prescriptions", methods=["GET"])
@jwt_required
def list_prescriptions(id):
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid ID'}), 400
    doc = patients.find_one({"_id": ObjectId(id)}, {"prescriptions": 1, "_id": 0})
    if not doc:
        return jsonify({'error': 'Patient not found'}), 404
    for p in doc.get("prescriptions", []):
        if isinstance(p.get("_id"), ObjectId):
            p["_id"] = str(p["_id"])
    return jsonify(doc)

@app.route("/api/v1.0/patients/<string:id>/prescriptions", methods=["POST"])
@jwt_required
def add_prescription(id):
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid patient ID'}), 400
    body = incoming_data()
    required = ("name", "start")
    if not all(k in body for k in required):
        return jsonify({'error': 'Missing prescription data'}), 400
    presc = {
        "_id": ObjectId(),
        "name": body["name"],
        "start": body.get("start"),
        "stop": body.get("stop"),
        "status": body.get("status", "active")
    }
    result = patients.update_one({"_id": ObjectId(id)}, {"$push": {"prescriptions": presc}})
    if result.matched_count == 0:
        return jsonify({'error': 'Patient not found'}), 404
    return jsonify({"message": "Prescription added", "prescription_id": str(presc["_id"])}), 201

@app.route("/api/v1.0/patients/<string:pid>/prescriptions/<string:rid>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_prescription(pid, rid):
    if not (is_valid_objectid(pid) and is_valid_objectid(rid)):
        return jsonify({'error': 'Invalid ID'}), 400
    result = patients.update_one(
        {"_id": ObjectId(pid)},
        {"$pull": {"prescriptions": {"_id": ObjectId(rid)}}}
    )
    if result.modified_count == 0:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'message': 'Prescription deleted'})

@app.route("/api/v1.0/patients/<string:id>/careplans", methods=["GET"])
@jwt_required
def list_careplans(id):
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid ID'}), 400
    doc = patients.find_one({"_id": ObjectId(id)}, {"careplans": 1, "_id": 0})
    if not doc:
        return jsonify({'error': 'Patient not found'}), 404
    for c in doc.get("careplans", []):
        if isinstance(c.get("_id"), ObjectId):
            c["_id"] = str(c["_id"])
    return jsonify(doc)

@app.route("/api/v1.0/patients/<string:id>/careplans", methods=["POST"])
@jwt_required
def add_careplan(id):
    if not is_valid_objectid(id):
        return jsonify({'error': 'Invalid patient ID'}), 400
    body = incoming_data()
    required = ("description", "start")
    if not all(k in body for k in required):
        return jsonify({'error': 'Missing careplan data'}), 400
    cp = {
        "_id": ObjectId(),
        "description": body["description"],
        "start": body.get("start"),
        "stop": body.get("stop")
    }
    result = patients.update_one({"_id": ObjectId(id)}, {"$push": {"careplans": cp}})
    if result.matched_count == 0:
        return jsonify({'error': 'Patient not found'}), 404
    return jsonify({"message": "Careplan added", "careplan_id": str(cp["_id"])}), 201

@app.route("/api/v1.0/patients/<string:pid>/careplans/<string:cid>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_careplan(pid, cid):
    if not (is_valid_objectid(pid) and is_valid_objectid(cid)):
        return jsonify({'error': 'Invalid ID'}), 400
    result = patients.update_one(
        {"_id": ObjectId(pid)},
        {"$pull": {"careplans": {"_id": ObjectId(cid)}}}
    )
    if result.modified_count == 0:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'message': 'Careplan deleted'})

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
    pipeline = [
        {"$unwind": "$appointments"},
        {"$group": {"_id": "$appointments.doctor", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    return jsonify(list(patients.aggregate(pipeline)))

@app.route("/api/v1.0/stats/prescriptions", methods=["GET"])
@jwt_required
def prescriptions_stats():
    pipeline = [
        {"$unwind": "$prescriptions"},
        {"$group": {"_id": "$prescriptions.name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    return jsonify(list(patients.aggregate(pipeline)))

@app.route("/api/v1.0/stats/careplans", methods=["GET"])
@jwt_required
def careplans_stats():
    pipeline = [
        {"$unwind": "$careplans"},
        {"$group": {"_id": "$careplans.description", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    return jsonify(list(patients.aggregate(pipeline)))

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Server error"}), 500

if __name__ == "__main__":
    print(f"Using MongoDB database: {db_name}")
    app.run(debug=True)
