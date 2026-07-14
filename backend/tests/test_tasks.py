from datetime import datetime, timedelta, timezone

from app.seed import seed_getquizsolve
from app.tasks.celery_app import celery_app
from app.tasks.run_tasks import active_brand_ids, due_brand_ids, is_due


def test_active_brand_ids(db):
    seed_getquizsolve(db)
    assert len(active_brand_ids(db)) == 1


def test_beat_schedule_is_hourly_dispatcher():
    sched = celery_app.conf.beat_schedule
    assert "dispatch-due-brands" in sched
    assert sched["dispatch-due-brands"]["task"] == "app.tasks.run_tasks.dispatch_due_brands"


def test_tasks_registered():
    for name in (
        "app.tasks.run_tasks.run_prompt",
        "app.tasks.run_tasks.run_brand",
        "app.tasks.run_tasks.dispatch_due_brands",
        "app.tasks.run_tasks.run_all_brands",
    ):
        assert name in celery_app.tasks


def test_is_due_frequency(db):
    brand = seed_getquizsolve(db)
    now = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)

    brand.run_frequency = "manual"
    assert is_due(brand, now) is False

    brand.run_frequency = "daily"
    brand.last_run_at = None
    assert is_due(brand, now) is True  # never run -> due

    brand.last_run_at = now - timedelta(hours=25)
    assert is_due(brand, now) is True  # > 24h

    brand.last_run_at = now - timedelta(hours=5)
    assert is_due(brand, now) is False  # within window

    brand.run_frequency = "hourly"
    brand.last_run_at = now - timedelta(minutes=90)
    assert is_due(brand, now) is True


def test_due_brand_ids_stamps_last_run(db):
    brand = seed_getquizsolve(db)
    brand.run_frequency = "daily"
    brand.last_run_at = None
    db.flush()
    now = datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc)

    ids = due_brand_ids(db, now)
    assert ids == [str(brand.id)]
    assert brand.last_run_at == now
    # second pass same window -> not due
    assert due_brand_ids(db, now) == []
