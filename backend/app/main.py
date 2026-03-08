import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app.database import init_db, get_db, async_session
from app.models import Candidate, Interview, Score, User, Job
from app.schemas import DashboardStats
from app.routers import jobs, candidates, interviews, webhooks, auth, debug
from app.dependencies import get_current_user
from app.services.bolna import BolnaService, BolnaAPIError
from app.services.scoring import ScoringEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Trigger hot reload


async def poll_stale_interviews():
    """
    Background task: every 2 minutes, find interviews stuck in `in_progress`
    for more than 5 minutes (i.e. Bolna finished but the webhook was missed
    because Render was sleeping) and recover them by fetching the transcript
    directly from Bolna's API.
    """
    POLL_INTERVAL = 120       # seconds between sweeps
    STALE_AFTER   = 5 * 60   # treat as stale after 5 min

    await asyncio.sleep(10)   # let the server fully start first
    logger.info("Bolna recovery poller started")

    while True:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=STALE_AFTER)
            async with async_session() as db:
                result = await db.execute(
                    select(Interview)
                    .where(
                        Interview.status == "in_progress",
                        Interview.bolna_call_id.isnot(None),
                        Interview.created_at <= cutoff,
                    )
                )
                stale = result.scalars().all()

            if stale:
                logger.info(f"Poller: found {len(stale)} stale interview(s) to recover")

            for iv in stale:
                try:
                    bolna = BolnaService()
                    data = await bolna.get_execution(iv.bolna_call_id)

                    # Only process calls Bolna considers done
                    if data.get("status") not in ("completed", "ended", "done", "failed"):
                        continue

                    # Extract transcript (same logic as webhook handler)
                    transcript = (
                        data.get("transcript", "")
                        or data.get("concatenated_transcript", "")
                        or data.get("call_transcript", "")
                    )
                    if not transcript:
                        extracted = data.get("extracted_data") or {}
                        transcript = extracted.get("transcript", "") or extracted.get("concatenated_transcript", "")
                    if not transcript:
                        for turn in (data.get("conversation") or []):
                            transcript += f"{turn.get('role','unknown')}: {turn.get('content','')}\n"

                    async with async_session() as db:
                        # Re-fetch inside fresh session
                        res2 = await db.execute(
                            select(Interview).where(Interview.id == iv.id)
                        )
                        interview = res2.scalar_one_or_none()
                        if not interview:
                            continue

                        interview.raw_webhook_data = data
                        interview.completed_at = datetime.now(timezone.utc)

                        if transcript:
                            interview.transcript = transcript
                            interview.status = "completed"
                            await db.commit()
                            logger.info(f"Poller: recovered transcript for interview {iv.id}")

                            # Auto-score
                            try:
                                res3 = await db.execute(
                                    select(Interview)
                                    .options(
                                        joinedload(Interview.candidate).joinedload(Candidate.job),
                                        joinedload(Interview.score),
                                    )
                                    .where(Interview.id == iv.id)
                                )
                                interview = res3.unique().scalar_one()
                                job_desc = interview.candidate.job.description or interview.candidate.job.title
                                scorer = ScoringEngine()
                                scores = await scorer.score_transcript(transcript, job_desc)
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
                                logger.info(f"Poller: scored interview {iv.id}: overall={score.overall}")
                            except Exception as score_err:
                                logger.error(f"Poller: scoring failed for {iv.id}: {score_err}")
                                await db.rollback()
                                interview.candidate.status = "screened"
                                await db.commit()
                        else:
                            interview.status = "failed"
                            interview.candidate.status = "pending"
                            await db.commit()
                            logger.warning(f"Poller: no transcript from Bolna for {iv.id}")

                except BolnaAPIError as e:
                    logger.warning(f"Poller: Bolna API error for {iv.bolna_call_id}: {e}")
                except Exception as e:
                    logger.error(f"Poller: unexpected error for interview {iv.id}: {e}")

        except Exception as outer:
            logger.error(f"Poller sweep failed: {outer}")

        await asyncio.sleep(POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting VoiceScreen API...")
    await init_db()
    logger.info("Database tables created/verified")
    poller = asyncio.create_task(poll_stale_interviews())
    yield
    poller.cancel()
    logger.info("Shutting down VoiceScreen API...")


app = FastAPI(
    title="VoiceScreen API",
    description="Voice AI-powered HR Interview Screening",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "https://voicescreen-app.onrender.com",
        "https://voicescreen.netlify.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(candidates.router)
app.include_router(interviews.router)
app.include_router(webhooks.router)
app.include_router(debug.router)


@app.get("/api/dashboard/stats", response_model=DashboardStats, tags=["Dashboard"])
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get overview statistics for the dashboard."""
    total = await db.execute(select(func.count(Candidate.id)).join(Job, Candidate.job_id == Job.id).where(Job.user_id == current_user.id))
    total_candidates = total.scalar() or 0

    screened = await db.execute(
        select(func.count(Interview.id))
        .join(Candidate, Interview.candidate_id == Candidate.id)
        .join(Job, Candidate.job_id == Job.id)
        .where(Interview.status == "completed", Job.user_id == current_user.id)
    )
    screened_count = screened.scalar() or 0

    avg = await db.execute(
        select(func.avg(Score.overall))
        .join(Interview, Score.interview_id == Interview.id)
        .join(Candidate, Interview.candidate_id == Candidate.id)
        .join(Job, Candidate.job_id == Job.id)
        .where(Job.user_id == current_user.id)
    )
    avg_score = round(avg.scalar() or 0, 1)

    top = await db.execute(
        select(func.count(Score.id))
        .join(Interview, Score.interview_id == Interview.id)
        .join(Candidate, Interview.candidate_id == Candidate.id)
        .join(Job, Candidate.job_id == Job.id)
        .where(Score.overall >= 7.0, Job.user_id == current_user.id)
    )
    top_rated = top.scalar() or 0

    return DashboardStats(
        total_candidates=total_candidates,
        screened=screened_count,
        avg_score=avg_score,
        top_rated=top_rated,
    )


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "VoiceScreen API"}
