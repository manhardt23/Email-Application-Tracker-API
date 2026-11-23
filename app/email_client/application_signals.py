"""Rules for what counts as a job-application email.

The LLM still classifies anything :func:`should_classify` lets through.
These patterns only do two narrower jobs:

- Pass real application mail (confirmation, rejection, interview, offer,
  assessment) that the keyword gate used to drop.
- Override the model when the wording is unambiguous, and refuse job
  alerts and newsletters the model sometimes accepts.

Ordinary marketing stays out. A footer that says "apply now" does not
cancel a real confirmation or rejection.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.llm.base import EmailClassification
from app.llm.normalization import canonicalize_stage, clean_optional_text

logger = logging.getLogger(__name__)

# Sender domains that mostly send alerts. Real application mail from these
# still passes when the wording is an explicit lifecycle signal.
JOB_BOARD_DOMAINS = (
    "indeed.com",
    "indeedmail.com",
    "indeedemail.com",
    "indeedapply.com",
    "linkedin.com",
    "glassdoor.com",
    "glassdoormail.com",
    "ziprecruiter.com",
    "ziprecruiteremail.com",
    "monster.com",
    "careerbuilder.com",
    "dice.com",
    "simplyhired.com",
    "snagajob.com",
    "jobvite.com",
    "greenhouse.io",
    "greenhouse-mail.io",
    "lever.co",
    "workday.com",
    "myworkday.com",
    "myworkdayjobs.com",
    "icims.com",
    "smartrecruiters.com",
    "ashbyhq.com",
    "recruitee.com",
    "bamboohr.com",
    "successfactors.com",
    "taleo.net",
    "workable.com",
    "naukri.com",
    "shine.com",
)

_LIFECYCLE_STAGES = {"applied", "rejected", "interview", "offer", "assessment"}
_STAGE_RANK = {
    "other": 0,
    "applied": 1,
    "assessment": 2,
    "interview": 3,
    "offer": 4,
    "rejected": 5,
}

# Digests and marketing. These veto weak mentions ("you applied", "your
# interest") but not a direct confirmation, rejection, interview, or offer.
_DIGEST_PATTERNS = (
    r"\bnew jobs (?:for you|matching|available)\b",
    r"\b(?:job|jobs) (?:alert|alerts|digest|recommendations?)\b",
    r"\bjobs you might (?:like|be interested)\b",
    r"\brecommended jobs\b",
    r"\bsimilar (?:positions|jobs|roles)\b",
    r"\b(?:weekly|daily) (?:job )?digest\b",
    r"\bnewsletter\b",
    r"\blimited[- ]time offer\b",
    r"\bspecial offer\b",
    r"\b\d+% off\b",
    r"\bpeople you may know\b",
    r"\bconnection request\b",
    r"\bbased on your (?:application|profile|activity|search)\b",
    r"\bnew role available\b",
    r"\binterview with (?:our )?(?:ceo|founder|cto)\b",
    r"\bresume your (?:subscription|membership|trial)\b",
    r"\bwe(?:'re| are) hiring\b",
    r"\bjoin our team\b",
    r"\bapply now\b",
    r"\bnew (?:job )?openings?\b",
    r"\bopen positions?\b",
    r"\bcareer opportunities\b",
    r"\blooking for (?:an? )?(?:software )?engineers?\b",
)

_REJECT_ALWAYS = (
    r"\bregret to inform\b",
    r"\bwe regret\b.{0,40}\b(?:to inform|that we)\b",
    r"\b(?:pursue|pursuing) other candidates\b",
    r"\bmoving forward with other candidates\b",
    r"\byou were not selected\b",
    r"\bnot selected for (?:the |this )?(?:role|position|job|application)\b",
    r"\bnot (?:be )?moving forward with your (?:application|candidacy)\b",
    r"\b(?:will not|won't|wont) be proceeding with your application\b",
    r"\bapplication (?:was|has been) (?:unsuccessful|rejected|declined)\b",
    r"\b(?:have )?decided to (?:pursue|go with|move forward with) "
    r"(?:other|another) (?:candidates|applicants)\b",
    r"\b(?:chosen|chose) (?:to )?(?:move forward with|pursue) "
    r"(?:another|other) (?:candidates|applicants)\b",
    r"\bthe position you applied for has been filled\b",
    r"\bunfortunately\b.{0,80}\bnot (?:be )?moving forward\b",
    r"\b(?:will not|won't|wont) be moving forward\b",
)

# Needs a job word, and a digest/newsletter vetoes these. Bare "not selected"
# or "position has been filled" shows up in career advice and closed-role alerts.
_REJECT_WITH_CONTEXT = (
    r"\bnot (?:be )?moving forward\b",
    r"\b(?:will not|won't|wont) be (?:proceeding|progressing)\b",
    r"\bdecid(?:ed|ing) not to (?:move forward|proceed|continue)\b",
    r"\bnot selected\b",
    r"\bno longer (?:being )?considered\b",
    r"\bposition has been filled\b",
    r"\bafter careful (?:consideration|review)\b.{0,80}\b(?:not|unable|decline|regret)\b",
)

_OFFER = (
    r"\boffer of employment\b",
    r"\boffer letter\b",
    r"\bjob offer\b",
    r"\b(?:extend|extending) (?:you )?an offer\b",
    r"\b(?:pleased|happy|excited) to (?:extend|make) (?:you )?an offer\b",
    r"\bverbal offer\b",
    r"\bwritten offer\b",
    r"\boffer for the (?:role|position)\b",
    r"\bcongratulations\b.{0,80}\b"
    r"(?:an offer|your offer|the offer|offer of|offer letter|job offer)\b",
)

_ASSESSMENT = (
    r"\bcoding (?:challenge|assessment|test|exercise)\b",
    r"\btake[- ]home (?:assignment|assessment|test|exercise|project)\b",
    r"\b(?:online|skills|technical) assessment\b",
    r"\bcomplete (?:the |this |your )?(?:assessment|coding challenge|technical assessment)\b",
    r"\b(?:hackerrank|codility|codesignal|testgorilla) (?:assessment|test|challenge|invitation)\b",
    r"\binvit\w* (?:you )?to (?:take|complete)\b.{0,50}\b"
    r"(?:assessment|challenge|hackerrank|codility)\b",
)

_INTERVIEW = (
    r"\binterview invitation\b",
    r"\binvitation to interview\b",
    r"\binvit\w* you to (?:an |a )?(?:(?:phone|video|virtual|onsite|on-site) )?interview\b",
    r"\b(?:please )?(?:schedule|book|confirm) your interview\b",
    r"\byour interview (?:is |has been )?(?:confirmed|scheduled)\b",
    r"\bconfirm(?:ing)? your interview\b",
    r"\byour interview\b",
    r"\b(?:phone|video|virtual|onsite|on-site) interview\b",
    r"\bwe(?:'d| would) like to (?:schedule|set up|arrange|invite you to) "
    r"(?:an |a )?(?:phone screen|interview)\b",
    r"\b(?:schedule|book|invite|invitation|confirm)(?:\w+)?\b.{0,40}\bphone screen\b",
    r"\bphone screen\b.{0,40}\b(?:schedule|invite|invitation|with|for the)\b",
    r"\bnext round of interviews?\b",
    r"\b(?:complete|initiate|start|your) (?:a |the |your )?background check\b",
)

_APPLIED_STRONG = (
    r"\bthank you for applying\b",
    r"\bthanks for applying\b",
    r"\bthank you for your application\b",
    r"\bthanks for your application\b",
    r"\bwe(?:'ve| have)? received your (?:application|resume|cv)\b",
    r"\byour application (?:has been|was|is) (?:successfully )?"
    r"(?:received|submitted|sent|under review|being reviewed)\b",
    r"\bapplication (?:has been|was) (?:successfully )?(?:received|submitted|sent)\b",
    r"\byour application was sent\b",
    r"\bapplication (?:received|submitted|confirmation)\b",
    r"\bconfirm(?:ing|ation of) (?:your |the )?application\b",
    r"\b(?:status of|update on|regarding) your application\b",
    r"\bapplication status\b",
    r"\bviewed your application\b",
    r"\bfollowing up on your application\b",
    r"\b(?:status of|update on|regarding) your candidacy\b",
    r"\byour candidacy (?:for|at|with)\b",
)

# Real when the message is about the recipient, not a job digest.
_APPLIED_WEAK = (
    r"\byou applied to\b",
    r"\bthank you for your interest in\b.{0,80}\b(?:role|position|team|opportunity)\b",
    r"\b(?:complete|finish) your application\b",
    r"\bapplication (?:is )?incomplete\b",
)

_KEYWORD_PATTERNS = (
    r"\bapplications?\b",
    r"\bapplied\b",
    r"\bapplying\b",
    r"\binterviews?\b",
    r"\bassessments?\b",
    r"\bcandidates?\b",
    r"\bcandidacy\b",
    r"\bresume\b",
    r"\bcv\b",
    r"\bphone screen\b",
    r"\byour application\b",
    r"\bnext steps\b",
    r"\boffer letter\b",
    r"\bjob offer\b",
    r"\boffer of employment\b",
)

_JOB_CONTEXT = re.compile(
    r"\b(applications?|applied|applying|candidac(?:y|ies)|candidates?|"
    r"interviews?|roles?|positions?|resumes?|cv|hiring|recruiter|employment|job)\b"
)

_DIGEST_RE = tuple(re.compile(p) for p in _DIGEST_PATTERNS)
_REJECT_ALWAYS_RE = tuple(re.compile(p) for p in _REJECT_ALWAYS)
_REJECT_CONTEXT_RE = tuple(re.compile(p) for p in _REJECT_WITH_CONTEXT)
_OFFER_RE = tuple(re.compile(p) for p in _OFFER)
_ASSESSMENT_RE = tuple(re.compile(p) for p in _ASSESSMENT)
_INTERVIEW_RE = tuple(re.compile(p) for p in _INTERVIEW)
_APPLIED_STRONG_RE = tuple(re.compile(p) for p in _APPLIED_STRONG)
_APPLIED_WEAK_RE = tuple(re.compile(p) for p in _APPLIED_WEAK)
_KEYWORD_RE = tuple(re.compile(p) for p in _KEYWORD_PATTERNS)


@dataclass(frozen=True)
class SignalJudgment:
    """``application`` forces a lifecycle email. ``maybe`` goes to the LLM.
    ``skip`` is a newsletter, alert, or message with nothing to classify."""

    disposition: str
    stage: str | None = None


def combined_text(subject: str | None, body: str | None) -> str:
    raw = f"{subject or ''} {body or ''}"
    raw = (
        raw.replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("`", "'")
    )
    return re.sub(r"\s+", " ", raw).strip().lower()


def _sender_domain(sender: str | None) -> str | None:
    match = re.search(r"@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", sender or "")
    return match.group(1).lower() if match else None


def is_job_board_sender(sender: str | None) -> bool:
    domain = _sender_domain(sender)
    if not domain:
        return False
    return any(domain == known or domain.endswith("." + known) for known in JOB_BOARD_DOMAINS)


def _matches(patterns: tuple[re.Pattern[str], ...], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def is_digest_or_newsletter(text: str) -> bool:
    return _matches(_DIGEST_RE, text)


def infer_stage_from_text(text: str) -> str | None:
    """Return a lifecycle stage when the wording is explicit, else None."""
    digest = is_digest_or_newsletter(text)
    if _matches(_REJECT_ALWAYS_RE, text):
        return "rejected"
    if (
        not digest
        and _JOB_CONTEXT.search(text) is not None
        and _matches(_REJECT_CONTEXT_RE, text)
    ):
        return "rejected"
    if _matches(_OFFER_RE, text):
        return "offer"
    if _matches(_ASSESSMENT_RE, text):
        return "assessment"
    if _matches(_INTERVIEW_RE, text):
        return "interview"
    if _matches(_APPLIED_STRONG_RE, text):
        return "applied"
    if _matches(_APPLIED_WEAK_RE, text) and not digest:
        return "applied"
    return None


def infer_stage(subject: str | None, body: str | None) -> str | None:
    return infer_stage_from_text(combined_text(subject, body))


def _keyword_hits(text: str) -> int:
    return sum(1 for pattern in _KEYWORD_RE if pattern.search(text))


def judge_email(sender: str | None, subject: str | None, body: str | None) -> SignalJudgment:
    text = combined_text(subject, body)
    stage = infer_stage_from_text(text)
    if stage:
        return SignalJudgment("application", stage)
    if is_digest_or_newsletter(text):
        return SignalJudgment("skip")
    if is_job_board_sender(sender):
        # Alerts from Indeed/LinkedIn/ATS domains need explicit lifecycle wording.
        logger.debug("job board email from %s without application wording", _sender_domain(sender))
        return SignalJudgment("skip")
    if _keyword_hits(text) >= 2:
        return SignalJudgment("maybe")
    if re.search(r"\b(?:interview|assessment|phone screen)\b", text) and re.search(
        r"\b(?:schedule|invitation|invite|confirm|zoom|meet)\b", text
    ):
        return SignalJudgment("maybe")
    return SignalJudgment("skip")


def should_classify(sender: str | None, subject: str | None, body: str | None) -> bool:
    """True when the email is worth an LLM call (or already unambiguous)."""
    return judge_email(sender, subject, body).disposition != "skip"


def stage_rank(stage: str | None) -> int:
    if not stage:
        return 0
    return _STAGE_RANK.get(stage, 1)


def merge_stages(model_stage: str | None, text_stage: str | None) -> str | None:
    """Prefer the email's stage when it is further along, and always keep a rejection."""
    model = canonicalize_stage(model_stage)
    text = text_stage if text_stage in _LIFECYCLE_STAGES else None
    if text == "rejected" or model == "rejected":
        return "rejected"
    if text and model and text in _STAGE_RANK and model in _STAGE_RANK:
        return text if _STAGE_RANK[text] >= _STAGE_RANK[model] else model
    return text or model


def reconcile_classification(
    sender: str | None,
    subject: str | None,
    body: str | None,
    result: EmailClassification | None,
) -> EmailClassification | None:
    """Correct unambiguous false negatives and newsletter false positives."""
    judgment = judge_email(sender, subject, body)
    if result is None:
        if judgment.disposition != "application":
            return None
        return EmailClassification(
            is_application=True,
            stage=judgment.stage,
            confidence="medium",
        )

    company = clean_optional_text(result.company)
    position = clean_optional_text(result.position)
    model_stage = canonicalize_stage(result.stage)
    stage = merge_stages(model_stage, judgment.stage)

    if judgment.disposition == "application":
        confidence = result.confidence if result.is_application else "medium"
        if confidence not in {"high", "medium", "low"}:
            confidence = "medium"
        return EmailClassification(
            is_application=True,
            company=company,
            position=position,
            stage=stage or judgment.stage,
            confidence=confidence,
        )

    if judgment.disposition == "skip" and result.is_application:
        return EmailClassification(
            is_application=False,
            company=company,
            position=position,
            stage=None,
            confidence="low",
        )

    if (
        not result.is_application
        and model_stage in _LIFECYCLE_STAGES
        and judgment.disposition == "maybe"
    ):
        # The model named a real stage and then said it was not an application.
        return EmailClassification(
            is_application=True,
            company=company,
            position=position,
            stage=model_stage,
            confidence="medium",
        )

    return EmailClassification(
        is_application=bool(result.is_application),
        company=company,
        position=position,
        stage=stage if result.is_application else model_stage,
        confidence=result.confidence or "low",
    )
