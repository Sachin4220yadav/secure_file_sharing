from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

db = SQLAlchemy()
jwt = JWTManager()

def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
