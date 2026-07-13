# Dogfooding Limelight on GetQuizSolve (M7)

Phase 1 is built and deployed (see `docs/DEPLOY.md`). Dogfooding is the ongoing
loop: run the tracker on GetQuizSolve, read the gaps, act on them, watch the
trend move. This runs on the **live Fly deploy** (real ChatGPT-with-search).

## One-time setup (from the browser — no SSH)
1. Open the Vercel dashboard URL, click **Settings**, paste your `ADMIN_TOKEN`.
2. **Seed GetQuizSolve** (if the brand list is empty).
3. **Generate prompts** — expands the single seed prompt into 40–100 real buyer
   prompts across intent types (scrapes getquizsolve.com + infers competitors).
4. **Run now** — executes every active prompt through ChatGPT search. Takes a
   while for a large prompt set; the daily scheduler (`beat`, 06:00 UTC) then
   keeps it fresh automatically.

## The daily loop
- The **beat** scheduler enqueues a run per brand every day; the **worker**
  executes them and recomputes scores. You don't have to do anything.
- Each morning, open the dashboard:
  - **Visibility score** (7d / 30d / All) — is the trend rising?
  - **Share of voice** — are we gaining on Coursology / CheatMate / QuizSolverAI / QuizAce?
  - **Gaps & recommendations** — which prompts do competitors win that we don't?
    Click **Generate recommendations** for concrete next actions.
  - **Top cited sources** — the domains ChatGPT leans on (Reddit, review sites,
    listicles). These are where to go get GetQuizSolve mentioned.

## Acting on the output (the point of dogfooding)
For each gap, pick the highest-leverage move:
- **Prompt gap** (competitors named, we're absent): create the asset that would
  earn a mention — a comparison page, a Reddit answer, a listicle pitch.
- **Source gap** (a domain cited repeatedly): get GetQuizSolve represented there.
- Re-run after a week and confirm the visibility score / share-of-voice moved.

## Reading the logs
Structured JSON logs stream to `fly logs -a limelight-geo` (and to Grafana Loki
if wired). Useful events:
- `provider.openai.run` — `web_search_invoked`, `annotation_count`, `citations`
  (is search actually firing and citing?)
- `run.completed` — `brand_mentioned`, `mentions`, `citations` per run
- `task.run_all_brands.enqueued` / `task.run_brand.done` — the daily schedule
- `gaps.recommend` — recommendation generation

Copy any anomalous line and share it to debug.

## Phase 1 ship criterion — met
A daily-updating GetQuizSolve dashboard showing: visibility trend, competitor
share-of-voice, top cited sources, and a ranked gap list — from live
ChatGPT-with-search data. Next: Phase 2 (Google AI Overviews + Gemini adapters).
