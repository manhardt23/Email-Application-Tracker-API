"""Map a stored application position onto one dashboard role group.

The match reads the position string already stored on the application.
Classification writes that string; this module does not invent titles.
The first matching group wins, so each application is counted once.
NOC is checked before network, and help desk before IT support, because
those phrases overlap. A title that matches nothing is other.
"""

from __future__ import annotations

import re
from collections import defaultdict

_GROUP_SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "noc",
        "NOC",
        (
            r"\bnoc\b",
            r"network operations",
        ),
    ),
    (
        "help_desk",
        "Help desk",
        (
            r"help[\s-]*desk",
            r"service desk",
        ),
    ),
    (
        "it_support",
        "IT support",
        (
            r"\bit support\b",
            r"technical support",
            r"tech support",
            r"desktop support",
            r"\bit technician\b",
            r"support technician",
        ),
    ),
    (
        "sysadmin",
        "Sysadmin",
        (
            r"sys[\s-]*admin",
            r"system(?:s)? administrator",
            r"system(?:s)? admin\b",
            r"linux admin",
            r"windows admin",
        ),
    ),
    (
        "network",
        "Network",
        (
            r"\bnetwork\b",
            r"\bnetadmin\b",
        ),
    ),
    (
        "software",
        "Software",
        (
            r"\bsoftware\b",
            r"\bswe\b",
            r"\bsde\b",
            r"\bdeveloper\b",
            r"\bprogrammer\b",
            r"full[\s-]*stack",
            r"front[\s-]*end",
            r"back[\s-]*end",
        ),
    ),
)

ROLE_GROUPS: tuple[tuple[str, str, tuple[re.Pattern[str], ...]], ...] = tuple(
    (group_id, label, tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns))
    for group_id, label, patterns in _GROUP_SPECS
)

OTHER_ID = "other"
OTHER_LABEL = "Other"


def classify_position(position: str | None) -> str:
    """Return the group id for a stored position, or ``other``."""
    text = (position or "").strip()
    if not text:
        return OTHER_ID
    for group_id, _label, patterns in ROLE_GROUPS:
        if any(pattern.search(text) for pattern in patterns):
            return group_id
    return OTHER_ID


def group_positions(positions: list[str]) -> list[dict]:
    """Count stored positions by group, keeping the original title strings.

    Every named group is returned, including those with zero applications.
    ``other`` is included so unmatched titles stay visible. The sum of
    ``applications`` equals ``len(positions)``.
    """
    titles: dict[str, dict[str, int]] = {
        group_id: defaultdict(int) for group_id, _, _ in ROLE_GROUPS
    }
    titles[OTHER_ID] = defaultdict(int)
    for position in positions:
        stored = position if position is not None else ""
        titles[classify_position(stored)][stored] += 1

    groups: list[tuple[str, str]] = [(group_id, label) for group_id, label, _ in ROLE_GROUPS]
    groups.append((OTHER_ID, OTHER_LABEL))
    payload = []
    for group_id, label in groups:
        bucket = titles[group_id]
        ranked = sorted(bucket.items(), key=lambda item: (-item[1], item[0].casefold()))
        payload.append(
            {
                "id": group_id,
                "label": label,
                "applications": sum(bucket.values()),
                "titles": [{"title": title, "applications": count} for title, count in ranked],
            }
        )
    return payload
