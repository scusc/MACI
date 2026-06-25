# MACI — Multi-Agent Consensus Itinerary

> Autonomous AI delegates that negotiate complex travel constraints into perfectly synchronized, conflict-free group itineraries.

## What is MACI?

MACI is a B2B SaaS product that solves the nightmare of coordinating group travel for enterprises. Instead of a human travel agent manually juggling spreadsheets of conflicting schedules, budgets, and airport constraints, MACI assigns each cluster of travelers a personal **AI delegate**. These delegates autonomously negotiate — proposing flights, rejecting misaligned options, and converging on a single, conflict-free group itinerary.

### Core Insight

> Group travel is **not a search problem**. It is a **distributed game theory and dispute resolution problem**.

## Architecture

```
Frontend (Next.js) → FastAPI Backend → PostgreSQL + Redis
                         ├── Orchestrator (MapReduce clustering + convergence enforcement)
                         ├── AI Delegates (context-sharded LLM calls via LiteLLM + Instructor)
                         └── Flight Providers (Amadeus + Duffel + SerpAPI)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+ / FastAPI |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| LLM | Google Gemini Flash (via LiteLLM) |
| Flight Data | Amadeus + Duffel + SerpAPI |
| Frontend | Next.js 14 |
| Deployment | Docker Compose |

## Quick Start

```bash
# 1. Clone and navigate
git clone <repo> && cd MACI

# 2. Copy environment config
cp backend/.env.example backend/.env

# 3. Start infrastructure (PostgreSQL + Redis)
docker-compose up -d db redis

# 4. Setup Python environment
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 5. Run database migrations
alembic upgrade head

# 6. Start the backend
uvicorn app.main:app --reload --port 8000

# 7. Open API docs
open http://localhost:8000/docs
```

## Project Structure

```
MACI/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── config.py            # Settings (env vars)
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── models/              # ORM models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── api/                 # Route handlers
│   │   ├── services/            # Business logic
│   │   ├── providers/           # Flight data adapters
│   │   ├── llm/                 # LLM abstraction
│   │   └── core/                # Shared utilities
│   ├── migrations/              # Alembic migrations
│   └── tests/
├── frontend/                    # Next.js (coming soon)
├── docker-compose.yml
└── README.md
```

## License

Private — All rights reserved.
