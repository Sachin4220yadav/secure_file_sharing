from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from models import db, bcrypt
from routes.auth import auth_bp
from routes.files import files_bp
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt = JWTManager(app)
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(files_bp, url_prefix='/api')
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Method not allowed'}), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(413)
    def file_too_large(error):
        return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Invalid token'}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Authorization token is required'}), 401
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'message': 'File sharing API is running',
            'version': '1.0.0'
        })
    
    # API info endpoint
    @app.route('/api')
    def api_info():
        return jsonify({
            'message': 'File Sharing API',
            'version': '1.0.0',
            'endpoints': {
                'auth': {
                    'signup': 'POST /api/auth/signup',
                    'login': 'POST /api/auth/login',
                    'verify_email': 'GET /api/auth/verify-email/<token>',
                    'profile': 'GET /api/auth/profile'
                },
                'files': {
                    'upload': 'POST /api/upload (Ops only)',
                    'list_files': 'GET /api/files (Client only)',
                    'generate_download_link': 'POST /api/files/<id>/download-link (Client only)',
                    'download': 'GET /api/download/<token>',
                    'file_details': 'GET /api/files/<id>',
                    'my_uploads': 'GET /api/my-uploads (Ops only)'
                }
            }
        })
    
    return app

# Initialize database
def init_db(app):
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    app = create_app()
    
    # Initialize database
    init_db(app)
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"Starting Flask application on port {port}")
    print("API Documentation available at: http://localhost:5000/api")
    
    app.run(host='0.0.0.0', port=port, debug=debug)