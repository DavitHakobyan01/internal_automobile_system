from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List

from validation import compute_dealer_health, validate_row


SCRAPER_MONITOR: Dict[str, Any] = {
    "running": False,
    "started_at": None,
    "updated_at": None,
    "dealers": {},
}


def _timestamp(now: datetime | None = None) -> datetime:
    return now or datetime.utcnow()


def reset_monitor_state(now: datetime | None = None) -> None:
    """Reset monitor to initial state. Primarily used for tests."""

    SCRAPER_MONITOR["running"] = False
    SCRAPER_MONITOR["started_at"] = None
    SCRAPER_MONITOR["updated_at"] = _timestamp(now)
    SCRAPER_MONITOR["dealers"] = {}


def start_monitoring(now: datetime | None = None) -> None:
    timestamp = _timestamp(now)

    SCRAPER_MONITOR["running"] = True
    SCRAPER_MONITOR["started_at"] = timestamp
    SCRAPER_MONITOR["updated_at"] = timestamp
    SCRAPER_MONITOR["dealers"] = {}


def record_dealer_result(
    dealer_name: str, rows: List[Dict[str, Any]], run_date: date | None = None, now: datetime | None = None
) -> None:
    run_date = run_date or date.today()
    timestamp = _timestamp(now)

    validated_rows = [validate_row(row, run_date) for row in rows]
    health = compute_dealer_health(validated_rows)

    SCRAPER_MONITOR["dealers"][dealer_name] = {
        "status": health["status"],
        "total_rows": health["total_rows"],
        "invalid_required_rows": health["invalid_required_rows"],
        "attention_rows": health["attention_rows"],
        "top_issues": health["top_issues"],
    }
    SCRAPER_MONITOR["updated_at"] = timestamp


def record_dealer_exception(dealer_name: str, exc: Exception, now: datetime | None = None) -> None:
    timestamp = _timestamp(now)

    SCRAPER_MONITOR["dealers"][dealer_name] = {
        "status": "FAIL",
        "total_rows": 0,
        "invalid_required_rows": 0,
        "attention_rows": 0,
        "top_issues": [f"exception: {exc}"],
    }
    SCRAPER_MONITOR["updated_at"] = timestamp


def finish_monitoring(now: datetime | None = None) -> None:
    SCRAPER_MONITOR["running"] = False
    SCRAPER_MONITOR["updated_at"] = _timestamp(now)