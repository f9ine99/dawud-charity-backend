from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from datetime import datetime
import uuid

# Import Base from database module to ensure consistency
from database import Base

class DonationSubmission(Base):
    __tablename__ = "donation_submissions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_reference = Column(String, unique=True, index=True, nullable=True)
    donor_name = Column(String, nullable=False)
    donor_contact = Column(String, nullable=False)  # Email or phone
    bank_used = Column(String, nullable=False)
    amount_donated = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    proof_image_path = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)
    verified_by = Column(String, nullable=True)  # Admin username who verified

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
