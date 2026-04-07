# Email Application Tracker API

Backend API for tracking job applications directly from inbox activity. This project is being built in phased increments, and this README is intentionally roadmap-focused so contributors can quickly see what is done, what is in progress, and what is planned next.

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
| 3 | Email Parser | In Progress | BeautifulSoup structured extraction + Message-ID dedup |
| 4 | LLM -> Groq | Planned | Groq adapter + provider abstraction |
| 5 | API Cleanup | Planned | Final `/api/v1/` endpoint surface + job status |
| 6 | Worker Entrypoint | Planned | `app/worker.py` end-to-end run logging |
| 7 | Tests | Planned | Unit/integration coverage baseline |
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

## Local Development (Target Workflow)

1. Create a virtual environment and install dependencies.
2. Configure environment variables (`DATABASE_URL`, IMAP settings, provider settings).
3. Run migrations.
4. Start API locally.
5. Trigger a manual email-check job via API.

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
