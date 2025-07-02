from flask import Blueprint, request, jsonify, current_app, url_for
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User, UserType
from functools import wraps
import re

auth_bp = Blueprint('auth', __name__)

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    # At least 8 characters, one uppercase, one lowercase, one digit
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

def ops_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type != UserType.OPS:
            return jsonify({'error': 'Access denied. Ops role required.'}), 403
        return f(*args, **kwargs)
    return decorated_function

def client_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.user_type != UserType.CLIENT or not user.is_verified:
            return jsonify({'error': 'Access denied. Verified client role required.'}), 403
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'user_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        user_type = data['user_type'].lower()
        
        # Validate input
        if not username or len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters long'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        if not validate_password(password):
            return jsonify({'error': 'Password must be at least 8 characters with uppercase, lowercase, and digit'}), 400
        
        if user_type not in ['ops', 'client']:
            return jsonify({'error': 'User type must be either "ops" or "client"'}), 400
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 409
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 409
        
        # Create user
        user = User(
            username=username,
            email=email,
            user_type=UserType.OPS if user_type == 'ops' else UserType.CLIENT
        )
        user.set_password(password)
        
        # For client users, generate verification token
        if user.user_type == UserType.CLIENT:
            verification_token = user.generate_verification_token()
            verification_link = url_for('auth.verify_email', token=verification_token, _external=True)
        else:
            # Ops users are auto-verified
            user.is_verified = True
            verification_link = None
        
        db.session.add(user)
        db.session.commit()
        
        response_data = {
            'message': 'User created successfully',
            'user': user.to_dict()
        }
        
        if verification_link:
            response_data['verification_link'] = verification_link
            response_data['message'] += '. Please verify your email to activate your account.'
        
        return jsonify(response_data), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    try:
        user = User.query.filter_by(verification_token=token).first()
        
        if not user:
            return jsonify({'error': 'Invalid verification token'}), 400
        
        if user.is_verified:
            return jsonify({'message': 'Email already verified'}), 200
        
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        
        return jsonify({'message': 'Email verified successfully. You can now login.'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username and password are required'}), 400
        
        username = data['username'].strip()
        password = data['password']
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check if client user is verified
        if user.user_type == UserType.CLIENT and not user.is_verified:
            return jsonify({'error': 'Please verify your email before logging in'}), 401
        
        # Create access token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500