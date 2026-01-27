from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from .partimer_models import (
    UserRole, WorkerStatus, EmployerStatus, JobStatus, 
    MatchStatus, PaymentStatus, DayOfWeek
)


# ============================================================================
# Auth Schemas
# ============================================================================

class UserRegisterWorker(BaseModel):
    """Worker registration via phone"""
    phone: str = Field(..., min_length=10, max_length=20)
    whatsapp_consent: bool = Field(default=False)


class UserRegisterEmployer(BaseModel):
    """Employer registration via email/password"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    company_name: str = Field(..., min_length=2)
    contact_person: str = Field(..., min_length=2)
    phone: str = Field(..., min_length=10, max_length=20)
    city: str = Field(..., min_length=2)


class UserLogin(BaseModel):
    """Login credentials"""
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    otp: Optional[str] = None


class TokenResponse(BaseModel):
    """Auth token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: UserRole


# ============================================================================
# Worker Schemas
# ============================================================================

class WorkerProfileCreate(BaseModel):
    """Create/Update worker profile"""
    full_name: str = Field(..., min_length=2, max_length=255)
    age: Optional[int] = Field(None, ge=16, le=100)
    gender: Optional[str] = None
    city: str = Field(..., min_length=2)
    area: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    max_commute_km: float = Field(10.0, ge=0, le=100)
    skills: Optional[str] = None
    experience_years: int = Field(0, ge=0, le=50)
    languages: Optional[str] = None


class WorkerProfileOut(BaseModel):
    """Worker profile response"""
    id: int
    user_id: int
    full_name: str
    age: Optional[int]
    gender: Optional[str]
    city: str
    area: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    max_commute_km: float
    skills: Optional[str]
    experience_years: int
    languages: Optional[str]
    phone_verified: bool
    identity_verified: bool
    reliability_score: float
    total_jobs_completed: int
    total_jobs_accepted: int
    total_jobs_rejected: int
    status: WorkerStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WorkerAvailabilityCreate(BaseModel):
    """Create worker availability slot"""
    day_of_week: DayOfWeek
    start_time: str = Field(..., pattern=r'^([01]\d|2[0-3]):([0-5]\d)$')
    end_time: str = Field(..., pattern=r'^([01]\d|2[0-3]):([0-5]\d)$')
    is_active: bool = True


class WorkerAvailabilityOut(BaseModel):
    """Worker availability response"""
    id: int
    worker_id: int
    day_of_week: DayOfWeek
    start_time: str
    end_time: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class WorkerDashboardStats(BaseModel):
    """Worker dashboard statistics"""
    pending_offers: int
    accepted_jobs: int
    total_earnings_estimate: float  # Informational only
    reliability_score: float


# ============================================================================
# Employer Schemas
# ============================================================================

class EmployerProfileCreate(BaseModel):
    """Create/Update employer profile"""
    company_name: str = Field(..., min_length=2, max_length=255)
    contact_person: str = Field(..., min_length=2, max_length=255)
    business_type: Optional[str] = None
    phone: str = Field(..., min_length=10, max_length=20)
    address: Optional[str] = None
    city: str = Field(..., min_length=2)


class EmployerProfileOut(BaseModel):
    """Employer profile response"""
    id: int
    user_id: int
    company_name: str
    contact_person: str
    business_type: Optional[str]
    phone: str
    address: Optional[str]
    city: str
    email_verified: bool
    identity_verified: bool
    trust_score: float
    total_jobs_posted: int
    total_leads_purchased: int
    status: EmployerStatus
    abuse_reports_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EmployerDashboardStats(BaseModel):
    """Employer dashboard statistics"""
    active_jobs: int
    total_matches_available: int
    total_leads_purchased: int
    total_spent: float


# ============================================================================
# Job Schemas
# ============================================================================

class JobCreate(BaseModel):
    """Create a new job posting"""
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    job_type: str = Field(..., min_length=2)
    location: str = Field(..., min_length=5)
    city: str = Field(..., min_length=2)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    start_date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    end_date: Optional[str] = Field(None, pattern=r'^\d{4}-\d{2}-\d{2}$')
    work_days: Optional[str] = None
    work_hours_start: str = Field(..., pattern=r'^([01]\d|2[0-3]):([0-5]\d)$')
    work_hours_end: str = Field(..., pattern=r'^([01]\d|2[0-3]):([0-5]\d)$')
    required_skills: Optional[str] = None
    min_age: Optional[int] = Field(None, ge=16, le=100)
    gender_preference: Optional[str] = Field(None, pattern=r'^(male|female|any)$')
    salary_amount: float = Field(..., gt=0)
    salary_period: str = Field("hourly", pattern=r'^(hourly|daily|per_job)$')
    workers_needed: int = Field(1, ge=1, le=100)
    max_radius_km: float = Field(10.0, ge=1, le=100)
    response_deadline_hours: int = Field(24, ge=1, le=168)


class JobUpdate(BaseModel):
    """Update job posting (limited fields)"""
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=20)
    salary_amount: Optional[float] = Field(None, gt=0)
    workers_needed: Optional[int] = Field(None, ge=1, le=100)


class JobOut(BaseModel):
    """Job response"""
    id: int
    employer_id: int
    title: str
    description: str
    job_type: str
    location: str
    city: str
    latitude: Optional[float]
    longitude: Optional[float]
    start_date: str
    end_date: Optional[str]
    work_days: Optional[str]
    work_hours_start: str
    work_hours_end: str
    required_skills: Optional[str]
    min_age: Optional[int]
    gender_preference: Optional[str]
    salary_amount: float
    salary_period: str
    workers_needed: int
    workers_matched: int
    status: JobStatus
    max_radius_km: float
    response_deadline_hours: int
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Job Match / Lead Schemas
# ============================================================================

class JobMatchOut(BaseModel):
    """Job match response (MINIMAL for worker, FULL after payment for employer)"""
    id: int
    job_id: int
    worker_id: int
    match_score: float
    distance_km: float
    status: MatchStatus
    sent_at: datetime
    response_deadline: datetime
    responded_at: Optional[datetime]
    worker_response: Optional[str]
    is_unlocked: bool
    lead_price: float
    
    class Config:
        from_attributes = True


class JobMatchWorkerView(BaseModel):
    """Worker's view of a job offer"""
    id: int
    job_id: int
    job_title: str
    job_description: str
    job_type: str
    location: str
    distance_km: float
    start_date: str
    work_hours_start: str
    work_hours_end: str
    salary_amount: float
    salary_period: str
    match_score: float
    response_deadline: datetime
    status: MatchStatus


class JobMatchEmployerView(BaseModel):
    """Employer's view of a match (before unlock)"""
    id: int
    worker_id: int
    match_score: float
    distance_km: float
    status: MatchStatus
    reliability_score: float
    experience_years: int
    skills: Optional[str]
    lead_price: float
    is_unlocked: bool
    # No contact details until payment


class JobMatchEmployerUnlocked(JobMatchEmployerView):
    """Employer's view after payment"""
    worker_full_name: str
    worker_phone: str
    worker_whatsapp: str


class WorkerResponseSubmit(BaseModel):
    """Worker's response to a job offer"""
    response: str = Field(..., pattern=r'^(yes|no)$')


# ============================================================================
# Payment Schemas
# ============================================================================

class PaymentInitiate(BaseModel):
    """Initiate payment for a lead"""
    job_match_id: int
    payment_method: str = "stripe"  # Could be extended


class PaymentOut(BaseModel):
    """Payment response"""
    id: int
    employer_id: int
    job_match_id: int
    amount: float
    currency: str
    payment_method: Optional[str]
    transaction_id: Optional[str]
    status: PaymentStatus
    initiated_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============================================================================
# Admin Schemas
# ============================================================================

class AdminActionCreate(BaseModel):
    """Create admin action log"""
    action_type: str = Field(..., min_length=2)
    target_type: str = Field(..., min_length=2)
    target_id: int
    reason: Optional[str] = None
    details: Optional[str] = None


class AdminActionLogOut(BaseModel):
    """Admin action log response"""
    id: int
    admin_user_id: int
    action_type: str
    target_type: str
    target_id: int
    reason: Optional[str]
    details: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdminWorkerAction(BaseModel):
    """Admin action on worker"""
    action: str = Field(..., pattern=r'^(activate|suspend|verify_identity)$')
    reason: Optional[str] = None


class AdminEmployerAction(BaseModel):
    """Admin action on employer"""
    action: str = Field(..., pattern=r'^(activate|suspend|restrict|verify_identity)$')
    reason: Optional[str] = None


class AdminJobAction(BaseModel):
    """Admin action on job"""
    action: str = Field(..., pattern=r'^(cancel|reopen)$')
    reason: Optional[str] = None


# ============================================================================
# System / Internal Schemas
# ============================================================================

class MatchingConfig(BaseModel):
    """Configuration for matching algorithm"""
    max_radius_km: float = Field(10.0, ge=1, le=100)
    min_match_score: float = Field(0.5, ge=0, le=1)
    response_deadline_hours: int = Field(24, ge=1, le=168)


class SystemStats(BaseModel):
    """System-wide statistics"""
    total_workers: int
    active_workers: int
    total_employers: int
    active_employers: int
    total_jobs: int
    active_jobs: int
    total_matches: int
    total_payments: int
    total_revenue: float
