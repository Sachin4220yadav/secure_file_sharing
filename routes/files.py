from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, File, DownloadLink, UserType
from routes.auth import ops_required, client_required
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

files_bp = Blueprint('files', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_file_extension(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def get_content_type(extension):
    content_types = {
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }
    return content_types.get(extension, 'application/octet-stream')

@files_bp.route('/upload', methods=['POST'])
@ops_required
def upload_file():
    try:
        current_user_id = get_jwt_identity()
        
        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Only pptx, docx, and xlsx files are permitted.'}), 400
        
        # Generate unique filename
        original_filename = file.filename
        file_extension = get_file_extension(original_filename)
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Ensure upload directory exists
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Create file record in database
        file_record = File(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            content_type=get_content_type(file_extension),
            uploader_id=current_user_id
        )
        
        db.session.add(file_record)
        db.session.commit()
        
        return jsonify({
            'message': 'File uploaded successfully',
            'file': file_record.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@files_bp.route('/files', methods=['GET'])
@client_required
def list_files():
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        per_page = min(per_page, 100)  # Limit to 100 files per page
        
        # Get files with pagination
        files_query = File.query.order_by(File.upload_date.desc())
        pagination = files_query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        files_list = [file.to_dict() for file in pagination.items]
        
        return jsonify({
            'files': files_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@files_bp.route('/files/<int:file_id>/download-link', methods=['POST'])
@client_required
def generate_download_link(file_id):
    try:
        current_user_id = get_jwt_identity()
        
        # Check if file exists
        file_record = File.query.get(file_id)
        if not file_record:
            return jsonify({'error': 'File not found'}), 404
        
        # Check if file actually exists on disk
        if not os.path.exists(file_record.file_path):
            return jsonify({'error': 'File not found on server'}), 404
        
        # Create download link
        expiry_minutes = current_app.config['DOWNLOAD_LINK_EXPIRY_MINUTES']
        download_link = DownloadLink(
            user_id=current_user_id,
            file_id=file_id,
            expiry_minutes=expiry_minutes
        )
        
        db.session.add(download_link)
        db.session.commit()
        
        return jsonify({
            'message': 'Download link generated successfully',
            'download_link': download_link.to_dict(),
            'download_url': f"/api/download/{download_link.token}"
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@files_bp.route('/download/<token>', methods=['GET'])
def download_file(token):
    try:
        # Find download link by token
        download_link = DownloadLink.query.filter_by(token=token).first()
        
        if not download_link:
            return jsonify({'error': 'Invalid download token'}), 404
        
        # Check if link is valid (not expired and not used)
        if not download_link.is_valid():
            if download_link.is_expired():
                return jsonify({'error': 'Download link has expired'}), 410
            else:
                return jsonify({'error': 'Download link has already been used'}), 410
        
        # Get the file
        file_record = download_link.file
        if not file_record:
            return jsonify({'error': 'File not found'}), 404
        
        # Check if file exists on disk
        if not os.path.exists(file_record.file_path):
            return jsonify({'error': 'File not found on server'}), 404
        
        # Mark link as used
        download_link.is_used = True
        db.session.commit()
        
        # Send file
        return send_file(
            file_record.file_path,
            as_attachment=True,
            download_name=file_record.original_filename,
            mimetype=file_record.content_type
        )
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

@files_bp.route('/files/<int:file_id>', methods=['GET'])
@jwt_required()
def get_file_details(file_id):
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if file exists
        file_record = File.query.get(file_id)
        if not file_record:
            return jsonify({'error': 'File not found'}), 404
        
        # Only allow access to file details for verified users
        if user.user_type == UserType.CLIENT and not user.is_verified:
            return jsonify({'error': 'Email verification required'}), 403
        
        return jsonify({
            'file': file_record.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@files_bp.route('/my-uploads', methods=['GET'])
@ops_required
def get_my_uploads():
    try:
        current_user_id = get_jwt_identity()
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        per_page = min(per_page, 100)
        
        # Get files uploaded by current user
        files_query = File.query.filter_by(uploader_id=current_user_id).order_by(File.upload_date.desc())
        pagination = files_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        files_list = [file.to_dict() for file in pagination.items]
        
        return jsonify({
            'files': files_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500