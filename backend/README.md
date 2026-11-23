# SENTINEL AI ? Backend & Orchestration Engine

> **Lead Developer**: Delvin  
> **Role**: Manager Agent & Backend Lead  
> **Repository**: [https://github.com/sahadhaneef/Sentinal-AI](https://github.com/sahadhaneef/Sentinal-AI)

---

## 1. Overview

The SENTINEL AI backend provides the central nervous system for autonomous failure recovery in monitored applications. Built with **Python 3.12+**, **FastAPI**, **SQLAlchemy 2.0 (async)**, and **SQLite (aiosqlite)**, it coordinates the six logical agents across the entire incident-repair lifecycle:

1. **Monitoring Agent** (Neha) ? log intake, error detection, and deduplication.
2. **Manager Agent** (Delvin) ? state machine workflow orchestration and audit history.
3. **Diagnosis Agent & Code RAG** (Sahad) ? root cause hypothesis and revision-bound source evidence.
4. **Repair Agent** (Yadhulakshmi) ? minimal unified diff patch generation.
5. **Testing Agent** (Sravan) ? isolated reproduction check and regression smoke testing.
6. **Reporting Agent** (Neha) ? evidence-backed summary reports with limitations.

Human approval operates as an immutable security gate prior to patch application.

---

## 2. Directory Structure

```text
backend/
??? alembic/                        # Alembic database migrations
?   ??? env.py                      # Async/sync Alembic migration environment
?   ??? versions/                   # Versioned migration scripts
??? app/
?   ??? main.py                     # FastAPI application setup, CORS, session & error handling
?   ??? core/
?   ?   ??? config.py               # Pydantic Settings & environment config
?   ?   ??? errors.py               # Structured SentinelError hierarchy & HTTP status codes
?   ?   ??? logging.py              # Structured JSON logging & request tracking
?   ?   ??? security.py             # Session signing, CSRF protection, actor derivation, idempotency
?   ??? db/
?   ?   ??? base.py                 # DB initialization & deterministic demo app seed data
?   ?   ??? models.py               # 15 SQLAlchemy ORM models + idempotency records
?   ?   ??? session.py              # Async engine & session factory (SQLite / aiosqlite)
?   ??? schemas/
?   ?   ??? common.py               # Pydantic v2 wire models strictly matching frontend contracts
?   ??? agents/
?   ?   ??? registry.py             # Agent protocol interface, registry, and development stubs
?   ??? services/
?   ?   ??? manager.py              # Manager Agent persistent state machine & crash recovery
?   ?   ??? apply.py                # Secure local patch application service with snapshots & rollback
?   ??? workers/
?   ?   ??? dispatcher.py           # Durable background workflow dispatcher
?   ??? api/
?       ??? v1/
?           ??? router.py           # Unified v1 router
?           ??? health.py           # GET /api/v1/health
?           ??? auth.py             # POST /api/v1/auth/login, /logout, GET /me
?           ??? artifacts.py        # GET /api/v1/artifacts/{id}
?           ??? dashboard.py        # GET /api/v1/dashboard/summary
?           ??? applications.py     # GET/POST /api/v1/applications
?           ??? incidents.py        # GET/POST /api/v1/incidents, /events, /runs, /workflow
?           ??? agents.py           # GET /api/v1/agents, /agents/{type}
?           ??? patches.py          # GET /api/v1/patches/{id}, /validation
?           ??? approvals.py        # POST /api/v1/incidents/{id}/decision, /apply
?           ??? settings.py         # GET/PATCH /api/v1/settings
??? demo_app/
?   ??? workspace/                  # Designated local sample application (Registration API)
?       ??? src/registration.py     # Buggy target module (NullReferenceError)
?       ??? tests/test_registration.py
??? tests/
?   ??? conftest.py                 # In-memory async SQLite fixtures & test client
?   ??? test_apply.py               # 7 patch engine, diff, hash, path traversal & rollback tests
?   ??? test_security.py            # 5 auth, CSRF, idempotency & approval safety gate tests
?   ??? test_integration.py         # 31 integration tests covering all 20 required scenarios
??? pyproject.toml
??? alembic.ini
??? .env.example
```

---

## 3. Quick Start (Windows PowerShell)

### Prerequisites
- Python 3.12+ (tested on Python 3.13)
- PowerShell 5.1+ or PowerShell Core

### 1. Installation

```powershell
# Navigate to backend directory
cd "backend"

# Install required packages
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pydantic-settings python-multipart python-dotenv httpx pytest pytest-asyncio greenlet ruff
```

### 2. Configure Environment & Migrations

```powershell
Copy-Item .env.example .env

# Run database migrations to apply latest schema
python -m alembic upgrade head
```

### 3. Run the Backend Server

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The server starts at `http://127.0.0.1:8000`.  
- API root: `http://127.0.0.1:8000/api/v1`
- Swagger UI documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/api/v1/health`

### 4. Run the Test Suite & Linter

```powershell
# Run all 43 tests
python -m pytest tests/ -v

# Run code style and linter checks
python -m ruff check .
```

---

## 4. Connecting with Frontend

1. Ensure the backend is running at `http://localhost:8000`.
2. In the `frontend/` directory, set environment variables in `.env`:
   ```bash
   VITE_DATA_SOURCE=api
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   ```
3. Start the frontend:
   ```bash
   npm run dev
   ```
4. Access the web dashboard at `http://localhost:5173`.
