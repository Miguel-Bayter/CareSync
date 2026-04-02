# CareSync API

[![CI](https://github.com/Miguel-Bayter/CareSync/actions/workflows/ci.yml/badge.svg)](https://github.com/Miguel-Bayter/CareSync/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/Miguel-Bayter/CareSync)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

REST API for managing medications of elderly patients in care homes.  
Built with Domain-Driven Design, layered architecture, 100% test coverage, and zero-cost infrastructure.

**Live API → [caresync-tau.vercel.app/docs](https://caresync-tau.vercel.app/docs)**  
*(First request may take 20–50 s on free-tier cold start)*

---

## The Problem

In Colombia, thousands of elderly patients in care homes depend on caregivers to manage complex medication schedules. A missed dose of metformin or losartan can have serious health consequences. Manual tracking with paper or WhatsApp leads to errors, missed doses, and no adherence visibility for physicians.

CareSync automates the entire workflow: enroll a medication once, and the system schedules every dose for the next 30 days, detects missed doses automatically, checks drug interactions via OpenFDA, and generates a downloadable PDF report the family can bring to the physician.

---

## Live Demo

> **Swagger UI:** [caresync-tau.vercel.app/docs](https://caresync-tau.vercel.app/docs)

**Demo credentials (read-only, safe to try):**
| Field | Value |
|---|---|
| Email | `ana.torres@caresync.com` |
| Password | `Demo1234!` |

1. `POST /api/v1/auth/login` → copy the `access_token`
2. Click **Authorize** in the top-right of Swagger UI → paste the token
3. Explore patients, medications, doses, and download a PDF report

---

## Tech Stack

| Layer | Tool | Rationale |
|---|---|---|
| Framework | FastAPI 0.115 | Async-first, auto-generated OpenAPI, type-safe |
| Database | PostgreSQL via Neon.tech | Serverless Postgres, free tier, no credit card |
| ORM | SQLAlchemy 2.0 (sync) | Mature, explicit, no magic |
| Migrations | Alembic | Version-controlled schema changes |
| Auth | PyJWT + bcrypt | `python-jose` unmaintained since 2023; `passlib` has bcrypt v5 compat issues |
| Scheduler | APScheduler | Cron-style jobs without Redis |
| Drug Interactions | OpenFDA API | No API key, no cost |
| PDF Reports | fpdf2 | Pure Python — no GTK/system deps needed on Vercel Lambda |
| Logging | structlog | Structured JSON logs with correlation IDs |
| Hosting | Vercel | Serverless, free tier, custom domain support |
| **Total infra cost** | | **$0.00** |

---

## Architecture

```
HTTP Request
    │
    ▼
┌──────────┐
│  Router  │  Validates HTTP, delegates to service. Never contains business logic.
└────┬─────┘
     │
     ▼
┌──────────┐
│ Service  │  Business logic only. Raises domain exceptions, never HTTPException.
└────┬─────┘
     │
     ▼
┌────────────┐
│ Repository │  Data access only. Encapsulates all SQLAlchemy queries.
└────┬───────┘
     │
     ▼
┌────────────┐
│   Model    │  SQLAlchemy ORM. No logic.
└────┬───────┘
     │
     ▼
┌──────────────────────┐
│  PostgreSQL (Neon)   │
└──────────────────────┘
```

Each layer has **one responsibility** and depends only on the layer below it. Routers never touch repositories; services never return HTTP responses.

---

## Domain (Ubiquitous Language)

| Term | Description |
|---|---|
| `ResponsibleCaregiver` | Nurse or family member who manages medications |
| `ElderlyPatient` | The patient under care |
| `MedicationEnrollment` | Registering a medication + auto-scheduling all doses for 30 days |
| `ScheduledDose` | A single planned administration with confirmation tracking |
| `AdherenceRate` | % of doses confirmed vs scheduled — key medical KPI |
| `CriticalStockReport` | Alert when stock ≤ minimum or expiry ≤ 7 days |
| `DrugInteractionReport` | FDA-sourced interaction warnings between active medications |

---

## API Endpoints

All endpoints require `Authorization: Bearer <token>` except `/auth/*`.

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register a caregiver account |
| POST | `/api/v1/auth/login` | Login → JWT access token |

### Patients
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/patients/` | Enroll a new patient |
| GET | `/api/v1/patients/` | List all patients for the authenticated caregiver |
| GET | `/api/v1/patients/{id}/summary` | Patient summary with active medications |

### Medications
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/medications/` | Enroll medication + auto-schedule 30 days of doses |
| GET | `/api/v1/medications/{patient_id}/interactions` | Drug interactions via OpenFDA (LRU cached) |
| GET | `/api/v1/medications/critical-stock` | Medications with low stock or expiring soon |

### Doses
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/doses/{id}/confirm` | Confirm dose taken + decrement stock |
| GET | `/api/v1/doses/adherence/{patient_id}` | Adherence report for the last 30 days |

### Reports
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/reports/{patient_id}/medical-pdf` | Download monthly PDF report |

---

## Security

This API was audited against OWASP Top 10. Key measures in place:

| Risk | Mitigation |
|---|---|
| **Broken Auth** | PyJWT HS256, 30-min expiry, `SECRET_KEY` enforced ≥ 32 chars at startup |
| **User Enumeration** | Auth errors return identical `"Could not validate credentials"` regardless of cause |
| **Excessive Data Exposure** | Pydantic response schemas exclude password hashes and internal fields |
| **IDOR** | Every resource query filters by `caregiver_id` — users cannot access other caregivers' data |
| **CORS Misconfiguration** | `allow_credentials=False` with wildcard origin (browsers reject credentials + wildcard) |
| **Missing Security Headers** | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `HSTS` on every response |
| **PII in Logs** | Email addresses never logged; only opaque UUIDs in structured log output |
| **Weak Secrets** | `field_validator` raises `ValueError` at startup if `SECRET_KEY` < 32 characters |

---

## Technical Highlights

- **Bulk dose scheduling** — `db.add_all()` inserts 90 doses in a single round-trip, not 90 separate `INSERT` statements.
- **LRU cache for OpenFDA** — Module-level `@lru_cache` makes repeated interaction checks instant. Zero-cost alternative to Redis.
- **`pool_pre_ping=True`** — Handles Neon.tech serverless cold-start connection drops gracefully without crashing.
- **Lazy imports for heavy dependencies** — `fpdf2` is imported inside the method that uses it, keeping Lambda startup fast and allowing the rest of the API to work even if PDF generation fails.
- **Idempotent background jobs** — APScheduler jobs check for recent duplicate alerts before sending, preventing notification spam.
- **100% test coverage** — 203 tests across 14 unit test files (mocks) and 7 integration test files (SQLite in-memory), enforced in CI.
- **Conditional scheduler** — `ENABLE_SCHEDULER=false` disables APScheduler on serverless platforms where persistent processes don't exist.
- **Domain exceptions, not HTTP exceptions** — Services raise `NotFoundError`, `ForbiddenError`, etc. A central exception handler maps them to HTTP responses. Services stay framework-agnostic.

---

## Project Structure

```
medication-management-api/
├── app/
│   ├── core/           # config, security, exceptions, exception handlers, logging
│   ├── domain/         # enums, value objects (pure Python, no framework deps)
│   ├── models/         # SQLAlchemy ORM models
│   ├── repositories/   # data access layer — all queries live here
│   ├── services/       # business logic — one service per domain concept
│   ├── routers/        # FastAPI route handlers — HTTP in/out only
│   ├── scheduler/      # APScheduler jobs (missed-dose detection, stock alerts)
│   └── schemas/        # Pydantic request/response DTOs
├── alembic/            # database migrations
├── api/
│   └── index.py        # Vercel serverless entry point
├── scripts/            # seed data for demo environment
├── tests/
│   ├── unit/           # service tests with MagicMock (no DB)
│   └── integration/    # endpoint tests with FastAPI TestClient + SQLite
├── .env.example        # environment variable template
├── Dockerfile          # container build for self-hosted deployment
├── render.yaml         # Render.com deployment config (alternative to Vercel)
├── vercel.json         # Vercel serverless config
└── pyproject.toml      # ruff + mypy + pytest config
```

---

## Local Setup

**Prerequisites:** Python 3.11+, a PostgreSQL database (or use [Neon.tech](https://neon.tech) free tier)

```bash
# 1. Clone
git clone https://github.com/Miguel-Bayter/CareSync.git
cd CareSync/medication-management-api

# 2. Virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 4. Configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL and SECRET_KEY

# 5. Run migrations
alembic upgrade head

# 6. Load demo data (optional)
python scripts/seed.py

# 7. Start the server
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Running Tests

```bash
# All tests
pytest

# With HTML coverage report (opens htmlcov/index.html)
pytest --cov=app --cov-report=html

# Unit tests only (fast, no DB)
pytest tests/unit/

# Integration tests only
pytest tests/integration/
```

---

## Generating a Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Deployment

**Vercel (live):**  The project auto-deploys from `main` via `vercel.json`. Set the following environment variables in the Vercel dashboard:
- `DATABASE_URL` — Neon.tech connection string
- `SECRET_KEY` — at least 32 characters
- `ENABLE_SCHEDULER` — `false` (Vercel functions are stateless)

**Docker / self-hosted:** A `Dockerfile` is included for containerized deployment.  
**Render.com:** A `render.yaml` is included for one-click Render deployment.

---

*Built with FastAPI · PostgreSQL · Neon.tech · APScheduler · OpenFDA · fpdf2*  
*Total infrastructure cost: $0.00*
