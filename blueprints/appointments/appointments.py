from flask import Blueprint, request
from bson import ObjectId
import re, globals
from decorators import jwt_required, admin_required
from utils import response  

appointments_bp = Blueprint('appointments_bp', __name__, url_prefix='/api/v1.0/patients')
patients = globals.db["patients"]

def is_valid_objectid(id):
    return bool(re.fullmatch(r"[0-9a-fA-F]{24}", id))


@appointments_bp.route("/<string:pid>", methods=["POST"])
@jwt_required
@admin_required
def add_appointment(pid):
    """Add appointment to a patient (admin only)."""
    if not is_valid_objectid(pid):
        return response(False, message="Invalid patient ID", status=400)

    patient = patients.find_one({"_id": ObjectId(pid)})
    if not patient:
        return response(False, message="Patient not found", status=404)

    body = request.get_json() or request.form
    required = ("doctor", "date", "notes", "status")
    if not all(k in body for k in required):
        return response(False, message="Missing appointment data", status=400)

    appointment = {
        "_id": ObjectId(),
        "doctor": body["doctor"],
        "date": body["date"],
        "notes": body["notes"],
        "status": body["status"]
    }

    patients.update_one({"_id": ObjectId(pid)}, {"$push": {"appointments": appointment}})
    return response(True, message="Appointment added successfully", data={"appointment_id": str(appointment["_id"])}, status=201)

@appointments_bp.route("/<string:pid>/<string:aid>", methods=["PUT"])
@jwt_required
@admin_required
def update_appointment(pid, aid):
    """Update appointment details (supports partial updates, admin only)."""
    if not (is_valid_objectid(pid) and is_valid_objectid(aid)):
        return response(False, message="Invalid ID format", status=400)

    body = request.get_json() or {}
    update_fields = {
        f"appointments.$.{k}": v 
        for k, v in body.items() 
        if k in ("doctor", "date", "notes", "status")
    }
    if not update_fields:
        return response(False, message="No valid fields to update", status=400)

    owner_check = patients.find_one({
        "_id": ObjectId(pid),
        "appointments._id": ObjectId(aid)
    })
    if not owner_check:
        return response(False, message="Appointment not found for this patient", status=404)

    result = patients.update_one(
        {"_id": ObjectId(pid), "appointments._id": ObjectId(aid)},
        {"$set": update_fields}
    )

    if result.modified_count == 0:
        return response(False, message="Appointment not updated (no changes detected)", status=400)

    return response(True, message="Appointment updated successfully", data={"updated_fields": list(body.keys())})


@appointments_bp.route("/<string:pid>/<string:aid>", methods=["GET"])
@jwt_required
def get_appointment(pid, aid):
    """Get details of a single appointment."""
    if not (is_valid_objectid(pid) and is_valid_objectid(aid)):
        return response(False, message="Invalid ID format", status=400)

    patient = patients.find_one(
        {"_id": ObjectId(pid), "appointments._id": ObjectId(aid)},
        {"appointments.$": 1, "_id": 0}
    )
    if not patient:
        return response(False, message="Appointment not found for this patient", status=404)

    appt = patient["appointments"][0]
    appt["_id"] = str(appt["_id"])
    return response(True, data=appt, message="Appointment retrieved successfully")


@appointments_bp.route("/<string:pid>/<string:aid>", methods=["DELETE"])
@jwt_required
@admin_required
def delete_appointment(pid, aid):
    """Delete appointment (admin only)."""
    if not (is_valid_objectid(pid) and is_valid_objectid(aid)):
        return response(False, message="Invalid ID format", status=400)

    result = patients.update_one(
        {"_id": ObjectId(pid)},
        {"$pull": {"appointments": {"_id": ObjectId(aid)}}}
    )

    if result.modified_count == 0:
        return response(False, message="Appointment not found for this patient", status=404)

    return response(True, message="Appointment deleted successfully")
