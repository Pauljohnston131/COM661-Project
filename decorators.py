from flask import request, make_response
from functools import wraps
import jwt
import globals
from utils import response 

blacklist = globals.db['blacklist']

def jwt_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return response(False, message='Token missing', status=401)
        if blacklist.find_one({"token": token}):
            return response(False, message='Token blacklisted', status=401)
        try:
            jwt.decode(token, globals.secret_key, algorithms="HS256")
        except jwt.ExpiredSignatureError:
            return response(False, message='Token expired', status=401)
        except Exception:
            return response(False, message='Token invalid', status=401)
        return func(*args, **kwargs)
    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return response(False, message='Token missing', status=401)

        try:
            data = jwt.decode(token, globals.secret_key, algorithms="HS256")
        except jwt.ExpiredSignatureError:
            return response(False, message='Token expired', status=401)
        except jwt.InvalidTokenError:
            return response(False, message='Token invalid', status=401)
        except Exception:
            return response(False, message='Token invalid or missing', status=401)

        if not data.get("admin"):
            return response(False, message='Admin access required', status=403)

        return func(*args, **kwargs)
    return wrapper
