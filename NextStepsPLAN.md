# Email Application Tracker — Restructure & Frontend Plan

## Goal
Transition from a personal project to a self-hostable product with a public **demo** and a private **prod** instance, both running the *same* container image differentiated only by configuration, fronted by a **landing** site — plus a brand-new frontend built from the design system, and versioned releases people can download.

## Operating model (the rules everything below follows)
- **`main` is the deployable trunk.** Demo and prod both track it. Work happens on short-lived feature branches → PR → merge.
- **One image, config-differentiated.** Demo and prod differ only in env vars and which database they use — never in code.
- **Downloadable versions = git tags / GitHub Releases (SemVer).** `main` is what you're working on and what's deployed; tags are the pinned versions self-hosters pull.
- Each phase ends in a shippable state. Don't start a phase until the prior one is green.

---

## Phase 0 — Monorepo restructure & baseline
**Goal:** one repo, clean layout, trunk + versioning ready.

- Reorganize into:
  ```
  /api          FastAPI app
  /worker       email ingestion/classification worker
  /web          new React/TS frontend (Phase 1)
  /landing      static marketing site (Phase 5)
  /seed         sample fixtures + seed/reset scripts (Phase 2)
  /infra        docker-compose.*.yml, nginx confs
  /docs         self-host notes (later)
  .github/workflows/   CI/CD
  .env.example  CHANGELOG.md  README.md  LICENSE(MIT)
  ```
- Move existing code into place; fix import paths and Dockerfile build contexts.
- Update compose to the new paths; confirm `docker compose up` still runs end to end locally.
- Set `main` as default and protect it (require PR). Add a `__version__` and a `CHANGELOG.md` with an `Unreleased` section.

**Done when:** the full stack runs from the new structure locally and a PR into `main` passes CI (even if CI is just lint + build for now).
**Note:** this is a pure move — do it in one branch, verify nothing breaks, merge. Low risk, unblocks everything.

---

## Phase 1 — New frontend (the big one)
**Goal:** replace the current frontend with the design-system build, wired to the existing API, shipped to your current deployment.

Build it in slices (one Cursor pass each):

1. **Scaffold `/web`** — Vite + React + TS, `react-router-dom`, TanStack Query, `lucide-react`, `recharts`. Generate `src/styles/tokens.css` from `design.json` → `cssVariables`. Load Inter + JetBrains Mono.
2. **UI primitives** (`src/components/ui`) from the components spec: Button, Input, Select, Card, MetricCard, FilterPill, Table, StatusBadge, ClassificationTag, Drawer + Backdrop, EmptyState, Toast. Implement hover/focus/disabled states against the token contract.
3. **App shell** — Sidebar, Topbar (health + avatar), router, auth guard (redirect to `/login` with no token), and a shared 3-state helper (loading skeleton / empty / error).
4. **Pages, in dependency order** — one React Query hook per endpoint:
   - Login → `POST /auth/login`, then `GET /auth/me`
   - Dashboard → the five `/dashboard/*` endpoints (recharts line + donut, BarList, recent table)
   - Applications list → `GET /applications` (filters, pagination); Application detail → `GET` + `PUT /applications/{id}`
   - Emails → `GET /emails`, per-row Promote action
   - Promote drawer (shared) → `POST /emails/{id}/promote`; on success invalidate `emails`, `emails/review`, `applications`, `dashboard`
   - Review queue → `GET /emails/review`, reuse the drawer
   - Jobs/Admin → 3 `POST /jobs/*` triggers, `GET /jobs/{id}` polling, `GET /stats`
5. **Swap in** the new `/web` build on the existing prod deployment; retire the old frontend.

**Done when:** every page renders against the real API with loading/empty/error states, and the old frontend is gone.
**Note:** fully independent of demo/subdomain work — shipping this first gives immediate value at the lowest risk.

---

## Phase 2 — DEMO_MODE + seed data
**Goal:** one codebase that runs as your private app or the public demo via a single flag.

- **Backend:** add `DEMO_MODE`. When true: auto-authenticate a demo user; the job endpoints (`email-check`, `backfill`, `email-limit`) return *simulated* job status instead of touching a real mailbox; no real SMTP. Reads/writes hit the demo DB normally.
- **Frontend:** read the flag (build-time or a small `/config` endpoint); show the demo banner and route straight in as the demo user.
- **Seed:** `/seed` fixtures (sample companies/emails/statuses — reuse the wireframe dummy data), a `seed` script, and a `reset` script (truncate → reload from snapshot).

**Done when:** `DEMO_MODE=true` boots a working seeded app with zero real-world side effects, and `reset` returns it to the seed state.

---

## Phase 3 — Single-image CI/CD, two stacks
**Goal:** push to `main` → one image built → demo and prod both update.

- GitHub Actions on push to `main`: build **one** image, tag `:latest` and `:<git-sha>`, push to the registry.
- Two compose files on the box, both referencing the same image:
  - `docker-compose.prod.yml` → `DEMO_MODE=false`, real DB volume, port 8000
  - `docker-compose.demo.yml` → `DEMO_MODE=true`, demo DB volume, port 8001
- Deploy step: SSH to the box → `docker compose -f <file> pull && up -d` for **both** stacks. Schedule a cron that runs the demo `reset` script (e.g. hourly).

**Done when:** a commit to `main` automatically lands on both demo and prod, with isolated data stores.

---

## Phase 4 — Subdomains, Nginx, TLS
**Goal:** `app.manhardt.dev` (private) and `demo.manhardt.dev` (public) live.

- Cloudflare DNS: add `app` → EC2, `demo` → EC2 (root reserved for Phase 5).
- Cloudflare **Origin Certificate as wildcard** `*.manhardt.dev`; install on the box.
- Nginx server blocks: `app.*` → `:8000`, `demo.*` → `:8001`, each `proxy_pass` with security headers.
- Move your personal instance off the root host onto `app.manhardt.dev`.

**Done when:** both subdomains serve over HTTPS to the correct stack; real data lives only behind `app.*`.

---

## Phase 5 — Landing on Cloudflare Pages
**Goal:** marketing site at the root, decoupled from the app box.

- Connect the repo to Cloudflare Pages; set the build root to `/landing`; auto-deploy on push.
- Point `manhardt.dev` and `www` at Pages.
- CTAs: **Live demo** → `https://demo.manhardt.dev`, **Sign in** → `https://app.manhardt.dev`, plus the GitHub link.

**Done when:** the root loads the landing from Pages, CTAs route correctly, and the landing stays up independent of the app box.

---

## Phase 6 — First release
**Goal:** a stable, downloadable version distinct from `main`.

- Fill the `CHANGELOG`, tag `v1.0.0`, publish a GitHub Release.
- Optionally publish a versioned public image: `ghcr.io/manhardt23/app-tracker:v1.0.0`.
- README: short "what it is" + screenshots + the compose quickstart. (Deeper onboarding deferred, per your call.)

**Done when:** a tagged release exists; self-hosters pull a pinned version while demo/prod keep tracking `main`.

---

## Decisions to confirm
- **Registry:** GHCR is the natural home for the public/open-source image (free, public, GitHub-native). Keep ECR only if you specifically want it for the private pull path; otherwise GHCR can serve both demo and prod too.
- **Tracking:** demo + prod both track `main` (your stated preference). A later maturity step is demo = `main` (acts as staging) and prod = latest tag.

## Sequencing rationale
0 → 1 give you a stronger product on your current single deployment fast. 2 → 5 multiply that one product into demo + prod + landing without touching the code's behavior. 6 formalizes releases. Nothing here requires a rewrite — it's the same app, restructured and deployed like a real product.
