# ----------------------------------------------------------
# Authentication Blueprint – JWT-based login/logout/verify
# Author: Paul Johnston (B00888517)
# ----------------------------------------------------------

from flask import Blueprint, request
import jwt, bcrypt, datetime
import globals
from decorators import jwt_required
from utils import response  # ✅ unified response helper

# ----------------------------------------------------------
# Blueprint Setup
# ----------------------------------------------------------
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/v1.0/auth')
users = globals.db['users']
blacklist = globals.db['blacklist']


# ----------------------------------------------------------
# LOGIN
# ----------------------------------------------------------
@auth_bp.route('/login', methods=['GET'])
def login():
    """Authenticate user using Basic Auth and issue a JWT token."""
    auth = request.authorization
    if not auth:
        return response(False, message='Authentication required', status=401)

    user = users.find_one({'username': auth.username})
    if not user or not bcrypt.checkpw(auth.password.encode('utf-8'), user['password']):
        return response(False, message='Invalid credentials', status=401)

    token = jwt.encode({
        'user': auth.username,
        'admin': user.get('admin', False),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=45)
    }, globals.secret_key, algorithm="HS256")

    return response(True, data={'token': token}, message='Login successful')


# ----------------------------------------------------------
# LOGOUT
# ----------------------------------------------------------
@auth_bp.route('/logout', methods=['GET'])
@jwt_required
def logout():
    """Logout current user and blacklist the token."""
    token = request.headers.get('x-access-token')
    if token:
        blacklist.insert_one({"token": token})
    return response(True, message='Logged out successfully')


# ----------------------------------------------------------
# VERIFY TOKEN
# ----------------------------------------------------------
@auth_bp.route('/verify', methods=['GET'])
@jwt_required
def verify_token():
    """Check if the current JWT token is valid."""
    return response(True, message='Token is valid')


# ----------------------------------------------------------
# Default Admin User Seeder
# ----------------------------------------------------------
def create_default_user():
    """Ensure a default admin user exists."""
    if users.find_one({'username': 'admin'}) is None:
        hashed_pw = bcrypt.hashpw(b'admin123', bcrypt.gensalt())
        users.insert_one({'username': 'admin', 'password': hashed_pw, 'admin': True})
        print("Default admin user created: admin/admin123")

create_default_user()
