from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from itsdangerous import URLSafeTimedSerializer
import os

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)
jwt = JWTManager(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

from models import User, File

# Create DB tables
@app.before_first_request
def create_tables():
    db.create_all()

# Signup (client)
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if User.query.filter_by(email=email).first():
        return jsonify({'msg': 'User already exists'}), 400
    
    user = User(email=email, role='client')
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = serializer.dumps(email, salt='email-verify')
    verify_link = f"http://127.0.0.1:5000/verify/{token}"
    print(f"[MOCK EMAIL] Verify link: {verify_link}")

    return jsonify({'msg': 'User created. Verify your email.', 'verify_link': verify_link})

# Email verification
@app.route('/verify/<token>', methods=['GET'])
def verify(token):
    try:
        email = serializer.loads(token, salt='email-verify', max_age=3600)
    except:
        return jsonify({'msg': 'Invalid or expired link'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'msg': 'User not found'}), 404
    
    user.is_verified = True
    db.session.commit()
    return jsonify({'msg': 'Email verified'})

# Login (both ops + client)
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({'msg': 'Bad credentials'}), 401
    
    if user.role == 'client' and not user.is_verified:
        return jsonify({'msg': 'Email not verified'}), 403
    
    token = create_access_token(identity={'email': user.email, 'role': user.role})
    return jsonify({'token': token})

# Upload (ops only)
@app.route('/upload', methods=['POST'])
@jwt_required()
def upload():
    current = get_jwt_identity()
    if current['role'] != 'ops':
        return jsonify({'msg': 'Only ops can upload'}), 403

    if 'file' not in request.files:
        return jsonify({'msg': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'msg': 'No file selected'}), 400
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in ['pptx', 'docx', 'xlsx']:
        return jsonify({'msg': 'Invalid file type'}), 400
    
    path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(path)

    user = User.query.filter_by(email=current['email']).first()
    db.session.add(File(filename=file.filename, uploaded_by=user.id))
    db.session.commit()

    return jsonify({'msg': 'File uploaded'})

# List files (client only)
@app.route('/files', methods=['GET'])
@jwt_required()
def list_files():
    current = get_jwt_identity()
    if current['role'] != 'client':
        return jsonify({'msg': 'Only client can view files'}), 403
    
    files = File.query.all()
    return jsonify([{'id': f.id, 'filename': f.filename} for f in files])

# Generate download link
@app.route('/download-link/<int:file_id>', methods=['GET'])
@jwt_required()
def download_link(file_id):
    current = get_jwt_identity()
    if current['role'] != 'client':
        return jsonify({'msg': 'Only client can request download link'}), 403
    
    token = serializer.dumps({'file_id': file_id, 'email': current['email']}, salt='download')
    link = f"http://127.0.0.1:5000/download/{token}"
    return jsonify({'download_link': link})

# Download file
@app.route('/download/<token>', methods=['GET'])
def download(token):
    try:
        data = serializer.loads(token, salt='download', max_age=600)
    except:
        return jsonify({'msg': 'Invalid or expired download link'}), 400
    
    file = File.query.get(data['file_id'])
    if not file:
        return jsonify({'msg': 'File not found'}), 404
    
    path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
