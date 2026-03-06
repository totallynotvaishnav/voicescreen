import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.database import get_db
from app.models import Interview, Candidate, Score
from app.services.scoring import ScoringEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/bolna")
async def bolna_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive call completion data from Bolna.
    
    The webhook payload contains execution data with transcript, 
    call status, extracted_data, etc.
    """
    payload = await request.json()
    logger.info(f"Bolna webhook received: {payload.get('id', 'unknown')}")

    # Extract key fields from webhook payload
    call_id = payload.get("id") or payload.get("execution_id") or payload.get("call_id", "")
    status = payload.get("status", "")
    
    # Try multiple possible transcript field locations
    transcript = (
        payload.get("transcript", "")
        or payload.get("concatenated_transcript", "")
        or payload.get("call_transcript", "")
    )

    # Check nested under extracted_data
    if not transcript:
        extracted = payload.get("extracted_data", {})
        if isinstance(extracted, dict):
            transcript = extracted.get("transcript", "") or extracted.get("concatenated_transcript", "")

    # Also try concatenating conversation turns if transcript is in a list format
    conversation = payload.get("conversation", [])
    if not transcript and conversation:
        lines = []
        for turn in conversation:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            lines.append(f"{role}: {content}")
        transcript = "\n".join(lines)

    if not call_id:
        logger.warning("Webhook received without call_id")
        return {"status": "ignored", "reason": "no call_id"}

    # Find matching interview by bolna_call_id
    result = await db.execute(
        select(Interview)
        .options(
            joinedload(Interview.candidate).joinedload(Candidate.job),
            joinedload(Interview.score),
        )
        .where(Interview.bolna_call_id == call_id)
    )
    interview = result.unique().scalar_one_or_none()

    if not interview:
        logger.warning(f"No interview found for call_id: {call_id}")
        return {"status": "ignored", "reason": "interview not found"}

    # Update interview
    interview.transcript = transcript
    interview.raw_webhook_data = payload
    interview.status = "completed" if status in ("completed", "ended", "done") else status
    interview.completed_at = datetime.now(timezone.utc)

    # Commit transcript first so it's never lost even if scoring fails
    await db.commit()

    # Auto-score if transcript is available
    if transcript:
        try:
            job_desc = interview.candidate.job.description or interview.candidate.job.title
            scorer = ScoringEngine()
            scores = await scorer.score_transcript(transcript, job_desc)

            # Remove old score if exists
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
            logger.info(f"Scored interview {interview.id}: overall={score.overall}")
            await db.commit()

        except Exception as e:
            logger.error(f"Scoring failed for interview {interview.id}: {str(e)}")
            await db.rollback()
            # Still mark as screened even if scoring failed
            interview.candidate.status = "screened"
            await db.commit()
    else:
        interview.status = "failed"
        interview.candidate.status = "pending"
        logger.warning(f"No transcript in webhook for call {call_id}")
        await db.commit()

    return {"status": "processed", "interview_id": interview.id}
