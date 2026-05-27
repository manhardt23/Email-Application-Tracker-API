from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser, get_db
from app.db.models import Application, Company

router = APIRouter()

DbDep = Annotated[Session, Depends(get_db)]


def _normalize_stage(raw_stage: str | None) -> str:
    stage = (raw_stage or "").lower()
    if stage in {"interview", "assessment"}:
        return "interview"
    if stage in {"offer", "rejected", "applied"}:
        return stage
    return "other"


@router.get("/metrics")
def get_dashboard_metrics(db: DbDep, _user: AdminUser):
    rows = db.query(Application.stage).all()
    total = len(rows)
    counts = {"applied": 0, "interview": 0, "offer": 0, "rejected": 0}
    for (stage,) in rows:
        normalized = _normalize_stage(stage)
        if normalized in counts:
            counts[normalized] += 1

    responses_received = counts["interview"] + counts["offer"] + counts["rejected"]
    response_rate = round((responses_received / total) * 100) if total else 0

    return {
        "total_applications": total,
        "responses_received": responses_received,
        "interviews_scheduled": counts["interview"],
        "response_rate": response_rate,
    }


@router.get("/applications-over-time")
def get_applications_over_time(
    db: DbDep,
    _user: AdminUser,
    days: int = Query(default=30, ge=1, le=365),
):
    today = datetime.now(UTC).date()
    start_date = today - timedelta(days=days - 1)
    daily_rows = (
        db.query(func.date(Application.applied_date).label("day"), func.count(Application.id))
        .filter(func.date(Application.applied_date) >= start_date)
        .group_by(func.date(Application.applied_date))
        .all()
    )

    counts_by_day = {date.fromisoformat(str(day)): count for day, count in daily_rows if day}
    data = []
    for offset in range(days):
        current_day = start_date + timedelta(days=offset)
        data.append(
            {
                "day": current_day.isoformat(),
                "label": current_day.strftime("%b %d"),
                "applications": int(counts_by_day.get(current_day, 0)),
            }
        )
    return data


@router.get("/status-breakdown")
def get_status_breakdown(db: DbDep, _user: AdminUser):
    rows = db.query(Application.stage, func.count(Application.id)).group_by(Application.stage).all()
    counts = {"applied": 0, "interview": 0, "offer": 0, "rejected": 0}
    for stage, count in rows:
        normalized = _normalize_stage(stage)
        if normalized in counts:
            counts[normalized] += int(count)

    return [
        {"name": "Applied", "value": counts["applied"]},
        {"name": "Interview", "value": counts["interview"]},
        {"name": "Offer", "value": counts["offer"]},
        {"name": "Rejected", "value": counts["rejected"]},
    ]


@router.get("/recent-applications")
def get_recent_applications(
    db: DbDep,
    _user: AdminUser,
    limit: int = Query(default=8, ge=1, le=50),
):
    rows = (
        db.query(Application, Company.name)
        .join(Company, Application.company_id == Company.id)
        .order_by(Application.last_updated.desc())
        .limit(limit)
        .all()
    )

    data = []
    for application, company_name in rows:
        normalized = _normalize_stage(application.stage)
        status = (
            "Interview"
            if normalized == "interview"
            else "Offer"
            if normalized == "offer"
            else "Rejected"
            if normalized == "rejected"
            else "Applied"
        )
        data.append(
            {
                "company": company_name,
                "role": application.position,
                "status": status,
                "date_applied": application.applied_date.date().isoformat(),
            }
        )
    return data


@router.get("/top-companies")
def get_top_companies(
    db: DbDep,
    _user: AdminUser,
    limit: int = Query(default=5, ge=1, le=25),
):
    rows = (
        db.query(Company.name, func.count(Application.id).label("application_count"))
        .join(Application, Application.company_id == Company.id)
        .group_by(Company.id, Company.name)
        .order_by(func.count(Application.id).desc(), Company.name.asc())
        .limit(limit)
        .all()
    )
    return [{"company": company_name, "applications": int(count)} for company_name, count in rows]
