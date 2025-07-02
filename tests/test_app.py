import unittest
import json
import os
import tempfile
from io import BytesIO
from app import create_app
from models import db, User, File, DownloadLink, UserType
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    UPLOAD_FOLDER = tempfile.mkdtemp()
    WTF_CSRF_ENABLED = False

class FileShareTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Test data
        self.ops_user_data = {
            'username': 'ops_user',
            'email': 'ops@example.com',
            'password': 'OpsPassword123',
            'user_type': 'ops'
        }
        
        self.client_user_data = {
            'username': 'client_user',
            'email': 'client@example.com',
            'password': 'ClientPassword123',
            'user_type': 'client'
        }
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def create_test_file(self, filename='test.docx', content=b'test file content'):
        """Helper method to create a test file"""
        return (BytesIO(content), filename)
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_api_info(self):
        """Test API info endpoint"""
        response = self.client.get('/api')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('endpoints', data)
    
    def test_signup_ops_user(self):
        """Test ops user signup"""
        response = self.client.post('/api/auth/signup',
                                  data=json.dumps(self.ops_user_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['user']['user_type'], 'ops')
        self.assertTrue(data['user']['is_verified'])  # Ops users are auto-verified
    
    def test_signup_client_user(self):
        """Test client user signup"""
        response = self.client.post('/api/auth/signup',
                                  data=json.dumps(self.client_user_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['user']['user_type'], 'client')
        self.assertFalse(data['user']['is_verified'])  # Client users need verification
        self.assertIn('verification_link', data)
    
    def test_signup_validation(self):
        """Test signup input validation"""
        # Test missing fields
        response = self.client.post('/api/auth/signup',
                                  data=json.dumps({}),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Test invalid email
        invalid_data = self.client_user_data.copy()
        invalid_data['email'] = 'invalid-email'
        response = self.client.post('/api/auth/signup',
                                  data=json.dumps(invalid_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Test weak password
        weak_data = self.client_user_data.copy()
        weak_data['password'] = 'weak'
        response = self.client.post('/api/auth/signup',
                                  data=json.dumps(weak_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 400)
    
    def test_login_ops_user(self):
        """Test ops user login"""
        # First signup
        self.client.post('/api/auth/signup',
                        data=json.dumps(self.ops_user_data),
                        content_type='application/json')
        
        # Then login
        login_data = {
            'username': self.ops_user_data['username'],
            'password': self.ops_user_data['password']
        }
        response = self.client.post('/api/auth/login',
                                  data=json.dumps(login_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('access_token', data)
        self.assertEqual(data['user']['user_type'], 'ops')
    
    def test_login_client_user_unverified(self):
        """Test client user login without verification"""
        # First signup
        self.client.post('/api/auth/signup',
                        data=json.dumps(self.client_user_data),
                        content_type='application/json')
        
        # Try to login without verification
        login_data = {
            'username': self.client_user_data['username'],
            'password': self.client_user_data['password']
        }
        response = self.client.post('/api/auth/login',
                                  data=json.dumps(login_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('verify your email', data['error'])
    
    def test_email_verification(self):
        """Test email verification process"""
        # Signup client user
        response = self.client.post('/api/auth/signup',
                                  data=json.dumps(self.client_user_data),
                                  content_type='application/json')
        data = json.loads(response.data)
        verification_link = data['verification_link']
        
        # Extract token from verification link
        token = verification_link.split('/')[-1]
        
        # Verify email
        response = self.client.get(f'/api/auth/verify-email/{token}')
        self.assertEqual(response.status_code, 200)
        
        # Now login should work
        login_data = {
            'username': self.client_user_data['username'],
            'password': self.client_user_data['password']
        }
        response = self.client.post('/api/auth/login',
                                  data=json.dumps(login_data),
                                  content_type='application/json')
        self.assertEqual(response.status_code, 200)
    
    def test_file_upload_ops_user(self):
        """Test file upload by ops user"""
        # Setup ops user and get token
        self.client.post('/api/auth/signup',
                        data=json.dumps(self.ops_user_data),
                        content_type='application/json')
        
        login_response = self.client.post('/api/auth/login',
                                        data=json.dumps({
                                            'username': self.ops_user_data['username'],
                                            'password': self.ops_user_data['password']
                                        }),
                                        content_type='application/json')
        token = json.loads(login_response.data)['access_token']
        
        # Upload file
        data = {
            'file': self.create_test_file('test.docx')
        }
        response = self.client.post('/api/upload',
                                  data=data,
                                  headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.data)
        self.assertIn('file', response_data)
        self.assertEqual(response_data['file']['filename'], 'test.docx')
    
    def test_file_upload_invalid_type(self):
        """Test file upload with invalid file type"""
        # Setup ops user and get token
        self.client.post('/api/auth/signup',
                        data=json.dumps(self.ops_user_data),
                        content_type='application/json')
        
        login_response = self.client.post('/api/auth/login',
                                        data=json.dumps({
                                            'username': self.ops_user_data['username'],
                                            'password': self.ops_user_data['password']
                                        }),
                                        content_type='application/json')
        token = json.loads(login_response.data)['access_token']
        
        # Try to upload invalid file type
        data = {
            'file': self.create_test_file('test.txt')
        }
        response = self.client.post('/api/upload',
                                  data=data,
                                  headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('File type not allowed', response_data['error'])
    
    def test_list_files_client_user(self):
        """Test file listing by client user"""
        # Setup and verify client user
        self.client.post('/api/auth/signup',
                        data=json.dumps(self.client_user_data),
                        content_type='application/json')
        
        # Get verification token and verify
        user = User.query.filter_by(email=self.client_user_data['email']).first()
        self.client.get(f'/api/auth/verify-email/{user.verification_token}')
        
        # Login
        login_response = self.client.post('/api/auth/login',
                                        data=json.dumps({
                                            'username': self.client_user_data['username'],
                                            'password': self.client_user_data['password']
                                        }),
                                        content_type='application/json')
        token = json.loads(login_response.data)['access_token']
        
        # List files
        response = self.client.get('/api/files',
                                 headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('files', data)
        self.assertIn('pagination', data)
    
    def test_download_link_generation(self):
        """Test download link generation and usage"""
        # Setup ops user and upload file
        self.client.post('/api/auth/signup',
                        data=json.dumps(self.ops_user_data),
                        content_type='application/json')
        
        ops_login = self.client.post('/api/auth/login',
                                   data=json.dumps({
                                       'username': self.ops_user_data['username'],
                                       'password': self.ops_user_data['password']
                                   }),
                                   content_type='application/json')
        ops_token = json.loads(ops_login.data)['access_token']
        
        # Upload file
        upload_response = self.client.post('/api/upload',
                                         data={'file': self.create_test_file('test.docx')},
                                         headers={'Authorization': f'Bearer {ops_token}'})
        file_id = json.loads(upload_response.data)['file']['id']
        
        # Setup and verify client user
        self.client.post('/api/auth/signup',
                        data=json.dumps(self.client_user_data),
                        content_type='application/json')
        
        user = User.query.filter_by(email=self.client_user_data['email']).first()
        self.client.get(f'/api/auth/verify-email/{user.verification_token}')
        
        client_login = self.client.post('/api/auth/login',
                                      data=json.dumps({
                                          'username': self.client_user_data['username'],
                                          'password': self.client_user_data['password']
                                      }),
                                      content_type='application/json')
        client_token = json.loads(client_login.data)['access_token']
        
        # Generate download link
        response = self.client.post(f'/api/files/{file_id}/download-link',
                                  headers={'Authorization': f'Bearer {client_token}'})
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn('download_link', data)
        self.assertIn('download_url', data)
        
        # Use download link
        download_token = data['download_link']['token']
        download_response = self.client.get(f'/api/download/{download_token}')
        self.assertEqual(download_response.status_code, 200)
        
        # Try to use the same link again (should fail)
        download_response2 = self.client.get(f'/api/download/{download_token}')
        self.assertEqual(download_response2.status_code, 410)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to protected endpoints"""
        # Try to upload without token
        response = self.client.post('/api/upload',
                                  data={'file': self.create_test_file()})
        self.assertEqual(response.status_code, 401)
        
        # Try to list files without token
        response = self.client.get('/api/files')
        self.assertEqual(response.status_code, 401)
    
    def test_role_based_access(self):
        """Test role-based access control"""
        # Setup and verify client user
        self.client.post('/api/auth/signup',
                        data=json.dumps(self.client_user_data),
                        content_type='application/json')
        
        user = User.query.filter_by(email=self.client_user_data['email']).first()
        self.client.get(f'/api/auth/verify-email/{user.verification_token}')
        
        client_login = self.client.post('/api/auth/login',
                                      data=json.dumps({
                                          'username': self.client_user_data['username'],
                                          'password': self.client_user_data['password']
                                      }),
                                      content_type='application/json')
        client_token = json.loads(client_login.data)['access_token']
        
        # Client should not be able to upload files
        response = self.client.post('/api/upload',
                                  data={'file': self.create_test_file()},
                                  headers={'Authorization': f'Bearer {client_token}'})
        self.assertEqual(response.status_code, 403)

if __name__ == '__main__':
    unittest.main()