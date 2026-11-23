"""Link an incoming application email to an existing row, or create one.

The email worker and ``POST /emails/{id}/promote`` both use
``match_or_create_application``. Comparison uses the finder's
``normalize_label`` so case, punctuation, and extra spaces collapse.
"""

from __future__ import annotations

from app.db.models import Application, Company
from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository
from app.services.job_finder import normalize_label

UNKNOWN_COMPANY = "Unknown Company"
UNKNOWN_POSITION = "Unknown Position"


def match_or_create_application(
    company_repo: CompanyRepository,
    app_repo: ApplicationRepository,
    company_name: str,
    position_name: str,
) -> tuple[Application, bool]:
    """Return ``(application, created)``.

    Linking does not change the stored company name or title.
    Unknown company or title never uses the company-only rule; that path
    still creates or reuses the Unknown row.
    """
    if not _uses_unknown(company_name, position_name):
        linked = _find_link_target(app_repo, company_name, position_name)
        if linked is not None:
            return linked, False

    company = _company_for_create(company_repo, company_name)
    existing = app_repo.find_by_company_and_position(company.id, position_name)
    if existing is not None:
        return existing, False
    return app_repo.find_or_create(company.id, position_name), True


def _uses_unknown(company_name: str, position_name: str) -> bool:
    return company_name == UNKNOWN_COMPANY or position_name == UNKNOWN_POSITION


def _company_name(application: Application) -> str:
    company = application.company
    if company is None:
        return ""
    return company.name or ""


def _find_link_target(
    app_repo: ApplicationRepository,
    company_name: str,
    position_name: str,
) -> Application | None:
    target_company = normalize_label(company_name)
    target_title = normalize_label(position_name)
    if not target_company or not target_title:
        return None

    pair_matches: list[Application] = []
    company_matches: list[Application] = []
    for application in app_repo.get_all():
        if normalize_label(_company_name(application)) != target_company:
            continue
        company_matches.append(application)
        if normalize_label(application.position) == target_title:
            pair_matches.append(application)

    if pair_matches:
        # Several rows can already share a normalized company and title.
        # Link the oldest so a punctuation variant does not insert another.
        return min(pair_matches, key=lambda row: row.id)
    if len(company_matches) == 1:
        return company_matches[0]
    return None


def _company_for_create(company_repo: CompanyRepository, company_name: str) -> Company:
    """Reuse the one company with this normalized name.

    Unknown Company always uses today's exact find-or-create so it cannot
    attach to some other row. Several company rows that collapse to the same
    label also fall back to find-or-create.
    """
    if company_name == UNKNOWN_COMPANY:
        return company_repo.find_or_create(company_name)

    target = normalize_label(company_name)
    if target:
        matches = [
            company
            for company in company_repo.session.query(Company).all()
            if normalize_label(company.name) == target
        ]
        if len(matches) == 1:
            return matches[0]
    return company_repo.find_or_create(company_name)
