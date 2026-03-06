from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import Job, Candidate, Interview, Score
from app.schemas import JobCreate, JobResponse, JobListResponse

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.post("", response_model=JobResponse)
async def create_job(data: JobCreate, db: AsyncSession = Depends(get_db)):
    job = Job(title=data.title, department=data.department, description=data.description)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return JobResponse(
        id=job.id,
        title=job.title,
        department=job.department,
        description=job.description,
        created_at=job.created_at,
        candidate_count=0,
        screened_count=0,
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).order_by(Job.created_at.desc()))
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

    return JobListResponse(jobs=job_responses)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
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
