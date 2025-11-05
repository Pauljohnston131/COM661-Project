from flask import Blueprint, request
from bson import ObjectId
from decorators import jwt_required, admin_required
from utils import response
import globals, re

careplans_bp = Blueprint('careplans_bp', __name__, url_prefix='/api/v1.0/patients')
patients = globals.db["patients"]

def is_valid_objectid(id):
    return bool(re.fullmatch(r"[0-9a-fA-F]{24}", id))

@careplans_bp.route("/<string:pid>/careplans", methods=["GET"])
@jwt_required
def list_careplans(pid):
    """List all careplans for a patient."""
    if not is_valid_objectid(pid):
        return response(False, message="Invalid patient ID", status=400)
    
    doc = patients.find_one({"_id": ObjectId(pid)}, {"careplans": 1, "_id": 0})
    if not doc:
        return response(False, message="Patient not found", status=404)
    
    for c in doc.get("careplans", []):
        if isinstance(c.get("_id"), ObjectId):
            c["_id"] = str(c["_id"])
    
    return response(True, data={"careplans": doc.get("careplans", [])})


@careplans_bp.route("/<string:pid>/careplans", methods=["POST"])
@jwt_required
def add_careplan(pid):
    """Add a careplan for a patient."""
    if not is_valid_objectid(pid):
        return response(False, message="Invalid patient ID", status=400)
    
    body = request.get_json() or {}
    if not all(k in body for k in ("description", "start")):
        return response(False, message="Missing required fields: description, start", status=400)
    
    cp = {
        "_id": ObjectId(),
        "description": body["description"],
        "start": body["start"],
        "stop": body.get("stop")
    }
    
    patients.update_one({"_id": ObjectId(pid)}, {"$push": {"careplans": cp}})
    return response(True, message="Careplan added successfully", data={"id": str(cp["_id"])}, status=201)


@careplans_bp.route("/<string:pid>/careplans/<string:cid>", methods=["PUT"])
@jwt_required
@admin_required
def update_careplan(pid, cid):
    """Update careplan details (supports partial updates, admin only)."""
    if not (is_valid_objectid(pid) and is_valid_objectid(cid)):
        return response(False, message="Invalid ID format", status=400)
    
    body = request.get_json() or {}
    update_fields = {
        f"careplans.$.{k}": v
        for k, v in body.items()
        if k in ("description", "start", "stop")
    }

    if not update_fields:
        return response(False, message="No valid fields to update", status=400)

    owner_check = patients.find_one({
        "_id": ObjectId(pid),
        "careplans._id": ObjectId(cid)
    })
    if not owner_check:
        return response(False, message="Careplan not found for this patient", status=404)

    result = patients.update_one(
        {"_id": ObjectId(pid), "careplans._id": ObjectId(cid)},
        {"$set": update_fields}
    )

    if result.modified_count == 0:
        return response(False, message="Careplan not updated (no changes detected)", status=400)

    return response(True, message="Careplan updated successfully", data={"updated_fields": list(body.keys())})


@careplans_bp.route("/<string:pid>/careplans/<string:cid>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_careplan(pid, cid):
    """Delete careplan (admin only)."""
    if not (is_valid_objectid(pid) and is_valid_objectid(cid)):
        return response(False, message="Invalid ID format", status=400)
    
    result = patients.update_one(
        {"_id": ObjectId(pid)},
        {"$pull": {"careplans": {"_id": ObjectId(cid)}}}
    )

    if result.modified_count == 0:
        return response(False, message="Careplan not found for this patient", status=404)

    return response(True, message="Careplan deleted successfully")
