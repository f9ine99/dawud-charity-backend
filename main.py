from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Query, Body, Request, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from typing import List

from database import engine, Base, get_db, SessionLocal
from models import DonationSubmission as DonationSubmissionModel, Admin
from schemas import (
    DonationSubmissionCreate, DonationSubmission, AdminLogin, Token,
    AdminCreate, TokenData, PasswordChange
)
from auth import verify_password, get_password_hash, create_access_token, verify_token
from file_utils import (
    ensure_directories, save_upload_file_securely, get_file_path,
    cleanup_temp_files, sanitize_filename
)
from security_middleware import (
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    IPWhitelistMiddleware,
    setup_rate_limits,
    limiter
)
from websocket_manager import manager as ws_manager

# Lifespan event handler
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    print("Starting up Dawud Charity Hub Donation System...")

    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Ensure directories exist
    ensure_directories()

    # Clean up temp files
    cleanup_temp_files()

    # Create default admin user
    db = SessionLocal()
    try:
        # Check if default admin exists
        admin = db.query(Admin).filter(Admin.username == "admin").first()
        if not admin:
            default_admin = Admin(
                username="admin",
                email="admin@dawudcharity.org",
                hashed_password=get_password_hash("admin"),
                is_active=True
            )
            db.add(default_admin)
            db.commit()
            print("✅ Default admin user created: admin/admin")
        else:
            print("✅ Admin user already exists")
    finally:
        db.close()

    print("🚀 Server ready to accept connections!")

    yield

    # Shutdown code (if needed)
    print("🛑 Shutting down server...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Dawud Charity Hub - Donation System",
    description="Secure donation submission system with admin verification",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,  # Disable docs in production for security
    redoc_url=None  # Disable redoc in production for security
)

# Setup rate limiting
limiter = setup_rate_limits(app)

# Security Middleware (order matters!)
# 1. Request Validation - First line of defense
app.add_middleware(RequestValidationMiddleware)

# 2. Security Headers - Add security headers to responses
app.add_middleware(SecurityHeadersMiddleware)

# 3. IP Whitelist (Optional) - Uncomment and configure if needed
# admin_whitelist = os.getenv("ADMIN_IP_WHITELIST", "").split(",")
# if admin_whitelist and admin_whitelist[0]:
#     app.add_middleware(IPWhitelistMiddleware, whitelist=admin_whitelist)

# CORS middleware for frontend integration
# Production domains for Dawud Charity Hub
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://kedi.furi-cadaster.com,https://www.kedi.furi-cadaster.com"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods
    allow_headers=["Content-Type", "Authorization"],  # Explicit headers
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Mount static files for serving uploaded images securely
# In production, ensure uploads directory exists and has proper permissions
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Serve admin interface
@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/", response_class=HTMLResponse)
async def admin_interface():
    """Serve the admin interface."""
    admin_file = Path("templates/admin.html")
    if admin_file.exists():
        return admin_file.read_text()
    raise HTTPException(status_code=404, detail="Admin interface not found")

# Mount templates directory for admin assets
app.mount("/admin/assets", StaticFiles(directory="templates"), name="admin-assets")

# Security scheme
security = HTTPBearer()

# Dependency to get current admin user
async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise credentials_exception
    return username

# Public endpoints
@app.post("/api/submit-donation", response_model=dict)
@limiter.limit("10/minute")  # Max 10 donation submissions per minute per IP
async def submit_donation(
    request: Request,
    transaction_reference: str = Form(None),
    donor_name: str = Form(..., min_length=2, max_length=100),
    donor_contact: str = Form(...),
    bank_used: str = Form(...),
    amount_donated: str = Form(...),
    message: str = Form(None),
    proof_image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """Submit a donation confirmation with optional proof image."""

    # Validate inputs
    submission_data = DonationSubmissionCreate(
        transaction_reference=transaction_reference,
        donor_name=donor_name,
        donor_contact=donor_contact,
        bank_used=bank_used,
        amount_donated=amount_donated,
        message=message
    )

    # Handle file upload if provided
    image_path = None
    if proof_image and proof_image.filename:
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png"]
        if not proof_image.content_type or proof_image.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JPG and PNG images are allowed"
            )

        # Sanitize filename
        sanitized_filename = sanitize_filename(proof_image.filename)

        # Save file securely
        try:
            image_path = await save_upload_file_securely(proof_image, sanitized_filename)
            if not image_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid image file"
                )
        except ValueError as e:
            # File size or other validation error
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=str(e)
            )

    # Create database record using SQLAlchemy model
    db_submission = DonationSubmissionModel(
        transaction_reference=submission_data.transaction_reference,
        donor_name=submission_data.donor_name,
        donor_contact=submission_data.donor_contact,
        bank_used=submission_data.bank_used,
        amount_donated=submission_data.amount_donated,
        message=submission_data.message,
        proof_image_path=image_path
    )

    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)

    # Broadcast new donation via WebSocket
    await ws_manager.broadcast_new_donation({
        "id": db_submission.id,
        "transaction_reference": db_submission.transaction_reference,
        "donor_name": db_submission.donor_name,
        "donor_contact": db_submission.donor_contact,
        "bank_used": db_submission.bank_used,
        "amount_donated": db_submission.amount_donated,
        "message": db_submission.message,
        "submitted_at": db_submission.submitted_at.isoformat(),
        "is_verified": db_submission.is_verified
    })

    return {
        "success": True,
        "transaction_reference": db_submission.transaction_reference,
        "message": "Donation confirmation submitted successfully"
    }

# Admin authentication endpoints
@app.post("/api/admin/login", response_model=Token)
@limiter.limit("5/minute")  # Max 5 login attempts per minute per IP
async def login_admin(request: Request, admin_credentials: AdminLogin, db: Session = Depends(get_db)):
    """Admin login endpoint with rate limiting to prevent brute force attacks."""
    admin = db.query(Admin).filter(Admin.username == admin_credentials.username).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account disabled"
        )

    if not verify_password(admin_credentials.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token = create_access_token(
        data={"sub": admin.username},
        expires_delta=timedelta(minutes=30)
    )

    return {"access_token": access_token, "token_type": "bearer"}

# Password change endpoint
@app.put("/api/admin/change-password")
async def change_password(
    request: dict,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Change admin password."""
    # Extract parameters from request
    current_password = request.get('current_password')
    new_password = request.get('new_password')

    if not current_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current_password and new_password are required"
        )

    # Get the current admin user
    admin = db.query(Admin).filter(Admin.username == current_admin).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin user not found"
        )

    # Verify current password
    if not verify_password(current_password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Validate new password (minimum 8 characters)
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )

    # Update password
    admin.hashed_password = get_password_hash(new_password)
    db.commit()

    return {
        "success": True,
        "message": "Password changed successfully"
    }

# Protected admin endpoints
@app.get("/api/admin/dashboard-stats")
async def get_dashboard_stats(
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics."""
    try:
        # Total submissions
        total_submissions = db.query(DonationSubmissionModel).count()

        # Verified submissions
        verified_count = db.query(DonationSubmissionModel).filter(DonationSubmissionModel.is_verified == True).count()

        # Pending submissions
        pending_count = total_submissions - verified_count

        # Total amount (from verified submissions only)
        # Extract numeric part from amount strings like "100 ETB"
        verified_submissions = db.query(DonationSubmissionModel).filter(DonationSubmissionModel.is_verified == True).all()
        total_amount = 0.0
        for submission in verified_submissions:
            try:
                # Extract number from string like "100 ETB", "1,000 ETB", or "100.50 ETB"
                amount_str = submission.amount_donated
                # Remove currency symbols and extra spaces
                amount_str = amount_str.replace(' ETB', '').replace('ETB', '').replace(' BIRR', '').replace('BIRR', '').replace(' USD', '').replace('USD', '').replace(' EUR', '').replace('EUR', '').strip()
                # Remove commas for float conversion
                amount_str = amount_str.replace(',', '')
                amount_num = float(amount_str)
                total_amount += amount_num
            except (ValueError, AttributeError):
                # Skip invalid amounts
                continue

        return {
            "total_submissions": total_submissions,
            "verified_count": verified_count,
            "pending_count": pending_count,
            "total_amount": round(total_amount, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard stats: {str(e)}")

@app.get("/api/admin/submissions")
async def get_submissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    verified_only: bool = Query(False),
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all donation submissions with pagination."""
    query = db.query(DonationSubmissionModel)

    if verified_only:
        query = query.filter(DonationSubmissionModel.is_verified == True)

    submissions = query.order_by(desc(DonationSubmissionModel.submitted_at)).offset(skip).limit(limit).all()

    # Convert to JSON-serializable format
    result = []
    for submission in submissions:
        result.append({
            "id": submission.id,
            "transaction_reference": submission.transaction_reference,
            "donor_name": submission.donor_name,
            "donor_contact": submission.donor_contact,
            "bank_used": submission.bank_used,
            "amount_donated": submission.amount_donated,
            "message": submission.message,
            "proof_image_path": submission.proof_image_path,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "is_verified": submission.is_verified,
            "verified_at": submission.verified_at.isoformat() if submission.verified_at else None,
            "verified_by": submission.verified_by
        })

    return result

@app.get("/api/admin/submissions/{submission_id}", response_model=DonationSubmission)
async def get_submission(
    submission_id: int,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get a specific submission by ID."""
    submission = db.query(DonationSubmissionModel).filter(DonationSubmissionModel.id == submission_id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    return submission

@app.put("/api/admin/submissions/{submission_id}/verify")
async def verify_submission(
    submission_id: int,
    is_verified: bool = Query(...),
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Verify or unverify a submission."""
    submission = db.query(DonationSubmissionModel).filter(DonationSubmissionModel.id == submission_id).first()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )

    submission.is_verified = is_verified
    submission.verified_at = datetime.utcnow()
    submission.verified_by = current_admin

    db.commit()

    # Broadcast verification change via WebSocket
    await ws_manager.broadcast_donation_verified(
        donation_id=submission_id,
        verified=is_verified,
        verified_by=current_admin
    )

    return {
        "success": True,
        "message": f"Submission {'verified' if is_verified else 'unverified'} successfully"
    }

@app.get("/api/admin/export")
async def export_submissions(
    format: str = Query("csv", regex="^(csv|excel)$"),
    verified_only: bool = Query(False),
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Export submissions as CSV or Excel."""
    from io import BytesIO
    
    query = db.query(DonationSubmissionModel)

    if verified_only:
        query = query.filter(DonationSubmissionModel.is_verified == True)

    submissions = query.order_by(desc(DonationSubmissionModel.submitted_at)).all()

    # Convert to DataFrame
    data = []
    for sub in submissions:
        data.append({
            "Transaction Reference": sub.transaction_reference,
            "Donor Name": sub.donor_name,
            "Contact": sub.donor_contact,
            "Bank Used": sub.bank_used,
            "Amount": sub.amount_donated,
            "Message": sub.message or "",
            "Image Path": sub.proof_image_path or "",
            "Submitted At": sub.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
            "Verified": "Yes" if sub.is_verified else "No",
            "Verified At": sub.verified_at.strftime("%Y-%m-%d %H:%M:%S") if sub.verified_at else "",
            "Verified By": sub.verified_by or ""
        })

    df = pd.DataFrame(data)
    
    # Generate filename
    filename = f"donation_submissions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format if format == 'csv' else 'xlsx'}"

    # Create file in memory
    output = BytesIO()
    
    if format == "excel":
        df.to_excel(output, index=False, engine='openpyxl')
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:  # CSV
        df.to_csv(output, index=False)
        media_type = "text/csv"
    
    # Seek to beginning of file
    output.seek(0)
    
    # Return streaming response
    return StreamingResponse(
        output,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

# Serve uploaded images securely
@app.get("/api/admin/images/{image_path:path}")
async def get_submission_image(
    image_path: str,
    current_admin: str = Depends(get_current_admin)
):
    """Serve uploaded images for admin viewing."""
    file_path = get_file_path(image_path)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    return FileResponse(file_path, media_type="image/jpeg")


# WebSocket endpoint for real-time updates
@app.websocket("/ws/admin")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket endpoint for real-time admin dashboard updates.
    Requires JWT token authentication via query parameter.
    
    Usage: ws://localhost:8000/ws/admin?token=<jwt_token>
    """
    # Authenticate WebSocket connection
    try:
        admin_username = verify_token(token)
        
        if not admin_username:
            await websocket.close(code=1008, reason="Invalid authentication token")
            return
            
        # Verify admin exists and is active
        db = SessionLocal()
        try:
            admin = db.query(Admin).filter(Admin.username == admin_username).first()
            if not admin or not admin.is_active:
                await websocket.close(code=1008, reason="Admin not found or inactive")
                return
        finally:
            db.close()
        
        # Connect to WebSocket manager
        await ws_manager.connect(websocket, admin_username)
        
        try:
            # Keep connection alive and handle incoming messages
            while True:
                # Wait for any message from client (e.g., ping/pong)
                data = await websocket.receive_text()
                
                # Handle client messages if needed
                try:
                    message = json.loads(data)
                    
                    # Handle ping messages for keep-alive
                    if message.get("type") == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    # Handle request for current stats
                    elif message.get("type") == "request_stats":
                        db = SessionLocal()
                        try:
                            total_submissions = db.query(DonationSubmissionModel).count()
                            verified_count = db.query(DonationSubmissionModel).filter(
                                DonationSubmissionModel.is_verified == True
                            ).count()
                            pending_count = total_submissions - verified_count
                            
                            total_amount = db.query(
                                func.sum(func.cast(func.replace(DonationSubmissionModel.amount_donated, ',', ''), float))
                            ).filter(
                                DonationSubmissionModel.is_verified == True
                            ).scalar() or 0
                            
                            await ws_manager.send_personal_message({
                                "type": "stats_update",
                                "data": {
                                    "total_submissions": total_submissions,
                                    "verified_count": verified_count,
                                    "pending_count": pending_count,
                                    "total_amount": float(total_amount)
                                },
                                "timestamp": datetime.now().isoformat()
                            }, websocket)
                        finally:
                            db.close()
                    
                except json.JSONDecodeError:
                    # Ignore malformed JSON
                    pass
                    
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket, admin_username)
            
    except Exception as e:
        print(f"WebSocket authentication error: {e}")
        try:
            await websocket.close(code=1008, reason="Authentication failed")
        except:
            pass


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "websocket_connections": ws_manager.get_connection_count(),
        "connected_admins": ws_manager.get_connected_admins()
    }

# Test endpoint (disabled in production for security)
# Uncomment only for development debugging
# @app.get("/api/test")
# async def test_endpoint():
#     """Test endpoint for debugging."""
#     return {"message": "Backend is working!", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
