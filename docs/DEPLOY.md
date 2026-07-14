# Deploying Limelight

Backend → **Fly.io** (app `limelight-geo`, region `iad`), DB → **Supabase Postgres**
(`us-east-1`), frontend → **Vercel**.

This first deploy stands up the **API only**. The Celery worker + beat (the daily
scheduler) and Upstash Redis are added in M4. For now you trigger runs manually
over SSH — which also confirms the live OpenAI response shape.

Order: **Supabase → Upstash → Fly → Vercel → live check**.

Since M4, the Fly app runs **three process groups** — `app` (API), `worker`
(Celery), `beat` (daily scheduler). The worker/beat groups need `REDIS_URL`.

---

## 1. Supabase (database)

1. Create a project in **US East (us-east-1)**. Save the DB password.
2. Project → **Connect** → **ORMs / URI**. You need two connection strings, both
   via the pooler (IPv4-friendly). Replace `<REF>`, `<PASSWORD>`:

   **App (transaction pooler, port 6543)** → `DATABASE_URL`:
   ```
   postgresql+psycopg://postgres.<REF>:<PASSWORD>@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
   ```

   **Migrations (session pooler, port 5432)** → `DATABASE_URL_DIRECT`:
   ```
   postgresql+psycopg://postgres.<REF>:<PASSWORD>@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
   ```

   > Two different **ports** on the same pooler host. The app uses transaction
   > mode (6543); Alembic uses session mode (5432) because transaction mode
   > breaks migration DDL. Keep `postgresql+psycopg://` (our SQLAlchemy driver)
   > even if Supabase shows `postgresql://`.

---

## 1b. Upstash (Redis — Celery broker)

1. Create a **Redis** database (free tier), region close to `us-east-1`.
2. Copy the **`rediss://`** connection URL (TLS). That's `REDIS_URL`.
   The Celery app auto-enables TLS when the URL starts with `rediss://`.

---

## 2. Fly.io (backend API + worker + beat)

You can deploy either **from CI on git push** (recommended — no local flyctl) or
**manually**.

### Option A — deploy via GitHub Actions (push-to-deploy, hands-off)
`.github/workflows/fly-deploy.yml` **creates the app if missing** and runs
`flyctl deploy` on every push touching `backend/`. One-time setup:
1. Create an **org-scoped** token (an app-scoped deploy token can't create the
   app — chicken/egg):
   ```bash
   fly tokens create org        # pick your org; "personal" is the default
   ```
   Add it as repo secret **`FLY_API_TOKEN`** (GitHub → Settings → Secrets → Actions).
2. Run the workflow once (**Actions → Deploy backend to Fly → Run workflow**, or
   push a `backend/` change). It creates `limelight-geo` and deploys — the first
   deploy will start but the app has no secrets yet, so set them next.
3. Set the app secrets in the **Fly dashboard** (`limelight-geo` → Secrets):
   `OPENAI_API_KEY`, `ADMIN_TOKEN`, `REDIS_URL`, `DATABASE_URL`,
   `DATABASE_URL_DIRECT` (values from §1 / §1b).
4. Re-run the workflow. The `release_command` runs `alembic upgrade head`, then
   the API goes live.

> If your app lives in a non-personal org, edit `FLY_ORG` at the top of the
> workflow to match.

### Option B — deploy manually
From the repo root:

```bash
# once, if needed:
curl -L https://fly.io/install.sh | sh    # installs flyctl
fly auth login

cd backend

# Create the app WITHOUT deploying (fly.toml already exists; don't let it overwrite).
fly apps create limelight-geo        # if the name is taken, pick another and update fly.toml `app = ...`

# Set secrets (never commit these). Paste your real values:
fly secrets set \
  OPENAI_API_KEY="sk-..." \
  ADMIN_TOKEN="<long-random-string>" \
  REDIS_URL="rediss://default:<PW>@<host>.upstash.io:6379" \
  SERPAPI_API_KEY="<serpapi-key, only if tracking google_aio>" \
  DATABASE_URL="postgresql+psycopg://postgres.<REF>:<PASSWORD>@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require" \
  DATABASE_URL_DIRECT="postgresql+psycopg://postgres.<REF>:<PASSWORD>@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require"

# Deploy. The release_command runs `alembic upgrade head` against DATABASE_URL_DIRECT.
fly deploy
```

Verify:
```bash
curl https://limelight-geo.fly.dev/health          # {"status":"ok"}
fly ssh console -C "python -m app.cli seed"         # creates GetQuizSolve
curl https://limelight-geo.fly.dev/brands           # should list GetQuizSolve
```

---

## 3. Vercel (frontend)

1. **Import** the Git repo in Vercel.
2. Project settings:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite (auto-detected)
   - **Environment Variable**: `VITE_API_BASE = https://limelight-geo.fly.dev`
3. Deploy. Note the resulting URL, e.g. `https://limelight-<hash>.vercel.app`.

4. **Allow the frontend origin in the API's CORS**, then redeploy the backend:
   ```bash
   cd backend
   fly secrets set CORS_ORIGINS="https://<your-vercel-domain>.vercel.app"
   ```
   (Setting the secret triggers a restart; no full redeploy needed.)

---

## 4. Live check (confirms the OpenAI response shape — the M1 checkpoint)

Use the brand id that `python -m app.cli seed` printed in step 2 (or read it from
`curl https://limelight-geo.fly.dev/brands`). Then:

```bash
cd backend
BRAND=<brand-id-from-seed>
# Trigger a REAL ChatGPT-with-search run and inspect it:
fly ssh console -C "python -m app.cli run-brand $BRAND"
fly ssh console -C "python -m app.cli show-runs $BRAND"
```

`show-runs` should print a real answer, real cited domains, and mentions. Open
the Vercel URL — the dashboard should show a non-placeholder visibility score.

**If the run errors on the web_search tool type**, change `"web_search"` →
`"web_search_preview"` in `backend/app/providers/openai_provider.py`, redeploy,
and retry. (Send me the error / raw response and I'll adjust extraction.)

---

## Notes / gotchas
- **Supabase free tier auto-pauses after ~7 days idle.** The M4 daily cron keeps
  it warm; until then, an idle project may need a manual unpause in the dashboard.
- **Fly `min_machines_running = 0`** means the API cold-starts after idle (a
  couple seconds on first request). Fine for a dashboard; bump to `1` if you want
  it always warm.
- **Secrets live only in Fly/Vercel**, never in git. `.env` is gitignored.
- **Scheduler**: `worker` + `beat` process groups run continuously (they're not
  http services, so autostop doesn't apply). `beat` fires `run_all_brands` daily
  at 06:00 UTC, which enqueues a run per brand. Force one now with
  `fly ssh console -C "python -m app.cli run-brand <id> --async"` (enqueues via
  Celery) or trigger inline from the dashboard's "Run now".
- **Cost**: 3 tiny always-on-ish machines. `app` autostops when idle; `worker`
  and `beat` stay up for the schedule.
