"""Structured JSON logging → stdout.

One JSON object per line, so it's greppable in `fly logs` and ingests cleanly
into Grafana Loki / Cloud without a parser. Attach structured fields via the
`extra={"fields": {...}}` kwarg on any log call; use `log_event` for that.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Idempotently install the JSON handler on the root logger."""
    root = logging.getLogger()
    if any(getattr(h, "_limelight", False) for h in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._limelight = True  # type: ignore[attr-defined]
    root.handlers = [handler]
    root.setLevel(level)


def log_event(logger: logging.Logger, msg: str, /, level: int = logging.INFO, **fields: Any) -> None:
    """Emit a structured event: `log_event(log, "run.completed", run_id=..., citations=3)`."""
    logger.log(level, msg, extra={"fields": fields})
