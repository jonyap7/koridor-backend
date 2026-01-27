from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import hashlib

from ..db import get_db
from .. import partimer_models as models
from .. import partimer_schemas as schemas


router = APIRouter()
security = HTTPBearer()


# Simple token storage (in production, use Redis or JWT with proper secrets)
# Format: {token: {user_id: int, role: str, expires_at: datetime}}
active_tokens = {}


def hash_password(password: str) -> str:
    """Simple password hashing (in production, use bcrypt or similar)"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed


def create_access_token(user_id: int, role: str) -> str:
    """Create a new access token"""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    active_tokens[token] = {
        "user_id": user_id,
        "role": role,
        "expires_at": expires_at
    }
    return token


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    
    if token not in active_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    token_data = active_tokens[token]
    
    if datetime.utcnow() > token_data["expires_at"]:
        del active_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    
    user = db.query(models.User).filter(models.User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


def require_role(*allowed_roles: models.UserRole):
    """Dependency factory to require specific roles"""
    def role_checker(current_user: models.User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {allowed_roles}"
            )
        return current_user
    return role_checker


# ============================================================================
# Registration Endpoints
# ============================================================================

@router.post("/register/worker", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def register_worker(payload: schemas.UserRegisterWorker, db: Session = Depends(get_db)):
    """Register a new worker with phone number (OTP would be sent in production)"""
    
    # Check if phone already exists
    existing = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Create user
    user = models.User(
        role=models.UserRole.WORKER,
        phone=payload.phone,
        whatsapp_consent=payload.whatsapp_consent
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create worker profile (minimal)
    worker = models.Worker(
        user_id=user.id,
        full_name="",  # Will be filled in profile completion
        city="",  # Will be filled in profile completion
        phone_verified=False  # Would be True after OTP verification
    )
    db.add(worker)
    db.commit()
    
    # Generate token
    token = create_access_token(user.id, user.role.value)
    
    return schemas.TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        role=user.role
    )


@router.post("/register/employer", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def register_employer(payload: schemas.UserRegisterEmployer, db: Session = Depends(get_db)):
    """Register a new employer with email/password"""
    
    # Check if email already exists
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = models.User(
        role=models.UserRole.EMPLOYER,
        email=payload.email,
        password_hash=hash_password(payload.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create employer profile
    employer = models.Employer(
        user_id=user.id,
        company_name=payload.company_name,
        contact_person=payload.contact_person,
        phone=payload.phone,
        city=payload.city,
        email_verified=False  # Would be verified via email link
    )
    db.add(employer)
    db.commit()
    
    # Generate token
    token = create_access_token(user.id, user.role.value)
    
    return schemas.TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        role=user.role
    )


# ============================================================================
# Login Endpoints
# ============================================================================

@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    """Login with email/password (employer) or phone/OTP (worker)"""
    
    user = None
    
    # Email/password login (employers)
    if payload.email and payload.password:
        user = db.query(models.User).filter(
            models.User.email == payload.email,
            models.User.role == models.UserRole.EMPLOYER
        ).first()
        
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
    
    # Phone/OTP login (workers)
    elif payload.phone and payload.otp:
        user = db.query(models.User).filter(
            models.User.phone == payload.phone,
            models.User.role == models.UserRole.WORKER
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid phone number"
            )
        
        # In production, verify OTP from SMS service
        # For now, accept any OTP (development only)
        if payload.otp != "123456":  # Simple check for demo
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OTP"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid login credentials format"
        )
    
    # Generate token
    token = create_access_token(user.id, user.role.value)
    
    return schemas.TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        role=user.role
    )


# ============================================================================
# Current User Endpoint
# ============================================================================

@router.get("/me")
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """Get current authenticated user info"""
    return {
        "id": current_user.id,
        "role": current_user.role,
        "phone": current_user.phone,
        "email": current_user.email,
        "created_at": current_user.created_at
    }


# ============================================================================
# Logout Endpoint
# ============================================================================

@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Logout and invalidate token"""
    token = credentials.credentials
    if token in active_tokens:
        del active_tokens[token]
    return {"message": "Logged out successfully"}
