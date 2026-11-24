from datetime import UTC, date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser, get_db
from app.db.models import Application, Company, Email, EmailAnalysis
from app.services.dashboard_view import (
    ApplicationSnapshot,
    build_glance,
    build_series,
    responses_and_rate,
    stage_counts,
    status_label,
    to_date,
)
from app.services.role_groups import group_positions

router = APIRouter()

DbDep = Annotated[Session, Depends(get_db)]

# Stale applications have had no linked email and no row update for this many days.
# There is no separate stage-change log; last_updated is the stored update time.
STALE_AFTER_DAYS = 14


def _snapshots(db: Session) -> list[ApplicationSnapshot]:
    rows = db.query(
        Application.id,
        Application.stage,
        Application.position,
        Application.applied_date,
        Application.last_updated,
    ).all()
    return [
        ApplicationSnapshot(
            id=row.id,
            stage=row.stage,
            position=row.position or "",
            applied_on=to_date(row.applied_date),
            updated_on=to_date(row.last_updated),
        )
        for row in rows
    ]


def _latest_email_on(db: Session) -> dict[int, date]:
    rows = (
        db.query(EmailAnalysis.application_id, func.max(Email.received_date))
        .join(Email, Email.id == EmailAnalysis.email_id)
        .filter(EmailAnalysis.application_id.is_not(None))
        .group_by(EmailAnalysis.application_id)
        .all()
    )
    latest: dict[int, date] = {}
    for application_id, received in rows:
        if application_id is None:
            continue
        parsed = to_date(received)
        if parsed is not None:
            latest[int(application_id)] = parsed
    return latest


@router.get("/metrics")
def get_dashboard_metrics(db: DbDep, _user: AdminUser):
    snapshots = _snapshots(db)
    counts = stage_counts([row.stage for row in snapshots])
    total = len(snapshots)
    responses_received, response_rate = responses_and_rate(counts, total)
    return {
        "total_applications": total,
        "responses_received": responses_received,
        "interviews_scheduled": counts["interview"],
        "response_rate": response_rate,
    }


@router.get("/glance")
def get_dashboard_glance(
    db: DbDep,
    _user: AdminUser,
    stale_days: int = Query(default=STALE_AFTER_DAYS, ge=1, le=365),
):
    today = datetime.now(UTC).date()
    return build_glance(
        _snapshots(db),
        _latest_email_on(db),
        today=today,
        stale_days=stale_days,
    )


@router.get("/applications-over-time")
def get_applications_over_time(
    db: DbDep,
    _user: AdminUser,
    days: int = Query(
        default=30,
        ge=0,
        le=3650,
        description="Inclusive window ending today. 0 is all-time.",
    ),
    granularity: Literal["day", "week", "month"] = Query(default="day"),
):
    today = datetime.now(UTC).date()
    applied = [row.applied_on for row in _snapshots(db) if row.applied_on is not None]
    return build_series(applied, today=today, days=days, granularity=granularity)


@router.get("/status-breakdown")
def get_status_breakdown(db: DbDep, _user: AdminUser):
    counts = stage_counts([row.stage for row in _snapshots(db)])
    return [
        {"name": "Applied", "value": counts["applied"]},
        {"name": "Interview", "value": counts["interview"]},
        {"name": "Offer", "value": counts["offer"]},
        {"name": "Rejected", "value": counts["rejected"]},
    ]


@router.get("/role-breakdown")
def get_role_breakdown(db: DbDep, _user: AdminUser):
    return {"groups": group_positions([row.position for row in _snapshots(db)])}


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
        data.append(
            {
                "company": company_name,
                "role": application.position,
                "status": status_label(application.stage),
                "date_applied": application.applied_date.date().isoformat(),
            }
        )
    return data
