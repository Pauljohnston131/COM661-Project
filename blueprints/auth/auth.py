from flask import Blueprint, request
import jwt, bcrypt, datetime
import globals
from decorators import jwt_required
from utils import response  

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/v1.0/auth')
users = globals.db['users']
blacklist = globals.db['blacklist']

# get login
@auth_bp.route('/login', methods=['GET'])
def login():
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

# get logout
@auth_bp.route('/logout', methods=['GET'])
@jwt_required
def logout():
    token = request.headers.get('x-access-token')
    if token:
        blacklist.insert_one({"token": token})
    return response(True, message='Logged out successfully')

# get verify
@auth_bp.route('/verify', methods=['GET'])
@jwt_required
def verify_token():
    return response(True, message='Token is valid')

# helper: create default admin user
def create_default_user():
    if users.find_one({'username': 'admin'}) is None:
        hashed_pw = bcrypt.hashpw(b'admin123', bcrypt.gensalt())
        users.insert_one({'username': 'admin', 'password': hashed_pw, 'admin': True})
        print("Default admin user created: admin/admin123")

create_default_user()
