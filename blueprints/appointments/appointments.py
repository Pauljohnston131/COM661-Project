from flask import Blueprint, jsonify, request
from bson import ObjectId
import re, globals
from decorators import jwt_required, admin_required

appointments_bp = Blueprint('appointments_bp', __name__, url_prefix='/api/v1.0/patients')
patients = globals.db["patients"]

def is_valid_objectid(id):
    return bool(re.fullmatch(r"[0-9a-fA-F]{24}", id))

@appointments_bp.route("/<string:pid>", methods=["POST"])
@jwt_required
@admin_required
def add_appointment(pid):
    """Add appointment to patient (admin only)."""
    if not is_valid_objectid(pid):
        return jsonify({"error": "Invalid patient ID"}), 400

    patient = patients.find_one({"_id": ObjectId(pid)})
    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    body = request.get_json() or request.form
    required = ("doctor", "date", "notes", "status")
    if not all(k in body for k in required):
        return jsonify({"error": "Missing appointment data"}), 400

    appointment = {
        "_id": ObjectId(),
        "doctor": body["doctor"],
        "date": body["date"],
        "notes": body["notes"],
        "status": body["status"]
    }

    patients.update_one({"_id": ObjectId(pid)}, {"$push": {"appointments": appointment}})
    return jsonify({"message": "Appointment added", "appointment_id": str(appointment["_id"])}), 201

@appointments_bp.route("/<string:pid>/<string:aid>", methods=["PUT"])
@jwt_required
@admin_required
def update_appointment(pid, aid):
    """Update appointment fields (admin only)."""
    if not (is_valid_objectid(pid) and is_valid_objectid(aid)):
        return jsonify({"error": "Invalid ID"}), 400

    body = request.get_json() or {}
    update_fields = {f"appointments.$.{k}": v for k, v in body.items() if k in ("doctor", "date", "notes", "status")}

    if not update_fields:
        return jsonify({"error": "No valid fields to update"}), 400

    result = patients.update_one(
        {"_id": ObjectId(pid), "appointments._id": ObjectId(aid)},
        {"$set": update_fields}
    )

    if result.modified_count == 0:
        return jsonify({"error": "Appointment not found"}), 404
    return jsonify({"message": "Appointment updated"})

@appointments_bp.route("/<string:pid>/<string:aid>", methods=["GET"])
@jwt_required
def get_appointment(pid, aid):
    """Get appointment details."""
    if not (is_valid_objectid(pid) and is_valid_objectid(aid)):
        return jsonify({"error": "Invalid ID"}), 400

    patient = patients.find_one(
        {"_id": ObjectId(pid), "appointments._id": ObjectId(aid)},
        {"appointments.$": 1, "_id": 0}
    )
    if not patient:
        return jsonify({"error": "Appointment not found"}), 404
    appt = patient["appointments"][0]
    appt["_id"] = str(appt["_id"])
    return jsonify(appt)

@appointments_bp.route("/<string:pid>/<string:aid>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_appointment(pid, aid):
    """Delete appointment (admin only)."""
    if not (is_valid_objectid(pid) and is_valid_objectid(aid)):
        return jsonify({"error": "Invalid ID"}), 400
    result = patients.update_one(
        {"_id": ObjectId(pid)},
        {"$pull": {"appointments": {"_id": ObjectId(aid)}}}
    )
    if result.modified_count == 0:
        return jsonify({"error": "Appointment not found"}), 404
    return jsonify({"message": "Appointment deleted"})
