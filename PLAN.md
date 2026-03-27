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
| 2 | **DB Normalization** | Fresh schema (`emails`, `email_analyses`, `worker_runs`), Alembic |
| 3 | **Email Parser** | Structured BS4 HTML extraction, `Message-ID` dedup |
| 4 | **LLM → Groq** | Groq adapter, Protocol abstraction, Ollama for local dev |
| 5 | **API Cleanup** | Full `/api/v1/` endpoints, DB-backed job status |
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
