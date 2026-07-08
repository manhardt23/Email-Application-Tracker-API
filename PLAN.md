# Email Application Tracker — Project Plan

## Stack

- **API:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic
- **Database:** PostgreSQL via Docker Compose `db` service on EC2 (no RDS)
- **LLM:** Groq free tier (`llama-3.3-70b-versatile`) in prod; Ollama for local dev; `quick_filter` pre-screen to minimize API calls
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

## API Endpoints (paths below are under `/api/v1/`)

| Method | Path                 | Description                                                            |
| ------ | -------------------- | ---------------------------------------------------------------------- |
| GET    | `/health`            | Liveness check (`/api/v1/health`)                                      |
| GET    | `/applications`      | List all (filter: `?stage=`)                                           |
| GET    | `/applications/{id}` | Single application                                                     |
| PUT    | `/applications/{id}` | Update stage/notes                                                     |
| GET    | `/emails`            | List processed emails                                                  |
| GET    | `/emails/review`     | Emails needing review                                                  |
| POST   | `/jobs/email-check`  | Manual trigger                                                         |
| POST   | `/jobs/email-limit`  | In-memory fetch override (`1..1000`; API process only — see Key Notes) |
| GET    | `/jobs/{job_id}`     | Job status                                                             |

## Phases

| #   | Phase                        | Deliverable                                                                                                             |
| --- | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 1   | **Foundation** ✅            | Package structure, imports fixed, Pydantic config, requirements.txt                                                     |
| 2   | **DB Normalization** ✅      | Fresh schema (`emails`, `email_analyses`, `worker_runs`), Alembic                                                       |
| 3   | **Email Parser** ✅          | Structured BS4 HTML extraction, `Message-ID` dedup                                                                      |
| 4   | **LLM → Groq** ✅            | Groq adapter, Protocol abstraction, Ollama for local dev                                                                |
| 5   | **API Cleanup** ✅           | Full `/api/v1/` endpoints, DB-backed job status                                                                         |
| 6   | **Worker Entrypoint** ✅     | Hardened `python -m app.worker` for cron/Docker, observability, exit contract                                           |
| 7   | **Tests** ✅                 | pytest unit + integration, **≥70%** line coverage, CI-ready test commands                                               |
| 8   | **Docker** ✅                | Multi-stage Dockerfile, docker-compose for local dev                                                                    |
| 9   | **CI/CD** ✅                 | GitHub Actions: test on PR/push, ECR image push + SSH deploy on `main`                                                  |
| 10  | **AWS Deployment** ✅        | EC2 + Docker Compose (`api` + `db`) + crontab + Secrets Manager                                                         |
| 11  | **Runtime email limit** ✅   | `POST /jobs/email-limit` in-memory override (`1..1000`); applies only to worker runs in the API process (see Key Notes) |
| 12  | **UID stale reset** ✅       | Reset IMAP cursor when tracked UID is older than 30 days or missing on server                                           |
| 13  | **JWT auth + RBAC** ✅       | `users` table, JWT, `admin` vs `viewer`, seeded demo user                                                               |
| 14  | **Nginx + HTTPS**            | Domain, reverse proxy, Let's Encrypt (prerequisite for public demo)                                                     |
| 15  | **Frontend dashboard**       | Static HTML/CSS/Tailwind/JS at `/`, login, applications/emails/jobs UI                                                  |
| 16  | **Public stats endpoint**    | `GET /stats` with total emails, job-related count, last completed run timestamp, completed run count (7d)               |
| 17  | **React SPA shell**          | Vite React + TS frontend served by FastAPI at `/`, auth login flow, protected dashboard stats                           |
| 18  | **Active applications page** | Admin-only applications view with navbar and active-stage filtering in React UI                                         |
| 19  | **Domain + HTTPS proxy**     | Nginx reverse proxy on `jemanhardt.dev` with Let's Encrypt and CI-deployed config                                       |

## Key Notes

- DB is decoupled via Repository pattern — swapping PostgreSQL for another DB is a single `DATABASE_URL` change
- LLM is decoupled via `LLMClassifier` Protocol — set `LLM_PROVIDER=groq` for prod, `ollama` for local
- `quick_filter` stays: reduces LLM calls by pre-screening obvious non-job emails (keyword + domain check)
- System crontab fires worker at: `0 7,12,17,20 * * 1-5` (7am, 12pm, 5pm, 8pm weekdays)
- PostgreSQL credentials → AWS Secrets Manager; injected at container startup via IAM Instance Profile
- Set EBS `DeleteOnTermination=false` before launching EC2 to protect PostgreSQL data
- **`POST /jobs/email-limit` scope:** The override lives in the API container’s memory. It applies to worker runs started from that same process (e.g. `POST /jobs/email-check` via FastAPI `BackgroundTasks`). Crontab-started `python -m app.worker` in a **separate** container/process does **not** see the override; use `MAX_EMAILS_PER_RUN` / `EMAIL_LIMIT` in env for scheduled runs.

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

- Implement Groq adapter for `llama-3.3-70b-versatile`
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

- Standardize log lines to include `**worker_run_id`\*\* (and job status transitions) where useful
- Replace ad-hoc `print` with `**logging**` (module logger), levels appropriate for prod vs dev
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
**This phase delivers:** A **repeatable pytest setup** for unit + integration tests, **shared fixtures** where they reduce duplication, **meaningful coverage** of repositories/services/API paths not yet exercised, a documented `**coverage run` / `coverage report`** workflow targeting **≥70%** line coverage, and a **single command\*\* (documented in `README` or `PLAN`) that CI can call later in Phase 9.

### Chunk 0 (phase bootstrap)

- Create branch from `main`: `phase7-test-coverage` (hyphenated; keeps branch names grep-friendly)
- Keep all Phase 7 work on this branch until the phase is agreed complete

### Chunk 1 (pytest layout & markers)

- Confirm or add `**pytest.ini`** / `**pyproject.toml\*\*` `[tool.pytest.ini_options]`—`testpaths`, asyncio mode if needed, optional markers (`integration`, `slow`)
- Normalize `**tests/unit/**` vs `**tests/integration/**` naming; ensure `tests/conftest.py` (root) can hold shared fixtures without circular imports

### Chunk 2 (unit coverage — gaps)

- Identify modules below reasonable coverage (repositories, `app/services`, `app/api/v1` routes not covered by phase-specific files)
- Add focused unit tests with mocks; avoid testing implementation trivia — assert behavior and error paths

### Chunk 3 (integration tests)

- Add `**tests/integration/**` tests that spin up the FastAPI app (or key routers) with a **test database** (SQLite in-memory + dependency overrides, or transactional PostgreSQL pattern — pick one and document)
- Cover at least one happy-path flow that crosses API → DB (e.g. health + one CRUD-style route if fixtures allow)

### Chunk 4 (coverage gate & docs)

- Add `**coverage`** / `**pytest-cov**`to dev dependencies if not present; document`**pytest --cov=app --cov-fail-under=70\*\*`(or equivalent) in`README`or a short comment in`pyproject.toml`
- If **70%** is not yet reachable in one pass, document current % and ratchet plan — prefer failing CI later (Phase 9) over silently lowering the bar

### Chunk 5 (fixtures & hygiene)

- Extract repeated test setup (DB session, app client, seed helpers) into `**conftest.py`\*\* fixtures
- Address flaky patterns (time-dependent tests, unordered collections) early

### Chunk 6 (verification)

- Run full `**pytest**` + `**coverage report**` locally; fix lint on touched files
- Incremental commits per completed chunk

## Phase 11 Breakdown (manageable chunks)

**Phase:** 11 — Runtime worker email limit override — **✅ complete**  
**Already done:** Phases 1–10 complete, with worker using env defaults (`MAX_EMAILS_PER_RUN` and legacy `EMAIL_LIMIT`)  
**This phase delivered:** A non-`PATCH` API endpoint to set a process-local in-memory override (`1..1000`) for worker email fetch count. The override applies to subsequent worker runs **in the same API process** (e.g. `POST /jobs/email-check`); separate cron/worker containers use env limits only (see Key Notes).

### Chunk 1 (runtime override state)

- Add a small worker runtime module with set/get/clear/effective helpers
- Keep override in memory only (no DB migration, no env writeback)

### Chunk 2 (API endpoint)

- Add `POST /api/v1/jobs/email-limit`
- Validate body range `1..1000`
- Return applied value and source metadata

### Chunk 3 (worker integration)

- Apply override in `app/worker.py` after existing default resolution logic
- Preserve fallback behavior when no override is set

### Chunk 4 (tests)

- API tests for happy path + out-of-range validation
- Worker test proving runtime override is used for `fetch_emails()`

### Chunk 5 (verification)

- Run unit tests for touched phase5/phase6 test modules
- Fix any lint issues introduced by this change

## Phase 12 Breakdown (manageable chunks)

**Phase:** 12 — UID stale tracking reset  
**Already done:** Phases 1–11 on `main`, including UID-based incremental fetch in worker runs  
**This phase delivers:** Cursor reset to mailbox head when the tracked UID points to an email older than 30 days, so stale backlogs are skipped.

### Chunk 1 (staleness decision)

- Resolve staleness from IMAP email date at tracked UID (not DB record age)
- If tracked UID date is older than 30 days, reset to latest mailbox UID
- If tracked UID cannot be resolved on server, reset to latest mailbox UID when available

### Chunk 2 (fetch behavior alignment)

- Ensure `fetch_recent_emails()` returns newest messages first
- Keep `since_uid` incremental semantics unchanged for non-stale cursors

### Chunk 3 (tests)

- Add unit tests for recent UID (no reset), stale UID (reset), and missing UID (reset)
- Keep existing worker exit-code tests intact

### Chunk 4 (verification)

- Run targeted unit tests for worker module changes
- Fix lint issues introduced by this phase

## Phase 13 Breakdown (manageable chunks)

**Phase:** 13 — JWT auth with role-based access control  
**Already done:** Phases 1–12 on `main`; all `/api/v1/*` routes are currently unauthenticated  
**This phase delivers:** A `users` table, password hashing, JWT issuance, an auth dependency applied to all routes, RBAC distinguishing read-only (demo) from full-access (admin) users, and a seeded demo user for public viewing.

### Chunk 0 (phase bootstrap)

- Branch from `main`: `phase13-jwt-auth`
- Add `passlib[bcrypt]>=1.7.4` and `python-jose[cryptography]>=3.3.0` to `requirements.txt`

### Chunk 1 (user model + migration)

- Add `User` model: `id`, `username` (unique), `password_hash`, `role` (`admin` or `viewer`), `created_at`
- Add `UserRepository` with `find_by_username`, `create`, `verify_password`
- Add `migrations/003_users.sql` for PostgreSQL; SQLAlchemy `create_all` covers SQLite tests
- Seed script (`scripts/seed_users.py`) that creates admin + demo viewer; run once on EC2 with credentials from `~/deploy/.env`

### Chunk 2 (auth core)

- Add `app/auth/` module: `hashing.py` (bcrypt wrappers), `jwt_handler.py` (encode/decode with `JWT_SECRET`, `JWT_ALGORITHM=HS256`, `JWT_EXPIRY_MINUTES=1440`), `dependencies.py` (`get_current_user`, `require_admin`)
- Add `JWT_SECRET` and `JWT_EXPIRY_MINUTES` to `app/config.py` Settings; document in README

### Chunk 3 (auth endpoints)

- Add `app/api/v1/auth.py`: `POST /auth/login` (username + password → access token), `GET /auth/me` (current user info)
- Register router under `/api/v1/auth` in `app/api/v1/router.py`
- Login returns 401 on bad credentials; never reveals whether the username exists

### Chunk 4 (apply auth to existing routes)

- Add `Depends(get_current_user)` to every route except `/health` and `/auth/login`
- Add `Depends(require_admin)` to `PUT /applications/{id}`, `POST /jobs/email-check`, `POST /jobs/email-limit`
- Demo user can `GET` everything; write attempts return 403

### Chunk 5 (tests)

- Unit: hashing roundtrip, JWT encode/decode, expiry rejection, malformed token rejection
- Integration: login happy/sad paths, protected route without token returns 401, demo user `PUT` returns 403, admin `PUT` succeeds
- Update existing API tests to attach a token via fixture

### Chunk 6 (verification)

- Run `pytest` (gate stays ≥70%)
- Run `ruff check .`
- Document seed script and required env vars in README

## Phase 14 Breakdown (manageable chunks)

**Phase:** 14 — Domain, Nginx reverse proxy, HTTPS  
**Already done:** Phases 1–13; API and auth running over plain HTTP at `3.93.168.186:8000`  
**This phase delivers:** A registered domain pointed at EC2, Nginx serving as reverse proxy in front of the API, and Let's Encrypt HTTPS via Certbot — the prerequisite for a public auth-protected demo.

### Chunk 0 (phase bootstrap)

- Branch from `main`: `phase14-nginx-https`
- Buy a domain (Cloudflare Registrar or Namecheap, ~$12/year)
- Create A record pointing the apex (or `tracker.<your-domain>`) at `3.93.168.186`

### Chunk 1 (Nginx container in compose)

- Add `nginx` service to `docker-compose.prod.yml`: image `nginx:alpine`, ports `80:80` and `443:443`, mounts `./nginx/conf.d` and `./nginx/certs`
- Write `nginx/conf.d/tracker.conf`: server block listening on 80, proxies `/api/` and `/docs` to `api:8000`, serves `/usr/share/nginx/html` for everything else (frontend goes here in Phase 15)
- Remove the `8000:8000` port mapping from the `api` service — only Nginx is internet-facing now

### Chunk 2 (Certbot + HTTPS)

- Add `certbot` service or use `certbot/certbot` one-shot to issue cert for the domain
- Add 443 server block to Nginx config with cert paths under `/etc/letsencrypt/live/<domain>/`
- Add HTTP→HTTPS redirect in the port 80 server block
- Add a renewal cron entry on EC2: `0 3 * * * docker compose run --rm certbot renew && docker compose exec nginx nginx -s reload`

### Chunk 3 (CI/CD adjustments)

- Update `.github/workflows/ci.yml` deploy job to copy `nginx/` directory and updated `docker-compose.prod.yml` to EC2
- Verify deploy still succeeds end-to-end with the new topology

### Chunk 4 (verification)

- `curl https://<domain>/api/v1/health` returns 200
- `curl http://<domain>/api/v1/health` returns 301 to HTTPS
- Update README live API link from `http://3.93.168.186:8000/docs` to `https://<domain>/docs`

## Phase 15 Breakdown (manageable chunks)

**Phase:** 15 — Vanilla HTML/CSS/Tailwind/JS frontend  
**Already done:** Phases 1–14; auth-protected API behind HTTPS at `https://<domain>/api/v1`  
**This phase delivers:** A static SPA-style dashboard at `https://<domain>/` showing applications, emails, and worker job status, with login flow and demo account banner.

### Chunk 0 (phase bootstrap)

- Branch from `main`: `phase15-frontend-dashboard`
- Create `frontend/` directory at repo root with `index.html`, `login.html`, `app.js`, `auth.js`, `api.js`, `styles.css`
- Use Tailwind via CDN to keep the build trivial — no Node toolchain in this phase

### Chunk 1 (auth flow)

- `login.html`: username + password form, posts to `/api/v1/auth/login`, stores JWT in `localStorage`
- `auth.js`: `getToken()`, `setToken()`, `clearToken()`, `requireAuth()` (redirects to login if no token), `isAdmin()` (decodes JWT role claim for UI only; backend still enforces roles)
- `api.js`: `apiFetch(path, opts)` wrapper that attaches `Authorization: Bearer <token>` and redirects to login on 401

### Chunk 2 (dashboard page)

- `index.html` with three sections: Applications, Emails, Jobs
- Applications section: table with stage filter, columns for company / position / stage / last_updated; admin sees an "Edit" button per row, demo does not
- Emails section: paginated table backed by `GET /emails`, with a "Needs Review" toggle that switches to `GET /emails/review`
- Jobs section: "Trigger Email Check" button (admin-only, calls `POST /jobs/email-check`), polls `GET /jobs/{id}` every 3 seconds while status is `queued` or `running`

### Chunk 3 (demo UX)

- Show a banner on every page when logged in as demo: "You are viewing this dashboard as a read-only demo user. Sign in as admin for full access."
- Hide all admin-only buttons when `isAdmin()` is false; backend still enforces 403 as defense in depth
- Add demo credentials to the login page so visitors can copy-paste

### Chunk 4 (Nginx serves it)

- Build step is just `cp -r frontend/* nginx/html/` — no bundler
- Update `nginx/conf.d/tracker.conf` root to point at `/usr/share/nginx/html`
- Verify the GitHub Actions deploy ships the `frontend/` directory to EC2

### Chunk 5 (polish & verification)

- Loading states on every fetch, friendly error messages on 401/403/5xx
- Mobile-responsive Tailwind classes on all tables
- Update README with screenshots and the live URL
- Run `ruff check .` and `pytest` — no backend changes, but verify nothing broke

## Phase 16 Breakdown (manageable chunks)

**Phase:** 16 — Public operational stats endpoint  
**Already done:** Phases 1–15 with JWT/RBAC and production worker run tracking  
**This phase delivers:** A public `GET /api/v1/stats` endpoint for recruiter/demo visibility into processing scale and worker freshness.

### Chunk 1 (stats route)

- Add `app/api/v1/stats.py` with no auth dependency
- Return:
  - `total_emails_processed` (count of `emails`)
  - `job_related_emails` (count of `email_analyses.is_application=true`)
  - `worker_last_ran_at` (latest completed `worker_runs.finished_at`)
  - `worker_run_count_7d` (completed runs finished in last 7 days)

### Chunk 2 (router wiring)

- Register `/api/v1/stats` in `app/api/v1/router.py`

### Chunk 3 (tests + verification)

- Add endpoint tests for empty DB and populated aggregates
- Verify endpoint remains public (no token required)
- Run targeted tests and lint on touched files

## Phase 17 Breakdown (manageable chunks)

**Phase:** 17 — React SPA shell served by FastAPI  
**Already done:** Phases 1–16, including JWT auth (`/api/v1/auth/login`) and public stats aggregation  
**This phase delivers:** Single-domain UX where FastAPI serves API/docs and a built React SPA from one Docker image.

### Chunk 1 (routing decisions + backend wiring)

- Keep existing API namespace under `/api/v1/*`
- Keep docs public at `/docs` and `/openapi.json`
- Expose stats at public root (`/stats`)
- Mount built frontend static assets at `/` last, with SPA fallback to `index.html`

### Chunk 2 (frontend scaffold)

- Create `frontend/` with Vite + React + TypeScript
- Add Tailwind CSS + shadcn/ui baseline helpers/components
- Add React Router + TanStack Query setup

### Chunk 3 (auth + dashboard MVP)

- Add `/login` page with email/password form posting to `/api/v1/auth/login`
- Store JWT in localStorage and inject as Bearer for API calls
- Add protected `/` route showing stats from `/stats`
- Add 401 interceptor to clear token and redirect to `/login`

### Chunk 4 (container build + env docs)

- Update Dockerfile to build frontend and copy `frontend/dist` into runtime image
- Keep single process/container deployment model
- Update `.env.example` with any frontend-related env knobs

### Chunk 5 (verification)

- Run backend tests for route changes
- Run frontend build validation
- Run lint checks on touched files

## Phase 18 Breakdown (manageable chunks)

**Phase:** 18 — Admin applications page + navigation shell  
**Already done:** Phase 17 SPA shell with login and stats dashboard  
**This phase delivers:** A navbar and an admin-only `/applications` page listing active/open applications.

### Chunk 1 (RBAC tightening for applications list)

- Change `GET /api/v1/applications` to require `AdminUser`
- Update auth tests so viewer receives `403` and admin still has list access

### Chunk 2 (frontend navigation shell)

- Add shared navbar with links for Dashboard and Applications
- Keep Applications link visible only for admin role
- Reuse navbar across protected pages

### Chunk 3 (applications page)

- Add protected `/applications` route
- Add admin-only route guard (`AdminRoute`)
- Query `/api/v1/applications` via auth API client
- Filter to active stages: `applied`, `interview`, `assessment`, `offer`
- Render table with loading/empty/error states

### Chunk 4 (verification)

- Run frontend build
- Run targeted auth/API tests
- Run lint on touched files

## Phase 19 Breakdown (manageable chunks)

**Phase:** 19 — Domain + HTTPS reverse proxy  
**Already done:** SPA + API unified in one container image, routed under FastAPI  
**This phase delivers:** `jemanhardt.dev` and `www.jemanhardt.dev` served over HTTPS via Nginx in front of the API container.

### Chunk 1 (compose topology)

- Add `nginx` and `certbot` services to `docker-compose.prod.yml`
- Remove host exposure of API port `8000`; route traffic through Nginx only
- Mount ACME/certificate volumes for cert issuance and renewal

### Chunk 2 (nginx config assets)

- Add `nginx/conf.d/tracker.http.conf` for initial HTTP and ACME challenge routing
- Add `nginx/conf.d/tracker.https.conf.example` for post-certificate TLS + redirect setup
- Configure proxy to preserve host/proto/IP headers

### Chunk 3 (CI deploy sync)

- Ensure deploy job creates nginx/certbot directories on EC2
- Copy `nginx/**` from repo to `~/deploy` during deploy
- Keep deploy using one compose file and one container stack

### Chunk 4 (verification + ops handoff)

- Run full lint + tests before commit
- Provide one-time certbot issuance command for EC2
- Document config swap step from HTTP config to HTTPS config

## Phase 20 Breakdown (manageable chunks)

**Phase:** 20 — Applications page controls  
**Already done:** Phase 18 admin applications list with active-stage focus  
**This phase delivers:** Backend stage filtering with `All` option and a page-level manual job trigger button.

### Chunk 1 (stage filter)

- Add stage dropdown on frontend applications page with options: `all`, `applied`, `rejected`, `interview`, `assessment`
- Drive list requests with `GET /api/v1/applications?stage=<value>` and map `all` to unfiltered `GET /api/v1/applications`
- Treat API `404` ("no applications found") as an empty state in UI

### Chunk 2 (manual job trigger)

- Add page-level `Trigger Job` button wired to `POST /api/v1/jobs/email-check`
- Show loading state while request is pending
- Show success message with returned `job_id` and status, or an error message on failure

### Chunk 3 (verification)

- Run frontend build for type safety and bundling checks
- Fix any lints introduced by touched frontend files

## Phase 21 Breakdown (manageable chunks)

**Phase:** 21 — Frontend visual polish + dashboard messaging  
**Already done:** Phase 20 applications controls and backend stage filtering  
**This phase delivers:** A more professional UI theme across login/dashboard/applications and a dashboard section explaining app purpose + privacy-limited insight.

### Chunk 1 (visual system refresh)

- Apply a consistent professional palette (slate base with indigo/teal accents)
- Improve card/navbar surface styling (radius, subtle ring/shadow, gradients)
- Keep UX behavior unchanged

### Chunk 2 (dashboard landing content)

- Treat dashboard as landing experience post-login
- Add concise "what this app does" content
- Add privacy-focused "why insight is limited" explanation for showcase context

### Chunk 3 (page polish)

- Refresh login page with stronger project presentation and privacy messaging
- Refresh applications page controls/table styling while preserving existing endpoint behavior

### Chunk 4 (verification)

- Run frontend build and lint checks for touched files

## Phase 26 Breakdown (manageable chunks)

**Phase:** 26 — Portfolio dashboard layout build  
**Already done:** Prior shell/dashboard styling passes with light-gray + white card direction  
**This phase delivers:** New componentized dashboard architecture (AppShell, Sidebar, TopBar, reusable Card, KPI + chart/table cards) with mocked data and API wiring deferred.

### Chunk 1 (shell chrome)

- Build `AppShell`, `Sidebar`, and `TopBar` using flex sibling layout (`min-w-0` on content side)
- Keep auth interaction in top bar (`Sign in` / `Sign out`) based on token presence

### Chunk 2 (shared card foundation)

- Build reusable `Card` component with optional title/action header
- Apply consistent rounded/border/shadow/spacing tokens

### Chunk 3 (dashboard composition)

- Build `Dashboard` page with header actions, KPI row, and 2/3 + 1/3 card grid
- Implement card modules: top companies list, recent applications table, applications-over-time line chart, status donut chart
- Use mocked constants in each card for layout-first delivery

### Chunk 4 (verification)

- Install `recharts` and `lucide-react`
- Run frontend build and lint checks for touched files

## Phase 27 Breakdown (manageable chunks)

**Phase:** 27 — Modular API-backed applications page  
**Already done:** Phase 26 modular dashboard shell and card architecture  
**This phase delivers:** Applications view rebuilt into the same componentized structure as dashboard, using live API data and preserving admin-only behavior.

### Chunk 1 (component extraction)

- Split applications UI into reusable cards (filters, summary, table)
- Keep shared card styling and spacing consistent with dashboard

### Chunk 2 (page composition)

- Create `Applications` page with dashboard-style layout and header actions
- Preserve stage filtering, loading, empty, and error states

### Chunk 3 (API behavior)

- Keep data sourced from `GET /applications` with optional stage query
- Keep manual trigger action via `POST /jobs/email-check`
- Keep 404 empty-list behavior for filtered queries

### Chunk 4 (routing and verification)

- Route `/applications` to new modular `Applications` page
- Run frontend build and lint checks for touched files

## Phase 28 Breakdown (manageable chunks)

**Phase:** 28 — Public/demo vs authenticated/live dashboard data  
**Already done:** Phase 26 modular dashboard layout and Phase 27 modular API-backed applications page  
**This phase delivers:** Public users can view dashboard immediately with polished preset data, while signed-in users automatically receive live API-backed dashboard data when permitted.

### Chunk 1 (data mode switching)

- Detect auth state in dashboard
- Use demo data when unauthenticated
- Attempt live data when authenticated

### Chunk 2 (live data shaping)

- Build dashboard metrics/charts/tables from API application records
- Keep visual design unchanged while swapping data source

### Chunk 3 (fallback behavior)

- If live fetch fails (for example RBAC restrictions), show a small notice
- Continue rendering stable demo data to avoid empty/broken dashboard UX

### Chunk 4 (verification)

- Run frontend build and lint checks for touched files

## Phase 29 Breakdown (manageable chunks)

**Phase:** 29 — Dedicated dashboard aggregate endpoints  
**Already done:** Phase 28 dashboard auth-aware live/demo switching with frontend-derived live metrics  
**This phase delivers:** Admin-only dashboard API endpoints for metrics, trend data, status breakdown, recent rows, and top companies; frontend live mode consumes these endpoints directly.

### Chunk 1 (backend endpoint surface)

- Add admin-only `/api/v1/dashboard/*` endpoints:
  - `metrics`
  - `applications-over-time`
  - `status-breakdown`
  - `recent-applications`
  - `top-companies`
- Keep trend window default at 30 days

### Chunk 2 (frontend live wiring)

- Replace live dashboard data derivation from `/applications` with dedicated dashboard endpoints
- Keep unauthenticated users on stable demo data fallback

### Chunk 3 (tests)

- Add unit API tests for dashboard endpoints and key aggregations
- Add RBAC coverage for admin-only dashboard endpoints

### Chunk 4 (verification)

- Run targeted backend tests for API/auth modules
- Run frontend build and lint checks for touched files

## Phase 30 Breakdown (manageable chunks)

**Phase:** 30 — Cloudflare origin certs only  
**Already done:** Nginx TLS deployment path with Certbot-based assets  
**This phase delivers:** Production TLS served only from Cloudflare origin certificates (`origin.pem`/`origin.key`) with Certbot removed from compose and deploy setup.

### Chunk 1 (compose + nginx)

- Remove `certbot` service and Let's Encrypt mounts from `docker-compose.prod.yml`
- Mount `./nginx/certs` into nginx container at `/etc/nginx/certs`
- Update nginx TLS config paths to Cloudflare origin cert files

### Chunk 2 (deploy workflow)

- Update CI deploy setup to create `~/deploy/nginx/certs` (no certbot directories)
- Keep existing nginx config sync and compose restart flow

### Chunk 3 (verification)

- Validate nginx config in container (`nginx -t`)
- Reload/recreate nginx with updated cert mount and config

## Phase 33 Breakdown (manageable chunks) — CONFIRMED

**Phase:** 33 — Link correspondence emails to existing applications
**Branch:** `cursor/phase33-email-correspondence-linking-8364` (from `main`)
**Already done:** Emails ingest with `EmailAnalysis.application_id` (nullable FK), `POST /emails/{id}/promote` (creates/finds an application by company+position and links), `GET /applications/{id}/emails` timeline on the application detail page, client-side `classifyEmail()` tagging (interview invite / acknowledgement / offer / rejection / not relevant / needs review).
**This phase delivers:** From the Emails tab, attach a correspondence email (thank-you note, recruiter reply, automated rejection, etc.) to an **existing** application without creating a new one or mutating its stage — plus a per-application view (Application Detail page only) that makes thin correspondence (e.g. "just an ack and an auto-rejection, nothing else") obvious at a glance. **Explicitly excludes** any changes to the Needs Review queue/flow (slated for a separate revamp) and any dashboard changes.

### Decisions (confirmed)

- Linking is a distinct action from **Promote**: Promote creates/attaches by company+position and forces `is_application=True`; **Link** just sets `application_id` on the email's analysis and leaves `is_application`/`detected_*`/stage untouched.
- Linking does **not** change the application's `stage` automatically (**Option A**) — stage stays a fully manual/pipeline concern, edited only via the existing Application Detail stage dropdown, never nudged or auto-applied by linking an email.
- Only `admin` role can link/unlink (matches existing `promote`/`dismiss` RBAC).
- Existing application search reuses `GET /applications?q=` (no new search endpoint needed).
- Moving an email to a different application is unlink-then-link (no direct "move" endpoint in this phase).
- Correspondence visibility is scoped to the **Application Detail page only** — classification tags + a small counts summary on that page's linked-emails timeline. No dashboard changes, no Applications-list badge.

### Chunk 1 (phase bootstrap)

- Branch from `main`: `cursor/phase33-email-correspondence-linking-8364`
- Keep all Phase 33 work on this branch until the phase is agreed complete

### Chunk 2 (link/unlink API)

- Add `POST /api/v1/emails/{email_id}/link` (admin-only), body `{application_id: int}`
  - 404 if email or application not found
  - If the email has no `EmailAnalysis` yet, create a minimal one (`is_application=False`, `confidence="manual"`, `needs_review=False`) then set `application_id`
  - If an analysis exists, only set `application_id` — leave `is_application`/`detected_*`/`needs_review` as-is
  - Idempotent: linking to the same application twice is a no-op success
- Add `POST /api/v1/emails/{email_id}/unlink` (admin-only)
  - 404 if email not found or not currently linked
  - Clears `application_id` only; preserves all other analysis fields
- Extend `AnalysisRepository` with `unlink_from_application` (mirrors existing `link_to_application`) and a shared helper for "ensure a manual analysis row exists" reused by both `promote` and `link`

### Chunk 3 (backend tests)

- `tests/unit/test_phase33_email_linking.py`:
  - link with existing analysis, link with no analysis (creates one), link 404s (missing email/application)
  - unlink success, unlink 404 (not linked / missing email)
  - idempotent re-link to same application
  - viewer role gets 403 on both endpoints

### Chunk 4 (frontend data layer)

- `types/api.ts`: `LinkEmailRequest { application_id: number }`
- `hooks/useEmails.ts`: `useLinkEmail()`, `useUnlinkEmail()` — invalidate emails, applications, and dashboard query keys on success (mirrors `usePromoteEmail`)

### Chunk 5 (Link drawer — Emails tab)

- New `LinkDrawer` component (sibling to `PromoteDrawer`): debounced search input against `GET /applications?q=`, results list (company — position — stage badge), select-to-confirm, calls `POST /emails/{id}/link`
- `Emails.tsx` action cell: when unlinked, show both **Promote** and **Link** actions; when linked, keep the "Linked" link and add a small **Unlink** affordance

### Chunk 6 (application detail correspondence view)

- `ApplicationDetail.tsx` "Linked emails" card: render the existing `ClassificationTag` per timeline item (reuse from Emails page) and add a compact summary strip above the list (e.g. "3 emails — 1 acknowledgement, 1 rejection, 1 interview invite") computed client-side via `classifyEmail()`
- Add an **Unlink** action per timeline row for correcting mistaken links from the application side too

### Chunk 7 (verification)

- Backend: `pytest` (coverage gate) + `ruff check .` on touched files
- Frontend: `npm run build` + lint on touched files
- Incremental commits per completed chunk

## Phase 25 Breakdown (manageable chunks)

**Phase:** 25 — Visual spacing + surface layering  
**Already done:** Phase 23 admin shell and dashboard composition work  
**This phase delivers:** A cleaner look with light-gray canvas, softer card geometry, and stronger white-space separation between dashboard/application sections.

### Chunk 1 (shell spacing)

- Increase page breathing room with a muted canvas behind content
- Keep auth/nav behavior unchanged

### Chunk 2 (dashboard layering)

- Group major dashboard blocks in subtle tinted panels
- Keep white cards inside panels for clean contrast
- Preserve all current data and placeholders

### Chunk 3 (applications layering)

- Apply the same panel + card separation to controls and table
- Keep filter/trigger/query logic unchanged

### Chunk 4 (verification)

- Run frontend build and lint checks for touched files

## Phase 22 Breakdown (manageable chunks)

**Phase:** 22 — Visual depth pass  
**Already done:** Phase 21 baseline UI polish and privacy messaging  
**This phase delivers:** Less text-heavy UI with icon-backed metric tiles, stronger visual states, and richer applications table styling.

### Chunk 1 (dashboard visual depth)

- Add icon-backed stat tiles with clearer hierarchy and subtle hover transitions
- Upgrade dashboard loading/error states into styled callout cards

### Chunk 2 (applications visual depth)

- Add stage summary chips and stage-specific badge colors
- Add stronger table framing, hover feedback, and improved row hierarchy
- Keep API behaviors and filtering logic unchanged

### Chunk 3 (micro-interactions)

- Add subtle transition polish to navbar and action controls
- Preserve readability and contrast

### Chunk 4 (verification)

- Run frontend build and lint checks for touched files

## Phase 23 Breakdown (manageable chunks)

**Phase:** 23 — Admin-style frontend shell  
**Already done:** Phase 22 visual depth pass and component polish  
**This phase delivers:** A cleaner admin dashboard structure inspired by modern templates: left sidebar, top context bar, and richer dashboard composition with placeholder chart spacing.

### Chunk 1 (layout shell)

- Add protected app shell with left sidebar nav (`Dashboard`, `Applications`, `API Docs`)
- Add top bar with section title, role badge, and sign-out action
- Keep login route outside shell

### Chunk 2 (dashboard composition)

- Expand dashboard into multi-block layout with stats, placeholder activity visualization, highlights, and table preview
- Keep existing live stats API data intact

### Chunk 3 (routing integration)

- Wrap protected routes with shell layout and keep existing auth/admin guards
- Preserve current endpoint behavior on all pages

### Chunk 4 (verification)

- Run frontend build and lint checks for touched files

## Phase 26 Breakdown (manageable chunks)

**Phase:** 26 — One-time backdated worker run  
**Already done:** Normal incremental worker trigger (`POST /jobs/email-check`) with UID cursoring, dedupe guards, and admin-only access controls  
**This phase delivers:** A one-time admin-triggered backfill run that pulls older missed emails by date window without advancing the normal incremental UID cursor.

### Chunk 1 (API trigger)

- Add `POST /jobs/email-backfill` (admin-only)
- Accept `from_date` (required), `to_date` (optional, defaults now), and optional `max_emails` cap
- Validate `from_date <= to_date`

### Chunk 2 (worker backfill mode)

- Add optional backfill args to worker execution path
- Reuse existing parse/classify/persist pipeline
- Keep duplicate protections unchanged
- Prevent backfill runs from mutating `last_processed_uid`

### Chunk 3 (IMAP date-window fetch)

- Add date-range IMAP fetch helper for backfill mode
- Keep normal incremental UID fetch path untouched

### Chunk 4 (verification)

- Add/adjust unit + integration tests for backfill trigger and worker mode behavior
- Run focused pytest suite for touched paths

## Phase 27 Breakdown (manageable chunks)

**Phase:** 27 — Manual email promotion to applications  
**Already done:** Automatic application creation now happens during worker ingestion and backfill runs  
**This phase delivers:** An admin endpoint to promote already-ingested email rows into the applications table when historical rows were missed before the new ingest logic.

### Chunk 1 (promotion endpoint)

- Add `POST /emails/{email_id}/promote` (admin-only)
- Resolve company/position/stage from request overrides, detected analysis values, then safe fallbacks

### Chunk 2 (analysis + linking behavior)

- If analysis exists, force/link it to an application row
- If analysis is missing, create a minimal manual analysis row and link it
- Keep dedupe behavior by resolving through existing company+position application rows

### Chunk 3 (verification)

- Add unit/integration coverage for promote success, missing-analysis promotion, and idempotent re-promote
- Run targeted and full pytest validation

## Phase 32 Breakdown (manageable chunks)

**Phase:** 32 — API rate limiting  
**Branch:** `phase32-rate-limiting` (from `main`)  
**Already done:** Nothing — no rate limiting exists today  
**This phase delivers:** Configurable tiered rate limits on API endpoints only (`/api/v1/*` and `/stats`). No frontend, nginx, or other feature changes.

### Scope

| In scope | Out of scope |
| -------- | ------------ |
| `/api/v1/*` endpoints | SPA static assets at `/` |
| `GET /stats` | Nginx-level `limit_req` |
| Env-configurable limits | Redis / multi-replica shared store |
| 429 responses + unit tests | Auth/RBAC changes |

### Endpoint inventory

| Access | Endpoints |
| ------ | --------- |
| **Public (no JWT)** | `GET /api/v1/health`, `POST /api/v1/auth/login`, `GET /stats` |
| **Any authenticated user** | `GET /api/v1/auth/me`, `GET /api/v1/emails/review` |
| **Admin only** | applications, dashboard, emails (except review), jobs |

### Rate limit tiers (proposed defaults)

| Tier | Applies to | Default | Key |
| ---- | ---------- | ------- | --- |
| **Login** | `POST /api/v1/auth/login` | 10/min | Client IP |
| **Public** | `GET /api/v1/health`, `GET /stats` | 60/min | Client IP |
| **Global** | All API routes (baseline) | 120/min | Username from JWT, else IP |
| **Expensive** | High-cost reads + job triggers | 10/min | Username from JWT, else IP |

**Expensive endpoints** (stack on top of global):

- `POST /api/v1/jobs/email-check`
- `POST /api/v1/jobs/email-backfill`
- `GET /api/v1/emails` (up to 1000 rows)
- `GET /api/v1/emails/review` (up to 1000 rows)
- `GET /api/v1/applications` (up to 200 rows)

All other authenticated endpoints inherit **global only**.

IP resolution: `X-Forwarded-For` (first hop) → `X-Real-IP` → direct client (Nginx already sets the proxy headers).

### Chunk 1 (dependency + config)

- Add `slowapi>=0.1.9` to `requirements.txt`
- Add settings to `app/config.py`:
  - `RATE_LIMIT_ENABLED` (default `true`)
  - `RATE_LIMIT_LOGIN` (default `10/minute`)
  - `RATE_LIMIT_PUBLIC` (default `60/minute`)
  - `RATE_LIMIT_GLOBAL` (default `120/minute`)
  - `RATE_LIMIT_EXPENSIVE` (default `10/minute`)

### Chunk 2 (limiter module + app wiring)

- Create `app/middleware/rate_limit.py`:
  - `get_client_ip(request)` — proxy-aware IP extraction
  - `get_rate_limit_key(request)` — `user:{username}` when Bearer JWT is valid, else `ip:{ip}`
  - Module-level `limiter` + `configure_rate_limiting(app)` (registers `SlowAPIMiddleware`, 429 handler)
- Call `configure_rate_limiting(app)` in `app/main.py` before router mount

### Chunk 3 (route decorators)

Add `@limiter.limit(...)` + `request: Request` to targeted handlers only:

| File | Routes | Limit |
| ---- | ------ | ----- |
| `auth.py` | `POST /login` | Login (IP, `override_defaults=True`) |
| `health.py` | `GET /health` | Public (IP, `override_defaults=True`) |
| `stats.py` | `GET /stats` | Public (IP, `override_defaults=True`) |
| `jobs.py` | `POST /email-check`, `POST /email-backfill` | Expensive |
| `emails.py` | `GET /emails`, `GET /emails/review` | Expensive |
| `applications.py` | `GET /applications` | Expensive |

Global baseline applies everywhere else via limiter `default_limits` — no per-route decorator needed on dashboard, single-resource GETs, PUTs, etc.

### Chunk 4 (tests)

- `tests/unit/test_rate_limit.py`:
  - IP/key extraction helpers
  - 429 when limit exceeded (isolated mini-app)
  - `configure_rate_limiting` skips middleware when disabled
- `tests/conftest.py`: set `limiter.enabled = False` so existing tests never flake

### Chunk 5 (verification)

- `python -m pytest` — full suite must pass (≥70% coverage gate)
- Manual smoke: hit `/api/v1/health` repeatedly, confirm 429 after threshold

### Deployment notes

- Single EC2 / single Uvicorn process → in-memory store is sufficient
- Set `RATE_LIMIT_ENABLED=false` locally if needed during heavy dev
- If API is ever scaled to multiple replicas, revisit with Redis-backed storage

### Files touched (expected)

| File | Change |
| ---- | ------ |
| `requirements.txt` | Add `slowapi` |
| `app/config.py` | Rate limit settings |
| `app/middleware/rate_limit.py` | **New** — limiter setup |
| `app/main.py` | Wire middleware |
| `app/api/v1/auth.py` | Login limit |
| `app/api/v1/health.py` | Public limit |
| `app/api/v1/stats.py` | Public limit |
| `app/api/v1/jobs.py` | Expensive limits |
| `app/api/v1/emails.py` | Expensive limit on list |
| `app/api/v1/applications.py` | Expensive limit on list |
| `tests/conftest.py` | Disable limiter in tests |
| `tests/unit/test_rate_limit.py` | **New** — unit tests |
