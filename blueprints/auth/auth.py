from flask import Blueprint, jsonify, request, make_response
import jwt, bcrypt, datetime
import globals
from decorators import jwt_required

# Blueprint now defines the prefix once
auth_bp = Blueprint('auth_bp', __name__, url_prefix='/api/v1.0/auth')

users = globals.db['users']
blacklist = globals.db['blacklist']

@auth_bp.route('/login', methods=['GET'])
def login():
    """Authenticate user using Basic Auth and issue a JWT token."""
    auth = request.authorization
    if not auth:
        return make_response(jsonify({'error': 'Authentication required'}), 401)

    user = users.find_one({'username': auth.username})
    if not user or not bcrypt.checkpw(auth.password.encode('utf-8'), user['password']):
        return make_response(jsonify({'error': 'Invalid credentials'}), 401)

    token = jwt.encode({
        'user': auth.username,
        'admin': user.get('admin', False),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=45)
    }, globals.secret_key, algorithm="HS256")

    return jsonify({'token': token})

@auth_bp.route('/logout', methods=['GET'])
@jwt_required
def logout():
    """Logout current user and blacklist the token."""
    token = request.headers.get('x-access-token')
    if token:
        blacklist.insert_one({"token": token})
    return jsonify({'message': 'Logged out successfully'})

@auth_bp.route('/verify', methods=['GET'])
@jwt_required
def verify_token():
    """Check if the current JWT token is valid."""
    return jsonify({'message': 'Token is valid'})

def create_default_user():
    """Ensure a default admin user exists."""
    if users.find_one({'username': 'admin'}) is None:
        hashed_pw = bcrypt.hashpw(b'admin123', bcrypt.gensalt())
        users.insert_one({'username': 'admin', 'password': hashed_pw, 'admin': True})
        print("Default admin user created: admin/admin123")

create_default_user()
