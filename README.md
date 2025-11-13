# Dawud Charity Hub - Backend API

FastAPI backend for donation management with real-time admin dashboard.

## Overview

Secure donation submission system where donors submit confirmations with proof images. Administrators verify, manage, and export donation data through a real-time dashboard.

## Features

**Public**
- Donation submission with transaction reference
- Optional proof image upload (JPG/PNG, max 5MB)
- Multiple bank support

**Admin**
- Session-based authentication
- Real-time dashboard with WebSocket updates
- Donation verification workflow
- Search, filter, and export (CSV/Excel)
- Dashboard statistics

**Security**
- Rate limiting, security headers, request validation
- SQL injection and XSS protection
- Secure file uploads with UUID filenames
- Bcrypt password hashing (12 rounds)
- JWT tokens for WebSocket authentication

## Tech Stack

- FastAPI 0.104.1
- SQLite (SQLAlchemy ORM)
- Session + JWT authentication
- bcrypt, slowapi, pandas, openpyxl
- Uvicorn

## Installation

### Prerequisites
- Python 3.8+
- pip

### Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp env.example .env
# Edit .env with your settings

# 4. Run application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Database and default admin user (`admin/admin`) are created automatically on first run.

**Important**: Change default admin password immediately.

## Configuration

Create `.env` file:

```env
# Required
SECRET_KEY=your-secure-random-key-here
ALLOWED_ORIGINS=https://yourdomain.com,http://localhost:3000

# Optional
ACCESS_TOKEN_EXPIRE_MINUTES=30
ADMIN_IP_WHITELIST=127.0.0.1,192.168.1.100
```

Generate secure key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## API Endpoints

### Public

**POST /api/submit-donation**
- Content-Type: `multipart/form-data`
- Parameters: `donor_name`, `donor_contact`, `bank_used`, `amount_donated`, `transaction_reference` (optional), `message` (optional), `proof_image` (optional)
- Rate limit: 10/minute per IP

**GET /health**
- Health check endpoint

### Admin (Requires Authentication)

**POST /api/admin/login**
- Body: `{"username": "admin", "password": "password"}`
- Rate limit: 5/minute per IP

**POST /api/admin/logout**

**PUT /api/admin/change-password**
- Body: `{"current_password": "...", "new_password": "..."}`

**GET /api/admin/dashboard-stats**
- Returns: total submissions, verified count, pending count, total amount

**GET /api/admin/submissions**
- Query params: `skip`, `limit`, `verified_only`, `search`
- Returns: Array of donation submissions

**GET /api/admin/submissions/{id}**
- Returns: Single submission

**PUT /api/admin/submissions/{id}/verify**
- Body: `{"is_verified": true}`

**DELETE /api/admin/delete/{id}**

**GET /api/admin/export**
- Query params: `format` (csv/excel), `verified_only`
- Returns: File download

**GET /api/admin/banks**
- Returns: List of unique bank names

**GET /api/admin/images/{image_path}**
- Returns: Image file

### WebSocket

**WS /ws/admin?token={jwt_token}**
- Real-time updates for admin dashboard
- Message types: `new_donation`, `donation_verified`, `stats_update`, `connection_established`
- Supports ping/pong for keep-alive

## Database Models

### DonationSubmission
```python
id: int (PK)
transaction_reference: str (optional, unique)
donor_name: str
donor_contact: str  # Email or phone
bank_used: str
amount_donated: str  # e.g., "100 ETB"
message: str (optional)
proof_image_path: str (optional)
submitted_at: datetime
is_verified: bool (default: False)
verified_at: datetime (optional)
verified_by: str (optional)  # Admin username
```

### Admin
```python
id: int (PK)
username: str (unique)
email: str (unique)
hashed_password: str
is_active: bool (default: True)
created_at: datetime
```

## Security

1. **Security Headers**: CSP, XSS protection, frame options, HSTS
2. **Request Validation**: SQL injection and XSS pattern detection, 5MB size limit
3. **Rate Limiting**: Configurable per endpoint
4. **File Upload**: Type validation, size limits, UUID filenames, PIL content verification
5. **Authentication**: Bcrypt hashing, session management, JWT for WebSocket
6. **IP Whitelisting**: Optional admin endpoint restriction

## Project Structure

```
dawud-charity-backend/
├── main.py                 # FastAPI app and routes
├── models.py               # SQLAlchemy models
├── schemas.py              # Pydantic schemas
├── database.py             # DB configuration
├── auth.py                 # JWT and password hashing
├── security_middleware.py  # Security middleware
├── file_utils.py           # File upload handling
├── websocket_manager.py    # WebSocket manager
├── requirements.txt
├── .env                    # Environment variables
├── data/
│   └── donations.db       # SQLite database
├── uploads/donations/     # Uploaded images
└── templates/             # Admin HTML pages
```

## Running

**Development:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Direct:**
```bash
python main.py
```

Access:
- API: `http://localhost:8000`
- Admin: `http://localhost:8000/admin`
- Dashboard: `http://localhost:8000/admin/dashboard`

## Development

### Default Admin
- Username: `admin`
- Password: `admin`
- Change immediately in production

### Create Admin User
```python
from database import SessionLocal
from models import Admin
from auth import get_password_hash

db = SessionLocal()
admin = Admin(
    username="newadmin",
    email="admin@example.com",
    hashed_password=get_password_hash("password"),
    is_active=True
)
db.add(admin)
db.commit()
db.close()
```

### Testing
```bash
# Health check
curl http://localhost:8000/health

# Submit donation
curl -X POST http://localhost:8000/api/submit-donation \
  -F "donor_name=John Doe" \
  -F "donor_contact=john@example.com" \
  -F "bank_used=Bank Name" \
  -F "amount_donated=100 ETB"
```

## Deployment

### Checklist
- [ ] Set secure `SECRET_KEY`
- [ ] Update `ALLOWED_ORIGINS` with production domains
- [ ] Change default admin password
- [ ] Configure reverse proxy (Nginx)
- [ ] Enable HTTPS/SSL
- [ ] Set file permissions for `uploads/` and `data/`
- [ ] Configure logging
- [ ] Set up database backups
- [ ] Use process manager (systemd/supervisor)

### Nginx Example
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    client_max_body_size 5M;
}
```

### Systemd Service
```ini
[Unit]
Description=Dawud Charity Hub Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/dawud-charity-backend
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable: `sudo systemctl enable dawud-charity && sudo systemctl start dawud-charity`

## Notes

- Database tables auto-created on first run
- Directories auto-created on startup
- Temporary files cleaned on startup
- WebSocket requires JWT token authentication
- File uploads validated and sanitized
- Images stored with UUID filenames
