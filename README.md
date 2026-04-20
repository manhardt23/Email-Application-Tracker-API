# Email Application Tracker API

Backend API that ingests job-related inbox activity, classifies emails, and persists application state for retrieval and updates.

## Project Goal

This project tracks real job application progress by:
- connecting to Comcast/Xfinity inboxes over IMAP,
- parsing and classifying job-related emails,
- storing normalized records in PostgreSQL, and
- exposing `/api/v1` endpoints for application, email, and worker-run operations.

## Current Status

Source-of-truth plan and phase history: `PLAN.md`.

### Phase Progress

| # | Phase | Status | Deliverable |
|---|-------|--------|-------------|
| 1 | Foundation | Complete | Package structure, config setup, requirements |
| 2 | DB Normalization | Complete | Normalized schema + migrations |
| 3 | Email Parser | Complete | BeautifulSoup extraction + `Message-ID` dedup |
| 4 | LLM -> Groq | Complete | Provider abstraction + Groq/Ollama adapters |
| 5 | API Cleanup | Complete | `/api/v1` endpoint surface + DB-backed job status |
| 6 | Worker Entrypoint | Complete | Standalone worker, exit contract, retries, logging, config |
| 7 | Tests | Complete | Unit + integration tests, coverage gate in `pyproject.toml` |
| 8 | Docker | Complete | Multi-stage image + Compose for local/prod |
| 9 | CI/CD | Complete | GitHub Actions test + deploy pipeline |
| 10 | AWS Deployment | In progress | EC2 deployment model with Compose + scheduled worker runs |
| 11 | Runtime Worker Limit API | In progress | `POST /api/v1/jobs/email-limit` in-memory worker override |

## Architecture (Current)

```text
EC2 host
|- Docker Compose `db` service (PostgreSQL)
|- Docker Compose `api` service (FastAPI app)
`- Worker process (`python -m app.worker`) triggered manually, by API, or by scheduler
```

The worker stays decoupled from API request/response flow and runs as a one-shot process.

## Implemented Tech Stack

- **Language/runtime:** Python 3.12
- **API framework:** FastAPI
- **Validation/config:** Pydantic v2 + `pydantic-settings`
- **Data layer:** SQLAlchemy 2.x repositories + Alembic migration assets
- **Database:** PostgreSQL 16 (Compose-managed)
- **Email ingestion/parsing:** IMAP + BeautifulSoup4 + `quick_filter` pre-screening
- **LLM integration:** Groq (`llama-3.1-8b-instant`) and Ollama via provider abstraction
- **Containerization:** Docker multi-stage build + Docker Compose
- **Quality/verification:** pytest, pytest-cov, ruff
- **CI/CD + cloud:** GitHub Actions, Amazon ECR, EC2 (SSH deploy workflow)

## API Surface (`/api/v1`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | API liveness check |
| GET | `/applications` | List applications (`?stage=` filter) |
| GET | `/applications/{id}` | Fetch a single application |
| PUT | `/applications/{id}` | Update stage/notes |
| GET | `/emails` | List processed emails |
| GET | `/emails/review` | List emails requiring review |
| POST | `/jobs/email-check` | Queue and trigger a worker run |
| POST | `/jobs/email-limit` | Set process-local worker fetch override (`1..1000`) |
| GET | `/jobs/{job_id}` | Fetch worker run status + metrics |

## Repository Structure

```text
app/
|- main.py
|- worker.py
|- config.py
|- logging_config.py
|- api/v1/
|- db/
|  |- models.py
|  |- database.py
|  `- repositories/
|- services/
|  `- worker_runtime.py
|- llm/
`- email_client/
```

## Worker Operation

`app/worker.py` is a standalone process that fetches emails, runs classification, persists records, and exits with a stable code.

### Run locally

```bash
python -m app.worker
```

### Run in Docker

```bash
docker run --rm --env-file /etc/tracker.env <IMAGE> python -m app.worker
```

### Example cron entry (EC2)

```cron
0 7,12,17,20 * * 1-5  docker run --rm --env-file /etc/tracker.env <IMAGE> python -m app.worker
```

### Required environment variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `EMAIL_USER` | IMAP account username |
| `EMAIL_PASS` | IMAP account password |
| `LLM_PROVIDER` | `groq` or `ollama` |
| `GROQ_API_KEY` | Required when `LLM_PROVIDER=groq` |

### Optional worker knobs

| Variable | Default | Description |
|----------|---------|-------------|
| `IMAP_SERVER` | `imap.comcast.net` | IMAP hostname |
| `IMAP_TIMEOUT_SECONDS` | `30` | IMAP connect/read timeout |
| `MAX_EMAILS_PER_RUN` | `10` | Preferred per-run fetch cap |
| `EMAIL_LIMIT` | `5` | Legacy cap retained for compatibility |
| `STALE_RUN_TTL_MINUTES` | `1440` | TTL before stale queued/running rows reconcile |
| `LOG_LEVEL` | `INFO` | Worker log verbosity |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Pipeline completes successfully |
| `1` | Pipeline fails unexpectedly; `WorkerRun` is marked `failed` |
| `2` | Another run is active; invocation exits without work |
| `3` | Fatal configuration/bootstrap error |

### Relationship to `POST /jobs/email-check`

`POST /jobs/email-check` creates a queued `WorkerRun` row and starts background execution with `worker_run_id`.  
The worker claims queued runs (`queued -> running`), updates metrics, and marks `completed` or `failed`.  
`POST /jobs/email-limit` sets an in-memory override used by subsequent in-process worker invocations.

## Testing

Tests live in `tests/unit/` and `tests/integration/`.

```bash
# Run all tests (coverage gate: >=70%)
pytest

# Run unit tests
pytest tests/unit/

# Run integration tests
pytest -m integration

# Skip integration tests
pytest -m "not integration"
```

Coverage gate is enforced by `pyproject.toml` and CI.  
Current observed baseline: **83.91%** line coverage (`129` tests passing).

## CI/CD (GitHub Actions)

Workflow: `.github/workflows/ci.yml`.

- **CI job:** runs `ruff check .` and `python -m pytest` on pull requests and pushes.
- **Deploy job (main only):** builds Docker image, pushes SHA and `latest` tags to ECR, copies `docker-compose.prod.yml` to EC2, and restarts the `api` service via `docker compose`.

### Repository secrets (deploy)

| Secret | Purpose |
|--------|---------|
| `AWS_ACCESS_KEY_ID` | IAM access key for ECR push |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |
| `AWS_REGION` | ECR region |
| `ECR_REPOSITORY` | ECR repository name |
| `EC2_HOST` | EC2 public host/IP |
| `EC2_USER` | SSH user |
| `EC2_SSH_PRIVATE_KEY` | SSH private key |
| `EC2_DEPLOY_DIR` | Optional deploy directory on EC2 |

## Docker Local Development

### 1) Prepare env

```bash
cp .env.example .env
```

Set real values for `EMAIL_USER`, `EMAIL_PASS`, and `GROQ_API_KEY`.

### 2) Start API + Postgres

```bash
docker compose up --build -d db api
```

Docs:
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

### 3) Apply SQL migrations (existing DB only)

Fresh local Docker volumes create tables on startup from SQLAlchemy models.  
Run SQL migrations only when attaching to existing persisted DB state.

```powershell
Get-Content "migrations/001_worker_run_queue_timestamps.sql" | docker compose exec -T db psql -U job_tracker_user -d job_tracker
Get-Content "migrations/002_worker_run_last_processed_uid.sql" | docker compose exec -T db psql -U job_tracker_user -d job_tracker
```

### 4) Run worker one-shot

```bash
docker compose run --rm --profile worker worker
```

## Resume-Justifiable Technical Highlights

- Designed a decoupled worker execution model with DB-backed run state transitions (`queued -> running -> completed/failed`) and conflict protection for concurrent runs.
- Implemented runtime-safe processing controls (validated `POST /jobs/email-limit` + env-based limits) without redeploying the API.
- Enforced quality gates in CI (`ruff` + `pytest` + coverage threshold) and maintained an active coverage baseline above the configured floor.
- Automated container delivery from GitHub Actions to ECR and EC2 with tagged image promotion (`SHA` + `latest`) and remote Compose rollout.

## Plan (Future Work)

- Add a lightweight frontend dashboard (likely React + Tailwind) to visualize application funnel metrics.
- Expand production worker scheduling/operations hardening for long-running deployment usage.
- Continue phase tracking in `PLAN.md` for scoped, incremental delivery.

## Author

**Jacob Manhardt**  
[LinkedIn](https://www.linkedin.com/in/jacob-manhardt-b9b75025b/)
