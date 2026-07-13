from app.seed import seed_getquizsolve
from app.tasks.celery_app import celery_app
from app.tasks.run_tasks import active_brand_ids


def test_active_brand_ids(db):
    seed_getquizsolve(db)
    ids = active_brand_ids(db)
    assert len(ids) == 1


def test_daily_beat_schedule_registered():
    sched = celery_app.conf.beat_schedule
    assert "daily-run-all-brands" in sched
    assert sched["daily-run-all-brands"]["task"] == "app.tasks.run_tasks.run_all_brands"


def test_tasks_registered():
    for name in (
        "app.tasks.run_tasks.run_prompt",
        "app.tasks.run_tasks.run_brand",
        "app.tasks.run_tasks.run_all_brands",
    ):
        assert name in celery_app.tasks
