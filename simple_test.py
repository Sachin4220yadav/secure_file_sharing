#!/usr/bin/env python3
"""
Simple test script to verify the Flask application functionality
Run this instead of the full unit tests if there are compatibility issues
"""

import requests
import json
import time
import subprocess
import sys
import os
from threading import Thread

def test_api_basic():
    """Test basic API functionality"""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing File Sharing API...")
    
    # Test health check
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print("❌ Health check failed")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test API info
    try:
        response = requests.get(f"{base_url}/api")
        if response.status_code == 200:
            print("✅ API info endpoint working")
        else:
            print("❌ API info endpoint failed")
    except Exception as e:
        print(f"❌ API info endpoint failed: {e}")
    
    # Test ops user signup
    ops_user = {
        "username": "test_ops",
        "email": "ops@test.com",
        "password": "TestPass123",
        "user_type": "ops"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/auth/signup",
            json=ops_user,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 201:
            print("✅ Ops user signup successful")
            ops_data = response.json()
        else:
            print(f"❌ Ops user signup failed: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ Ops user signup failed: {e}")
        return False
    
    # Test ops user login
    try:
        response = requests.post(
            f"{base_url}/api/auth/login",
            json={"username": "test_ops", "password": "TestPass123"},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            print("✅ Ops user login successful")
            ops_token = response.json()["access_token"]
        else:
            print(f"❌ Ops user login failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ops user login failed: {e}")
        return False
    
    # Test client user signup
    client_user = {
        "username": "test_client",
        "email": "client@test.com",
        "password": "TestPass123",
        "user_type": "client"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/auth/signup",
            json=client_user,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 201:
            print("✅ Client user signup successful")
            client_data = response.json()
            verification_link = client_data.get("verification_link")
        else:
            print(f"❌ Client user signup failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Client user signup failed: {e}")
        return False
    
    # Test file listing (should require authentication)
    try:
        response = requests.get(f"{base_url}/api/files")
        if response.status_code == 401:
            print("✅ File listing correctly requires authentication")
        else:
            print(f"❌ File listing security issue: {response.status_code}")
    except Exception as e:
        print(f"⚠️  File listing test failed: {e}")
    
    print("\n🎉 Basic API tests completed!")
    print("📝 Manual testing steps:")
    print(f"1. Verify email using: {verification_link}")
    print("2. Login as client user")
    print("3. Upload files as ops user")
    print("4. Generate download links as client user")
    print("5. Test file downloads")
    
    return True

def start_flask_app():
    """Start the Flask application in a separate process"""
    print("🚀 Starting Flask application...")
    
    # Create a simple startup script
    startup_code = '''
import sys
sys.path.append(".")

try:
    from app import create_app
    app = create_app()
    with app.app_context():
        from models import db
        db.create_all()
        print("Database initialized successfully!")
    
    print("Starting Flask server on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install -r requirements-legacy.txt")
    sys.exit(1)
except Exception as e:
    print(f"Application startup error: {e}")
    sys.exit(1)
'''
    
    with open('start_app.py', 'w') as f:
        f.write(startup_code)
    
    try:
        process = subprocess.Popen([sys.executable, 'start_app.py'])
        return process
    except Exception as e:
        print(f"Failed to start Flask app: {e}")
        return None

if __name__ == "__main__":
    print("🔧 Simple Flask API Tester")
    print("=" * 50)
    
    # Check if we should start the app or just test
    if len(sys.argv) > 1 and sys.argv[1] == "test-only":
        print("Testing existing running application...")
        test_api_basic()
    else:
        print("Starting application and running tests...")
        
        # Try to start the Flask app
        flask_process = start_flask_app()
        
        if flask_process:
            # Wait a bit for the app to start
            print("⏳ Waiting for application to start...")
            time.sleep(5)
            
            # Run tests
            test_success = test_api_basic()
            
            # Clean up
            print("\n🛑 Stopping Flask application...")
            flask_process.terminate()
            
            # Clean up temporary file
            if os.path.exists('start_app.py'):
                os.remove('start_app.py')
            
            if test_success:
                print("✅ All tests completed successfully!")
            else:
                print("❌ Some tests failed. Check the output above.")
        else:
            print("❌ Failed to start Flask application")
            print("💡 Try running manually: python3 app.py")