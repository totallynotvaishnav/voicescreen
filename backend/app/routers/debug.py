"""
Debug/diagnostic router for transcript troubleshooting.
⚠️  FOR DEVELOPMENT & PRODUCTION DEBUGGING ONLY — remove or gate behind auth when done.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import Interview, Candidate, Score
from app.services.bolna import BolnaService, BolnaAPIError
from app.dependencies import get_current_user
from app.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/debug", tags=["Debug"])


# ---------------------------------------------------------------------------
# 1. List all interviews with their transcript health summary
# ---------------------------------------------------------------------------
@router.get("/interviews/transcript-health")
async def transcript_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return a table of every interview showing:
    - bolna_call_id stored in DB
    - status field
    - whether transcript is present / its length
    - whether raw_webhook_data was received
    - whether a score row exists
    - timestamps
    """
    result = await db.execute(
        select(Interview)
        .options(
            joinedload(Interview.candidate),
            joinedload(Interview.score),
        )
        .order_by(desc(Interview.created_at))
    )
    interviews = result.unique().scalars().all()

    rows = []
    for iv in interviews:
        transcript_len = len(iv.transcript) if iv.transcript else 0
        rows.append({
            "interview_id": iv.id,
            "candidate_name": iv.candidate.name if iv.candidate else None,
            "bolna_call_id": iv.bolna_call_id,
            "status": iv.status,
            "transcript_present": bool(iv.transcript),
            "transcript_length": transcript_len,
            "transcript_preview": (iv.transcript or "")[:200] if iv.transcript else None,
            "webhook_received": iv.raw_webhook_data is not None,
            "score_present": iv.score is not None,
            "created_at": iv.created_at.isoformat() if iv.created_at else None,
            "completed_at": iv.completed_at.isoformat() if iv.completed_at else None,
        })

    return {
        "total": len(rows),
        "summary": {
            "with_transcript": sum(1 for r in rows if r["transcript_present"]),
            "without_transcript": sum(1 for r in rows if not r["transcript_present"]),
            "webhook_received": sum(1 for r in rows if r["webhook_received"]),
            "no_call_id": sum(1 for r in rows if not r["bolna_call_id"]),
        },
        "interviews": rows,
    }


# ---------------------------------------------------------------------------
# 2. Inspect a single interview — full raw webhook payload included
# ---------------------------------------------------------------------------
@router.get("/interviews/{interview_id}/inspect")
async def inspect_interview(
    interview_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Full diagnostic dump for one interview:
    - All DB fields
    - The complete raw_webhook_data that was received
    - Score breakdown if present
    """
    result = await db.execute(
        select(Interview)
        .options(
            joinedload(Interview.candidate),
            joinedload(Interview.score),
        )
        .where(Interview.id == interview_id)
    )
    iv = result.unique().scalar_one_or_none()
    if not iv:
        raise HTTPException(status_code=404, detail="Interview not found")

    score_data = None
    if iv.score:
        s = iv.score
        score_data = {
            "communication": s.communication,
            "experience": s.experience,
            "motivation": s.motivation,
            "availability": s.availability,
            "cultural_fit": s.cultural_fit,
            "role_fit": s.role_fit,
            "overall": s.overall,
            "summary": s.summary,
        }

    return {
        "interview": {
            "id": iv.id,
            "candidate_id": iv.candidate_id,
            "candidate_name": iv.candidate.name if iv.candidate else None,
            "bolna_call_id": iv.bolna_call_id,
            "status": iv.status,
            "created_at": iv.created_at.isoformat() if iv.created_at else None,
            "completed_at": iv.completed_at.isoformat() if iv.completed_at else None,
        },
        "transcript": {
            "present": bool(iv.transcript),
            "length": len(iv.transcript) if iv.transcript else 0,
            "content": iv.transcript,
        },
        "raw_webhook_data": iv.raw_webhook_data,
        "score": score_data,
    }


# ---------------------------------------------------------------------------
# 3. Fetch execution details directly from Bolna API
# ---------------------------------------------------------------------------
@router.get("/bolna/execution/{execution_id}")
async def fetch_bolna_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Call Bolna's API and return the raw execution object for a given execution_id.
    Useful to check whether Bolna itself has the transcript and what fields it uses.
    """
    try:
        bolna = BolnaService()
        data = await bolna.get_execution(execution_id)
        return {
            "execution_id": execution_id,
            "bolna_response": data,
            # Highlight the fields we look for in the webhook
            "transcript_field_check": {
                "transcript": data.get("transcript"),
                "concatenated_transcript": data.get("concatenated_transcript"),
                "call_transcript": data.get("call_transcript"),
                "status": data.get("status"),
                "extracted_data.transcript": (data.get("extracted_data") or {}).get("transcript"),
                "conversation_turns": len(data.get("conversation", [])),
            },
        }
    except BolnaAPIError as e:
        raise HTTPException(status_code=e.status_code,
                            detail=f"Bolna API error: {e.detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 4. Re-fetch from Bolna & re-run webhook processing for an existing interview
# ---------------------------------------------------------------------------
@router.post("/interviews/{interview_id}/replay-from-bolna")
async def replay_from_bolna(
    interview_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pull the latest execution data from Bolna for this interview's call_id,
    then re-run the transcript extraction and DB update — without re-scoring.
    Returns what transcript was found and what was saved.
    """
    result = await db.execute(
        select(Interview).options(joinedload(Interview.candidate))
        .where(Interview.id == interview_id)
    )
    iv = result.unique().scalar_one_or_none()
    if not iv:
        raise HTTPException(status_code=404, detail="Interview not found")

    if not iv.bolna_call_id:
        raise HTTPException(
            status_code=400, detail="Interview has no bolna_call_id stored")

    try:
        bolna = BolnaService()
        data = await bolna.get_execution(iv.bolna_call_id)
    except BolnaAPIError as e:
        raise HTTPException(status_code=e.status_code,
                            detail=f"Bolna API error: {e.detail}")

    # Replicate the same extraction logic as the webhook handler
    transcript = (
        data.get("transcript", "")
        or data.get("concatenated_transcript", "")
        or data.get("call_transcript", "")
    )
    if not transcript:
        extracted = data.get("extracted_data", {})
        if isinstance(extracted, dict):
            transcript = extracted.get("transcript", "") or extracted.get(
                "concatenated_transcript", "")

    conversation = data.get("conversation", [])
    if not transcript and conversation:
        lines = []
        for turn in conversation:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            lines.append(f"{role}: {content}")
        transcript = "\n".join(lines)

    if transcript:
        iv.transcript = transcript
        iv.raw_webhook_data = data
        iv.status = "completed"
        iv.completed_at = datetime.now(timezone.utc)
        await db.commit()
        saved = True
    else:
        saved = False

    return {
        "interview_id": interview_id,
        "bolna_call_id": iv.bolna_call_id,
        "transcript_found": bool(transcript),
        "transcript_length": len(transcript) if transcript else 0,
        "transcript_preview": transcript[:500] if transcript else None,
        "saved_to_db": saved,
        "bolna_status": data.get("status"),
        "bolna_keys": list(data.keys()),
    }


# ---------------------------------------------------------------------------
# 5. Simulate a webhook payload — test parsing without a real call
# ---------------------------------------------------------------------------
@router.post("/webhook/simulate")
async def simulate_webhook(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    POST a JSON body shaped like a Bolna webhook to see exactly how the parser
    would extract the transcript, without touching the DB.

    Example body:
    {
        "id": "some-call-id",
        "status": "completed",
        "transcript": "Agent: Hello...",
        "extracted_data": {}
    }
    """
    payload = await request.json()

    call_id = payload.get("id") or payload.get(
        "execution_id") or payload.get("call_id", "")
    status = payload.get("status", "")

    transcript = (
        payload.get("transcript", "")
        or payload.get("concatenated_transcript", "")
        or payload.get("call_transcript", "")
    )
    source = None
    if payload.get("transcript"):
        source = "transcript"
    elif payload.get("concatenated_transcript"):
        source = "concatenated_transcript"
    elif payload.get("call_transcript"):
        source = "call_transcript"

    if not transcript:
        extracted = payload.get("extracted_data", {})
        if isinstance(extracted, dict):
            transcript = extracted.get("transcript", "") or extracted.get(
                "concatenated_transcript", "")
            if transcript:
                source = "extracted_data.transcript"

    conversation = payload.get("conversation", [])
    if not transcript and conversation:
        lines = []
        for turn in conversation:
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            lines.append(f"{role}: {content}")
        transcript = "\n".join(lines)
        if transcript:
            source = "conversation[]"

    return {
        "parsed": {
            "call_id": call_id,
            "status": status,
            "transcript_found": bool(transcript),
            "transcript_source_field": source,
            "transcript_length": len(transcript) if transcript else 0,
            "transcript_preview": transcript[:500] if transcript else None,
        },
        "top_level_keys": list(payload.keys()),
        "would_match_interview": bool(call_id),
        "would_score": bool(transcript),
    }


# ---------------------------------------------------------------------------
# 6. Show the last N raw webhook payloads received
# ---------------------------------------------------------------------------
@router.get("/webhooks/recent")
async def recent_webhooks(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the most recently received raw_webhook_data payloads so you can
    inspect exactly what Bolna is sending.
    """
    result = await db.execute(
        select(Interview)
        .options(joinedload(Interview.candidate))
        .where(Interview.raw_webhook_data.isnot(None))
        .order_by(desc(Interview.completed_at))
        .limit(limit)
    )
    interviews = result.unique().scalars().all()

    return {
        "count": len(interviews),
        "webhooks": [
            {
                "interview_id": iv.id,
                "candidate_name": iv.candidate.name if iv.candidate else None,
                "bolna_call_id": iv.bolna_call_id,
                "completed_at": iv.completed_at.isoformat() if iv.completed_at else None,
                "transcript_saved": bool(iv.transcript),
                "raw_webhook_keys": list(iv.raw_webhook_data.keys()) if isinstance(iv.raw_webhook_data, dict) else None,
                "raw_webhook_data": iv.raw_webhook_data,
            }
            for iv in interviews
        ],
    }
