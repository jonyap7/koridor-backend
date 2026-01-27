"""
Matching Service - Core algorithm for matching jobs with workers

This service implements Phase 9 of the master prompt:
- Availability + time matching
- Location radius filtering
- Job_match creation
- Response deadline handling
- Match scoring
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import math
from typing import List, Tuple

from . import partimer_models as models


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


def parse_time(time_str: str) -> Tuple[int, int]:
    """Parse time string 'HH:MM' to (hour, minute)"""
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


def time_to_minutes(time_str: str) -> int:
    """Convert time string 'HH:MM' to minutes since midnight"""
    hour, minute = parse_time(time_str)
    return hour * 60 + minute


def check_time_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    """Check if two time ranges overlap"""
    start1_mins = time_to_minutes(start1)
    end1_mins = time_to_minutes(end1)
    start2_mins = time_to_minutes(start2)
    end2_mins = time_to_minutes(end2)
    
    return not (end1_mins <= start2_mins or end2_mins <= start1_mins)


def check_day_match(job_days: str, availability_day: models.DayOfWeek) -> bool:
    """Check if job days include the availability day"""
    if not job_days:
        return True  # No restriction
    
    job_days_list = [d.strip().lower() for d in job_days.split(",")]
    return availability_day.value.lower() in job_days_list


def calculate_match_score(
    worker: models.Worker,
    job: models.Job,
    distance_km: float,
    skill_match: float
) -> float:
    """
    Calculate match score between worker and job
    
    Factors:
    - Distance (closer is better)
    - Reliability score (higher is better)
    - Experience (more is better)
    - Skill match (better match is better)
    
    Returns: Score between 0 and 1
    """
    # Distance score (inverse relationship, normalized to max_radius)
    distance_score = max(0, 1 - (distance_km / job.max_radius_km))
    
    # Reliability score (normalized to 0-1)
    reliability_score = worker.reliability_score / 10.0
    
    # Experience score (diminishing returns after 5 years)
    experience_score = min(1.0, worker.experience_years / 5.0)
    
    # Weighted combination
    score = (
        distance_score * 0.4 +
        reliability_score * 0.3 +
        experience_score * 0.1 +
        skill_match * 0.2
    )
    
    return round(score, 3)


def check_skill_match(worker_skills: str, job_skills: str) -> float:
    """
    Check skill match between worker and job
    Returns score between 0 and 1
    """
    if not job_skills or not worker_skills:
        return 0.5  # Neutral if no skills specified
    
    worker_skills_set = set([s.strip().lower() for s in worker_skills.split(",")])
    job_skills_set = set([s.strip().lower() for s in job_skills.split(",")])
    
    if not job_skills_set:
        return 0.5
    
    matched = len(worker_skills_set.intersection(job_skills_set))
    total_required = len(job_skills_set)
    
    return matched / total_required if total_required > 0 else 0.5


def find_matching_workers(job: models.Job, db: Session) -> List[models.Worker]:
    """
    Find workers that match a job's requirements
    
    Matching criteria:
    1. Worker status is ACTIVE
    2. Worker location within max_radius_km
    3. Worker availability matches job work hours
    4. Worker meets age requirement (if any)
    5. Worker meets gender preference (if any)
    6. Worker has not already been matched to this job
    """
    # Base query - active workers in same city
    query = db.query(models.Worker).filter(
        models.Worker.status == models.WorkerStatus.ACTIVE,
        models.Worker.city == job.city
    )
    
    # Age filter
    if job.min_age:
        query = query.filter(models.Worker.age >= job.min_age)
    
    # Gender filter
    if job.gender_preference and job.gender_preference != "any":
        query = query.filter(models.Worker.gender == job.gender_preference)
    
    potential_workers = query.all()
    
    # Filter by location if coordinates available
    if job.latitude and job.longitude:
        filtered_workers = []
        for worker in potential_workers:
            if worker.latitude and worker.longitude:
                distance = haversine_distance(
                    job.latitude, job.longitude,
                    worker.latitude, worker.longitude
                )
                if distance <= min(job.max_radius_km, worker.max_commute_km):
                    filtered_workers.append(worker)
        potential_workers = filtered_workers
    
    # Filter by availability
    matched_workers = []
    for worker in potential_workers:
        # Check if worker already has a match for this job
        existing_match = db.query(models.JobMatch).filter(
            models.JobMatch.job_id == job.id,
            models.JobMatch.worker_id == worker.id
        ).first()
        
        if existing_match:
            continue  # Skip if already matched
        
        # Check availability
        availability_slots = db.query(models.WorkerAvailability).filter(
            models.WorkerAvailability.worker_id == worker.id,
            models.WorkerAvailability.is_active == True
        ).all()
        
        has_matching_availability = False
        for slot in availability_slots:
            # Check if day matches
            if check_day_match(job.work_days, slot.day_of_week):
                # Check if time overlaps
                if check_time_overlap(
                    job.work_hours_start, job.work_hours_end,
                    slot.start_time, slot.end_time
                ):
                    has_matching_availability = True
                    break
        
        if has_matching_availability:
            matched_workers.append(worker)
    
    return matched_workers


def create_job_matches(job: models.Job, db: Session, max_matches: int = 10, auto_commit: bool = True) -> int:
    """
    Create job matches for a job posting
    
    Args:
        job: The job to create matches for
        db: Database session
        max_matches: Maximum number of matches to create
        auto_commit: Whether to commit within this function (default True for backward compatibility)
    
    Returns: Number of matches created
    """
    # Find matching workers
    workers = find_matching_workers(job, db)
    
    if not workers:
        return 0
    
    # Calculate scores and create matches
    matches_created = 0
    scored_workers = []
    
    for worker in workers:
        # Calculate distance
        if job.latitude and job.longitude and worker.latitude and worker.longitude:
            distance_km = haversine_distance(
                job.latitude, job.longitude,
                worker.latitude, worker.longitude
            )
        else:
            distance_km = 5.0  # Default estimate
        
        # Calculate skill match
        skill_match = check_skill_match(worker.skills, job.required_skills)
        
        # Calculate overall match score
        score = calculate_match_score(worker, job, distance_km, skill_match)
        
        scored_workers.append((worker, score, distance_km))
    
    # Sort by score (descending)
    scored_workers.sort(key=lambda x: x[1], reverse=True)
    
    # Create matches for top workers (up to max_matches or workers_needed)
    limit = min(max_matches, job.workers_needed * 3)  # Send to 3x the needed workers
    
    for worker, score, distance_km in scored_workers[:limit]:
        # Calculate response deadline
        response_deadline = datetime.utcnow() + timedelta(hours=job.response_deadline_hours)
        
        # Create match
        match = models.JobMatch(
            job_id=job.id,
            worker_id=worker.id,
            match_score=score,
            distance_km=round(distance_km, 2),
            status=models.MatchStatus.PENDING,
            sent_at=datetime.utcnow(),
            response_deadline=response_deadline,
            lead_price=3.0  # Standard lead price
        )
        db.add(match)
        matches_created += 1
    
    # Update job status
    if matches_created > 0:
        job.status = models.JobStatus.MATCHING
        job.workers_matched = matches_created
    
    if auto_commit:
        db.commit()
    
    return matches_created


def handle_expired_matches(db: Session, auto_commit: bool = True) -> int:
    """
    Mark matches as expired if response deadline has passed
    
    Args:
        db: Database session
        auto_commit: Whether to commit within this function (default True)
    
    Returns: Number of matches marked as expired
    """
    now = datetime.utcnow()
    
    expired_matches = db.query(models.JobMatch).filter(
        models.JobMatch.status == models.MatchStatus.PENDING,
        models.JobMatch.response_deadline < now
    ).all()
    
    count = 0
    for match in expired_matches:
        match.status = models.MatchStatus.EXPIRED
        count += 1
    
    if auto_commit:
        db.commit()
    
    return count


def trigger_matching_for_job(job_id: int, db: Session) -> dict:
    """
    Trigger matching algorithm for a specific job
    
    Returns: Dictionary with matching results
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    
    if not job:
        return {"error": "Job not found"}
    
    if job.status not in [models.JobStatus.OPEN, models.JobStatus.MATCHING]:
        return {"error": f"Job status must be OPEN or MATCHING, current: {job.status.value}"}
    
    matches_created = create_job_matches(job, db)
    
    return {
        "job_id": job.id,
        "matches_created": matches_created,
        "job_status": job.status.value
    }
