# File Sharing API

A secure Flask-based file sharing system with two user types: **Ops** (can upload files) and **Clients** (can download files).

## Features

- 🔐 **JWT Authentication** with role-based access control
- 📧 **Email Verification** for client users
- 📁 **File Upload** (pptx, docx, xlsx only) for Ops users
- 🔗 **Secure Download Links** that expire in 10 minutes
- 🚫 **One-time Use** download links
- 📊 **File Listing** with pagination
- ✅ **Comprehensive Test Suite**

## Project Structure

```
.
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── models.py           # SQLAlchemy database models
├── requirements.txt    # Python dependencies
├── routes/
│   ├── __init__.py
│   ├── auth.py         # Authentication routes
│   └── files.py        # File management routes
├── tests/
│   └── test_app.py     # Unit tests
├── uploads/            # File storage directory
└── README.md           # This file
```

## Installation & Setup

### Local Development

1. **Clone and navigate to the project:**
   ```bash
   git clone <your-repo-url>
   cd file-sharing-api
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   
   For Python 3.8-3.11:
   ```bash
   pip install -r requirements-legacy.txt
   ```
   
   For Python 3.12+:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

### Troubleshooting

If you encounter SQLAlchemy compatibility issues with Python 3.13:

1. **Use the legacy requirements:**
   ```bash
   pip install -r requirements-legacy.txt
   ```

2. **Or run the simple test script:**
   ```bash
   python3 simple_test.py
   ```

3. **For immediate testing without dependency issues:**
   ```bash
   # Test basic functionality
   python3 simple_test.py test-only
   ```

The API will be available at `http://localhost:5000`

### Environment Variables (Optional)

Create a `.env` file for production:

```env
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
DATABASE_URL=sqlite:///production.db
FLASK_ENV=production
```

## API Documentation

### Base URL
```
http://localhost:5000/api
```

### Authentication

All authenticated endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

### User Types

- **Ops**: Can upload files, auto-verified upon signup
- **Client**: Can download files, requires email verification

---

## API Endpoints

### Health Check

#### GET `/health`
Check if the API is running.

**Response:**
```json
{
  "status": "healthy",
  "message": "File sharing API is running",
  "version": "1.0.0"
}
```

---

### Authentication

#### POST `/api/auth/signup`
Create a new user account.

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123",
  "user_type": "client"  // or "ops"
}
```

**Response (Client):**
```json
{
  "message": "User created successfully. Please verify your email to activate your account.",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "user_type": "client",
    "is_verified": false,
    "created_at": "2024-01-01T12:00:00"
  },
  "verification_link": "http://localhost:5000/api/auth/verify-email/abc123..."
}
```

#### GET `/api/auth/verify-email/<token>`
Verify client user email.

**Response:**
```json
{
  "message": "Email verified successfully. You can now login."
}
```

#### POST `/api/auth/login`
Login and get JWT token.

**Request Body:**
```json
{
  "username": "john_doe",  // or email
  "password": "SecurePass123"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "user_type": "client",
    "is_verified": true,
    "created_at": "2024-01-01T12:00:00"
  }
}
```

#### GET `/api/auth/profile`
Get current user profile (requires authentication).

---

### File Management

#### POST `/api/upload` (Ops Only)
Upload a file.

**Headers:**
```
Authorization: Bearer <ops-user-token>
Content-Type: multipart/form-data
```

**Form Data:**
- `file`: File to upload (pptx, docx, or xlsx only)

**Response:**
```json
{
  "message": "File uploaded successfully",
  "file": {
    "id": 1,
    "filename": "document.docx",
    "file_size": 12345,
    "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "upload_date": "2024-01-01T12:00:00",
    "uploader": "ops_user"
  }
}
```

#### GET `/api/files` (Client Only)
List all uploaded files with pagination.

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10, max: 100)

**Response:**
```json
{
  "files": [
    {
      "id": 1,
      "filename": "document.docx",
      "file_size": 12345,
      "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "upload_date": "2024-01-01T12:00:00",
      "uploader": "ops_user"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 1,
    "pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

#### POST `/api/files/<file_id>/download-link` (Client Only)
Generate a secure download link for a file.

**Response:**
```json
{
  "message": "Download link generated successfully",
  "download_link": {
    "token": "abc123-def456-ghi789",
    "expires_at": "2024-01-01T12:10:00",
    "is_expired": false,
    "file_id": 1
  },
  "download_url": "/api/download/abc123-def456-ghi789"
}
```

#### GET `/api/download/<token>`
Download a file using a secure token.

**Response:** File download or error message

#### GET `/api/my-uploads` (Ops Only)
Get files uploaded by the current ops user.

---

## Example Requests

### cURL Examples

#### 1. Signup (Client)
```bash
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "username": "client_user",
    "email": "client@example.com",
    "password": "ClientPass123",
    "user_type": "client"
  }'
```

#### 2. Signup (Ops)
```bash
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "username": "ops_user",
    "email": "ops@example.com",
    "password": "OpsPass123",
    "user_type": "ops"
  }'
```

#### 3. Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "ops_user",
    "password": "OpsPass123"
  }'
```

#### 4. Upload File (Ops)
```bash
curl -X POST http://localhost:5000/api/upload \
  -H "Authorization: Bearer YOUR_OPS_TOKEN" \
  -F "file=@document.docx"
```

#### 5. List Files (Client)
```bash
curl -X GET http://localhost:5000/api/files \
  -H "Authorization: Bearer YOUR_CLIENT_TOKEN"
```

#### 6. Generate Download Link (Client)
```bash
curl -X POST http://localhost:5000/api/files/1/download-link \
  -H "Authorization: Bearer YOUR_CLIENT_TOKEN"
```

#### 7. Download File
```bash
curl -X GET http://localhost:5000/api/download/YOUR_DOWNLOAD_TOKEN \
  -O -J
```

### Postman Collection

You can import this JSON into Postman:

```json
{
  "info": {
    "name": "File Sharing API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:5000/api"
    },
    {
      "key": "ops_token",
      "value": ""
    },
    {
      "key": "client_token",
      "value": ""
    }
  ],
  "item": [
    {
      "name": "Auth",
      "item": [
        {
          "name": "Signup Ops",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"ops_user\",\n  \"email\": \"ops@example.com\",\n  \"password\": \"OpsPass123\",\n  \"user_type\": \"ops\"\n}"
            },
            "url": "{{base_url}}/auth/signup"
          }
        },
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Content-Type",
                "value": "application/json"
              }
            ],
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"ops_user\",\n  \"password\": \"OpsPass123\"\n}"
            },
            "url": "{{base_url}}/auth/login"
          }
        }
      ]
    },
    {
      "name": "Files",
      "item": [
        {
          "name": "Upload File",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{ops_token}}"
              }
            ],
            "body": {
              "mode": "formdata",
              "formdata": [
                {
                  "key": "file",
                  "type": "file",
                  "src": "document.docx"
                }
              ]
            },
            "url": "{{base_url}}/upload"
          }
        },
        {
          "name": "List Files",
          "request": {
            "method": "GET",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{client_token}}"
              }
            ],
            "url": "{{base_url}}/files"
          }
        }
      ]
    }
  ]
}
```

## Testing

### Full Test Suite

Run the comprehensive test suite:

```bash
python -m pytest tests/test_app.py -v
```

Or using unittest:

```bash
python -m unittest tests.test_app -v
```

### Simple Testing (Compatibility Issues)

If you encounter compatibility issues with the full test suite:

```bash
# Run basic functionality tests
python3 simple_test.py

# Or test against running application
python3 simple_test.py test-only
```

### Manual Testing

You can also test the API manually using the provided curl examples or Postman collection.

**Test Coverage:**
- ✅ User signup and validation
- ✅ Email verification
- ✅ Login authentication
- ✅ File upload (valid/invalid types)
- ✅ File listing
- ✅ Download link generation
- ✅ Secure file download
- ✅ Role-based access control
- ✅ Token expiration

## Deployment

### Deploy on Render

1. **Create a new Web Service on Render**
2. **Connect your GitHub repository**
3. **Set environment variables:**
   ```
   SECRET_KEY=your-production-secret-key
   JWT_SECRET_KEY=your-production-jwt-key
   FLASK_ENV=production
   ```
4. **Build command:** `pip install -r requirements.txt`
5. **Start command:** `python app.py`

### Deploy on Replit

1. **Create a new Repl**
2. **Upload your code files**
3. **Install dependencies:** `pip install -r requirements.txt`
4. **Run:** `python app.py`

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t file-sharing-api .
docker run -p 5000:5000 file-sharing-api
```

## Security Features

- ✅ **Password Hashing** with bcrypt
- ✅ **JWT Token Authentication**
- ✅ **Role-based Access Control**
- ✅ **File Type Validation**
- ✅ **Secure Download Links** (UUID-based)
- ✅ **Link Expiration** (10 minutes)
- ✅ **One-time Use** download links
- ✅ **Email Verification** for clients
- ✅ **Input Validation** and sanitization
- ✅ **CORS Support**

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

MIT License - feel free to use this code for your projects!