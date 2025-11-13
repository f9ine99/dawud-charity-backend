# Dawud Charity Hub - Backend API

A secure, production-ready FastAPI backend for managing donation submissions with real-time admin dashboard updates.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Database Models](#database-models)
- [Security Features](#security-features)
- [Project Structure](#project-structure)
- [Running the Application](#running-the-application)
- [Development](#development)
- [Deployment](#deployment)

## 🎯 Overview

Dawud Charity Hub Backend is a secure donation management system that allows donors to submit donation confirmations with proof images, while administrators can verify, manage, and export donation data through a real-time dashboard.

### Key Capabilities

- **Public Donation Submission**: Secure form submission with image upload
- **Admin Dashboard**: Real-time updates via WebSocket connections
- **Verification System**: Admin verification workflow for donations
- **Data Export**: CSV and Excel export functionality
- **Security First**: Multiple layers of security middleware and rate limiting

## ✨ Features

### Public Features
- ✅ Donation submission with transaction reference
- ✅ Optional proof image upload (JPG/PNG, max 5MB)
- ✅ Multiple bank support
- ✅ Donor contact information (email/phone)
- ✅ Custom donation messages

### Admin Features
- ✅ Session-based authentication
- ✅ Real-time dashboard with WebSocket updates
- ✅ Donation verification/unverification
- ✅ Search and filter donations
- ✅ Export to CSV/Excel
- ✅ Dashboard statistics
- ✅ Password change functionality
- ✅ Image viewing for proof submissions

### Security Features
- ✅ Rate limiting on sensitive endpoints
- ✅ Security headers (CSP, XSS protection, etc.)
- ✅ Request validation middleware
- ✅ SQL injection and XSS protection
- ✅ Secure file upload handling
- ✅ Bcrypt password hashing
- ✅ JWT tokens for WebSocket authentication
- ✅ Optional IP whitelisting

## 🛠 Tech Stack

- **Framework**: FastAPI 0.104.1
- **Database**: SQLite (SQLAlchemy ORM)
- **Authentication**: Session-based + JWT tokens
- **Password Hashing**: bcrypt
- **File Handling**: aiofiles, PIL/Pillow
- **Real-time**: WebSocket support
- **Rate Limiting**: slowapi
- **Data Export**: pandas, openpyxl
- **Server**: Uvicorn

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone the Repository

```bash
cd dawud-charity-backend
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

```bash
cp env.example .env
```

Edit `.env` file with your configuration (see [Configuration](#configuration) section).

### Step 5: Initialize Database

The database will be automatically created on first run. The application will:
- Create the `data/` directory
- Initialize SQLite database at `data/donations.db`
- Create all necessary tables
- Create default admin user (username: `admin`, password: `admin`)

**⚠️ Important**: Change the default admin password immediately after first login!

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Security - Generate a secure random key for production
SECRET_KEY=your-super-secret-jwt-key-change-this-in-production

# CORS - Allowed origins for frontend (comma-separated)
ALLOWED_ORIGINS=https://kedi.furi-cadaster.com,https://www.kedi.furi-cadaster.com,http://localhost:3000

# Rate Limiting (Optional)
MAX_DONATION_SUBMISSIONS_PER_MINUTE=10
MAX_LOGIN_ATTEMPTS_PER_MINUTE=5

# File Upload Settings
MAX_FILE_SIZE_MB=5
ALLOWED_FILE_TYPES=image/jpeg,image/jpg,image/png

# Session Settings
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Optional: IP Whitelist for Admin Endpoints
ADMIN_IP_WHITELIST=127.0.0.1,192.168.1.100
```

### Generating a Secure Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 📡 API Endpoints

### Public Endpoints

#### Submit Donation
```http
POST /api/submit-donation
Content-Type: multipart/form-data

Parameters:
- transaction_reference (optional): Transaction reference number
- donor_name (required): Donor's full name (2-100 characters)
- donor_contact (required): Email or phone number
- bank_used (required): Bank name
- amount_donated (required): Amount (e.g., "100 ETB", "1,000.50")
- message (optional): Donation message
- proof_image (optional): JPG/PNG image file (max 5MB)

Response:
{
  "success": true,
  "transaction_reference": "...",
  "message": "Donation confirmation submitted successfully"
}
```

**Rate Limit**: 10 requests per minute per IP

### Admin Endpoints

All admin endpoints require authentication via session cookie.

#### Login
```http
POST /api/admin/login
Content-Type: application/json

Body:
{
  "username": "admin",
  "password": "password"
}

Response:
{
  "success": true,
  "message": "Login successful",
  "redirect": "/admin/dashboard"
}
```

**Rate Limit**: 5 requests per minute per IP

#### Logout
```http
POST /api/admin/logout

Response:
{
  "success": true,
  "message": "Logged out successfully"
}
```

#### Change Password
```http
PUT /api/admin/change-password
Content-Type: application/json

Body:
{
  "current_password": "old_password",
  "new_password": "new_password"
}

Response:
{
  "success": true,
  "message": "Password changed successfully"
}
```

#### Dashboard Statistics
```http
GET /api/admin/dashboard-stats

Response:
{
  "total_submissions": 150,
  "verified_count": 120,
  "pending_count": 30,
  "total_amount": 125000.50
}
```

#### Get Submissions
```http
GET /api/admin/submissions?skip=0&limit=100&verified_only=false&search=john

Query Parameters:
- skip (default: 0): Number of records to skip
- limit (default: 100, max: 999999): Number of records to return
- verified_only (default: false): Filter verified submissions only
- search (optional): Search in donor name, transaction reference, or contact

Response: Array of donation submission objects
```

#### Get Submission by ID
```http
GET /api/admin/submissions/{submission_id}

Response: Single donation submission object
```

#### Verify/Unverify Submission
```http
PUT /api/admin/submissions/{submission_id}/verify
Content-Type: application/json

Body:
{
  "is_verified": true
}

Response:
{
  "success": true,
  "message": "Submission verified successfully"
}
```

#### Delete Submission
```http
DELETE /api/admin/delete/{submission_id}

Response:
{
  "success": true,
  "message": "Submission deleted successfully"
}
```

#### Export Submissions
```http
GET /api/admin/export?format=csv&verified_only=false

Query Parameters:
- format: "csv" or "excel" (default: "csv")
- verified_only (default: false): Export only verified submissions

Response: File download (CSV or Excel)
```

#### Get Banks List
```http
GET /api/admin/banks

Response: ["Bank Name 1", "Bank Name 2", ...]
```

#### Get Submission Image
```http
GET /api/admin/images/{image_path}

Example: /api/admin/images/donations/filename.jpg

Response: Image file (JPEG/PNG)
```

### WebSocket Endpoint

#### Real-time Admin Updates
```javascript
// Connect to WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/admin?token=${jwt_token}`);

// Message Types:
// - connection_established: Initial connection confirmation
// - new_donation: New donation submitted
// - donation_verified: Donation verification status changed
// - stats_update: Dashboard statistics updated
// - pong: Response to ping message

// Send ping for keep-alive
ws.send(JSON.stringify({ type: "ping" }));

// Request current stats
ws.send(JSON.stringify({ type: "request_stats" }));
```

### Health Check

```http
GET /health

Response:
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "websocket_connections": 2,
  "connected_admins": ["admin"]
}
```

## 🗄 Database Models

### DonationSubmission

```python
{
  "id": int (Primary Key),
  "transaction_reference": str (Optional, Unique),
  "donor_name": str (Required),
  "donor_contact": str (Required),  # Email or phone
  "bank_used": str (Required),
  "amount_donated": str (Required),  # e.g., "100 ETB"
  "message": str (Optional),
  "proof_image_path": str (Optional),  # Relative path
  "submitted_at": datetime (Auto-generated),
  "is_verified": bool (Default: False),
  "verified_at": datetime (Optional),
  "verified_by": str (Optional)  # Admin username
}
```

### Admin

```python
{
  "id": int (Primary Key),
  "username": str (Required, Unique),
  "email": str (Required, Unique),
  "hashed_password": str (Required),
  "is_active": bool (Default: True),
  "created_at": datetime (Auto-generated)
}
```

## 🔒 Security Features

### 1. Security Headers Middleware
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security`
- `Content-Security-Policy`
- `Referrer-Policy`
- `Permissions-Policy`

### 2. Request Validation Middleware
- SQL injection pattern detection
- XSS pattern detection
- Request size validation (5MB limit)
- Input sanitization

### 3. Rate Limiting
- Donation submissions: 10/minute per IP
- Login attempts: 5/minute per IP
- Configurable via environment variables

### 4. File Upload Security
- File type validation (JPG/PNG only)
- File size limits (5MB max)
- Filename sanitization
- UUID-based secure filenames
- Image content validation (PIL verification)
- Path traversal protection

### 5. Authentication & Authorization
- Bcrypt password hashing (12 rounds)
- Session-based authentication for admin
- JWT tokens for WebSocket connections
- Password strength requirements (min 8 characters)

### 6. Optional IP Whitelisting
- Configure `ADMIN_IP_WHITELIST` in `.env` to restrict admin access

## 📁 Project Structure

```
dawud-charity-backend/
├── main.py                 # FastAPI application and routes
├── models.py               # SQLAlchemy database models
├── schemas.py              # Pydantic validation schemas
├── database.py             # Database configuration and session
├── auth.py                 # Authentication utilities (JWT, password hashing)
├── security_middleware.py  # Security middleware (headers, validation, rate limiting)
├── file_utils.py           # Secure file upload handling
├── websocket_manager.py    # WebSocket connection management
├── requirements.txt        # Python dependencies
├── env.example             # Environment variables template
├── .env                    # Environment variables (create from env.example)
├── data/
│   └── donations.db       # SQLite database (auto-created)
├── uploads/
│   └── donations/         # Uploaded proof images
├── temp/                   # Temporary file storage
└── templates/
    ├── login.html          # Admin login page
    └── dashboard.html      # Admin dashboard
```

## 🚀 Running the Application

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# Run with production settings
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Python Directly

```bash
python main.py
```

The application will be available at:
- **API**: `http://localhost:8000`
- **Admin Login**: `http://localhost:8000/admin`
- **Admin Dashboard**: `http://localhost:8000/admin/dashboard`
- **API Docs** (disabled in production): `http://localhost:8000/docs`

## 💻 Development

### Default Admin Credentials

On first run, a default admin user is created:
- **Username**: `admin`
- **Password**: `admin`

**⚠️ Change this immediately in production!**

### Creating Additional Admin Users

You can create additional admin users by directly inserting into the database or by creating a management script. Example:

```python
from database import SessionLocal
from models import Admin
from auth import get_password_hash

db = SessionLocal()
new_admin = Admin(
    username="newadmin",
    email="newadmin@example.com",
    hashed_password=get_password_hash("secure_password"),
    is_active=True
)
db.add(new_admin)
db.commit()
db.close()
```

### Database Migrations

The application uses SQLAlchemy with automatic table creation. For production, consider using Alembic for migrations:

```bash
# Initialize Alembic (if not already done)
alembic init alembic

# Create a migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Testing

Test endpoints using curl or any HTTP client:

```bash
# Health check
curl http://localhost:8000/health

# Submit donation
curl -X POST http://localhost:8000/api/submit-donation \
  -F "donor_name=John Doe" \
  -F "donor_contact=john@example.com" \
  -F "bank_used=Commercial Bank" \
  -F "amount_donated=100 ETB" \
  -F "proof_image=@/path/to/image.jpg"
```

## 🚢 Deployment

### Production Checklist

- [ ] Change `SECRET_KEY` to a secure random value
- [ ] Update `ALLOWED_ORIGINS` with production domain(s)
- [ ] Change default admin password
- [ ] Set up proper database (consider PostgreSQL for production)
- [ ] Configure reverse proxy (Nginx/Apache)
- [ ] Enable HTTPS/SSL certificates
- [ ] Set up proper file permissions for `uploads/` and `data/` directories
- [ ] Configure logging
- [ ] Set up backup strategy for database
- [ ] Consider IP whitelisting for admin endpoints
- [ ] Disable API documentation (`docs_url=None` - already configured)
- [ ] Set up process manager (systemd, supervisor, PM2)
- [ ] Configure firewall rules

### Nginx Configuration Example

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Increase upload size limit
    client_max_body_size 5M;
}
```

### Systemd Service Example

Create `/etc/systemd/system/dawud-charity.service`:

```ini
[Unit]
Description=Dawud Charity Hub Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/dawud-charity-backend
Environment="PATH=/path/to/dawud-charity-backend/venv/bin"
ExecStart=/path/to/dawud-charity-backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable dawud-charity
sudo systemctl start dawud-charity
```

## 📝 Notes

- The application automatically creates necessary directories on startup
- Temporary files are cleaned up on startup
- Database tables are created automatically on first run
- WebSocket connections require JWT token authentication
- All file uploads are validated and sanitized
- Images are stored with UUID-based filenames for security

## 🤝 Support

For issues, questions, or contributions, please refer to the project repository or contact the development team.

## 📄 License

[Specify your license here]

---

**Built with ❤️ for Dawud Charity Hub**

