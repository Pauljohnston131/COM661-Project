from flask import Blueprint, jsonify, request
from bson import ObjectId
import re
import globals
from decorators import jwt_required, admin_required

patients_bp = Blueprint('patients_bp', __name__, url_prefix='/api/v1.0/patients')
patients = globals.db["patients"]

def is_valid_objectid(id):
    return bool(re.fullmatch(r"[0-9a-fA-F]{24}", id))

def incoming_data():
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

@patients_bp.route("/", methods=["GET"])
@jwt_required
def get_patients():
    """Get paginated list of patients (filter by condition)."""
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = max(1, min(50, int(request.args.get("limit", 10))))
    except ValueError:
        return jsonify({"error": "Invalid pagination parameters"}), 400

    query = {}
    if request.args.get("condition"):
        query["condition"] = {"$regex": request.args["condition"], "$options": "i"}

    docs = list(patients.find(query).skip((page - 1) * limit).limit(limit))
    total = patients.count_documents(query)

    results = [{
        "id": str(p["_id"]),
        "name": re.sub(r"\d+", "", str(p.get("name", ""))).strip().title(),
        "age": p.get("age"),
        "gender": p.get("gender"),
        "condition": p.get("condition"),
        "appointment_count": len(p.get("appointments", [])),
        "prescription_count": len(p.get("prescriptions", [])),
        "careplan_count": len(p.get("careplans", []))
    } for p in docs]

    return jsonify({"page": page, "count": len(results), "total": total, "patients": results})

@patients_bp.route("/", methods=["POST"])
@jwt_required
def add_patient():
    """Add a new patient."""
    body = incoming_data()
    error = validate_patient_data(body)
    if error:
        return jsonify({"error": error}), 400

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
    result = patients.insert_one(new_patient)
    return jsonify({"message": "Patient added", "id": str(result.inserted_id)}), 201

@patients_bp.route("/<string:id>", methods=["GET"])
@jwt_required
def get_patient(id):
    """Get full details of a patient by ID."""
    if not is_valid_objectid(id):
        return jsonify({"error": "Invalid ID"}), 400
    p = patients.find_one({"_id": ObjectId(id)})
    if not p:
        return jsonify({"error": "Not found"}), 404
    p["_id"] = str(p["_id"])
    for field in ["appointments", "prescriptions", "careplans"]:
        for sub in p.get(field, []):
            if isinstance(sub.get("_id"), ObjectId):
                sub["_id"] = str(sub["_id"])
    return jsonify(p)

@patients_bp.route("/<string:id>", methods=["PUT"])
@jwt_required
def update_patient(id):
    """Update patient information."""
    if not is_valid_objectid(id):
        return jsonify({"error": "Invalid ID"}), 400
    body = incoming_data()
    error = validate_patient_data(body)
    if error:
        return jsonify({"error": error}), 400

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
        return jsonify({"error": "Patient not found"}), 404
    return jsonify({"message": "Patient updated successfully"})

@patients_bp.route("/<string:id>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_patient(id):
    """Delete a patient (admin only)."""
    if not is_valid_objectid(id):
        return jsonify({"error": "Invalid ID"}), 400
    result = patients.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"message": "Patient deleted"})
