import os

class Config:
    SECRET_KEY = 'supersecretkey'  # In real use, replace with random secure key
    SQLALCHEMY_DATABASE_URI = 'sqlite:///file_sharing.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'jwtsecretkey'  # Replace with random secure key
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
