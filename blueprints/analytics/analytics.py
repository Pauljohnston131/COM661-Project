from flask import Blueprint, jsonify, request
from decorators import jwt_required
from bson import ObjectId
import globals

analytics_bp = Blueprint("analytics_bp", __name__, url_prefix="/api/v1.0")
patients = globals.db["patients"]

@analytics_bp.route("/search", methods=["GET"])
@jwt_required
def search_patients():
    """Search patients by name or condition (case-insensitive)."""
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "Missing search query"}), 400

    results = patients.find(
        {
            "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"condition": {"$regex": q, "$options": "i"}},
            ]
        }
    )

    data = []
    for p in results:
        p["_id"] = str(p["_id"])
        
        for field in ["appointments", "prescriptions", "careplans"]:
            if field in p:
                for sub in p[field]:
                    if isinstance(sub.get("_id"), ObjectId):
                        sub["_id"] = str(sub["_id"])
        data.append(p)

    return jsonify({"query": q, "count": len(data), "results": data})


@analytics_bp.route("/stats/appointments", methods=["GET"])
@jwt_required
def appointment_stats():
    """
    Count appointments per doctor with optional filters:
    - year=YYYY
    - limit=N (default 10)
    """
    year = request.args.get("year")
    limit = int(request.args.get("limit", 10))

    pipeline = [{"$unwind": "$appointments"}]
    if year:
        pipeline.append({"$match": {"appointments.date": {"$regex": year}}})

    pipeline += [
        {"$group": {"_id": "$appointments.doctor", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
        {"$project": {"doctor": "$_id", "count": 1, "_id": 0}},
    ]

    stats = list(patients.aggregate(pipeline))
    return jsonify({"year": year or "all", "results": stats})

@analytics_bp.route("/stats/prescriptions", methods=["GET"])
@jwt_required
def prescription_stats():
    """
    Count prescriptions by medication name.
    Optional query params:
    - status=active/completed
    - limit=N
    """
    status = request.args.get("status")
    limit = int(request.args.get("limit", 10))

    pipeline = [{"$unwind": "$prescriptions"}]
    if status:
        pipeline.append({"$match": {"prescriptions.status": status}})

    pipeline += [
        {"$group": {"_id": "$prescriptions.name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
        {"$project": {"medication": "$_id", "count": 1, "_id": 0}},
    ]

    stats = list(patients.aggregate(pipeline))
    return jsonify({"status": status or "all", "results": stats})


@analytics_bp.route("/stats/careplans", methods=["GET"])
@jwt_required
def careplan_stats():
    """
    Count careplans by description (optional year and limit).
    """
    year = request.args.get("year")
    limit = int(request.args.get("limit", 10))

    pipeline = [{"$unwind": "$careplans"}]
    if year:
        pipeline.append({"$match": {"careplans.start": {"$regex": year}}})

    pipeline += [
        {"$group": {"_id": "$careplans.description", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
        {"$project": {"careplan": "$_id", "count": 1, "_id": 0}},
    ]

    stats = list(patients.aggregate(pipeline))
    return jsonify({"year": year or "all", "results": stats})


@analytics_bp.route("/stats/overview", methods=["GET"])
@jwt_required
def overview_stats():
    """
    Provides a combined analytics overview using MongoDB $facet.
    Returns:
      - top_doctors
      - top_medications
      - active_careplans
    """
    limit = int(request.args.get("limit", 5))

    pipeline = [
        {
            "$facet": {
                "top_doctors": [
                    {"$unwind": "$appointments"},
                    {"$group": {"_id": "$appointments.doctor", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": limit},
                    {"$project": {"doctor": "$_id", "count": 1, "_id": 0}},
                ],
                "top_medications": [
                    {"$unwind": "$prescriptions"},
                    {"$group": {"_id": "$prescriptions.name", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": limit},
                    {"$project": {"medication": "$_id", "count": 1, "_id": 0}},
                ],
                "active_careplans": [
                    {"$unwind": "$careplans"},
                    {
                        "$match": {
                            "$or": [
                                {"careplans.stop": "Unknown"},
                                {"careplans.stop": {"$exists": False}},
                            ]
                        }
                    },
                    {"$group": {"_id": "$careplans.description", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}},
                    {"$limit": limit},
                    {"$project": {"careplan": "$_id", "count": 1, "_id": 0}},
                ],
            }
        }
    ]

    stats = list(patients.aggregate(pipeline))
    return jsonify(stats[0] if stats else {})
