# Email Application Tracker API

Backend API for tracking job applications directly from inbox activity. This project is being built in phased increments, and this README is intentionally roadmap-focused so contributors can quickly see what is done and what is planned next.

## Project Goal

Build a personal applicant-tracking backend that:
- connects to Comcast/Xfinity email over IMAP
- parses and classifies job-related emails
- stores structured application data in PostgreSQL
- exposes clean REST endpoints for retrieval, updates, and job processing

## Current Status

Current source-of-truth plan: `PLAN.md`

### Phase Progress

| # | Phase | Status | Deliverable |
|---|-------|--------|-------------|
| 1 | Foundation | Complete | Package structure, config setup, requirements |
| 2 | DB Normalization | Complete | Normalized schema + Alembic migrations |
| 3 | Email Parser | Complete | BeautifulSoup structured extraction + Message-ID dedup |
| 4 | LLM -> Groq | Complete | Groq adapter + provider abstraction |
| 5 | API Cleanup | Complete | Final `/api/v1/` endpoint surface + job status |
| 6 | Worker Entrypoint | Complete | `python -m app.worker`: exit codes, logging, IMAP retries, worker env config, tests + README operator docs |
| 7 | Tests | Complete | pytest unit + integration, 83% line coverage, ≥70% gate in pyproject.toml |
| 8 | Docker | Planned | Multi-stage image + compose setup |
| 9 | CI/CD | Planned | GitHub Actions test/build/deploy flow |
| 10 | AWS Deployment | Planned | EC2 deployment with host PostgreSQL + cron scheduling |

## Planned Architecture

```text
EC2 Instance
|- PostgreSQL (host OS, EBS-backed)
|- API container (Docker, systemd-managed)
`- Worker container (cron-triggered batch runs)
```

The worker is intentionally decoupled from API request/response flow and runs on schedule during peak hours.

## Planned Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.x + Alembic
- PostgreSQL (on EC2 host)
- IMAP + BeautifulSoup (email parsing)
- LLM provider abstraction:
  - Groq (`llama-3.1-8b-instant`) for production
  - Ollama for local development
- Docker + ECR
- GitHub Actions CI/CD

## Planned API Surface (`/api/v1`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | API liveness check |
| GET | `/applications` | List applications (`?stage=` filter) |
| GET | `/applications/{id}` | Fetch single application |
| PUT | `/applications/{id}` | Update stage/notes |
| GET | `/emails` | List processed emails |
| GET | `/emails/review` | List emails needing review |
| POST | `/jobs/email-check` | Trigger manual processing job |
| GET | `/jobs/{job_id}` | Check processing job status |

## Repository Structure

```text
app/
|- main.py
|- worker.py
|- config.py
|- api/v1/
|- db/
|  |- models.py
|  |- database.py
|  `- repositories/
|- services/
|- llm/
`- email_client/
```

## Running the Worker

The worker (`app/worker.py`) is a standalone process that fetches emails, runs LLM classification, and exits. It is decoupled from the API and designed to be triggered by cron or `docker run`.

### Locally

```bash
python -m app.worker
```

### In Docker

```bash
docker run --rm --env-file /etc/tracker.env <IMAGE> python -m app.worker
```

### Via cron (EC2)

```cron
0 7,12,17,20 * * 1-5  docker run --rm --env-file /etc/tracker.env <IMAGE> python -m app.worker
```

### Required environment variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `EMAIL_USER` | IMAP account username |
| `EMAIL_PASS` | IMAP account password |
| `LLM_PROVIDER` | `groq` (prod) or `ollama` (local) |
| `GROQ_API_KEY` | Required when `LLM_PROVIDER=groq` |

### Optional worker knobs

| Variable | Default | Description |
|----------|---------|-------------|
| `IMAP_SERVER` | `imap.comcast.net` | IMAP hostname |
| `IMAP_TIMEOUT_SECONDS` | `30` | TCP socket timeout for IMAP connections |
| `MAX_EMAILS_PER_RUN` | `50` | Maximum emails fetched per worker run |
| `EMAIL_LIMIT` | `10` | Legacy fetch limit (effective limit = min of both) |
| `STALE_RUN_TTL_MINUTES` | `1440` | Age at which queued/running rows are auto-failed |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, etc.) |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Pipeline completed successfully |
| `1` | Unexpected pipeline failure; `WorkerRun` row marked `failed` |
| `2` | No slot available (another run is active) — safe for cron to ignore |
| `3` | Fatal configuration error — check env vars and retry |

### Relationship to `POST /jobs/email-check`

The API endpoint creates a `WorkerRun` row in `queued` state and fires the worker in a background thread passing the `worker_run_id`. The worker claims the row (`queued → running`) and updates it to `completed` or `failed`. Cron/manual invocations create their own row. Only one active run is permitted at a time (enforced by a partial unique index on `worker_runs`).

## Testing

Tests live in `tests/unit/` and `tests/integration/`.  
All tests use SQLite in-memory — no running database required.

```bash
# Run all tests with coverage (gate: ≥70% line coverage)
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest -m integration

# Skip integration tests
pytest -m "not integration"

# Print coverage report without the per-file detail
pytest --cov=app --cov-report=term
```

The `≥70%` gate is enforced via `addopts` in `pyproject.toml` and will be wired into CI in Phase 9.  
Current baseline: **≥83%** line coverage.

## Local Development (Target Workflow)

1. Create a virtual environment and install dependencies.
2. Configure environment variables (`DATABASE_URL`, IMAP settings, provider settings).
3. Run migrations.
4. Start API locally.
5. Trigger a manual email-check job via API or run `python -m app.worker` directly.

Exact commands may evolve while active phases are completed; use `PLAN.md` and project scripts as current implementation details shift.

## Roadmap Notes

- Keep data model portable via repository pattern and `DATABASE_URL`.
- Keep LLM provider swappable via protocol-based abstraction.
- Preserve `quick_filter` pre-screening to reduce unnecessary LLM calls.
- Run worker on weekday peak-hour schedule for cost-efficient processing.

## Future Plans

- Add a lightweight frontend dashboard later (likely React + Tailwind) for visualizing application stages, trends, and funnel metrics once backend phases are stable.

## Author

**Jacob Manhardt**  
[LinkedIn](https://www.linkedin.com/in/jacob-manhardt-b9b75025b/)
