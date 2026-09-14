---
phase: P0.1
plan: 1
wave: 1
gap_closure: false
---

# Plan P0.1.1: Foundation & Environment Setup

## Objective
Establish the foundational infrastructure, Docker Compose environment, PostgreSQL database with pgvector, configuration management with Pydantic Settings, and FastAPI health verification endpoint. This satisfies the baseline platform requirements for reproducible one-command startup without implementing any downstream retrieval, ingestion, or agent logic.

## Context
Load these files for context:
- `.gsd/SPEC.md`
- `.gsd/REQUIREMENTS.md`
- `.gsd/DECISIONS.md`
- `architecture.md` (Sections 13, 14.1, 16, 20)
- `PRD.md` (Sections 7, 8, 17)

## Tasks

<task type="auto" effort="medium">
  <name>Docker Compose & Environment Configuration</name>
  <files>
    docker-compose.yml
    .env.example
    .gitignore
  </files>
  <action>
    Create the multi-container configuration for PostgreSQL 16 + pgvector, Ollama, and the FastAPI backend.
    
    Steps:
    1. Create `docker-compose.yml`:
       - `postgres`: image `pgvector/pgvector:pg16`, internal port `5432`, optional host mapping `${HOST_PORT_POSTGRES:-5432}:5432`, environment `POSTGRES_DB=lenny_growth`, `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`, volume `postgres_data:/var/lib/postgresql/data`, healthcheck `pg_isready -U postgres -d lenny_growth`.
       - `ollama`: image `ollama/ollama:latest`, internal port `11434`, host mapping `${HOST_PORT_OLLAMA:-11434}:11434`, volume `ollama_data:/root/.ollama`.
       - `backend`: build `./backend`, internal port `8000`, host mapping `${HOST_PORT_BACKEND:-8000}:8000`, env_file `.env`, depends_on `postgres` (condition: service_healthy) and `ollama` (condition: service_started).
       - define bridge network `lenny_internal` and named volumes `postgres_data`, `ollama_data`.
    2. Create `.env.example`:
       - `ENVIRONMENT=development`
       - `LOG_LEVEL=INFO`
       - `CORS_ORIGINS=["http://localhost:3000"]`
       - `DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/lenny_growth`
       - `HOST_PORT_POSTGRES=5432`
       - `HOST_PORT_BACKEND=8000`
       - `HOST_PORT_FRONTEND=3000`
       - `HOST_PORT_OLLAMA=11434`
       - `LLM_PROVIDER=ollama`
       - `OLLAMA_BASE_URL=http://ollama:11434`
       - `OLLAMA_MODEL=llama3.1:8b`
       - `OLLAMA_TIMEOUT_SECONDS=60.0`
       - `EMBED_MODEL=nomic-embed-text`
       - `EMBED_DIMENSIONS=768`
       - `ANTHROPIC_API_KEY=`
       - `ANTHROPIC_MODEL=claude-3-5-sonnet-20241022`
       - `RETRIEVAL_TOP_K=15`
       - `GROUNDING_STRONG_THRESHOLD=0.78`
       - `GROUNDING_LIMITED_THRESHOLD=0.65`
    3. Create `.gitignore`:
       - Ignore `.env`, `data/transcripts/`, Python cache files (`__pycache__`, `*.pyc`), `.pytest_cache`, `.venv`, `node_modules/`, `.coverage`. Keep `.env.example` tracked.
    
    AVOID: Modifying `DATABASE_URL` with `HOST_PORT_POSTGRES`. Internal Docker container communication must remain strictly on `postgres:5432`.
    AVOID: Any references to `weak` or `GROUNDING_WEAK_THRESHOLD`. Use only `GROUNDING_LIMITED_THRESHOLD`.
  </action>
  <verify>
    Check configuration syntax and verify port mappings:
    `docker compose config`
  </verify>
  <done>
    `docker compose config` succeeds without syntax errors, exposing services `postgres`, `ollama`, and `backend`.
  </done>
</task>

<task type="auto" effort="medium">
  <name>Backend Scaffold, Database Schema & Engine Initialization</name>
  <files>
    backend/Dockerfile
    backend/pyproject.toml
    backend/app/core/config.py
    backend/app/core/logging.py
    backend/app/db/schema.sql
    backend/app/db/session.py
    backend/app/db/init_db.py
  </files>
  <action>
    Scaffold the backend package and implement PostgreSQL DDL schema with pgvector.
    
    Steps:
    1. Create `backend/pyproject.toml`:
       - Standard packaging with Python >=3.11.
       - Dependencies: `fastapi>=0.110.0`, `uvicorn[standard]>=0.28.0`, `pydantic>=2.6.0`, `pydantic-settings>=2.2.0`, `sqlalchemy>=2.0.28`, `asyncpg>=0.29.0`, `pgvector>=0.2.5`, `httpx>=0.27.0`, `python-json-logger>=2.0.7`, `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`.
    2. Create `backend/Dockerfile`:
       - Base `python:3.11-slim`, install `curl`, copy `pyproject.toml`, pip install dependencies, copy application code, expose 8000, start uvicorn.
    3. Create `backend/app/core/config.py`:
       - Pydantic `BaseSettings` reading environment variables with canonical `GROUNDING_LIMITED_THRESHOLD: float = 0.65`, `DATABASE_URL`, `OLLAMA_BASE_URL`, etc.
    4. Create `backend/app/core/logging.py`:
       - Structured JSON logger formatter with timestamp, level, name, and correlation ID support.
    5. Create `backend/app/db/schema.sql`:
       - Exact DDL from Architecture §14.1:
         - `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`
         - `CREATE EXTENSION IF NOT EXISTS "vector";`
         - `episodes` table
         - `transcript_chunks` table with `VECTOR(768)` and HNSW index (`vector_cosine_ops`)
         - `sessions` table
         - `messages` table with `evidence_tier`
         - `source_references` table
         - `artifacts` table
    6. Create `backend/app/db/session.py` and `backend/app/db/init_db.py`:
       - Async SQLAlchemy engine (`create_async_engine`) and sessionmaker.
       - Async DB initialization executing `schema.sql` idempotently.
    
    AVOID: Altering the vector dimension away from 768.
    AVOID: External ORM migrations or external SaaS dependencies (no Supabase, no Railway).
  </action>
  <verify>
    Verify python syntax and schema validity by executing a schema test or syntax check.
  </verify>
  <done>
    Backend package files are syntactically valid and DDL schema matches Architecture §14.1 with `VECTOR(768)`.
  </done>
</task>

<task type="auto" effort="medium">
  <name>FastAPI App Factory, Health Endpoint & Automated Verification</name>
  <files>
    backend/app/api/v1/health.py
    backend/app/main.py
    backend/tests/test_config.py
    backend/tests/test_health.py
  </files>
  <action>
    Implement FastAPI application, health check router, and unit/integration tests.
    
    Steps:
    1. Create `backend/app/api/v1/health.py`:
       - `GET /api/v1/health`
       - Verifies PostgreSQL reachability (`SELECT 1`).
       - Verifies Ollama service reachability (`GET {OLLAMA_BASE_URL}/api/tags`).
       - Note: Verify service reachability only; do NOT check model download/readiness status.
       - Returns 200 with `{"status": "ok", "database": "connected", "ollama": "reachable", "provider": settings.LLM_PROVIDER}` if both succeed.
       - If PostgreSQL fails, returns 503 Service Unavailable with RFC 7807 problem details.
       - If Ollama is unreachable, reports status degraded/unreachable.
    2. Create `backend/app/main.py`:
       - FastAPI app factory.
       - Lifespan context calling `init_db()`.
       - CORS middleware with `settings.CORS_ORIGINS`.
       - Include `/api/v1/health` router. Also alias `/health` for convenience.
    3. Create `backend/tests/test_config.py`:
       - Verify Settings reads defaults and validates `GROUNDING_LIMITED_THRESHOLD`.
    4. Create `backend/tests/test_health.py`:
       - Test health check endpoint with mocked DB and HTTP clients.
  </action>
  <verify>
    Run pytest:
    `pytest backend/tests`
    Run Docker compose:
    `docker compose up -d`
    Verify endpoint:
    `curl -s http://localhost:8000/api/v1/health`
  </verify>
  <done>
    Pytest suite passes; `curl http://localhost:8000/api/v1/health` returns valid JSON showing database and Ollama status.
  </done>
</task>

## Must-Haves
After all tasks complete, verify:
- [ ] `docker-compose.yml` configures PostgreSQL 16 + pgvector, Ollama, and FastAPI backend.
- [ ] PostgreSQL container uses internal port 5432; host port mapping is configurable via `HOST_PORT_POSTGRES`.
- [ ] PostgreSQL DDL executes cleanly and includes `VECTOR(768)`.
- [ ] `GET /api/v1/health` returns status of PostgreSQL and Ollama reachability.
- [ ] Zero application code from P0.2 or later (no ingestion, no retrieval, no grounding gate, no Pi bridge).
- [ ] No references to `weak` or `GROUNDING_WEAK_THRESHOLD`.

## Success Criteria
- [ ] `docker compose up -d` starts services without error.
- [ ] Health endpoint responds with 200 OK.
- [ ] Automated tests pass.
