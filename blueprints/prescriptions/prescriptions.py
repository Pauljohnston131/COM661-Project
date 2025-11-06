from flask import Blueprint, request
from bson import ObjectId
from decorators import jwt_required, admin_required
from utils import response
import globals, re

prescriptions_bp = Blueprint('prescriptions_bp', __name__, url_prefix='/api/v1.0/patients')
patients = globals.db["patients"]

# helper: validate objectid
def is_valid_objectid(id):
    return bool(re.fullmatch(r"[0-9a-fA-F]{24}", id))

# get prescriptions
@prescriptions_bp.route("/<string:pid>/prescriptions", methods=["GET"])
@jwt_required
def list_prescriptions(pid):
    if not is_valid_objectid(pid):
        return response(False, message="Invalid patient ID", status=400)
    
    doc = patients.find_one({"_id": ObjectId(pid)}, {"prescriptions": 1, "_id": 0})
    if not doc:
        return response(False, message="Patient not found", status=404)
    
    for p in doc.get("prescriptions", []):
        if isinstance(p.get("_id"), ObjectId):
            p["_id"] = str(p["_id"])
    
    return response(True, data={"prescriptions": doc.get("prescriptions", [])})

# post add prescription
@prescriptions_bp.route("/<string:pid>/prescriptions", methods=["POST"])
@jwt_required
def add_prescription(pid):
    if not is_valid_objectid(pid):
        return response(False, message="Invalid patient ID", status=400)
    
    body = request.get_json() or {}
    if not all(k in body for k in ("name", "start")):
        return response(False, message="Missing fields: name, start", status=400)

    presc = {
        "_id": ObjectId(),
        "name": body["name"],
        "start": body["start"],
        "stop": body.get("stop"),
        "status": body.get("status", "active")
    }

    patients.update_one({"_id": ObjectId(pid)}, {"$push": {"prescriptions": presc}})
    return response(True, message="Prescription added", data={"id": str(presc["_id"])}, status=201)

# put update prescription
@prescriptions_bp.route("/<string:pid>/prescriptions/<string:rid>", methods=["PUT"])
@jwt_required
@admin_required
def update_prescription(pid, rid):
    if not (is_valid_objectid(pid) and is_valid_objectid(rid)):
        return response(False, message="Invalid ID format", status=400)

    body = request.get_json() or {}
    update_fields = {
        f"prescriptions.$.{k}": v
        for k, v in body.items()
        if k in ("name", "start", "stop", "status")
    }

    if not update_fields:
        return response(False, message="No valid fields to update", status=400)

    owner_check = patients.find_one({
        "_id": ObjectId(pid),
        "prescriptions._id": ObjectId(rid)
    })
    if not owner_check:
        return response(False, message="Prescription not found for this patient", status=404)

    result = patients.update_one(
        {
            "_id": ObjectId(pid),
            "prescriptions._id": ObjectId(rid)
        },
        {"$set": update_fields}
    )

    if result.modified_count == 0:
        return response(False, message="Prescription not updated (no changes detected)", status=400)

    return response(True, message="Prescription updated successfully", data={"updated_fields": list(body.keys())})

# delete prescription
@prescriptions_bp.route("/<string:pid>/prescriptions/<string:rid>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_prescription(pid, rid):
    if not (is_valid_objectid(pid) and is_valid_objectid(rid)):
        return response(False, message="Invalid ID", status=400)
    
    result = patients.update_one(
        {"_id": ObjectId(pid)},
        {"$pull": {"prescriptions": {"_id": ObjectId(rid)}}}
    )
    if result.modified_count == 0:
        return response(False, message="Prescription not found", status=404)
    
    return response(True, message="Prescription deleted successfully")
