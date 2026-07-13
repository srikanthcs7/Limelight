"""Console entrypoint — the primary trigger before the UI exists.

    python -m app.cli seed
    python -m app.cli run-brand <brand_id>
    python -m app.cli show-runs <brand_id>

CLI and Celery tasks share the same runner/scoring code (added in M1/M3).
"""
from __future__ import annotations

import uuid

import typer
from sqlalchemy import select

from app.db import session_scope
from app.logging_config import configure_logging
from app.models import Citation, Mention, Prompt, Run
from app.seed import seed_getquizsolve

configure_logging()
app = typer.Typer(help="Limelight — AI Visibility Tracker CLI")


@app.command()
def seed() -> None:
    """Create the GetQuizSolve brand + competitors + a starter prompt (idempotent)."""
    with session_scope() as db:
        brand = seed_getquizsolve(db)
        typer.echo(f"seeded brand {brand.display_name} ({brand.id})")


@app.command("show-runs")
def show_runs(brand_id: str, limit: int = 10) -> None:
    """Dump the latest runs (+ mentions + citations) for a brand to the console."""
    bid = uuid.UUID(brand_id)
    with session_scope() as db:
        prompt_ids = list(db.scalars(select(Prompt.id).where(Prompt.brand_id == bid)))
        if not prompt_ids:
            typer.echo("no prompts for this brand")
            return
        runs = list(
            db.scalars(
                select(Run)
                .where(Run.prompt_id.in_(prompt_ids))
                .order_by(Run.run_at.desc())
                .limit(limit)
            )
        )
        if not runs:
            typer.echo("no runs yet — trigger one with `run-brand`")
            return
        for run in runs:
            mentions = list(db.scalars(select(Mention).where(Mention.run_id == run.id)))
            citations = list(db.scalars(select(Citation).where(Citation.run_id == run.id)))
            typer.echo(f"\n=== run {run.id} @ {run.run_at:%Y-%m-%d %H:%M} ===")
            typer.echo(f"answer: {run.answer_text[:280]}...")
            typer.echo(
                "mentions: "
                + (
                    ", ".join(
                        f"{m.entity_name}"
                        f"{'*' if m.is_tracked_brand else ''}"
                        f"(pos={m.position})"
                        for m in mentions
                    )
                    or "(none)"
                )
            )
            typer.echo(
                "citations: " + (", ".join(sorted({c.domain for c in citations})) or "(none)")
            )


@app.command("run-prompt")
def run_prompt(prompt_id: str) -> None:
    """Run a single prompt through its engine and store the run. (Implemented in M1.)"""
    from app.pipeline.runner import run_single_prompt

    with session_scope() as db:
        run = run_single_prompt(db, uuid.UUID(prompt_id))
        typer.echo(f"stored run {run.id}")


@app.command("run-brand")
def run_brand(brand_id: str, use_async: bool = typer.Option(False, "--async")) -> None:
    """Run all active prompts for a brand now. (Implemented in M1; --async in M4.)"""
    from app.pipeline.runner import run_brand_prompts

    bid = uuid.UUID(brand_id)
    if use_async:
        from app.tasks.run_tasks import run_brand as run_brand_task

        run_brand_task.delay(str(bid))
        typer.echo(f"enqueued run for brand {bid}")
        return
    with session_scope() as db:
        runs = run_brand_prompts(db, bid)
        typer.echo(f"stored {len(runs)} run(s) for brand {bid}")


@app.command("gen-prompts")
def gen_prompts(brand_id: str, target: int = 60) -> None:
    """Scrape the brand's domain and generate buyer prompts across intent types."""
    from app.pipeline.prompt_gen import generate_for_brand

    with session_scope() as db:
        summary = generate_for_brand(db, uuid.UUID(brand_id), target=target)
        typer.echo(f"generated: {summary}")


@app.command()
def score(brand_id: str) -> None:
    """Recompute scores for a brand's window. (Implemented in M3.)"""
    from app.pipeline.scoring import recompute_scores

    with session_scope() as db:
        result = recompute_scores(db, uuid.UUID(brand_id))
        typer.echo(f"recomputed scores: {result}")


@app.command()
def gaps(brand_id: str) -> None:
    """Print the ranked gap list for a brand. (Implemented in M6.)"""
    from app.pipeline.gaps import compute_gaps

    with session_scope() as db:
        report = compute_gaps(db, uuid.UUID(brand_id))
        typer.echo(report)


if __name__ == "__main__":
    app()
