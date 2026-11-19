"""Compare a posting to the editable qualification profile.

Fit is computed here so the cards stay aligned with the profile the user
can edit. The xAI finder may also return a fit label; the API does not use it.
"""

from __future__ import annotations

import re

FIT_MET = "met"
FIT_PARTIAL = "partial"
FIT_GAP = "gap"

_SPLIT = re.compile(r"[,;\n]+")


def normalize_label(value: str | None) -> str:
    """Case-fold and collapse punctuation and whitespace to single spaces."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def role_key(company: str | None, title: str | None) -> tuple[str, str]:
    return normalize_label(company), normalize_label(title)


def _phrases(text: str | None) -> list[str]:
    phrases = []
    for part in _SPLIT.split(text or ""):
        phrase = normalize_label(part)
        if phrase:
            phrases.append(phrase)
    return phrases


def _contains_phrase(haystack: str, phrase: str) -> bool:
    if not phrase or not haystack:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])"
    return re.search(pattern, haystack) is not None


def summarize_fit(
    *,
    target_titles: str,
    skills: str,
    title: str,
    requirements: str,
) -> str:
    """Return met, partial, or gap.

    A title matches when one target phrase appears in the posting title.
    Skills match as whole phrases in the title or the requirements summary.
    met means every signal the profile actually lists is fully met.
    gap means the profile is empty or nothing matched.
    partial is everything between those.
    """
    targets = _phrases(target_titles)
    skill_list = _phrases(skills)
    title_norm = normalize_label(title)
    blob = f"{title_norm} {normalize_label(requirements)}".strip()

    title_hit = any(_contains_phrase(title_norm, target) for target in targets)
    skill_hits = sum(1 for skill in skill_list if _contains_phrase(blob, skill))

    title_level: str | None
    if targets:
        title_level = FIT_MET if title_hit else FIT_GAP
    else:
        title_level = None

    skills_level: str | None
    if skill_list:
        if skill_hits == len(skill_list):
            skills_level = FIT_MET
        elif skill_hits > 0:
            skills_level = FIT_PARTIAL
        else:
            skills_level = FIT_GAP
    else:
        skills_level = None

    levels = [level for level in (title_level, skills_level) if level is not None]
    if not levels:
        return FIT_GAP
    if all(level == FIT_MET for level in levels):
        return FIT_MET
    if all(level == FIT_GAP for level in levels):
        return FIT_GAP
    return FIT_PARTIAL
