from flask import Blueprint, request
from bson import ObjectId
import re
import globals
from decorators import jwt_required, admin_required
from utils import response 

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
        return response(False, message="Invalid pagination parameters", status=400)

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

    return response(True, data={
        "page": page,
        "count": len(results),
        "total": total,
        "patients": results
    })


@patients_bp.route("/", methods=["POST"])
@jwt_required
def add_patient():
    """Add a new patient."""
    body = incoming_data()
    error = validate_patient_data(body)
    if error:
        return response(False, message=error, status=400)

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
    return response(True,
                    message="Patient added successfully",
                    data={"id": str(result.inserted_id)},
                    status=201)

@patients_bp.route("/<string:id>", methods=["GET"])
@jwt_required
def get_patient(id):
    """Get full details of a patient by ID."""
    if not is_valid_objectid(id):
        return response(False, message="Invalid patient ID", status=400)
    
    p = patients.find_one({"_id": ObjectId(id)})
    if not p:
        return response(False, message="Patient not found", status=404)
    
    p["_id"] = str(p["_id"])
    for field in ["appointments", "prescriptions", "careplans"]:
        for sub in p.get(field, []):
            if isinstance(sub.get("_id"), ObjectId):
                sub["_id"] = str(sub["_id"])
    
    return response(True, data=p, message="Patient retrieved successfully")

@patients_bp.route("/<string:id>", methods=["PUT"])
@jwt_required
def update_patient(id):
    """Update patient information (supports partial updates)."""
    if not is_valid_objectid(id):
        return response(False, message="Invalid patient ID", status=400)
    
    body = incoming_data()
    if not body:
        return response(False, message="No fields provided for update", status=400)

    allowed_fields = {"name", "age", "gender", "condition", "image_url"}
    update_fields = {}

    for key, value in body.items():
        if key in allowed_fields:
            if key == "age":
                try:
                    age = int(value)
                    if age < 0 or age > 120:
                        return response(False, message="Age must be between 0 and 120", status=400)
                    update_fields["age"] = age
                except (ValueError, TypeError):
                    return response(False, message="Age must be a number", status=400)
            else:
                update_fields[key] = value

    if not update_fields:
        return response(False, message="No valid fields to update", status=400)

    result = patients.update_one(
        {"_id": ObjectId(id)},
        {"$set": update_fields}
    )

    if result.matched_count == 0:
        return response(False, message="Patient not found", status=404)
    
    return response(True, message="Patient updated successfully", data={"updated_fields": list(update_fields.keys())})


@patients_bp.route("/<string:id>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_patient(id):
    """Delete a patient (admin only)."""
    if not is_valid_objectid(id):
        return response(False, message="Invalid ID", status=400)
    
    result = patients.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 0:
        return response(False, message="Patient not found", status=404)
    
    return response(True, message="Patient deleted successfully")
