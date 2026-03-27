# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

SGMC Brain is the unified governance hub for Stroud Green Medical Clinic. It interconnects policies, events, risks, compliance checks, and safety alerts into a single "brain" that any staff role can use to know what to do and how to manage events. It generates CQC-ready evidence packs.

**Architecture**: Option A+C hybrid — unified FastAPI monolith as system of record, with Claude Agent SDK layer planned for intelligent features.

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (mapped columns), Alembic, Pydantic v2
- **Frontend:** React 19 + TypeScript, Vite, Tailwind CSS 3, React Router 7, TanStack Query
- **Database:** PostgreSQL 16 (port 5440 dev, 5440 Synology)
- **Cache/Queue:** Redis 7 (port 6380)
- **Auth:** Cloudflare Access JWT validation middleware
- **Deployment:** Docker Compose on Synology NAS (host networking), Nginx reverse proxy

## Commands

### Backend (`cd backend`)
```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8090    # Dev server
alembic upgrade head                                      # Run migrations
alembic revision --autogenerate -m "description"          # New migration
python scripts/seed_all.py                                # Seed all data
python scripts/seed_policies.py                           # Seed policies only
python scripts/seed_event_types.py                        # Seed event types only
python scripts/seed_roles.py                              # Seed RBAC roles
```

### Frontend (`cd frontend`)
```bash
npm install          # Install dependencies
npm run dev          # Dev server at http://localhost:3000 (proxies /api to :8090)
npm run build        # TypeScript check + Vite production build
npm run lint         # ESLint
```

### Docker
```bash
# Local development
docker-compose -f docker/docker-compose.dev.yml up -d
docker-compose -f docker/docker-compose.dev.yml up -d --build

# Synology production
docker-compose -f docker/docker-compose.synology.yml up -d --build
```

No test framework is configured yet.

## Architecture

### Monorepo Layout
```
backend/
  main.py              # Re-exports app (uvicorn entry point)
  app/
    main.py            # FastAPI app, middleware, router registration, lifespan
    api/
      deps.py          # Dependency injection: get_current_actor, get_session
      routes/          # Route handlers (health, auth, policies, events, risks)
    core/
      config.py        # Pydantic Settings (env vars)
      database.py      # SQLAlchemy engine + get_db() session generator
      auth.py          # CloudflareAccessMiddleware + Actor dataclass
    models/            # SQLAlchemy ORM models (7 modules, 18 tables)
    schemas/           # Pydantic schemas (TODO)
    services/          # Business logic (TODO)
    workers/           # Celery tasks (TODO)
  alembic/versions/    # DB migrations
  scripts/             # Seed scripts
frontend/
  src/
    api/               # client.ts (fetch wrapper), types.ts
    components/        # Layout, shared UI
    hooks/             # useAuth
    pages/             # Route pages (dashboard, policies, events, risks)
  nginx.conf           # Production Nginx config
docker/
  docker-compose.dev.yml      # Local dev
  docker-compose.synology.yml # Synology production
agent/                 # Claude Agent SDK runtime (planned)
seed-data/             # JSON Schema event types, historical CSV
```

### Data Model (18 tables across 7 modules)

**Core governance loop:**
- `policies` + `policy_versions` + `policy_cqc_mappings` + `policy_acknowledgments`
- `event_types` + `events` + `event_history` + `event_actions`
- `risks` + `risk_reviews` + `risk_actions`

**Compliance:**
- `check_templates` + `staff_checks` + `check_documents`

**Alerts:**
- `alerts` + `alert_actions` + `alert_notifications`

**Evidence:**
- `evidence_packs` + `evidence_items`

**System:**
- `users` + `roles` + `permissions` + `user_roles` + `role_permissions`
- `audit_log`

### Request Flow
1. Nginx (port 8120) serves the SPA and proxies `/api/` to FastAPI (port 8090), forwarding CF Access headers
2. Middleware: CORS → CloudflareAccessMiddleware. `/api/health` bypasses auth.
3. Auth resolution: CF_ACCESS_REQUIRED=true validates JWT; false falls back to dev email
4. Routes inject `Actor` and `Session` via `Depends()`
5. Alembic migrations auto-run on app startup via FastAPI lifespan

### Port Map

| Service    | Dev          | Synology     |
|------------|-------------|--------------|
| PostgreSQL | 5440        | 5440         |
| Redis      | 6380        | 6380         |
| FastAPI    | 8090        | 8090         |
| Frontend   | 3000 (Vite) | 8120 (Nginx) |

### API Endpoints (all prefixed `/api`)
- `/health` - Health check (no auth)
- `/auth/me` - Current authenticated user
- `/policies` - CRUD with filters (domain, status, search)
- `/events` - CRUD with filters (type, status, severity, search)
- `/events/types` - List event type definitions
- `/risks` - CRUD with filters (category, status, min_score)

### RBAC Model
5 roles with hierarchical permissions:
- **reception** (level 0): read policies, read/write events, read compliance/alerts
- **clinical** (level 10): + write compliance, read risks
- **gp** (level 20): + write policies/risks/alerts, approve events, read evidence
- **manager** (level 30): read/write/approve all resources
- **partner** (level 40): full admin on all resources

## Key Conventions

- All models use UUID primary keys (via `mapped_column(UUID(as_uuid=True))`)
- Soft deletes via `is_active` fields where applicable
- Audit trail via `created_by`, `updated_by` on models + `audit_log` table
- Event payloads stored as JSONB, validated against `event_types.json_schema`
- Policy content stored as structured JSONB; .docx files are generated output
- Risk scores use NHS 5x5 matrix: likelihood(1-5) x impact(1-5)
- Frontend API calls centralized in `frontend/src/api/client.ts` — generic `api<T>()` fetch wrapper
- Frontend uses React hooks + TanStack Query for server state
- Vite dev server proxies `/api` to `http://localhost:8090`

## Docker/Synology Deployment

- All services use `network_mode: host` (required for Synology Container Manager — bridge networking broken)
- Redis on port 6380 (not default 6379 to avoid conflicts)
- Postgres on port 5440 (not 5432 — Synology system postgres uses that)
- Frontend Dockerfile: multi-stage (node builder → nginx runtime)
- Must set `HOSTNAME: "0.0.0.0"` for any Next.js containers on host networking
- Volume paths on Synology: `/volume1/docker/sgmc-brain/`

## Environment Variables (Backend)

| Variable              | Default                                                           | Notes                             |
|-----------------------|-------------------------------------------------------------------|-----------------------------------|
| `DATABASE_URL`        | `postgresql+psycopg://postgres:postgres@127.0.0.1:5440/sgmc_brain` |                                 |
| `REDIS_URL`           | `redis://127.0.0.1:6379/0`                                       | Use port 6380 on Synology         |
| `CF_ACCESS_REQUIRED`  | `false`                                                           | Set `true` for production         |
| `CF_ACCESS_TEAM_DOMAIN` | -                                                               | Cloudflare team domain            |
| `CF_ACCESS_AUD`       | -                                                                 | Also from `/run/secrets/cf_access_aud` |
| `DEV_AUTH_EMAIL`      | `dev@stroudgreenmedical.co.uk`                                    |                                   |
| `STAFF_API_URL`       | `http://127.0.0.1:8080/api`                                      | SGMC Data Manager API             |

## Seed Data

- **54 policies** mapped from SGMC Data Manager custom-policies/*.docx
- **4 event types** (JSON Schema): Significant Event, Near Miss, Violent Patient Incident, Supplier/IT Incident
- **5 RBAC roles** with 32 permissions
- **Historical significant events** CSV from practice records
