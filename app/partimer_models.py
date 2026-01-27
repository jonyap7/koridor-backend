from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .db import Base


# Enums
class UserRole(str, enum.Enum):
    WORKER = "worker"
    EMPLOYER = "employer"
    ADMIN = "admin"


class WorkerStatus(str, enum.Enum):
    PENDING = "pending"  # Just registered
    ACTIVE = "active"  # Verified and can receive offers
    INACTIVE = "inactive"  # Temporarily unavailable
    SUSPENDED = "suspended"  # Admin action


class EmployerStatus(str, enum.Enum):
    PENDING = "pending"  # Just registered
    ACTIVE = "active"  # Can post jobs
    RESTRICTED = "restricted"  # Limited access due to abuse
    SUSPENDED = "suspended"  # Admin action


class JobStatus(str, enum.Enum):
    DRAFT = "draft"  # Created but not published
    OPEN = "open"  # Published, seeking workers
    MATCHING = "matching"  # System finding matches
    FILLED = "filled"  # Worker(s) accepted
    CANCELLED = "cancelled"  # Cancelled by employer or admin
    COMPLETED = "completed"  # Job done


class MatchStatus(str, enum.Enum):
    PENDING = "pending"  # Sent to worker, awaiting response
    ACCEPTED = "accepted"  # Worker accepted
    REJECTED = "rejected"  # Worker rejected
    EXPIRED = "expired"  # Response deadline passed
    UNLOCKED = "unlocked"  # Employer paid and unlocked contact


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class DayOfWeek(str, enum.Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


# Models
class User(Base):
    """Base user table - all users (workers, employers, admins) have an entry here"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(SQLEnum(UserRole), nullable=False)
    phone = Column(String(20), unique=True, nullable=True, index=True)  # For workers
    email = Column(String(255), unique=True, nullable=True, index=True)  # For employers/admins
    password_hash = Column(String(255), nullable=True)  # For email/password auth
    whatsapp_consent = Column(Boolean, default=False)  # Explicit WhatsApp consent
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    worker_profile = relationship("Worker", back_populates="user", uselist=False)
    employer_profile = relationship("Employer", back_populates="user", uselist=False)


class Worker(Base):
    """Worker profile and verification details"""
    __tablename__ = "workers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Personal details
    full_name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)
    
    # Location
    city = Column(String(100), nullable=False, index=True)
    area = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    max_commute_km = Column(Float, default=10.0)  # Maximum distance willing to travel
    
    # Skills and experience
    skills = Column(Text, nullable=True)  # Comma-separated or JSON
    experience_years = Column(Integer, default=0)
    languages = Column(String(255), nullable=True)  # Comma-separated
    
    # Verification and reliability
    phone_verified = Column(Boolean, default=False)
    identity_verified = Column(Boolean, default=False)  # Manual admin verification
    reliability_score = Column(Float, default=0.0)  # 0-10 scale
    total_jobs_completed = Column(Integer, default=0)
    total_jobs_accepted = Column(Integer, default=0)
    total_jobs_rejected = Column(Integer, default=0)
    
    # Status
    status = Column(SQLEnum(WorkerStatus), default=WorkerStatus.PENDING, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="worker_profile")
    availability = relationship("WorkerAvailability", back_populates="worker", cascade="all, delete-orphan")
    job_matches = relationship("JobMatch", back_populates="worker")


class WorkerAvailability(Base):
    """Worker availability schedule"""
    __tablename__ = "worker_availability"
    
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    
    # Time availability
    day_of_week = Column(SQLEnum(DayOfWeek), nullable=False)
    start_time = Column(String(10), nullable=False)  # Format: "HH:MM"
    end_time = Column(String(10), nullable=False)  # Format: "HH:MM"
    
    # Active/inactive
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    worker = relationship("Worker", back_populates="availability")


class Employer(Base):
    """Employer profile"""
    __tablename__ = "employers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Business details
    company_name = Column(String(255), nullable=False)
    contact_person = Column(String(255), nullable=False)
    business_type = Column(String(100), nullable=True)
    
    # Contact
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=False, index=True)
    
    # Verification and trust
    email_verified = Column(Boolean, default=False)
    identity_verified = Column(Boolean, default=False)
    trust_score = Column(Float, default=5.0)  # 0-10 scale
    
    # Usage stats
    total_jobs_posted = Column(Integer, default=0)
    total_leads_purchased = Column(Integer, default=0)
    
    # Status and abuse flags
    status = Column(SQLEnum(EmployerStatus), default=EmployerStatus.PENDING, index=True)
    abuse_reports_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="employer_profile")
    jobs = relationship("Job", back_populates="employer")
    payments = relationship("Payment", back_populates="employer")


class Job(Base):
    """Job posting - the employer's request for part-time workers"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    
    # Job details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    job_type = Column(String(100), nullable=False)  # e.g., "delivery", "cashier", "packing"
    
    # Location
    location = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Time requirements
    start_date = Column(String(20), nullable=False)  # Format: "YYYY-MM-DD"
    end_date = Column(String(20), nullable=True)  # For recurring jobs
    work_days = Column(String(255), nullable=True)  # Comma-separated days
    work_hours_start = Column(String(10), nullable=False)  # Format: "HH:MM"
    work_hours_end = Column(String(10), nullable=False)  # Format: "HH:MM"
    
    # Requirements
    required_skills = Column(Text, nullable=True)
    min_age = Column(Integer, nullable=True)
    gender_preference = Column(String(20), nullable=True)  # "male", "female", "any"
    
    # Salary (INFORMATIONAL ONLY - not used for payment)
    salary_amount = Column(Float, nullable=False)
    salary_period = Column(String(20), default="hourly")  # "hourly", "daily", "per_job"
    
    # Workers needed
    workers_needed = Column(Integer, default=1)
    workers_matched = Column(Integer, default=0)
    
    # Status
    status = Column(SQLEnum(JobStatus), default=JobStatus.DRAFT, index=True)
    
    # Matching configuration
    max_radius_km = Column(Float, default=10.0)  # Max distance for matching workers
    response_deadline_hours = Column(Integer, default=24)  # Hours for worker to respond
    
    # Metadata
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employer = relationship("Employer", back_populates="jobs")
    job_matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")


class JobMatch(Base):
    """Job Match / Lead - the core product that gets sold"""
    __tablename__ = "job_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    
    # Matching score and details
    match_score = Column(Float, nullable=False)  # Algorithmic score
    distance_km = Column(Float, nullable=False)
    
    # Response tracking
    status = Column(SQLEnum(MatchStatus), default=MatchStatus.PENDING, index=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    response_deadline = Column(DateTime, nullable=False)
    responded_at = Column(DateTime, nullable=True)
    worker_response = Column(String(10), nullable=True)  # "yes" or "no"
    
    # Contact unlock tracking
    is_unlocked = Column(Boolean, default=False)  # Has employer paid to see contact?
    unlocked_at = Column(DateTime, nullable=True)
    
    # Lead pricing
    lead_price = Column(Float, default=3.0)  # Price employer pays to unlock this lead
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="job_matches")
    worker = relationship("Worker", back_populates="job_matches")
    payment = relationship("Payment", back_populates="job_match", uselist=False)


class Payment(Base):
    """Payment records - lead-based payment model"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    employer_id = Column(Integer, ForeignKey("employers.id"), nullable=False, index=True)
    job_match_id = Column(Integer, ForeignKey("job_matches.id"), nullable=False, unique=True)
    
    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="MYR")
    
    # Payment gateway details
    payment_method = Column(String(50), nullable=True)
    transaction_id = Column(String(255), nullable=True, unique=True)
    payment_gateway_response = Column(Text, nullable=True)  # JSON
    
    # Status
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    
    # Metadata
    initiated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    employer = relationship("Employer", back_populates="payments")
    job_match = relationship("JobMatch", back_populates="payment")


class AdminActionLog(Base):
    """Audit log for admin actions"""
    __tablename__ = "admin_action_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Action details
    action_type = Column(String(50), nullable=False, index=True)  # e.g., "suspend_worker", "cancel_job"
    target_type = Column(String(50), nullable=False)  # e.g., "worker", "employer", "job"
    target_id = Column(Integer, nullable=False)
    
    # Context
    reason = Column(Text, nullable=True)
    details = Column(Text, nullable=True)  # JSON for additional context
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
