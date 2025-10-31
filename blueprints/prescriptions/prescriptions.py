from flask import Blueprint, jsonify, request
from bson import ObjectId
from decorators import jwt_required, admin_required
import globals, re

prescriptions_bp = Blueprint('prescriptions_bp', __name__, url_prefix='/api/v1.0/patients')
patients = globals.db["patients"]

def is_valid_objectid(id):
    return bool(re.fullmatch(r"[0-9a-fA-F]{24}", id))

@prescriptions_bp.route("/<string:pid>/prescriptions", methods=["GET"])
@jwt_required
def list_prescriptions(pid):
    """List all prescriptions for a patient."""
    if not is_valid_objectid(pid):
        return jsonify({"error": "Invalid ID"}), 400
    doc = patients.find_one({"_id": ObjectId(pid)}, {"prescriptions": 1, "_id": 0})
    if not doc:
        return jsonify({"error": "Patient not found"}), 404
    for p in doc.get("prescriptions", []):
        if isinstance(p.get("_id"), ObjectId):
            p["_id"] = str(p["_id"])
    return jsonify(doc)

@prescriptions_bp.route("/<string:pid>/prescriptions", methods=["POST"])
@jwt_required
def add_prescription(pid):
    """Add prescription to patient."""
    if not is_valid_objectid(pid):
        return jsonify({"error": "Invalid ID"}), 400
    body = request.get_json() or {}
    if not all(k in body for k in ("name", "start")):
        return jsonify({"error": "Missing fields"}), 400

    presc = {
        "_id": ObjectId(),
        "name": body["name"],
        "start": body["start"],
        "stop": body.get("stop"),
        "status": body.get("status", "active")
    }

    patients.update_one({"_id": ObjectId(pid)}, {"$push": {"prescriptions": presc}})
    return jsonify({"message": "Prescription added", "id": str(presc["_id"])}), 201

@prescriptions_bp.route("/<string:pid>/prescriptions/<string:rid>", methods=["PUT"])
@jwt_required
@admin_required
def update_prescription(pid, rid):
    """Update prescription details (admin only)."""
    if not (is_valid_objectid(pid) and is_valid_objectid(rid)):
        return jsonify({"error": "Invalid ID"}), 400
    body = request.get_json() or {}
    update_fields = {f"prescriptions.$.{k}": v for k, v in body.items() if k in ("name", "start", "stop", "status")}
    if not update_fields:
        return jsonify({"error": "No valid fields to update"}), 400

    result = patients.update_one(
        {"_id": ObjectId(pid), "prescriptions._id": ObjectId(rid)},
        {"$set": update_fields}
    )
    if result.modified_count == 0:
        return jsonify({"error": "Prescription not found"}), 404
    return jsonify({"message": "Prescription updated"})

@prescriptions_bp.route("/<string:pid>/prescriptions/<string:rid>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_prescription(pid, rid):
    """Delete prescription (admin only)."""
    if not (is_valid_objectid(pid) and is_valid_objectid(rid)):
        return jsonify({"error": "Invalid ID"}), 400
    result = patients.update_one(
        {"_id": ObjectId(pid)},
        {"$pull": {"prescriptions": {"_id": ObjectId(rid)}}}
    )
    if result.modified_count == 0:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"message": "Prescription deleted"})
