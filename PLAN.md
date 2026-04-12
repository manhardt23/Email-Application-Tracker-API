# Email Application Tracker — Project Plan

## Stack

- **API:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic
- **Database:** PostgreSQL on EC2 host (no RDS)
- **LLM:** Groq free tier (`llama-3.1-8b-instant`) in prod; Ollama for local dev; `quick_filter` pre-screen to minimize API calls
- **Email Parsing:** BeautifulSoup structured HTML extraction (Phase 3)
- **Scheduler:** System crontab on EC2 triggers `app/worker.py` as a Docker container at peak hours — decoupled from API
- **Infrastructure:** EC2 (t2.micro/t3.micro) + PostgreSQL on host + Docker + ECR
- **CI/CD:** GitHub Actions → ECR push → SSH deploy on merge to `main`

## Cost (~$9-10/month)

- EC2 t3.micro: ~$7.50/month (free on t2.micro first 12 months)
- EBS 20GB: ~$1.60/month
- ECR: ~$0.10/month
- Groq: **free**
- Secrets Manager: ~$1.20/month

## Architecture

```
EC2 Instance
├── PostgreSQL (host OS, data on EBS)
├── API Container (Docker, systemd-managed, :8000)
└── Worker Container (Docker, triggered by crontab at peak hours, exits after run)
```

## Project Structure

```
app/
├── main.py          # FastAPI app factory
├── worker.py        # Standalone worker entrypoint (cron target)
├── config.py        # Pydantic Settings
├── api/v1/          # Versioned REST endpoints
├── db/
│   ├── models.py
│   ├── database.py
│   └── repositories/   # Repository pattern
├── services/        # Business logic (email pipeline orchestration)
├── llm/             # LLM abstraction (Groq/Ollama swappable via LLM_PROVIDER env var)
└── email_client/    # IMAP client + BS4 parser + quick_filter
```

## API Endpoints (`/api/v1/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/applications` | List all (filter: `?stage=`) |
| GET | `/applications/{id}` | Single application |
| PUT | `/applications/{id}` | Update stage/notes |
| GET | `/emails` | List processed emails |
| GET | `/emails/review` | Emails needing review |
| POST | `/jobs/email-check` | Manual trigger |
| GET | `/jobs/{job_id}` | Job status |

## Phases

| # | Phase | Deliverable |
|---|-------|-------------|
| 1 | **Foundation** ✅ | Package structure, imports fixed, Pydantic config, requirements.txt |
| 2 | **DB Normalization** ✅ | Fresh schema (`emails`, `email_analyses`, `worker_runs`), Alembic |
| 3 | **Email Parser** ✅ | Structured BS4 HTML extraction, `Message-ID` dedup |
| 4 | **LLM → Groq** ✅ | Groq adapter, Protocol abstraction, Ollama for local dev |
| 5 | **API Cleanup** 🚧 | Full `/api/v1/` endpoints, DB-backed job status |
| 6 | **Worker Entrypoint** | `app/worker.py` end-to-end, `worker_runs` logging |
| 7 | **Tests** | pytest unit + integration, 70%+ coverage |
| 8 | **Docker** | Multi-stage Dockerfile, docker-compose for local dev |
| 9 | **CI/CD** | GitHub Actions: test on PR, build+deploy on merge |
| 10 | **AWS Deployment** | EC2 + PostgreSQL + systemd + crontab + Secrets Manager |

## Key Notes

- DB is decoupled via Repository pattern — swapping PostgreSQL for another DB is a single `DATABASE_URL` change
- LLM is decoupled via `LLMClassifier` Protocol — set `LLM_PROVIDER=groq` for prod, `ollama` for local
- `quick_filter` stays: reduces LLM calls by pre-screening obvious non-job emails (keyword + domain check)
- System crontab fires worker at: `0 7,12,17,20 * * 1-5` (7am, 12pm, 5pm, 8pm weekdays)
- PostgreSQL credentials → AWS Secrets Manager; injected at container startup via IAM Instance Profile
- Set EBS `DeleteOnTermination=false` before launching EC2 to protect PostgreSQL data

## Phase 4 Breakdown (manageable chunks)

**Phase:** 4 — LLM to Groq  
**Already done:** Phase 1 Foundation, Phase 2 DB Normalization, Phase 3 Email Parser  
**This phase delivers:** Groq-backed classifier in prod, Ollama parity for local, provider-based routing via config

### Chunk 0 (phase bootstrap)
- Create branch from `main`: `phase4 llm groq integration`
- Keep all Phase 4 work on this branch until phase completion

### Chunk 1 (provider contract + routing)
- Finalize/confirm `LLMClassifier` protocol contract
- Route classifier implementation via `LLM_PROVIDER`
- Fail fast on invalid provider values with actionable error

### Chunk 2 (Groq adapter)
- Implement Groq adapter for `llama-3.1-8b-instant`
- Normalize request/response into shared classifier output schema
- Handle provider/API errors with consistent app-level exceptions

### Chunk 3 (Ollama parity)
- Ensure Ollama adapter uses the same normalized output contract
- Keep local dev path straightforward with minimal env setup

### Chunk 4 (pipeline integration)
- Wire provider factory into email analysis service
- Preserve `quick_filter` behavior to avoid unnecessary LLM calls
- Add logs for provider, latency, and classification outcome

### Chunk 5 (tests)
- Add/update tests for:
  - provider routing (`groq`, `ollama`, invalid provider)
  - adapter normalization and failure paths
  - mocked integration flow through analysis pipeline

### Chunk 6 (verification)
- Run lint/tests for touched files
- Commit each completed chunk separately

## Phase 5 Breakdown (manageable chunks)

**Phase:** 5 — API cleanup  
**Already done:** Phases 1–4 on `main` (including LLM Groq integration)  
**This phase delivers:** All documented `/api/v1/` routes implemented against the DB, and job trigger/status backed by `worker_runs` instead of in-memory state.

### Chunk 0 (phase bootstrap)
- Create branch from `main`: `phase5-api-cleanup` (hyphenated; mirrors `phase4-llm-groq-integration`)
- Keep all Phase 5 work on this branch until the phase is agreed complete

### Chunk 1 (emails endpoints)
- Add `GET /api/v1/emails` — list stored emails (reuse/extend `EmailRepository`; define sort/pagination or sensible defaults)
- Add `GET /api/v1/emails/review` — emails whose analysis has `needs_review=True` (reuse `AnalysisRepository.get_needs_review`, load related `Email` for the response)
- Register routes in `app/api/v1/router.py`

### Chunk 2 (applications `PUT`)
- Add `PUT /api/v1/applications/{id}` — update `stage` and/or `notes` as in the endpoint table
- Extend `ApplicationRepository` (or a small service) for explicit user updates vs pipeline-only `update_stage` rules

### Chunk 3 (DB-backed jobs API)
- Remove in-memory `_jobs` from `app/api/v1/jobs.py`
- `POST /api/v1/jobs/email-check`: create a `WorkerRun` via `WorkerRunRepository`, return stable `job_id` (use string form of run integer id for compatibility with existing clients)
- `GET /api/v1/jobs/{job_id}`: load run by id; map `WorkerRun` fields to response (`status`, timestamps, counters, `error_message`)
- Return **409** when a run with `status=running` already exists (add a small repo query helper if needed)

### Chunk 4 (worker ↔ run wiring)
- Thread optional `worker_run_id` into `app.worker.run` (and the pipeline as needed) so API-triggered runs call `WorkerRunRepository.complete` / `fail` with real counts
- Cron/manual `python -m app.worker` runs without id: either skip run rows for that path in this phase or create an implicit run — pick one behavior and document it in code comments

### Chunk 5 (polish & tests)
- Optional: Pydantic response models for OpenAPI clarity where it helps
- Tests for new/changed endpoints (happy path, 404, 409 for concurrent job, job status shape)

### Chunk 6 (verification)
- Run lint/tests for touched files
- Incremental commits per completed chunk
