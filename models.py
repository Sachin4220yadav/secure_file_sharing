from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from sqlalchemy import Enum
import enum
import uuid

db = SQLAlchemy()
bcrypt = Bcrypt()

class UserType(enum.Enum):
    OPS = "ops"
    CLIENT = "client"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    user_type = db.Column(Enum(UserType), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    uploaded_files = db.relationship('File', backref='uploader', lazy=True)
    download_links = db.relationship('DownloadLink', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def generate_verification_token(self):
        self.verification_token = str(uuid.uuid4())
        return self.verification_token
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'user_type': self.user_type.value,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat()
        }

class File(db.Model):
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    content_type = db.Column(db.String(100), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Key
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    download_links = db.relationship('DownloadLink', backref='file', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.original_filename,
            'file_size': self.file_size,
            'content_type': self.content_type,
            'upload_date': self.upload_date.isoformat(),
            'uploader': self.uploader.username
        }

class DownloadLink(db.Model):
    __tablename__ = 'download_links'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False)
    
    def __init__(self, user_id, file_id, expiry_minutes=10):
        self.user_id = user_id
        self.file_id = file_id
        self.token = str(uuid.uuid4())
        self.expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        return not self.is_expired() and not self.is_used
    
    def to_dict(self):
        return {
            'token': self.token,
            'expires_at': self.expires_at.isoformat(),
            'is_expired': self.is_expired(),
            'file_id': self.file_id
        }