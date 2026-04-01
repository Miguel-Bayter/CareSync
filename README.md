# CareSync API

![CI](https://github.com/Miguel-Bayter/CareSync/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

REST API for managing medications of elderly patients in care homes.
Built with Domain-Driven Design, layered architecture, and zero-cost infrastructure.

---

## The Problem

In Colombia, thousands of elderly patients in care homes depend on caregivers to manage complex medication schedules. A missed dose of metformin or losartan can have serious consequences. Manual tracking with paper or WhatsApp messages leads to errors, missed doses, and no visibility into adherence patterns for physicians.

CareSync automates the entire medication workflow: from enrolling a medication to scheduling every dose for the next 30 days, detecting missed doses automatically, checking drug interactions via OpenFDA, and generating a PDF report the family can bring to the physician.

---

## Live Demo

> First request may take 30-50 seconds (free tier cold start)

**Swagger UI:** `/docs`

**Demo credentials:**
- Email: `ana.torres@caresync.com`
- Password: `Demo1234!`

---

## Tech Stack

| Component | Tool | Why Free |
|---|---|---|
| API Framework | FastAPI 0.115 | Open source |
| Database | PostgreSQL via Neon.tech | 20 free projects, no card |
| ORM | SQLAlchemy 2.0 (sync) | Open source |
| Migrations | Alembic | Open source |
| Auth | PyJWT + bcrypt | Open source |
| Scheduler | APScheduler | No Redis needed |
| Email | Gmail SMTP | Free with App Password |
| Drug Interactions | OpenFDA API | No API key required |
| PDF Reports | fpdf2 | Pure Python, no GTK |
| Logging | structlog | Structured JSON logs |
| Hosting | Vercel | Free serverless tier |
| **Total cost** | | **$0.00** |

---

## Architecture

```
HTTP Request
    │
    ▼
┌─────────┐
│  Router │  ← validates HTTP, delegates to service
└────┬────┘
     │
     ▼
┌─────────┐
│ Service │  ← business logic, raises domain exceptions
└────┬────┘
     │
     ▼
┌────────────┐
│ Repository │  ← data access only, no business logic
└────┬───────┘
     │
     ▼
┌──────────┐
│  Model   │  ← SQLAlchemy ORM
└────┬─────┘
     │
     ▼
┌──────────────┐
│  PostgreSQL  │  ← Neon.tech serverless
└──────────────┘
```

---

## Domain (Ubiquitous Language)

| Term | Description |
|---|---|
| `ResponsibleCaregiver` | Nurse or family member who manages medications |
| `ElderlyPatient` | The patient under care |
| `MedicationEnrollment` | Registering a medication + auto-scheduling all doses |
| `ScheduledDose` | A single planned administration |
| `AdherenceRate` | % of doses confirmed vs scheduled (key medical KPI) |
| `CriticalStockReport` | Alert when stock ≤ minimum or expiry ≤ 7 days |
| `DrugInteractionReport` | FDA-sourced interaction warnings |

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register a caregiver account |
| POST | `/api/v1/auth/login` | Login → JWT token |

### Patients
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/patients/` | Enroll a new patient |
| GET | `/api/v1/patients/` | List my patients |
| GET | `/api/v1/patients/{id}/summary` | Patient summary |

### Medications
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/medications/` | Enroll medication + auto-schedule 30 days of doses |
| GET | `/api/v1/medications/{patient_id}/interactions` | Drug interactions via OpenFDA (cached) |
| GET | `/api/v1/medications/critical-stock` | Low stock or expiring soon |

### Doses
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/doses/{id}/confirm` | Confirm dose taken + decrement stock |
| GET | `/api/v1/doses/adherence/{patient_id}` | Adherence report (last 30 days) |

### Reports
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/reports/{patient_id}/medical-pdf` | Download monthly PDF report |

---

## Good Practices Applied

- **Layered Architecture** — Router → Service → Repository → Model. Each layer has one responsibility.
- **Domain-Driven Design** — Ubiquitous Language throughout. `confirm_dose_taken()` not `update_dose()`.
- **Domain Exceptions** — Services raise `NotFoundError`, `ForbiddenError`, etc. Never `HTTPException` inside services.
- **Type hints everywhere** — mypy compatible throughout.
- **Idempotent background jobs** — APScheduler jobs check for recent alerts before sending duplicates.
- **lru_cache for OpenFDA** — Module-level cache. First call ~2s, subsequent calls instant. $0 alternative to Redis.
- **bcrypt directly** — passlib[bcrypt] has compatibility issues with bcrypt v5+. Direct bcrypt is safer.
- **PyJWT** — python-jose is unmaintained since 2023.
- **pool_pre_ping=True** — Neon.tech serverless cold starts handled gracefully.
- **bulk_schedule with db.add_all()** — 90 doses in 1 DB round-trip, not 90.
- **100% test coverage** — 203 tests: unit tests with MagicMock + integration tests with SQLite in-memory.
- **Structured logging** — structlog with correlation IDs on every request.

---

## Local Setup

```bash
# Clone
git clone https://github.com/Miguel-Bayter/CareSync.git
cd CareSync/medication-management-api

# Virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Configure environment
cp .env.example .env
# Edit .env with your Neon.tech DATABASE_URL and SECRET_KEY

# Run migrations
alembic upgrade head

# Load demo data
python scripts/seed.py

# Start server
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`

---

## Running Tests

```bash
pytest                                    # run all tests
pytest --cov=app --cov-report=html       # with HTML coverage report
pytest tests/unit/                        # unit tests only
pytest tests/integration/                 # integration tests only
```

---

## Generating a Secret Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Project Structure

```
medication-management-api/
├── app/
│   ├── core/          # config, security, exceptions, logging
│   ├── domain/        # enums, value objects (pure Python)
│   ├── models/        # SQLAlchemy ORM models
│   ├── repositories/  # data access layer
│   ├── services/      # business logic
│   ├── routers/       # FastAPI route handlers
│   ├── scheduler/     # APScheduler jobs
│   └── schemas/       # Pydantic DTOs
├── alembic/           # database migrations
├── scripts/           # seed data
├── tests/
│   ├── unit/          # service tests with mocks
│   └── integration/   # endpoint tests with TestClient
├── .env.example
├── pyproject.toml     # ruff + mypy + pytest config
└── requirements.txt
```

---

*Built with FastAPI · PostgreSQL · Neon.tech · APScheduler · OpenFDA · fpdf2*
*Total infrastructure cost: $0.00*
