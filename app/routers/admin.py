from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..db import get_db
from .. import partimer_models as models
from .. import partimer_schemas as schemas
from .auth import get_current_user, require_role
from datetime import datetime


router = APIRouter()


# ============================================================================
# Admin Worker Management
# ============================================================================

@router.get("/workers", response_model=List[schemas.WorkerProfileOut])
def list_workers(
    status: str = None,
    city: str = None,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """List all workers with optional filters"""
    query = db.query(models.Worker)
    
    if status:
        try:
            worker_status = models.WorkerStatus(status)
            query = query.filter(models.Worker.status == worker_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    if city:
        query = query.filter(models.Worker.city == city)
    
    workers = query.order_by(models.Worker.created_at.desc()).all()
    return workers


@router.get("/workers/{worker_id}", response_model=schemas.WorkerProfileOut)
def get_worker(
    worker_id: int,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get specific worker details"""
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    return worker


@router.post("/workers/{worker_id}/action", response_model=schemas.WorkerProfileOut)
def worker_action(
    worker_id: int,
    payload: schemas.AdminWorkerAction,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Perform admin action on worker"""
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found"
        )
    
    # Perform action
    if payload.action == "activate":
        worker.status = models.WorkerStatus.ACTIVE
    elif payload.action == "suspend":
        worker.status = models.WorkerStatus.SUSPENDED
    elif payload.action == "verify_identity":
        worker.identity_verified = True
    
    worker.updated_at = datetime.utcnow()
    
    # Log action
    log = models.AdminActionLog(
        admin_user_id=current_user.id,
        action_type=payload.action,
        target_type="worker",
        target_id=worker_id,
        reason=payload.reason
    )
    db.add(log)
    
    db.commit()
    db.refresh(worker)
    
    return worker


# ============================================================================
# Admin Employer Management
# ============================================================================

@router.get("/employers", response_model=List[schemas.EmployerProfileOut])
def list_employers(
    status: str = None,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """List all employers with optional filters"""
    query = db.query(models.Employer)
    
    if status:
        try:
            employer_status = models.EmployerStatus(status)
            query = query.filter(models.Employer.status == employer_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    
    employers = query.order_by(models.Employer.created_at.desc()).all()
    return employers


@router.get("/employers/{employer_id}", response_model=schemas.EmployerProfileOut)
def get_employer(
    employer_id: int,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get specific employer details"""
    employer = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    
    if not employer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employer not found"
        )
    
    return employer


@router.post("/employers/{employer_id}/action", response_model=schemas.EmployerProfileOut)
def employer_action(
    employer_id: int,
    payload: schemas.AdminEmployerAction,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Perform admin action on employer"""
    employer = db.query(models.Employer).filter(models.Employer.id == employer_id).first()
    
    if not employer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employer not found"
        )
    
    # Perform action
    if payload.action == "activate":
        employer.status = models.EmployerStatus.ACTIVE
    elif payload.action == "suspend":
        employer.status = models.EmployerStatus.SUSPENDED
    elif payload.action == "restrict":
        employer.status = models.EmployerStatus.RESTRICTED
    elif payload.action == "verify_identity":
        employer.identity_verified = True
    
    employer.updated_at = datetime.utcnow()
    
    # Log action
    log = models.AdminActionLog(
        admin_user_id=current_user.id,
        action_type=payload.action,
        target_type="employer",
        target_id=employer_id,
        reason=payload.reason
    )
    db.add(log)
    
    db.commit()
    db.refresh(employer)
    
    return employer


# ============================================================================
# Admin Job Management
# ============================================================================

@router.get("/jobs", response_model=List[schemas.JobOut])
def list_jobs(
    status: str = None,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """List all jobs with optional filters"""
    query = db.query(models.Job)
    
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


@router.post("/jobs/{job_id}/action", response_model=schemas.JobOut)
def job_action(
    job_id: int,
    payload: schemas.AdminJobAction,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Perform admin action on job"""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Perform action
    if payload.action == "cancel":
        job.status = models.JobStatus.CANCELLED
    elif payload.action == "reopen":
        job.status = models.JobStatus.OPEN
    
    job.updated_at = datetime.utcnow()
    
    # Log action
    log = models.AdminActionLog(
        admin_user_id=current_user.id,
        action_type=payload.action,
        target_type="job",
        target_id=job_id,
        reason=payload.reason
    )
    db.add(log)
    
    db.commit()
    db.refresh(job)
    
    return job


# ============================================================================
# Admin Logs and Statistics
# ============================================================================

@router.get("/logs", response_model=List[schemas.AdminActionLogOut])
def get_action_logs(
    limit: int = 100,
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get recent admin action logs"""
    logs = db.query(models.AdminActionLog).order_by(
        models.AdminActionLog.created_at.desc()
    ).limit(limit).all()
    
    return logs


@router.get("/stats", response_model=schemas.SystemStats)
def get_system_stats(
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Get system-wide statistics"""
    
    total_workers = db.query(models.Worker).count()
    active_workers = db.query(models.Worker).filter(
        models.Worker.status == models.WorkerStatus.ACTIVE
    ).count()
    
    total_employers = db.query(models.Employer).count()
    active_employers = db.query(models.Employer).filter(
        models.Employer.status == models.EmployerStatus.ACTIVE
    ).count()
    
    total_jobs = db.query(models.Job).count()
    active_jobs = db.query(models.Job).filter(
        models.Job.status.in_([models.JobStatus.OPEN, models.JobStatus.MATCHING])
    ).count()
    
    total_matches = db.query(models.JobMatch).count()
    
    total_payments = db.query(models.Payment).filter(
        models.Payment.status == models.PaymentStatus.COMPLETED
    ).count()
    
    total_revenue = total_payments * 3.0  # Simplified
    
    return schemas.SystemStats(
        total_workers=total_workers,
        active_workers=active_workers,
        total_employers=total_employers,
        active_employers=active_employers,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_matches=total_matches,
        total_payments=total_payments,
        total_revenue=round(total_revenue, 2)
    )
