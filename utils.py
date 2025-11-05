from flask import jsonify

def response(success=True, data=None, message=None, status=200):
    
    payload = {"success": success}
    if message:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status