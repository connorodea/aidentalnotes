"""
auth.py - Authentication and Licensing for AI Dental Note Generator

This module handles JWT validation, license checking, and rate limiting.
"""
import os
import time
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional, Union
from fastapi import HTTPException, status
from collections import defaultdict
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aidentalnotes.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# License model
class License(Base):
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    plan_type = Column(String)  # "starter", "pro", "enterprise"
    active = Column(Boolean, default=True)
    notes_limit = Column(Integer)
    notes_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    stripe_customer_id = Column(String)
    stripe_subscription_id = Column(String)

# Create tables
Base.metadata.create_all(bind=engine)

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))

def create_token(user_id: str, email: str, plan_type: str) -> str:
    """
    Create a JWT token for a user.
    
    Args:
        user_id: The unique identifier for the user
        email: The user's email address
        plan_type: The subscription plan type
        
    Returns:
        str: A JWT token
    """
    expires = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode = {
        "sub": user_id,
        "email": email,
        "plan": plan_type,
        "exp": expires
    }
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> Dict:
    """
    Verify a JWT token and check license status.
    
    Args:
        token: The JWT token from the Authorization header
        
    Returns:
        dict: The decoded token payload
        
    Raises:
        HTTPException: If the token is invalid or license is inactive
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract the token from Bearer format
    if token.startswith("Bearer "):
        token = token[7:]
    
    try:
        # Decode and verify the token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Check if token is expired
        if datetime.fromtimestamp(payload["exp"]) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify license is active and has usage available
        db = SessionLocal()
        try:
            license = db.query(License).filter(License.user_id == payload["sub"]).first()
            
            if not license:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid license. Please subscribe.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if not license.active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Your license is inactive. Please renew your subscription.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            if license.notes_used >= license.notes_limit:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You have reached your monthly note generation limit. Please upgrade your plan.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Increment usage count
            license.notes_used += 1
            db.commit()
            
        finally:
            db.close()
        
        return payload
        
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

class RateLimiter:
    """
    Simple in-memory rate limiter for API endpoints.
    """
    def __init__(self, limit: int, window: int):
        """
        Initialize the rate limiter.
        
        Args:
            limit: Maximum number of requests allowed per window
            window: Time window in seconds
        """
        self.limit = limit
        self.window = window
        self.requests = defaultdict(list)
    
    def allow_request(self, identifier: str) -> bool:
        """
        Check if a request from the identifier is allowed.
        
        Args:
            identifier: A unique identifier (user ID or IP address)
            
        Returns:
            bool: True if the request is allowed, False otherwise
        """
        current_time = time.time()
        
        # Remove old requests outside the current window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < self.window
        ]
        
        # Check if the number of requests is below the limit
        if len(self.requests[identifier]) < self.limit:
            self.requests[identifier].append(current_time)
            return True
        
        return False

def create_license(
    user_id: str,
    email: str,
    plan_type: str,
    notes_limit: int,
    stripe_customer_id: str,
    stripe_subscription_id: str
) -> License:
    """
    Create a new license in the database.
    
    Args:
        user_id: The unique identifier for the user
        email: The user's email address
        plan_type: The subscription plan type
        notes_limit: Monthly note generation limit
        stripe_customer_id: Stripe customer ID
        stripe_subscription_id: Stripe subscription ID
        
    Returns:
        License: The newly created license
    """
    db = SessionLocal()
    try:
        # Check if license already exists
        existing_license = db.query(License).filter(License.user_id == user_id).first()
        if existing_license:
            # Update existing license
            existing_license.plan_type = plan_type
            existing_license.active = True
            existing_license.notes_limit = notes_limit
            existing_license.notes_used = 0
            existing_license.expires_at = datetime.utcnow() + timedelta(days=30)
            existing_license.stripe_customer_id = stripe_customer_id
            existing_license.stripe_subscription_id = stripe_subscription_id
            db.commit()
            return existing_license
        
        # Create new license
        new_license = License(
            user_id=user_id,
            email=email,
            plan_type=plan_type,
            active=True,
            notes_limit=notes_limit,
            notes_used=0,
            expires_at=datetime.utcnow() + timedelta(days=30),
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id
        )
        db.add(new_license)
        db.commit()
        db.refresh(new_license)
        return new_license
    finally:
        db.close()

def update_license_status(stripe_subscription_id: str, active: bool) -> Optional[License]:
    """
    Update the active status of a license by Stripe subscription ID.
    
    Args:
        stripe_subscription_id: The Stripe subscription ID
        active: The new active status
        
    Returns:
        License: The updated license or None if not found
    """
    db = SessionLocal()
    try:
        license = db.query(License).filter(License.stripe_subscription_id == stripe_subscription_id).first()
        if license:
            license.active = active
            db.commit()
            db.refresh(license)
        return license
    finally:
        db.close()

def reset_monthly_usage() -> None:
    """
    Reset the monthly usage for all active licenses.
    Should be called by a scheduled task at the beginning of each billing cycle.
    """
    db = SessionLocal()
    try:
        # Get the current time
        now = datetime.utcnow()
        
        # Find all licenses that need to be reset
        # This includes active licenses whose billing cycle has ended
        expired_licenses = db.query(License).filter(
            License.active == True,
            License.expires_at < now
        ).all()
        
        # Reset usage for each license and set new expiration date
        for license in expired_licenses:
            license.notes_used = 0
            license.expires_at = now + timedelta(days=30)
            
            # Log the reset for auditing purposes
            print(f"Reset usage for license ID {license.id} (user: {license.email})")
        
        # Commit the changes
        db.commit()
        
        # Return the number of licenses reset
        return len(expired_licenses)
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_usage_statistics() -> dict:
    """
    Get usage statistics for all active licenses.
    
    Returns:
        dict: Usage statistics by plan type
    """
    db = SessionLocal()
    try:
        stats = {
            "total_users": 0,
            "total_notes_used": 0,
            "plan_breakdown": {
                "starter": {"users": 0, "notes_used": 0, "notes_limit": 0},
                "pro": {"users": 0, "notes_used": 0, "notes_limit": 0},
                "enterprise": {"users": 0, "notes_used": 0, "notes_limit": 0}
            }
        }
        
        # Query all active licenses
        active_licenses = db.query(License).filter(License.active == True).all()
        
        # Update statistics
        for license in active_licenses:
            stats["total_users"] += 1
            stats["total_notes_used"] += license.notes_used
            
            plan = license.plan_type.lower()
            if plan in stats["plan_breakdown"]:
                stats["plan_breakdown"][plan]["users"] += 1
                stats["plan_breakdown"][plan]["notes_used"] += license.notes_used
                stats["plan_breakdown"][plan]["notes_limit"] += license.notes_limit
        
        return stats
    finally:
        db.close()
