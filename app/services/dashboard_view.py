"""Pure dashboard aggregates over dates and stages the API already stores."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

FUNNEL: tuple[tuple[str, str], ...] = (
    ("applied", "Applied"),
    ("interview", "Interview"),
    ("offer", "Offer"),
    ("rejected", "Rejected"),
)

GRANULARITIES = ("day", "week", "month")


@dataclass(frozen=True)
class ApplicationSnapshot:
    id: int
    stage: str | None
    position: str
    applied_on: date | None
    updated_on: date | None


def to_date(value: datetime | date | str | None) -> date | None:
    """Calendar date for a stored timestamp.

    Aware datetimes are read in UTC. Naive values keep the calendar date
    that was stored, which is what ``func.date`` used for the old chart.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(UTC).date()
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        if "T" in text or len(text) > 10:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                return parsed.astimezone(UTC).date()
            return parsed.date()
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def normalize_stage(raw_stage: str | None) -> str:
    stage = (raw_stage or "").lower()
    if stage in {"interview", "assessment"}:
        return "interview"
    if stage in {"offer", "rejected", "applied"}:
        return stage
    return "other"


def status_label(raw_stage: str | None) -> str:
    normalized = normalize_stage(raw_stage)
    if normalized == "interview":
        return "Interview"
    if normalized == "offer":
        return "Offer"
    if normalized == "rejected":
        return "Rejected"
    return "Applied"


def stage_counts(stages: list[str | None]) -> dict[str, int]:
    counts = {"applied": 0, "interview": 0, "offer": 0, "rejected": 0, "other": 0}
    for stage in stages:
        counts[normalize_stage(stage)] += 1
    return counts


def responses_and_rate(counts: dict[str, int], total: int) -> tuple[int, int]:
    """Responses are interview, offer, and rejected. Rate is an integer percent."""
    responses = counts["interview"] + counts["offer"] + counts["rejected"]
    rate = round((responses / total) * 100) if total else 0
    return responses, rate


def funnel_slices(counts: dict[str, int]) -> list[dict]:
    return [{"name": label, "value": counts[key]} for key, label in FUNNEL]


def build_glance(
    applications: list[ApplicationSnapshot],
    latest_email_on: dict[int, date],
    *,
    today: date,
    stale_days: int,
) -> dict:
    """Glance figures from stored stages, applied dates, updates, and emails.

    Stale means the latest of ``last_updated`` and any linked email
    ``received_date`` is at least ``stale_days`` before ``today``. There is
    no stage-change log. ``last_updated`` is the timestamp written when a
    newer email changes the stage and when the application row is edited,
    so a notes-only edit counts as an update.
    """
    counts = stage_counts([row.stage for row in applications])
    total = len(applications)
    responses, rate = responses_and_rate(counts, total)
    this_week_start = today - timedelta(days=today.weekday())
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(days=1)
    this_week_end = this_week_start + timedelta(days=6)

    def _in_week(applied_on: date | None, start: date, end: date) -> bool:
        return applied_on is not None and start <= applied_on <= end

    applied_dates = [row.applied_on for row in applications if row.applied_on is not None]
    last_applied = max(applied_dates) if applied_dates else None
    cutoff = today - timedelta(days=stale_days)
    stale = 0
    for row in applications:
        stamps = [
            stamp for stamp in (row.updated_on, latest_email_on.get(row.id)) if stamp is not None
        ]
        if stamps and max(stamps) <= cutoff:
            stale += 1

    return {
        "total_applications": total,
        "funnel": funnel_slices(counts),
        "other_stages": counts["other"],
        "responses_received": responses,
        "response_rate": rate,
        "this_week": sum(
            1 for row in applications if _in_week(row.applied_on, this_week_start, this_week_end)
        ),
        "last_week": sum(
            1 for row in applications if _in_week(row.applied_on, last_week_start, last_week_end)
        ),
        "last_applied_on": last_applied.isoformat() if last_applied else None,
        "days_since_last_application": (
            None if last_applied is None else max(0, (today - last_applied).days)
        ),
        "stale_days": stale_days,
        "stale_applications": stale,
    }


def build_series(
    applied_dates: list[date],
    *,
    today: date,
    days: int,
    granularity: str,
) -> list[dict]:
    """Bucket applied dates.

    ``days`` 0 is all-time, from the earliest stored date through today
    (or a later stored date, so a future stamp is not dropped). A positive
    window is ``days`` calendar days ending today, matching the old daily
    chart. Empty all-time is an empty list. A window with no rows is still
    zero-filled so the axis is the requested range.
    """
    if granularity not in GRANULARITIES:
        raise ValueError(f"granularity must be one of {GRANULARITIES}")
    if days == 0 and not applied_dates:
        return []
    if days == 0:
        start = min(applied_dates)
        end = max(max(applied_dates), today)
    else:
        start = today - timedelta(days=days - 1)
        end = today

    counts: dict[date, int] = {}
    for applied_on in applied_dates:
        if applied_on < start or applied_on > end:
            continue
        bucket = _bucket_start(applied_on, granularity)
        counts[bucket] = counts.get(bucket, 0) + 1

    buckets = list(_iter_buckets(start, end, granularity))
    span_years = bool(buckets) and buckets[0].year != buckets[-1].year
    return [
        {
            "day": bucket.isoformat(),
            "label": _label(bucket, granularity, span_years),
            "applications": counts.get(bucket, 0),
        }
        for bucket in buckets
    ]


def _bucket_start(day: date, granularity: str) -> date:
    if granularity == "month":
        return day.replace(day=1)
    if granularity == "week":
        return day - timedelta(days=day.weekday())
    return day


def _iter_buckets(start: date, end: date, granularity: str):
    cursor = _bucket_start(start, granularity)
    last = _bucket_start(end, granularity)
    while cursor <= last:
        yield cursor
        cursor = _next_bucket(cursor, granularity)


def _next_bucket(cursor: date, granularity: str) -> date:
    if granularity == "month":
        if cursor.month == 12:
            return date(cursor.year + 1, 1, 1)
        return date(cursor.year, cursor.month + 1, 1)
    if granularity == "week":
        return cursor + timedelta(days=7)
    return cursor + timedelta(days=1)


def _label(bucket: date, granularity: str, span_years: bool) -> str:
    if granularity == "month":
        return bucket.strftime("%b %Y") if span_years else bucket.strftime("%b")
    if span_years:
        return bucket.strftime("%b %d '%y")
    return bucket.strftime("%b %d")
