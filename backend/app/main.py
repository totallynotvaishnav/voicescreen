import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import init_db, get_db
from app.models import Candidate, Interview, Score, User
from app.schemas import DashboardStats
from app.routers import jobs, candidates, interviews, webhooks, auth
from app.dependencies import get_current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Trigger hot reload
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting VoiceScreen API...")
    await init_db()
    logger.info("Database tables created/verified")
    yield
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
