from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.database import get_db
from app.models import Candidate, Interview, Score, Job
from app.schemas import CandidateResponse, CandidateListResponse, CandidateDetailResponse, CSVUploadResponse, InterviewResponse, ScoreResponse
from app.services.csv_parser import parse_candidates_csv

router = APIRouter(prefix="/api", tags=["Candidates"])


@router.post("/jobs/{job_id}/candidates/upload", response_model=CSVUploadResponse)
async def upload_candidates_csv(
    job_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Verify job exists
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    content = await file.read()
    candidates_data, errors = parse_candidates_csv(content)

    created = 0
    for cand in candidates_data:
        candidate = Candidate(
            job_id=job_id,
            name=cand["name"],
            email=cand.get("email"),
            phone=cand["phone"],
            resume_url=cand.get("resume_url"),
        )
        db.add(candidate)
        created += 1

    await db.commit()
    return CSVUploadResponse(created=created, errors=errors)


@router.get("/jobs/{job_id}/candidates", response_model=CandidateListResponse)
async def list_candidates(
    job_id: str,
    sort_by: str = "score",
    db: AsyncSession = Depends(get_db),
):
    # Get candidates with their interview scores
    result = await db.execute(
        select(Candidate)
        .options(joinedload(Candidate.interview).joinedload(Interview.score))
        .where(Candidate.job_id == job_id)
        .order_by(Candidate.created_at.desc())
    )
    candidates = result.unique().scalars().all()

    responses = []
    for c in candidates:
        overall_score = None
        if c.interview and c.interview.score:
            overall_score = c.interview.score.overall

        responses.append(CandidateResponse(
            id=c.id,
            job_id=c.job_id,
            name=c.name,
            email=c.email,
            phone=c.phone,
            resume_url=c.resume_url,
            status=c.status,
            created_at=c.created_at,
            overall_score=overall_score,
        ))

    # Sort by score if requested
    if sort_by == "score":
        responses.sort(key=lambda x: x.overall_score or 0, reverse=True)

    return CandidateListResponse(candidates=responses, total=len(responses))


@router.get("/candidates/{candidate_id}", response_model=CandidateDetailResponse)
async def get_candidate_detail(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Candidate)
        .options(joinedload(Candidate.interview).joinedload(Interview.score), joinedload(Candidate.job))
        .where(Candidate.id == candidate_id)
    )
    candidate = result.unique().scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    interview_resp = None
    score_resp = None

    if candidate.interview:
        interview_resp = InterviewResponse(
            id=candidate.interview.id,
            candidate_id=candidate.interview.candidate_id,
            bolna_call_id=candidate.interview.bolna_call_id,
            status=candidate.interview.status,
            transcript=candidate.interview.transcript,
            created_at=candidate.interview.created_at,
            completed_at=candidate.interview.completed_at,
        )
        if candidate.interview.score:
            s = candidate.interview.score
            score_resp = ScoreResponse(
                id=s.id,
                interview_id=s.interview_id,
                communication=s.communication,
                experience=s.experience,
                motivation=s.motivation,
                availability=s.availability,
                cultural_fit=s.cultural_fit,
                role_fit=s.role_fit,
                overall=s.overall,
                summary=s.summary,
                created_at=s.created_at,
            )

    return CandidateDetailResponse(
        id=candidate.id,
        job_id=candidate.job_id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        resume_url=candidate.resume_url,
        status=candidate.status,
        created_at=candidate.created_at,
        job_title=candidate.job.title if candidate.job else None,
        interview=interview_resp,
        score=score_resp,
    )


@router.post("/candidates/{candidate_id}/schedule")
async def schedule_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate.status = "scheduled"
    await db.commit()
    return {"message": f"Candidate {candidate.name} scheduled for next round interview"}
