from flask import Blueprint, jsonify, request
from bson import ObjectId
from decorators import jwt_required, admin_required
import globals, re

careplans_bp = Blueprint('careplans_bp', __name__, url_prefix='/api/v1.0/patients')
patients = globals.db["patients"]

def is_valid_objectid(id):
    return bool(re.fullmatch(r"[0-9a-fA-F]{24}", id))

@careplans_bp.route("/<string:pid>", methods=["GET"])
@jwt_required
def list_careplans(pid):
    """List all careplans for a patient."""
    if not is_valid_objectid(pid):
        return jsonify({"error": "Invalid ID"}), 400
    doc = patients.find_one({"_id": ObjectId(pid)}, {"careplans": 1, "_id": 0})
    if not doc:
        return jsonify({"error": "Patient not found"}), 404
    for c in doc.get("careplans", []):
        if isinstance(c.get("_id"), ObjectId):
            c["_id"] = str(c["_id"])
    return jsonify(doc)

@careplans_bp.route("/<string:pid>", methods=["POST"])
@jwt_required
def add_careplan(pid):
    """Add careplan for a patient."""
    if not is_valid_objectid(pid):
        return jsonify({"error": "Invalid ID"}), 400
    body = request.get_json() or {}
    if not all(k in body for k in ("description", "start")):
        return jsonify({"error": "Missing fields"}), 400
    cp = {
        "_id": ObjectId(),
        "description": body["description"],
        "start": body["start"],
        "stop": body.get("stop")
    }
    patients.update_one({"_id": ObjectId(pid)}, {"$push": {"careplans": cp}})
    return jsonify({"message": "Careplan added", "id": str(cp["_id"])}), 201

@careplans_bp.route("/<string:pid>/<string:cid>", methods=["PUT"])
@jwt_required
@admin_required
def update_careplan(pid, cid):
    """Update careplan details (admin only)."""
    if not (is_valid_objectid(pid) and is_valid_objectid(cid)):
        return jsonify({"error": "Invalid ID"}), 400
    body = request.get_json() or {}
    update_fields = {f"careplans.$.{k}": v for k, v in body.items() if k in ("description", "start", "stop")}
    if not update_fields:
        return jsonify({"error": "No valid fields to update"}), 400

    result = patients.update_one(
        {"_id": ObjectId(pid), "careplans._id": ObjectId(cid)},
        {"$set": update_fields}
    )
    if result.modified_count == 0:
        return jsonify({"error": "Careplan not found"}), 404
    return jsonify({"message": "Careplan updated"})

@careplans_bp.route("/<string:pid>/<string:cid>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_careplan(pid, cid):
    """Delete careplan (admin only)."""
    if not (is_valid_objectid(pid) and is_valid_objectid(cid)):
        return jsonify({"error": "Invalid ID"}), 400
    result = patients.update_one(
        {"_id": ObjectId(pid)},
        {"$pull": {"careplans": {"_id": ObjectId(cid)}}}
    )
    if result.modified_count == 0:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"message": "Careplan deleted"})
