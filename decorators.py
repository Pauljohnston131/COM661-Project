from flask import request, jsonify, make_response
from functools import wraps
import jwt
import globals

blacklist = globals.db['blacklist']

def jwt_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return make_response(jsonify({'error': 'Token missing'}), 401)
        if blacklist.find_one({"token": token}):
            return make_response(jsonify({'error': 'Token blacklisted'}), 401)
        try:
            jwt.decode(token, globals.secret_key, algorithms="HS256")
        except jwt.ExpiredSignatureError:
            return make_response(jsonify({'error': 'Token expired'}), 401)
        except Exception:
            return make_response(jsonify({'error': 'Token invalid'}), 401)
        return func(*args, **kwargs)
    return wrapper

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('x-access-token')
        data = jwt.decode(token, globals.secret_key, algorithms="HS256")
        if data.get("admin"):
            return func(*args, **kwargs)
        return make_response(jsonify({'error': 'Admin access required'}), 401)
    return wrapper
