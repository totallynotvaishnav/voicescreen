from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Job, Candidate, Interview, Score, User
from app.schemas import JobCreate, JobResponse, JobListResponse
from app.dependencies import get_current_user
from typing import List

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    job: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new job posting."""
    new_job = Job(title=job.title, department=job.department, description=job.description, user_id=current_user.id)
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)
    return JobResponse(
        id=new_job.id,
        title=new_job.title,
        department=new_job.department,
        description=new_job.description,
        created_at=new_job.created_at,
        candidate_count=0,
        screened_count=0,
    )


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all jobs with their candidate counts."""
    result = await db.execute(select(Job).where(Job.user_id == current_user.id).order_by(Job.created_at.desc()))
    jobs = result.scalars().all()

    job_responses = []
    for job in jobs:
        # Count candidates
        count_result = await db.execute(
            select(func.count(Candidate.id)).where(Candidate.job_id == job.id)
        )
        candidate_count = count_result.scalar() or 0

        # Count screened (have completed interviews)
        screened_result = await db.execute(
            select(func.count(Interview.id))
            .join(Candidate, Interview.candidate_id == Candidate.id)
            .where(Candidate.job_id == job.id, Interview.status == "completed")
        )
        screened_count = screened_result.scalar() or 0

        job_responses.append(JobResponse(
            id=job.id,
            title=job.title,
            department=job.department,
            description=job.description,
            created_at=job.created_at,
            candidate_count=candidate_count,
            screened_count=screened_count,
        ))

    return job_responses


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific job with candidate count."""
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    count_result = await db.execute(
        select(func.count(Candidate.id)).where(Candidate.job_id == job.id)
    )
    candidate_count = count_result.scalar() or 0

    screened_result = await db.execute(
        select(func.count(Interview.id))
        .join(Candidate, Interview.candidate_id == Candidate.id)
        .where(Candidate.job_id == job.id, Interview.status == "completed")
    )
    screened_count = screened_result.scalar() or 0

    return JobResponse(
        id=job.id,
        title=job.title,
        department=job.department,
        description=job.description,
        created_at=job.created_at,
        candidate_count=candidate_count,
        screened_count=screened_count,
    )
