"""Follow-up detection, contact staging, and last_contact_at derivation."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.models import Application, Company, Email, EmailAnalysis

STALE_AFTER_DAYS = 14
OVERDUE_AFTER_DAYS = 21
UPCOMING_WINDOW_DAYS = 5
DEFAULT_LIMIT = 8

ACTIVE_STAGES = frozenset({"applied", "screening", "interview"})
TERMINAL_STAGES = frozenset({"offer", "rejected", "withdrawn", "no_response"})

FOLLOW_UP_OPEN = "open"
FOLLOW_UP_SNOOZED = "snoozed"
FOLLOW_UP_MUTED = "muted"

MESSAGE_TEMPLATE = (
    "Hi {first_name}, I recently applied for the {role} role at {company} "
    "({applied_relative}) and wanted to express my continued interest. "
    "I'd welcome the chance to connect and answer any questions about my background."
)

_LEGAL_SUFFIXES = re.compile(
    r"\b(inc\.?|llc\.?|l\.?l\.?c\.?|corp\.?|corporation|ltd\.?|limited|co\.?)\b",
    re.IGNORECASE,
)


def follow_up_timezone() -> datetime.tzinfo:
    """Server timezone for day-boundary math (user tz can replace later)."""
    return datetime.now().astimezone().tzinfo or UTC


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def local_today() -> date:
    return datetime.now(follow_up_timezone()).date()


def days_since_contact(last_contact_at: datetime | None, applied_date: datetime) -> int:
    anchor = _as_utc(last_contact_at or applied_date)
    today = local_today()
    anchor_day = anchor.astimezone(follow_up_timezone()).date()
    return max(0, (today - anchor_day).days)


def humanize_relative_past(value: datetime) -> str:
    days = days_since_contact(value, value)
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 14:
        return f"about {days} days ago"
    weeks = round(days / 7)
    if weeks == 1:
        return "about one week ago"
    if weeks < 8:
        return f"about {weeks} weeks ago"
    months = round(days / 30)
    if months == 1:
        return "about one month ago"
    return f"about {months} months ago"


def collapse_company_name(name: str) -> str:
    cleaned = _LEGAL_SUFFIXES.sub("", name)
    cleaned = re.sub(r"[\s,.-]+$", "", cleaned.strip())
    return " ".join(cleaned.split()).strip() or name.strip()


def build_linkedin_search_url(company_name: str) -> str:
    keywords = f"{collapse_company_name(company_name)} recruiter"
    return (
        "https://www.linkedin.com/search/results/people/?keywords="
        + quote(keywords, safe="")
    )


def build_suggested_message(
    *,
    contact_name: str | None,
    role: str,
    company: str,
    applied_date: datetime,
) -> str:
    first = (contact_name or "").strip().split()[0] if (contact_name or "").strip() else "there"
    return MESSAGE_TEMPLATE.format(
        first_name=first,
        role=role,
        company=company,
        applied_relative=humanize_relative_past(applied_date),
    )


def has_saved_contact(application: Application) -> bool:
    return bool((application.contact_linkedin_url or "").strip())


class FollowUpService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def recompute_last_contact_at(self, application: Application) -> datetime:
        latest_email_at = (
            self.session.query(func.max(Email.received_date))
            .join(EmailAnalysis, EmailAnalysis.email_id == Email.id)
            .filter(EmailAnalysis.application_id == application.id)
            .scalar()
        )
        candidates = [_as_utc(application.applied_date)]
        if latest_email_at is not None:
            candidates.append(_as_utc(latest_email_at))
        if application.last_contact_at is not None:
            candidates.append(_as_utc(application.last_contact_at))
        application.last_contact_at = max(candidates)
        return application.last_contact_at

    def mark_followed_up(self, application: Application, note: str | None = None) -> None:
        application.last_contact_at = datetime.now(UTC)
        application.follow_up_status = FOLLOW_UP_OPEN
        application.snoozed_until = None
        if note and note.strip():
            existing = (application.notes or "").strip()
            stamp = datetime.now(UTC).strftime("%Y-%m-%d")
            line = f"[{stamp} follow-up] {note.strip()}"
            application.notes = f"{existing}\n{line}".strip() if existing else line

    def snooze(self, application: Application, until: date) -> None:
        application.follow_up_status = FOLLOW_UP_SNOOZED
        application.snoozed_until = until

    def _follow_up_eligible(self, application: Application, today: date) -> bool:
        status = application.follow_up_status or FOLLOW_UP_OPEN
        if status == FOLLOW_UP_MUTED:
            return False
        if status == FOLLOW_UP_SNOOZED:
            if application.snoozed_until is None or application.snoozed_until > today:
                return False
        return True

    def get_dashboard(
        self,
        *,
        stale_after_days: int = STALE_AFTER_DAYS,
        limit: int = DEFAULT_LIMIT,
    ) -> dict:
        now = datetime.now(UTC)
        today = local_today()
        upcoming_end = now + timedelta(days=UPCOMING_WINDOW_DAYS)

        rows = (
            self.session.query(Application, Company.name)
            .join(Company, Application.company_id == Company.id)
            .options(joinedload(Application.company))
            .all()
        )

        upcoming: list[dict] = []
        stalled_candidates: list[dict] = []

        for application, company_name in rows:
            stage = (application.stage or "").lower()
            if application.next_event_at is not None:
                event_at = _as_utc(application.next_event_at)
                if now <= event_at <= upcoming_end:
                    event_day = event_at.astimezone(follow_up_timezone()).date()
                    upcoming.append(
                        {
                            "application_id": application.id,
                            "company": company_name,
                            "role": application.position,
                            "status": stage,
                            "event_at": event_at,
                            "in_days": max(0, (event_day - today).days),
                        }
                    )

            if stage not in ACTIVE_STAGES or stage in TERMINAL_STAGES:
                continue
            if not self._follow_up_eligible(application, today):
                continue

            last_contact = application.last_contact_at or application.applied_date
            days_since = days_since_contact(application.last_contact_at, application.applied_date)
            if days_since < stale_after_days:
                continue

            urgency = "overdue" if days_since >= OVERDUE_AFTER_DAYS else "due"
            has_contact = has_saved_contact(application)
            stalled_candidates.append(
                {
                    "application_id": application.id,
                    "company": company_name,
                    "role": application.position,
                    "status": stage,
                    "last_contact_at": _as_utc(last_contact),
                    "days_since_contact": days_since,
                    "urgency": urgency,
                    "has_contact": has_contact,
                    "contact": {
                        "name": application.contact_name,
                        "title": application.contact_title,
                        "linkedin_url": application.contact_linkedin_url,
                    },
                    "linkedin_search_url": build_linkedin_search_url(company_name),
                    "suggested_message": build_suggested_message(
                        contact_name=application.contact_name,
                        role=application.position,
                        company=company_name,
                        applied_date=application.applied_date,
                    ),
                }
            )

        upcoming.sort(key=lambda item: item["event_at"])
        stalled_candidates.sort(
            key=lambda item: (
                0 if item["urgency"] == "overdue" else 1,
                -item["days_since_contact"],
            )
        )
        stalled = stalled_candidates[:limit]

        return {
            "generated_at": now,
            "config": {
                "stale_after_days": stale_after_days,
                "overdue_after_days": OVERDUE_AFTER_DAYS,
                "upcoming_window_days": UPCOMING_WINDOW_DAYS,
            },
            "counts": {
                "stalled": len(stalled_candidates),
                "upcoming": len(upcoming),
                "needs_contact": sum(1 for item in stalled_candidates if not item["has_contact"]),
            },
            "upcoming": upcoming,
            "stalled": stalled,
        }
