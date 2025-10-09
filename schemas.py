from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
import re

class DonationSubmissionBase(BaseModel):
    transaction_reference: Optional[str] = None
    donor_name: str
    donor_contact: str  # Email or phone
    bank_used: str
    amount_donated: str
    message: Optional[str] = None

class DonationSubmissionCreate(DonationSubmissionBase):
    @validator('transaction_reference')
    def validate_transaction_reference(cls, v):
        if v is None:
            return None
        if not v.strip():
            return None  # Allow empty transaction reference
        if len(v) < 3:
            raise ValueError('Transaction reference must be at least 3 characters')
        if len(v) > 50:
            raise ValueError('Transaction reference must be less than 50 characters')
        # Allow alphanumeric, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Transaction reference can only contain letters, numbers, hyphens, and underscores')
        return v.strip()

    @validator('donor_name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Donor name is required')
        if len(v) < 2:
            raise ValueError('Donor name must be at least 2 characters')
        if len(v) > 100:
            raise ValueError('Donor name must be less than 100 characters')
        return v.strip()

    @validator('donor_contact')
    def validate_contact(cls, v):
        if not v.strip():
            raise ValueError('Contact information is required')
        # Check if it's a valid email or phone number
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        phone_pattern = r'^[\+]?[0-9\s\-\(\)]{10,}$'

        if not (re.match(email_pattern, v) or re.match(phone_pattern, v.replace(' ', ''))):
            raise ValueError('Please enter a valid email or phone number')
        return v.strip()

    @validator('bank_used')
    def validate_bank(cls, v):
        if not v.strip():
            raise ValueError('Bank information is required')
        return v.strip()

    @validator('amount_donated')
    def validate_amount(cls, v):
        if not v.strip():
            raise ValueError('Amount is required')
        # Allow numbers with optional decimal and currency symbols, supporting both comma-separated and plain formats
        amount_pattern = r'^\d{1,3}(,\d{3})*(\.\d{1,2})?\s*(ETB|BIRR|USD|EUR)?$|^\d+(\.\d{1,2})?\s*(ETB|BIRR|USD|EUR)?$'
        if not re.match(amount_pattern, v.upper()):
            raise ValueError('Please enter a valid amount (e.g., 100, 1,000, 100.50, 100 ETB)')
        return v.strip()

class DonationSubmission(DonationSubmissionBase):
    id: int
    transaction_reference: Optional[str] = None
    proof_image_path: Optional[str] = None
    submitted_at: datetime
    is_verified: bool
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None

    class Config:
        from_attributes = True

class AdminLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class AdminCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @validator('username')
    def validate_username(cls, v):
        if not v.strip():
            raise ValueError('Username is required')
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v.strip()

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters')
        return v
