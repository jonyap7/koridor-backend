from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..db import get_db
from .. import partimer_models as models
from .. import partimer_schemas as schemas
from .auth import get_current_user, require_role


router = APIRouter()


def get_worker_profile(user: models.User, db: Session) -> models.Worker:
    """Helper to get worker profile from user"""
    worker = db.query(models.Worker).filter(models.Worker.user_id == user.id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker profile not found"
        )
    return worker


# ============================================================================
# Worker Profile Endpoints
# ============================================================================

@router.get("/profile", response_model=schemas.WorkerProfileOut)
def get_profile(
    current_user: models.User = Depends(require_role(models.UserRole.WORKER)),
    db: Session = Depends(get_db)
):
    """Get worker's own profile"""
    worker = get_worker_profile(current_user, db)
    return worker


@router.put("/profile", response_model=schemas.WorkerProfileOut)
def update_profile(
    payload: schemas.WorkerProfileCreate,
    current_user: models.User = Depends(require_role(models.UserRole.WORKER)),
    db: Session = Depends(get_db)
):
    """Update worker profile"""
    worker = get_worker_profile(current_user, db)
    
    # Update fields
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(worker, field, value)
    
    worker.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(worker)
    
    return worker


# ============================================================================
# Worker Availability Endpoints
# ============================================================================

@router.get("/availability", response_model=List[schemas.WorkerAvailabilityOut])
def get_availability(
    current_user: models.User = Depends(require_role(models.UserRole.WORKER)),
    db: Session = Depends(get_db)
):
    """Get worker's availability schedule"""
    worker = get_worker_profile(current_user, db)
    availability = db.query(models.WorkerAvailability).filter(
        models.WorkerAvailability.worker_id == worker.id
    ).all()
    return availability


@router.post("/availability", response_model=schemas.WorkerAvailabilityOut, status_code=status.HTTP_201_CREATED)
def add_availability(
    payload: schemas.WorkerAvailabilityCreate,
    current_user: models.User = Depends(require_role(models.UserRole.WORKER)),
    db: Session = Depends(get_db)
):
    """Add availability slot"""
    worker = get_worker_profile(current_user, db)
    
    # Validate time range
    if payload.start_time >= payload.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time must be before end time"
        )
    
    # Check for overlapping slots on same day
    existing = db.query(models.WorkerAvailability).filter(
        models.WorkerAvailability.worker_id == worker.id,
        models.WorkerAvailability.day_of_week == payload.day_of_week,
        models.WorkerAvailability.is_active == True
    ).all()
    
    for slot in existing:
        if not (payload.end_time <= slot.start_time or payload.start_time >= slot.end_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Overlapping with existing slot on {payload.day_of_week}"
            )
    
    # Create new slot
    availability = models.WorkerAvailability(
        worker_id=worker.id,
        **payload.model_dump()
    )
    db.add(availability)
    db.commit()
    db.refresh(availability)
    
    return availability


@router.delete("/availability/{availability_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability(
    availability_id: int,
    current_user: models.User = Depends(require_role(models.UserRole.WORKER)),
    db: Session = Depends(get_db)
):
    """Delete availability slot"""
    worker = get_worker_profile(current_user, db)
    
    availability = db.query(models.WorkerAvailability).filter(
        models.WorkerAvailability.id == availability_id,
        models.WorkerAvailability.worker_id == worker.id
    ).first()
    
    if not availability:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability slot not found"
        )
    
    db.delete(availability)
    db.commit()
    
    return None


# ============================================================================
# Worker Job Offers Endpoints
# ============================================================================

@router.get("/offers", response_model=List[schemas.JobMatchWorkerView])
def get_job_offers(
    status: str = "pending",
    current_user: models.User = Depends(require_role(models.UserRole.WORKER)),
    db: Session = Depends(get_db)
):
    """Get job offers sent to worker"""
    worker = get_worker_profile(current_user, db)
    
    # Build query
    query = db.query(models.JobMatch).filter(
        models.JobMatch.worker_id == worker.id
    )
    
    # Filter by status
    if status == "pending":
        query = query.filter(models.JobMatch.status == models.MatchStatus.PENDING)
    elif status == "accepted":
        query = query.filter(models.JobMatch.status == models.MatchStatus.ACCEPTED)
    elif status == "rejected":
        query = query.filter(models.JobMatch.status == models.MatchStatus.REJECTED)
    
    matches = query.order_by(models.JobMatch.sent_at.desc()).all()
    
    # Build response with job details
    result = []
    for match in matches:
        job = db.query(models.Job).filter(models.Job.id == match.job_id).first()
        if job:
            result.append(schemas.JobMatchWorkerView(
                id=match.id,
                job_id=job.id,
                job_title=job.title,
                job_description=job.description,
                job_type=job.job_type,
                location=job.location,
                distance_km=match.distance_km,
                start_date=job.start_date,
                work_hours_start=job.work_hours_start,
                work_hours_end=job.work_hours_end,
                salary_amount=job.salary_amount,
                salary_period=job.salary_period,
                match_score=match.match_score,
                response_deadline=match.response_deadline,
                status=match.status
            ))
    
    return result


@router.post("/offers/{match_id}/respond", response_model=schemas.JobMatchOut)
def respond_to_offer(
    match_id: int,
    payload: schemas.WorkerResponseSubmit,
    current_user: models.User = Depends(require_role(models.UserRole.WORKER)),
    db: Session = Depends(get_db)
):
    """Worker responds to a job offer (YES or NO)"""
    worker = get_worker_profile(current_user, db)
    
    # Get match
    match = db.query(models.JobMatch).filter(
        models.JobMatch.id == match_id,
        models.JobMatch.worker_id == worker.id
    ).first()
    
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job offer not found"
        )
    
    # Check if already responded
    if match.status != models.MatchStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Offer already {match.status.value}"
        )
    
    # Check if deadline passed
    if models.datetime.utcnow() > match.response_deadline:
        match.status = models.MatchStatus.EXPIRED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Response deadline has passed"
        )
    
    # Update match with response
    match.worker_response = payload.response
    match.responded_at = models.datetime.utcnow()
    
    if payload.response == "yes":
        match.status = models.MatchStatus.ACCEPTED
        worker.total_jobs_accepted += 1
    else:
        match.status = models.MatchStatus.REJECTED
        worker.total_jobs_rejected += 1
    
    db.commit()
    db.refresh(match)
    
    return match


# ============================================================================
# Worker Dashboard Endpoints
# ============================================================================

@router.get("/dashboard", response_model=schemas.WorkerDashboardStats)
def get_dashboard(
    current_user: models.User = Depends(require_role(models.UserRole.WORKER)),
    db: Session = Depends(get_db)
):
    """Get worker dashboard statistics"""
    worker = get_worker_profile(current_user, db)
    
    pending_offers = db.query(models.JobMatch).filter(
        models.JobMatch.worker_id == worker.id,
        models.JobMatch.status == models.MatchStatus.PENDING
    ).count()
    
    accepted_jobs = db.query(models.JobMatch).filter(
        models.JobMatch.worker_id == worker.id,
        models.JobMatch.status == models.MatchStatus.ACCEPTED
    ).count()
    
    # Calculate estimated earnings (informational only)
    accepted_matches = db.query(models.JobMatch).filter(
        models.JobMatch.worker_id == worker.id,
        models.JobMatch.status == models.MatchStatus.ACCEPTED
    ).all()
    
    total_earnings_estimate = 0.0
    for match in accepted_matches:
        job = db.query(models.Job).filter(models.Job.id == match.job_id).first()
        if job:
            # Calculate hours based on actual work hours
            start_hour, start_min = map(int, job.work_hours_start.split(':'))
            end_hour, end_min = map(int, job.work_hours_end.split(':'))
            hours = (end_hour + end_min / 60.0) - (start_hour + start_min / 60.0)
            
            # Estimate based on job's salary period
            if job.salary_period == "hourly":
                total_earnings_estimate += job.salary_amount * hours
            elif job.salary_period == "daily":
                total_earnings_estimate += job.salary_amount
            else:  # per_job
                total_earnings_estimate += job.salary_amount
    
    return schemas.WorkerDashboardStats(
        pending_offers=pending_offers,
        accepted_jobs=accepted_jobs,
        total_earnings_estimate=round(total_earnings_estimate, 2),
        reliability_score=worker.reliability_score
    )
