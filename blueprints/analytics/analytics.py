from flask import Blueprint, jsonify, request
from decorators import jwt_required
from bson import ObjectId
import globals

analytics_bp = Blueprint("analytics_bp", __name__, url_prefix="/api/v1.0")
patients = globals.db["patients"]

def parse_pagination():
    """Helper to extract skip/limit from query params."""
    try:
        skip = max(0, int(request.args.get("skip", 0)))
        limit = max(1, min(50, int(request.args.get("limit", 10))))
    except ValueError:
        skip, limit = 0, 10
    return skip, limit

@analytics_bp.route("/search", methods=["GET"])
@jwt_required
def search_patients():
    """Search patients by name or condition (case-insensitive)."""
    q = request.args.get("q", "")
    gender = request.args.get("gender")  # optional demographic filter
    skip, limit = parse_pagination()

    if not q:
        return jsonify({"error": "Missing search query"}), 400

    filters = {
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"condition": {"$regex": q, "$options": "i"}},
        ]
    }
    if gender:
        filters["gender"] = {"$regex": gender, "$options": "i"}

    cursor = patients.find(filters).skip(skip).limit(limit)
    data = []
    for p in cursor:
        p["_id"] = str(p["_id"])
        for field in ["appointments", "prescriptions", "careplans"]:
            if field in p:
                for sub in p[field]:
                    if isinstance(sub.get("_id"), ObjectId):
                        sub["_id"] = str(sub["_id"])
        data.append(p)

    total = patients.count_documents(filters)
    return jsonify({
        "query": q,
        "filters": {"gender": gender or "all"},
        "count": len(data),
        "total": total,
        "skip": skip,
        "limit": limit,
        "results": data
    })

@analytics_bp.route("/stats/appointments", methods=["GET"])
@jwt_required
def appointment_stats():
    """Count appointments per doctor with optional year/gender filters and pagination."""
    year = request.args.get("year")
    gender = request.args.get("gender")
    skip, limit = parse_pagination()

    match_stage = {}
    if year:
        match_stage["appointments.date"] = {"$regex": year}
    if gender:
        match_stage["gender"] = {"$regex": gender, "$options": "i"}

    pipeline = [{"$unwind": "$appointments"}]
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline += [
        {"$group": {"_id": "$appointments.doctor", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {"$project": {"doctor": "$_id", "count": 1, "_id": 0}},
    ]

    stats = list(patients.aggregate(pipeline))
    return jsonify({
        "filters": {"year": year or "all", "gender": gender or "all"},
        "skip": skip,
        "limit": limit,
        "results": stats
    })

@analytics_bp.route("/stats/prescriptions", methods=["GET"])
@jwt_required
def prescription_stats():
    """Count prescriptions by medication name with optional status/gender filters and pagination."""
    status = request.args.get("status")
    gender = request.args.get("gender")
    skip, limit = parse_pagination()

    pipeline = [{"$unwind": "$prescriptions"}]
    match_stage = {}
    if status:
        match_stage["prescriptions.status"] = status
    if gender:
        match_stage["gender"] = {"$regex": gender, "$options": "i"}
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline += [
        {"$group": {"_id": "$prescriptions.name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {"$project": {"medication": "$_id", "count": 1, "_id": 0}},
    ]

    stats = list(patients.aggregate(pipeline))
    return jsonify({
        "filters": {"status": status or "all", "gender": gender or "all"},
        "skip": skip,
        "limit": limit,
        "results": stats
    })

@analytics_bp.route("/stats/careplans", methods=["GET"])
@jwt_required
def careplan_stats():
    """Count careplans by description with optional year/gender filters and pagination."""
    year = request.args.get("year")
    gender = request.args.get("gender")
    skip, limit = parse_pagination()

    pipeline = [{"$unwind": "$careplans"}]
    match_stage = {}
    if year:
        match_stage["careplans.start"] = {"$regex": year}
    if gender:
        match_stage["gender"] = {"$regex": gender, "$options": "i"}
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline += [
        {"$group": {"_id": "$careplans.description", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {"$project": {"careplan": "$_id", "count": 1, "_id": 0}},
    ]

    stats = list(patients.aggregate(pipeline))
    return jsonify({
        "filters": {"year": year or "all", "gender": gender or "all"},
        "skip": skip,
        "limit": limit,
        "results": stats
    })

@analytics_bp.route("/stats/overview", methods=["GET"])
@jwt_required
def overview_stats():
    """Combined analytics overview with optional gender filter."""
    gender = request.args.get("gender")
    limit = int(request.args.get("limit", 5))

    match_stage = {"gender": {"$regex": gender, "$options": "i"}} if gender else {}

    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    pipeline.append({
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
    })

    stats = list(patients.aggregate(pipeline))
    return jsonify({
        "filters": {"gender": gender or "all"},
        "limit": limit,
        "results": stats[0] if stats else {}
    })
