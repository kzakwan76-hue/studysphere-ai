"""Login throttling: slow down password guessing.

Failed attempts are stored in the database, so limits survive restarts and work across several
server processes. Two limits apply inside a sliding time window:
  - per (email, IP) pair: stops one client hammering one account
  - per IP: stops one client trying many accounts (credential stuffing)
The email is whatever was typed, even if no such account exists, so the behaviour never reveals
whether an account exists.
"""

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import LoginFailure


def _utc(moment: datetime) -> datetime:
    """SQLite hands back naive datetimes; they were stored as UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def seconds_until_allowed(db: Session, email: str, ip: str, now: datetime | None = None) -> int:
    """0 if this attempt may proceed, otherwise how many seconds the client must wait.

    `now` can be passed in so tests can control time.
    """
    settings = get_settings()
    window = timedelta(minutes=settings.login_window_minutes)
    now = now or datetime.now(timezone.utc)
    cutoff = now - window
    rules = (
        ((LoginFailure.email == email, LoginFailure.ip == ip), settings.login_max_failures),
        ((LoginFailure.ip == ip,), settings.login_max_failures_per_ip),
    )

    longest_wait = 0
    for conditions, limit in rules:
        times = list(
            db.scalars(
                select(LoginFailure.created_at)
                .where(*conditions, LoginFailure.created_at > cutoff)
                .order_by(LoginFailure.created_at)
            )
        )
        if len(times) >= limit:
            # The lock lifts when enough old failures expire to drop below the limit.
            unlock_at = _utc(times[len(times) - limit]) + window
            longest_wait = max(longest_wait, math.ceil((unlock_at - now).total_seconds()), 1)
    return longest_wait


def record_failure(db: Session, email: str, ip: str, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    db.add(LoginFailure(email=email, ip=ip, created_at=now))
    # Housekeeping: forget failures that are far too old to matter.
    stale = now - 2 * timedelta(minutes=get_settings().login_window_minutes)
    db.execute(delete(LoginFailure).where(LoginFailure.created_at < stale))
    db.commit()


def clear_failures(db: Session, email: str, ip: str) -> None:
    """A successful login wipes this email-and-IP pair's failure count."""
    db.execute(delete(LoginFailure).where(LoginFailure.email == email, LoginFailure.ip == ip))
    db.commit()