"""Shared API dependencies."""
from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import get_settings


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Gate write endpoints behind the ADMIN_TOKEN shared secret.

    If ADMIN_TOKEN is unset on the server, writes are disabled entirely (so a
    misconfigured deploy can't be triggered by anyone)."""
    token = get_settings().admin_token
    if not token:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured on the server")
    if x_admin_token != token:
        raise HTTPException(status_code=401, detail="invalid or missing admin token")
