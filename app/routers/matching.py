from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from ..db import get_db
from .. import partimer_models as models
from ..matching_service import trigger_matching_for_job, handle_expired_matches
from .auth import get_current_user, require_role


router = APIRouter()


@router.post("/jobs/{job_id}/trigger")
def trigger_job_matching(
    job_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(require_role(models.UserRole.EMPLOYER, models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Manually trigger matching for a job"""
    
    # Get job and verify ownership (if employer)
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # If employer, verify ownership
    if current_user.role == models.UserRole.EMPLOYER:
        employer = db.query(models.Employer).filter(models.Employer.user_id == current_user.id).first()
        if not employer or job.employer_id != employer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to trigger matching for this job"
            )
    
    # Trigger matching
    result = trigger_matching_for_job(job_id, db)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.post("/expire-matches")
def expire_old_matches(
    current_user: models.User = Depends(require_role(models.UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    """Admin endpoint to expire matches that have passed their deadline"""
    
    count = handle_expired_matches(db)
    
    return {
        "message": f"Marked {count} matches as expired"
    }
