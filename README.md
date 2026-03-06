# 🎙️ VoiceScreen — AI-Powered HR Interview Screening

> **Automate first-round phone screenings with Voice AI. Screen 500+ candidates in 24 hours instead of 2 weeks.**

VoiceScreen uses [Bolna](https://bolna.ai) Voice AI agents to conduct structured phone interviews automatically, then scores candidate transcripts using LLMs — surfacing top talent to recruiters on a premium real-time dashboard.

---

## 🏗️ Architecture

```
┌─────────────────┐     CSV Upload      ┌──────────────────┐
│                 │ ──────────────────▶  │                  │
│   React SPA     │                      │  FastAPI Backend  │
│   (Vite)        │ ◀──────────────────  │  (Async Python)   │
│                 │   REST JSON API      │                  │
└─────────────────┘                      └────────┬─────────┘
                                                  │
                              ┌────────────────────┼────────────────────┐
                              │                    │                    │
                              ▼                    ▼                    ▼
                    ┌──────────────┐    ┌──────────────────┐  ┌─────────────────┐
                    │  PostgreSQL  │    │   Bolna Voice AI  │  │  OpenRouter LLM  │
                    │  (Docker)    │    │   (Outbound Calls) │  │  (Scoring Engine) │
                    └──────────────┘    └──────────────────┘  └─────────────────┘
                                                │
                                                │ Webhook (POST)
                                                ▼
                                        ┌──────────────────┐
                                        │  /api/webhooks/  │
                                        │  bolna            │
                                        └──────────────────┘
```

### System Flow

1. **Recruiter** creates a job and uploads a CSV of candidates (name, phone, email)
2. **Backend** triggers Bolna outbound calls for each candidate
3. **Bolna AI agent** conducts a 5-question structured interview over the phone
4. **Bolna webhook** POSTs the call transcript back to our backend
5. **Scoring engine** sends the transcript to an LLM for evaluation on 6 dimensions
6. **Dashboard** displays ranked candidates with radar charts and actionable insights

---

## 🛠️ Tech Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| **Frontend** | React + Vite | Fast HMR, modern tooling, component architecture |
| **Backend** | FastAPI (Python) | Async-native, auto-docs (Swagger), Pydantic validation |
| **ORM** | SQLAlchemy 2.0 (async) | Type-safe models, async support with `asyncpg`, migration-ready |
| **Database** | PostgreSQL 17 | ACID compliance, JSON support, battle-tested at scale |
| **Voice AI** | Bolna | Managed outbound calling, real-time transcription, webhook delivery |
| **LLM Scoring** | OpenRouter (free tier) | OpenAI-compatible API, model flexibility, cost-effective |
| **Containerization** | Docker Compose | One-command local DB setup, prod-parity |
| **Tunneling** | ngrok | Exposes local webhook endpoint for Bolna callbacks |

---

## 🧠 Architectural Choices

### 1. FastAPI over Django/Flask

**Decision:** FastAPI as the backend framework.

**Rationale:**
- **Async-native** — Bolna webhook processing and LLM scoring are I/O-bound operations. FastAPI's native `async/await` support allows handling multiple concurrent webhooks and API calls without thread pool overhead.
- **Pydantic integration** — Request/response validation is automatic. Schemas double as documentation and type contracts.
- **Auto-generated OpenAPI docs** — `/docs` endpoint provides interactive API documentation out of the box, accelerating frontend integration.
- **Performance** — Benchmarks consistently show FastAPI outperforming Flask/Django for I/O-heavy workloads by 2-5x.

**Trade-off:** Smaller ecosystem than Django. No built-in admin panel. We mitigate this with our custom React dashboard.

---

### 2. PostgreSQL over MongoDB/SQLite

**Decision:** PostgreSQL as the primary database.

**Rationale:**
- **Relational integrity** — Jobs → Candidates → Interviews → Scores is a naturally relational schema. Foreign keys enforce data consistency that MongoDB cannot guarantee.
- **ACID transactions** — Scoring involves multiple writes (interview update + score creation). Transactions prevent partial writes if the LLM call fails mid-process.
- **JSON column support** — `raw_webhook_data` stores the full Bolna webhook payload as JSONB, giving us MongoDB-like flexibility for unstructured data *within* a relational model.
- **Scalability** — PostgreSQL handles millions of rows with proper indexing. The schema already uses UUIDs for distributed-ready primary keys.

**Trade-off:** Requires Docker for local dev (vs. SQLite's zero-config). We solve this with a single `docker compose up -d`.

---

### 3. SQLAlchemy 2.0 (Async) as the ORM

**Decision:** Use SQLAlchemy with `asyncpg` driver instead of raw SQL or a lighter ORM.

**Rationale:**
- **Type-safe models** — `Mapped[]` annotations provide IDE autocompletion and catch type errors at development time.
- **Async support** — `asyncpg` driver provides true non-blocking database operations, critical for webhook processing throughput.
- **Migration-ready** — Alembic (SQLAlchemy's migration tool) can be added for schema versioning without rewriting models.
- **Relationship loading** — `joinedload()` prevents N+1 query problems when fetching candidates with their interview scores.

**Trade-off:** More boilerplate than Tortoise ORM or raw SQL. The type safety and migration readiness justify this.

---

### 4. Webhook-Based Architecture (Not Polling)

**Decision:** Receive call results via Bolna webhooks instead of polling the API.

**Rationale:**
- **Real-time processing** — Transcripts are processed the moment calls end, not on a polling interval.
- **No wasted compute** — Polling would require a background scheduler hitting the Bolna API every N seconds, even when no calls are active.
- **Scalability** — Webhook handlers are stateless — they can be horizontally scaled behind a load balancer.
- **Reliability** — Transcript is committed to the database before scoring begins. If scoring fails, the transcript is never lost and can be re-scored.

**Trade-off:** Requires a publicly accessible endpoint (ngrok for dev, proper domain for prod).

---

### 5. LLM-Based Scoring over Rule-Based

**Decision:** Use LLMs (via OpenRouter) for transcript evaluation instead of keyword matching or rule-based scoring.

**Rationale:**
- **Nuance** — LLMs understand context, tone, and relevance. "I managed a team of 12" is weighted differently than "I once attended a team meeting" — keyword matching can't distinguish these.
- **6-dimensional scoring** — Communication, Experience, Motivation, Availability, Cultural Fit, and Role Fit require contextual understanding that only LLMs provide.
- **Weighted overall score** — Experience (25%) + Role Fit (25%) + Communication (15%) + Motivation (15%) + Cultural Fit (10%) + Availability (10%).
- **Model flexibility** — OpenRouter allows swapping models via `.env` without code changes. You can use free models for dev and GPT-4o for production.

**Trade-off:** LLM costs (~$0.01/scoring with paid models). Free models have rate limits. We mitigate with retry logic and configurable model selection.

---

### 6. React SPA with Client-Side Routing

**Decision:** Single Page Application with React Router, not server-rendered pages.

**Rationale:**
- **Dashboard UX** — SPA provides instant page transitions and real-time data updates. Recruiters navigating between jobs, candidates, and scores experience zero page reloads.
- **API decoupling** — Frontend and backend are fully decoupled. The backend serves only JSON, making it reusable for mobile apps or third-party integrations.
- **Component reusability** — Radar chart, status badges, CSV upload, and layout components are reused across pages.

**Trade-off:** No SSR/SEO (not needed — this is an internal recruiter tool behind auth).

---

### 7. Explicit Commit/Rollback Pattern

**Decision:** Use explicit `db.commit()` and `db.rollback()` in critical paths instead of relying on auto-commit.

**Rationale:**
- **Data safety** — In the webhook handler, the transcript is committed immediately before scoring begins. If the LLM call fails or times out, the transcript is preserved.
- **Atomicity control** — Scoring creates both a Score record and updates the Candidate status. If either fails, we rollback and still mark the candidate as screened.
- **Debugging clarity** — Explicit commits make the transaction boundaries visible in code, making it easier to reason about data consistency.

---

## 📁 Project Structure

```
bolna/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, lifespan, CORS, dashboard stats
│   │   ├── config.py            # Pydantic settings (env-based)
│   │   ├── database.py          # Async SQLAlchemy engine & session
│   │   ├── models.py            # ORM models: Job, Candidate, Interview, Score
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── jobs.py          # CRUD for jobs
│   │   │   ├── candidates.py    # CSV upload, listing, detail, scheduling
│   │   │   ├── interviews.py    # Start screening, rescore
│   │   │   └── webhooks.py      # Bolna webhook receiver + auto-scoring
│   │   └── services/
│   │       ├── bolna.py         # Bolna API client (make_call, get_execution)
│   │       ├── scoring.py       # LLM scoring engine (6-dimension evaluation)
│   │       └── csv_parser.py    # CSV validation & parsing
│   ├── .env                     # Environment variables (not committed)
│   ├── .env.example             # Template for env vars
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── main.jsx             # App entry point
│   │   ├── App.jsx              # React Router setup
│   │   ├── index.css            # Design system (dark theme, glassmorphism)
│   │   ├── api/client.js        # Axios instance
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Stats overview + ranked candidates
│   │   │   ├── Jobs.jsx         # Job listing + creation modal
│   │   │   ├── JobDetail.jsx    # Candidate upload + screening trigger
│   │   │   └── CandidateDetail.jsx  # Scores, radar chart, transcript
│   │   └── components/
│   │       ├── Layout.jsx       # Sidebar + main content wrapper
│   │       ├── StatusBadge.jsx  # Color-coded status indicators
│   │       ├── ScoreRadar.jsx   # Recharts radar visualization
│   │       └── CSVUpload.jsx    # Drag-and-drop file upload
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml           # PostgreSQL 17 container
├── sample_candidates.csv        # Test data
└── bolna_agent_config.json      # Bolna agent prompt reference
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+** with pip
- **Node.js 18+** with npm
- **Docker** (for PostgreSQL)
- **ngrok** account (free — for webhook tunneling)
- **Bolna** account with an agent configured
- **OpenRouter** API key (free tier available)

### 1. Clone & Setup Backend

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start PostgreSQL

```bash
# From project root
docker compose up -d
```

### 3. Start Backend

```bash
cd backend
python3 -m uvicorn app.main:app --reload --port 8000
```

### 4. Start ngrok (for Bolna webhooks)

```bash
# In a new terminal
ngrok http 8000
# Copy the https URL and set it as webhook in Bolna:
# https://your-ngrok-url.ngrok-free.app/api/webhooks/bolna
```

### 5. Start Frontend

```bash
# In a new terminal
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 6. Configure Bolna Agent

Set your ngrok webhook URL in Bolna platform → Analytics Tab:
```
https://your-ngrok-url.ngrok-free.app/api/webhooks/bolna
```

---

## 📋 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/dashboard/stats` | Dashboard statistics |
| `GET` | `/api/jobs` | List all jobs |
| `POST` | `/api/jobs` | Create a job |
| `GET` | `/api/jobs/{id}` | Get job details |
| `POST` | `/api/jobs/{id}/candidates/upload` | Upload candidates CSV |
| `GET` | `/api/jobs/{id}/candidates` | List candidates for a job |
| `POST` | `/api/jobs/{id}/start-screening` | Trigger outbound calls |
| `GET` | `/api/candidates/{id}` | Candidate detail (scores + transcript) |
| `POST` | `/api/candidates/{id}/schedule` | Schedule for next round |
| `POST` | `/api/interviews/{id}/rescore` | Re-run LLM scoring |
| `POST` | `/api/webhooks/bolna` | Bolna webhook receiver |

Full interactive docs available at `http://localhost:8000/docs`

---

## 🔮 Future Scope

### Short-Term (v1.1)

- **📧 Email notifications** — Auto-email candidates after screening with results/next steps
- **🔐 Recruiter authentication** — JWT-based login with role-based access (Admin, Recruiter, Viewer)
- **📄 Resume upload** — Per-candidate PDF resume storage and display on detail page

- **📊 Analytics dashboard** — Screening funnel metrics, average scores by department, time-to-hire tracking

### Medium-Term (v2.0)

- **🎯 Custom question sets** — Per-job configurable interview questions (stored in DB, passed to Bolna agent dynamically)
- **🌐 Multi-language support** — Bolna supports multilingual agents; extend scoring engine to handle non-English transcripts
- **📱 Mobile app** — React Native companion app for recruiters to review candidates on the go
- **🔗 ATS integration** — Bi-directional sync with Greenhouse, Lever, Workday via API connectors
- **🤖 AI-generated job descriptions** — Auto-generate JDs from role title + department using LLMs
- **⚖️ Bias detection** — Flag potential bias patterns in scoring across demographics


---

## ⚙️ Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5434/voicescreen` |
| `BOLNA_API_KEY` | Bolna platform API key | `bn-xxxx...` |
| `BOLNA_AGENT_ID` | ID of the configured Bolna agent | `dea4fd96-...` |
| `OPENAI_API_KEY` | OpenRouter (or OpenAI) API key | `sk-or-v1-xxxx...` |
| `LLM_BASE_URL` | LLM API base URL | `https://openrouter.ai/api/v1` |
| `LLM_MODEL` | Model identifier for scoring | `arcee-ai/trinity-large-preview:free` |

---

## 🧪 Interview Scoring Dimensions

Each candidate is evaluated on 6 dimensions (1.0–10.0 scale):

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| **Experience** | 25% | Relevance and depth of past experience |
| **Role Fit** | 25% | Suitability for the specific position |
| **Communication** | 15% | Clarity, articulation, professional tone |
| **Motivation** | 15% | Interest in the role and company |
| **Cultural Fit** | 10% | Values alignment and adaptability |
| **Availability** | 10% | Readiness to start, notice period |

The **overall score** is a weighted average of all dimensions.

---

## 📜 License

This project is for educational and demonstration purposes.

---

<p align="center">
  Built with ❤️ using FastAPI, React, Bolna AI, and OpenRouter
</p>
