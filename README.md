# Limelight — AI Visibility Tracker

Measures where a brand shows up when people ask AI assistants questions in its
category, tracks it over time, benchmarks against competitors, and surfaces the
gaps (a GEO/AEO tool).

**Phase 1** builds the whole pipeline against a single engine — **OpenAI/ChatGPT**
via the Responses API + `web_search` tool (real `url_citation` annotations +
`sources`). Everything below the provider (detection, scoring, storage, dashboard)
is engine-agnostic, so Phase 2 (Google AI Overviews, Gemini) is "write two
adapters," not a rewrite.

Primary goal is **dogfooding** — pointed at **GetQuizSolve** (`getquizsolve.com`).

## Architecture

```
prompt ──> EngineProvider.run() ──> {answer_text, cited_urls, raw}
                (openai)                     │
                                             ▼
                        detection ──> mentions   citations
                                             │
                                             ▼
                                   runs (append-only, immutable)
                                             │
                                             ▼
                              scoring (recomputed per window) ──> scores
                                             │
                                             ▼
                          API (FastAPI) ──> dashboard (React, read-only)
```

The **engine boundary** (`app/providers/base.py`) is the one thing to get right:
detection/scoring/storage/dashboard consume only `{answer_text, cited_urls}` and
never know which provider produced them.

## Stack
- Backend: Python 3.11, FastAPI, SQLAlchemy 2 + Alembic, Pydantic v2, `openai`, `rapidfuzz`, `tldextract`, `trafilatura`.
- Queue: Celery + Redis (worker + beat for the daily cron) — added in M4.
- DB: Postgres (Supabase in deployment).
- Frontend: React + Vite + TypeScript + Recharts — added in M5.

## Quickstart (local, Docker Compose)

```bash
cp .env.example .env          # set OPENAI_API_KEY
docker compose up -d postgres redis api
docker compose exec api alembic upgrade head
docker compose exec api python -m app.cli seed
```

Once M1 lands, trigger a run and inspect it — no UI needed:

```bash
docker compose exec api python -m app.cli run-brand <brand_id>
docker compose exec api python -m app.cli show-runs <brand_id>
```

The scheduler services (`worker`, `beat`) are behind a compose profile:
`docker compose --profile scheduler up -d`.

### Running the backend without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# point DATABASE_URL / DATABASE_URL_DIRECT at a Postgres you control, then:
alembic upgrade head
python -m app.cli seed
uvicorn app.main:app --reload
```

## CLI (the trigger before the UI exists)

| command | milestone | what it does |
|---|---|---|
| `seed` | M0 | create GetQuizSolve brand + competitors + a starter prompt |
| `show-runs <brand_id>` | M0 | dump latest runs/mentions/citations to the console |
| `run-prompt <prompt_id>` | M1 | run one prompt through OpenAI, store the run |
| `run-brand <brand_id>` | M1 | run all active prompts for a brand now (`--async` enqueues via Celery, M4) |
| `gen-prompts <brand_id>` | M2 | scrape domain → generate 40–100 buyer prompts |
| `score <brand_id>` | M3 | recompute scores for the window |
| `gaps <brand_id>` | M6 | print the ranked gap list |

## Deployment (Fly.io + Supabase + Upstash)

Backend → Fly.io (`limelight-geo`, region `iad`), DB → Supabase Postgres, frontend
→ Vercel. The first deploy is API-only; worker/beat + Upstash Redis land with M4.
Full step-by-step (Supabase → Fly → Vercel → live check) is in
[`docs/DEPLOY.md`](docs/DEPLOY.md). Config lives in `backend/fly.toml` and
`frontend/vercel.json`.

## Status

- [x] **M0** — scaffold, models, migration, seed, FastAPI skeleton, CLI
- [x] **M1** — vertical slice (OpenAI provider + runner + fuzzy detection + citations + scoring + read API + React dashboard)
- [ ] **M2** — prompt generation
- [ ] **M3** — full detection + scoring
- [ ] **M4** — scheduler + first deploy
- [ ] **M5** — dashboard
- [ ] **M6** — gap analysis + recommendations
- [ ] **M7** — dogfood on Fly
