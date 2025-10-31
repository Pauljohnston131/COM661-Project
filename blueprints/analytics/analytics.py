from flask import Blueprint, jsonify, request
from decorators import jwt_required
import globals
from bson import ObjectId

analytics_bp = Blueprint('analytics_bp', __name__, url_prefix='/api/v1.0')
patients = globals.db["patients"]

@analytics_bp.route("/search", methods=["GET"])
@jwt_required
def search_patients():
    """Search patients by name or condition."""
    q = request.args.get("q", "")
    
    results = patients.find({
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"condition": {"$regex": q, "$options": "i"}}
        ]
    })

    data = []
    for p in results:
        p["_id"] = str(p["_id"])

        # Convert embedded ObjectIDs
        for field in ["appointments", "prescriptions", "careplans"]:
            if field in p:
                for sub in p[field]:
                    if isinstance(sub.get("_id"), ObjectId):
                        sub["_id"] = str(sub["_id"])

        data.append(p)

    return jsonify({"results": data, "count": len(data)})

@analytics_bp.route("/stats/appointments", methods=["GET"])
@jwt_required
def appointment_stats():
    """Count appointments per doctor (optional year filter)."""
    year = request.args.get("year")
    pipeline = [{"$unwind": "$appointments"}]
    if year:
        pipeline.append({"$match": {"appointments.date": {"$regex": year}}})
    pipeline += [
        {"$group": {"_id": "$appointments.doctor", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    return jsonify(list(patients.aggregate(pipeline)))

@analytics_bp.route("/stats/prescriptions", methods=["GET"])
@jwt_required
def prescription_stats():
    """Count prescriptions by medication name (optional status filter)."""
    status = request.args.get("status")
    pipeline = [{"$unwind": "$prescriptions"}]
    if status:
        pipeline.append({"$match": {"prescriptions.status": status}})
    pipeline += [
        {"$group": {"_id": "$prescriptions.name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    return jsonify(list(patients.aggregate(pipeline)))

@analytics_bp.route("/stats/careplans", methods=["GET"])
@jwt_required
def careplan_stats():
    """Count careplans by description (optional year filter)."""
    year = request.args.get("year")
    pipeline = [{"$unwind": "$careplans"}]
    if year:
        pipeline.append({"$match": {"careplans.start": {"$regex": year}}})
    pipeline += [
        {"$group": {"_id": "$careplans.description", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    return jsonify(list(patients.aggregate(pipeline)))
