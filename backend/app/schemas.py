from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


# ── User Schemas ─────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime
    
    class Config:
        from_attributes = True


# ── Job Schemas ──────────────────────────────────────────────

class JobCreate(BaseModel):
    title: str
    department: Optional[str] = None
    description: Optional[str] = None


class JobResponse(BaseModel):
    id: str
    title: str
    department: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    candidate_count: int = 0
    screened_count: int = 0

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    jobs: list[JobResponse]


# ── Candidate Schemas ────────────────────────────────────────

class CandidateBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: str
    resume_url: Optional[str] = None


class CandidateCreate(CandidateBase):
    pass


class CandidateResponse(BaseModel):
    id: str
    job_id: str
    name: str
    email: Optional[str] = None
    phone: str
    resume_url: Optional[str] = None
    status: str
    created_at: datetime
    overall_score: Optional[float] = None

    model_config = {"from_attributes": True}


class CandidateListResponse(BaseModel):
    candidates: list[CandidateResponse]
    total: int


class CSVUploadResponse(BaseModel):
    created: int
    errors: list[str]


# ── Interview Schemas ────────────────────────────────────────

class InterviewResponse(BaseModel):
    id: str
    candidate_id: str
    bolna_call_id: Optional[str] = None
    status: str
    transcript: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Score Schemas ────────────────────────────────────────────

class ScoreResponse(BaseModel):
    id: str
    interview_id: str
    communication: float
    experience: float
    motivation: float
    availability: float
    cultural_fit: float
    role_fit: float
    overall: float
    summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Candidate Detail (full view) ─────────────────────────────

class CandidateDetailResponse(BaseModel):
    id: str
    job_id: str
    name: str
    email: Optional[str] = None
    phone: str
    resume_url: Optional[str] = None
    status: str
    created_at: datetime
    job_title: Optional[str] = None
    interview: Optional[InterviewResponse] = None
    score: Optional[ScoreResponse] = None

    model_config = {"from_attributes": True}


# ── Screening Schemas ────────────────────────────────────────

class StartScreeningResponse(BaseModel):
    message: str
    calls_initiated: int
    errors: list[str]


# ── Dashboard Schemas ────────────────────────────────────────

class DashboardStats(BaseModel):
    total_candidates: int
    screened: int
    avg_score: float
    top_rated: int
