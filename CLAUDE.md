# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered grading and moderation website for university educators. Teachers use it to:
1. Fetch student submissions and moderation reports from the **RiPPLE platform** via its API
2. Grade submissions automatically using **generative AI** against a teacher-defined rubric
3. View results and analytics in a clean UI

**Data hierarchy:** Teacher → Classes → (Students, Assessments) → (Submissions, Rubric) → AI Grades

---

## Deployment Strategy (Critical Constraint)

The app must support **zero code changes** to move between phases:

- **Phase 1 (current):** Runs locally on the teacher's desktop
- **Phase 2 (future):** Deployed to university cloud infrastructure (AWS/Azure)

All environment-specific values (database URL, API keys, service URLs, etc.) must be driven entirely by environment variables, never hardcoded. The frontend talks to the backend only via API — it must never assume a specific host.

---

## Tech Stack

### Backend
- **Language:** Python
- **Framework:** FastAPI
- **ORM:** SQLAlchemy (strict — all DB access goes through the ORM, no raw SQL)
- **Migrations:** Alembic
- **Dependency management:** `pip` + `requirements.txt`
- **Database:** SQLite for Phase 1 → PostgreSQL for Phase 2 (swap is a single `DATABASE_URL` env var change, no code changes)

### Frontend
- **Framework:** React (SPA), JavaScript (not TypeScript)
- **Build tool:** Vite
- **Styling:** TailwindCSS v4 (configured via `@tailwindcss/vite` plugin — no `tailwind.config.js`)
- **Other libraries:** **Consult the user before introducing any new frontend dependency** (state management, charting, data tables, routing, etc.)

### AI
- **Provider:** Anthropic (Claude models via the `anthropic` Python SDK)
- The AI layer is abstracted in `app/services/ai_service.py` — the model is configured via `ANTHROPIC_MODEL` env var

### External Integrations
- **RiPPLE API:** Deferred — stub lives in `app/services/ripple_service.py`

---

## Key Architectural Rules

- **Strictly decoupled:** Frontend is a pure SPA that communicates with the backend exclusively via REST API. No SSR, no server-side templating.
- **ORM-only DB access:** All database interaction goes through SQLAlchemy models. This is what enables the SQLite → PostgreSQL pivot.
- **Config via environment:** All environment-specific settings must live in `.env` files or environment variables, never in source code. See `backend/.env.example` and `frontend/.env.example`.
- **Consult before adding tech:** Propose any new library or tool to the user before adding it.

---

## Commands

All backend commands run from the `backend/` directory.

**Backend:**
```bash
cd backend

# First-time setup
pip install -r requirements.txt
cp .env.example .env  # then fill in real values

# Run dev server (API available at http://localhost:8000)
uvicorn app.main:app --reload

# Run database migrations
alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe the change"

# Run tests
pytest

# Run a single test
pytest tests/path/to/test_file.py::test_function_name
```

**Frontend:**
```bash
cd frontend

# First-time setup
npm install
cp .env.example .env.local  # then set VITE_API_URL

# Dev server (available at http://localhost:5173)
npm run dev

# Production build
npm run build

# Lint
npm run lint
```

---

## Project Structure

```
AI_Ripple_Grader/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app + CORS middleware
│   │   ├── core/
│   │   │   ├── config.py     # Pydantic Settings — reads all config from env vars
│   │   │   └── database.py   # SQLAlchemy engine, SessionLocal, Base, get_db()
│   │   ├── api/              # Route handlers (FastAPI routers)
│   │   ├── models/           # SQLAlchemy ORM models (import all in __init__.py)
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── services/
│   │       ├── ai_service.py      # Anthropic grading logic
│   │       └── ripple_service.py  # RiPPLE API stub
│   ├── alembic/              # Migration scripts (env.py reads DB URL from settings)
│   ├── alembic.ini
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.js     # Fetch wrapper — uses VITE_API_URL env var
│   │   ├── components/
│   │   ├── pages/
│   │   ├── App.jsx
│   │   └── index.css         # Just: @import "tailwindcss"
│   ├── vite.config.js        # Tailwind v4 configured here via plugin
│   └── .env.example
└── CLAUDE.md
```

### Key file notes
- `backend/app/models/__init__.py` — **must import every model module** so Alembic auto-detects schema changes
- `backend/alembic/env.py` — reads `DATABASE_URL` from `settings`, not from `alembic.ini`
- `frontend/src/api/client.js` — single place to change if API shape evolves; all components call through here
