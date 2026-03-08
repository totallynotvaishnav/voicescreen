import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.database import get_db
from app.models import Candidate, Interview, Job, Score, User
from app.schemas import StartScreeningResponse, InterviewResponse
from app.services.bolna import BolnaService
from app.services.scoring import ScoringEngine
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Interviews"])


@router.post("/jobs/{job_id}/start-screening", response_model=StartScreeningResponse)
async def start_screening(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger Bolna outbound calls for all pending candidates in a job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get candidates without interviews
    result = await db.execute(
        select(Candidate)
        .outerjoin(Interview)
        .where(Candidate.job_id == job_id, Interview.id.is_(None))
    )
    candidates = result.scalars().all()

    if not candidates:
        return StartScreeningResponse(
            message="No pending candidates to screen",
            calls_initiated=0,
            errors=[],
        )

    bolna = BolnaService()
    calls_initiated = 0
    errors = []

    for candidate in candidates:
        try:
            response = await bolna.make_call(
                phone_number=candidate.phone,
                candidate_name=candidate.name,
                job_title=job.title,
            )

            # Create interview record
            interview = Interview(
                candidate_id=candidate.id,
                bolna_call_id=response.get("execution_id") or response.get("run_id") or response.get("id") or response.get("call_id", ""),
                status="in_progress",
            )
            db.add(interview)
            candidate.status = "screening"
            calls_initiated += 1

        except Exception as e:
            logger.error(f"Failed to call {candidate.name}: {str(e)}")
            errors.append(f"{candidate.name}: {str(e)}")

    await db.commit()

    return StartScreeningResponse(
        message=f"Screening initiated for {calls_initiated} candidates",
        calls_initiated=calls_initiated,
        errors=errors,
    )


@router.get("/interviews/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Interview).where(Interview.id == interview_id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return InterviewResponse(
        id=interview.id,
        candidate_id=interview.candidate_id,
        bolna_call_id=interview.bolna_call_id,
        status=interview.status,
        transcript=interview.transcript,
        created_at=interview.created_at,
        completed_at=interview.completed_at,
    )


@router.post("/interviews/{interview_id}/rescore")
async def rescore_interview(
    interview_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Re-run GPT scoring on an existing interview transcript."""
    result = await db.execute(
        select(Interview)
        .options(
            joinedload(Interview.candidate).joinedload(Candidate.job),
            joinedload(Interview.score),
        )
        .where(Interview.id == interview_id)
    )
    interview = result.unique().scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if not interview.transcript:
        raise HTTPException(status_code=400, detail="No transcript available to score")

    job_desc = interview.candidate.job.description or interview.candidate.job.title

    scorer = ScoringEngine()
    scores = await scorer.score_transcript(interview.transcript, job_desc)

    # Delete old score if exists
    if interview.score:
        await db.delete(interview.score)
        await db.flush()

    score = Score(
        interview_id=interview.id,
        communication=scores.get("communication", 0),
        experience=scores.get("experience", 0),
        motivation=scores.get("motivation", 0),
        availability=scores.get("availability", 0),
        cultural_fit=scores.get("cultural_fit", 0),
        role_fit=scores.get("role_fit", 0),
        overall=scores.get("overall", 0),
        summary=scores.get("summary", ""),
    )
    db.add(score)
    interview.candidate.status = "screened"
    await db.commit()

    return {"message": "Interview rescored successfully", "overall_score": score.overall}
