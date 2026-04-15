# Email Application Tracker — Project Plan

## Stack

- **API:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic
- **Database:** PostgreSQL via Docker Compose `db` service on EC2 (no RDS)
- **LLM:** Groq free tier (`llama-3.1-8b-instant`) in prod; Ollama for local dev; `quick_filter` pre-screen to minimize API calls
- **Email Parsing:** BeautifulSoup structured HTML extraction (Phase 3)
- **Scheduler:** System crontab on EC2 triggers `app/worker.py` as a Docker container at peak hours — decoupled from API
- **Infrastructure:** EC2 (t2.micro/t3.micro) + Docker Compose (`api` + `db`) + ECR
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
├── PostgreSQL Container (`db`, data on EBS-backed Docker volume)
├── API Container (`api`, Docker Compose, :8000)
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
| 5 | **API Cleanup** ✅ | Full `/api/v1/` endpoints, DB-backed job status |
| 6 | **Worker Entrypoint** ✅ | Hardened `python -m app.worker` for cron/Docker, observability, exit contract |
| 7 | **Tests** ✅ | pytest unit + integration, **≥70%** line coverage, CI-ready test commands |
| 8 | **Docker** ✅ | Multi-stage Dockerfile, docker-compose for local dev |
| 9 | **CI/CD** ✅ | GitHub Actions: test on PR/push, ECR image push + SSH deploy on `main` |
| 10 | **AWS Deployment** | EC2 + Docker Compose (`api` + `db`) + crontab + Secrets Manager |

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

## Phase 6 Breakdown (manageable chunks)

**Phase:** 6 — Worker entrypoint (cron / Docker) — **✅ complete**  
**Already done:** Phases 1–5 on `main` (including `app/worker.py` pipeline, `WorkerRun` queued → running → complete/fail, API `POST /jobs/email-check` wiring, `migrations/001_worker_run_queue_timestamps.sql` for PostgreSQL)  
**This phase delivered:** A production-grade **standalone worker** suitable for crontab and `docker run … python -m app.worker`: predictable **exit codes**, **logging** (`app/logging_config.py`, module loggers), **config** knobs (`IMAP_TIMEOUT_SECONDS`, `MAX_EMAILS_PER_RUN`, `STALE_RUN_TTL_MINUTES`, etc.), **IMAP connect retries** with transient vs permanent errors in `email_client/client.py`, **tests** (`tests/unit/test_phase6_worker.py`), and **README** operator docs (`python -m app.worker`, Docker, cron, exit codes).

### Chunk 0 (phase bootstrap)
- Branch from `main`: `phase6-worker-entrypoint` (used for Phase 6 implementation)
- Phase complete — merge to `main` per repo workflow when ready

### Chunk 1 (exit contract & operator UX)
- Define and document **process exit codes** (e.g. `0` success, non-zero for configuration error vs pipeline failure vs “no slot” / concurrency) so cron can alert
- Ensure fatal misconfiguration fails fast with a clear message before IMAP (invalid `LLM_PROVIDER`, missing DB URL, etc.)
- Optional: minimal **CLI flags** or env-only contract — pick one style and document it in module docstring + README worker section

### Chunk 2 (logging & correlation)
- Standardize log lines to include **`worker_run_id`** (and job status transitions) where useful
- Replace ad-hoc `print` with **`logging`** (module logger), levels appropriate for prod vs dev
- Optional: single log line format (timestamp, level, run id, message) for grep/journald

### Chunk 3 (resilience & IMAP edge cases)
- Classify **transient vs permanent** IMAP/network errors; bounded **retries** or clear `WorkerRun.fail` messages where retries are not appropriate
- Confirm **duplicate / partial fetch** behavior is logged once per decision path (no log spam in large inboxes)

### Chunk 4 (worker-focused configuration)
- Add or tighten **Pydantic settings** used only by the worker (e.g. IMAP timeout, max messages per run, stale-run TTL if made configurable) with sensible defaults
- Keep secrets out of logs; validate limits at startup

### Chunk 5 (tests & documentation)
- Unit tests for **exit code** / early-exit paths (mock IMAP + DB session factory as needed)
- Short **README** subsection: how to run worker locally, in Docker, and via cron; required env vars; how it relates to `POST /jobs/email-check`

### Chunk 6 (verification)
- Run lint/tests for touched files
- Incremental commits per completed chunk

## Phase 7 Breakdown (manageable chunks)

**Phase:** 7 — Tests & coverage baseline  
**Already done:** Phases 1–6 on `main` (unit tests exist per phase: `tests/unit/test_phase3_email_parser.py`, `test_phase4_llm_providers.py`, `test_phase5_api.py`, `test_phase6_worker.py`; no repo-wide coverage gate yet)  
**This phase delivers:** A **repeatable pytest setup** for unit + integration tests, **shared fixtures** where they reduce duplication, **meaningful coverage** of repositories/services/API paths not yet exercised, a documented **`coverage run` / `coverage report`** workflow targeting **≥70%** line coverage, and a **single command** (documented in `README` or `PLAN`) that CI can call later in Phase 9.

### Chunk 0 (phase bootstrap)
- Create branch from `main`: `phase7-test-coverage` (hyphenated; keeps branch names grep-friendly)
- Keep all Phase 7 work on this branch until the phase is agreed complete

### Chunk 1 (pytest layout & markers)
- Confirm or add **`pytest.ini`** / **`pyproject.toml`** `[tool.pytest.ini_options]` — `testpaths`, asyncio mode if needed, optional markers (`integration`, `slow`)
- Normalize **`tests/unit/`** vs **`tests/integration/`** naming; ensure `tests/conftest.py` (root) can hold shared fixtures without circular imports

### Chunk 2 (unit coverage — gaps)
- Identify modules below reasonable coverage (repositories, `app/services`, `app/api/v1` routes not covered by phase-specific files)
- Add focused unit tests with mocks; avoid testing implementation trivia — assert behavior and error paths

### Chunk 3 (integration tests)
- Add **`tests/integration/`** tests that spin up the FastAPI app (or key routers) with a **test database** (SQLite in-memory + dependency overrides, or transactional PostgreSQL pattern — pick one and document)
- Cover at least one happy-path flow that crosses API → DB (e.g. health + one CRUD-style route if fixtures allow)

### Chunk 4 (coverage gate & docs)
- Add **`coverage`** / **`pytest-cov`** to dev dependencies if not present; document **`pytest --cov=app --cov-fail-under=70`** (or equivalent) in `README` or a short comment in `pyproject.toml`
- If **70%** is not yet reachable in one pass, document current % and ratchet plan — prefer failing CI later (Phase 9) over silently lowering the bar

### Chunk 5 (fixtures & hygiene)
- Extract repeated test setup (DB session, app client, seed helpers) into **`conftest.py`** fixtures
- Address flaky patterns (time-dependent tests, unordered collections) early

### Chunk 6 (verification)
- Run full **`pytest`** + **`coverage report`** locally; fix lint on touched files
- Incremental commits per completed chunk
