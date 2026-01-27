from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import math

from ..db import get_db
from .. import partimer_models as models
from .. import partimer_schemas as schemas
from .auth import get_current_user, require_role


# Configuration constant
DEFAULT_LEAD_PRICE = 3.0


router = APIRouter()


def get_employer_profile(user: models.User, db: Session) -> models.Employer:
    """Helper to get employer profile from user"""
    employer = db.query(models.Employer).filter(models.Employer.user_id == user.id).first()
    if not employer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employer profile not found"
        )
    return employer


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometers"""
    R = 6371.0  # Earth radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


# ============================================================================
# Employer Profile Endpoints
# ============================================================================

@router.get("/profile", response_model=schemas.EmployerProfileOut)
def get_profile(
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Get employer's own profile"""
    employer = get_employer_profile(current_user, db)
    return employer


@router.put("/profile", response_model=schemas.EmployerProfileOut)
def update_profile(
    payload: schemas.EmployerProfileCreate,
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Update employer profile"""
    employer = get_employer_profile(current_user, db)
    
    # Update fields
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employer, field, value)
    
    employer.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(employer)
    
    return employer


# ============================================================================
# Job Endpoints
# ============================================================================

@router.get("/jobs", response_model=List[schemas.JobOut])
def list_jobs(
    status: str = None,
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """List employer's jobs"""
    employer = get_employer_profile(current_user, db)
    
    query = db.query(models.Job).filter(models.Job.employer_id == employer.id)
    
    if status:
        try:
            job_status = models.JobStatus(status)
            query = query.filter(models.Job.status == job_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    jobs = query.order_by(models.Job.created_at.desc()).all()
    return jobs


@router.get("/jobs/{job_id}", response_model=schemas.JobOut)
def get_job(
    job_id: int,
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Get specific job"""
    employer = get_employer_profile(current_user, db)
    
    job = db.query(models.Job).filter(
        models.Job.id == job_id,
        models.Job.employer_id == employer.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return job


@router.post("/jobs", response_model=schemas.JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: schemas.JobCreate,
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Create a new job posting"""
    employer = get_employer_profile(current_user, db)
    
    # Check employer status
    if employer.status != models.EmployerStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot create jobs. Employer status: {employer.status.value}"
        )
    
    # Create job
    job = models.Job(
        employer_id=employer.id,
        **payload.model_dump()
    )
    db.add(job)
    
    # Update employer stats
    employer.total_jobs_posted += 1
    
    db.commit()
    db.refresh(job)
    
    return job


@router.put("/jobs/{job_id}", response_model=schemas.JobOut)
def update_job(
    job_id: int,
    payload: schemas.JobUpdate,
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Update job posting (limited fields, only if not yet published)"""
    employer = get_employer_profile(current_user, db)
    
    job = db.query(models.Job).filter(
        models.Job.id == job_id,
        models.Job.employer_id == employer.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Only allow updates if job is in draft or open status
    if job.status not in [models.JobStatus.DRAFT, models.JobStatus.OPEN]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update job with status: {job.status.value}"
        )
    
    # Update allowed fields
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)
    
    return job


@router.post("/jobs/{job_id}/publish", response_model=schemas.JobOut)
def publish_job(
    job_id: int,
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Publish a job and start matching process"""
    employer = get_employer_profile(current_user, db)
    
    job = db.query(models.Job).filter(
        models.Job.id == job_id,
        models.Job.employer_id == employer.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != models.JobStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is already {job.status.value}"
        )
    
    # Publish job
    job.status = models.JobStatus.OPEN
    job.published_at = datetime.utcnow()
    
    db.commit()
    db.refresh(job)
    
    # TODO: Trigger matching algorithm here
    
    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Cancel/delete a job (only if in draft status)"""
    employer = get_employer_profile(current_user, db)
    
    job = db.query(models.Job).filter(
        models.Job.id == job_id,
        models.Job.employer_id == employer.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Only allow deletion of draft jobs
    if job.status == models.JobStatus.DRAFT:
        db.delete(job)
    else:
        # Cancel published jobs instead of deleting
        job.status = models.JobStatus.CANCELLED
    
    db.commit()
    return None


# ============================================================================
# Job Matches / Leads Endpoints
# ============================================================================

@router.get("/jobs/{job_id}/matches", response_model=List[schemas.JobMatchEmployerView])
def get_job_matches(
    job_id: int,
    status: str = None,
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Get matches for a job (without contact details until payment)"""
    employer = get_employer_profile(current_user, db)
    
    job = db.query(models.Job).filter(
        models.Job.id == job_id,
        models.Job.employer_id == employer.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Build query for matches
    query = db.query(models.JobMatch).filter(models.JobMatch.job_id == job_id)
    
    # Filter by status if provided
    if status:
        try:
            match_status = models.MatchStatus(status)
            query = query.filter(models.JobMatch.status == match_status)
        except ValueError:
            # Show ACCEPTED matches by default if invalid status
            query = query.filter(models.JobMatch.status == models.MatchStatus.ACCEPTED)
    else:
        # Show ACCEPTED matches by default
        query = query.filter(models.JobMatch.status == models.MatchStatus.ACCEPTED)
    
    matches = query.all()
    
    result = []
    for match in matches:
        worker = db.query(models.Worker).filter(models.Worker.id == match.worker_id).first()
        if worker:
            result.append(schemas.JobMatchEmployerView(
                id=match.id,
                worker_id=worker.id,
                match_score=match.match_score,
                distance_km=match.distance_km,
                status=match.status,
                reliability_score=worker.reliability_score,
                experience_years=worker.experience_years,
                skills=worker.skills,
                lead_price=match.lead_price,
                is_unlocked=match.is_unlocked
            ))
    
    return result


@router.post("/matches/{match_id}/unlock", response_model=schemas.JobMatchEmployerUnlocked)
def unlock_match(
    match_id: int,
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Unlock worker contact details by paying for the lead"""
    employer = get_employer_profile(current_user, db)
    
    # Get match
    match = db.query(models.JobMatch).filter(models.JobMatch.id == match_id).first()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )
    
    # Verify match belongs to employer's job
    job = db.query(models.Job).filter(
        models.Job.id == match.job_id,
        models.Job.employer_id == employer.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This match does not belong to your jobs"
        )
    
    # Check if already unlocked
    if match.is_unlocked:
        # Already paid, return contact details
        worker = db.query(models.Worker).filter(models.Worker.id == match.worker_id).first()
        user = db.query(models.User).filter(models.User.id == worker.user_id).first()
        
        return schemas.JobMatchEmployerUnlocked(
            id=match.id,
            worker_id=worker.id,
            match_score=match.match_score,
            distance_km=match.distance_km,
            status=match.status,
            reliability_score=worker.reliability_score,
            experience_years=worker.experience_years,
            skills=worker.skills,
            lead_price=match.lead_price,
            is_unlocked=True,
            worker_full_name=worker.full_name,
            worker_phone=user.phone,
            worker_whatsapp=user.phone
        )
    
    # Check match status
    if match.status != models.MatchStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot unlock match with status: {match.status.value}"
        )
    
    # Create payment record (simplified - in production, integrate with payment gateway)
    payment = models.Payment(
        employer_id=employer.id,
        job_match_id=match.id,
        amount=match.lead_price,
        currency="MYR",
        payment_method="demo",
        transaction_id=f"DEMO_{match.id}_{datetime.utcnow().timestamp()}",
        status=models.PaymentStatus.COMPLETED,
        completed_at=datetime.utcnow()
    )
    db.add(payment)
    
    # Unlock the match
    match.is_unlocked = True
    match.unlocked_at = datetime.utcnow()
    match.status = models.MatchStatus.UNLOCKED
    
    # Update employer stats
    employer.total_leads_purchased += 1
    
    db.commit()
    db.refresh(match)
    
    # Get worker details
    worker = db.query(models.Worker).filter(models.Worker.id == match.worker_id).first()
    user = db.query(models.User).filter(models.User.id == worker.user_id).first()
    
    return schemas.JobMatchEmployerUnlocked(
        id=match.id,
        worker_id=worker.id,
        match_score=match.match_score,
        distance_km=match.distance_km,
        status=match.status,
        reliability_score=worker.reliability_score,
        experience_years=worker.experience_years,
        skills=worker.skills,
        lead_price=match.lead_price,
        is_unlocked=True,
        worker_full_name=worker.full_name,
        worker_phone=user.phone,
        worker_whatsapp=user.phone
    )


# ============================================================================
# Employer Dashboard Endpoints
# ============================================================================

@router.get("/dashboard", response_model=schemas.EmployerDashboardStats)
def get_dashboard(
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER)),
    db: Session = Depends(get_db)
):
    """Get employer dashboard statistics"""
    employer = get_employer_profile(current_user, db)
    
    active_jobs = db.query(models.Job).filter(
        models.Job.employer_id == employer.id,
        models.Job.status.in_([models.JobStatus.OPEN, models.JobStatus.MATCHING])
    ).count()
    
    # Count total matches available
    employer_jobs = db.query(models.Job.id).filter(
        models.Job.employer_id == employer.id
    ).all()
    job_ids = [j.id for j in employer_jobs]
    
    total_matches_available = db.query(models.JobMatch).filter(
        models.JobMatch.job_id.in_(job_ids),
        models.JobMatch.status == models.MatchStatus.ACCEPTED,
        models.JobMatch.is_unlocked == False
    ).count()
    
    # Calculate total spent
    payments = db.query(models.Payment).filter(
        models.Payment.employer_id == employer.id,
        models.Payment.status == models.PaymentStatus.COMPLETED
    ).all()
    
    total_spent = sum(payment.amount for payment in payments)
    
    return schemas.EmployerDashboardStats(
        active_jobs=active_jobs,
        total_matches_available=total_matches_available,
        total_leads_purchased=employer.total_leads_purchased,
        total_spent=round(total_spent, 2)
    )
