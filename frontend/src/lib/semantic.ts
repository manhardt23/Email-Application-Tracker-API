/**
 * Status + classification token maps (from design.json `semantic`).
 * Keyed to the REAL backend stage values: applied, interview, assessment,
 * offer, rejected, other. Dashboard endpoints return capitalized variants,
 * so everything is normalized to lowercase first.
 */
import type { EmailRow } from "../types/api";

export type Swatch = { label: string; fg: string; bg: string; border: string };

const STATUS: Record<string, Swatch> = {
  applied: { label: "Applied", fg: "#57534e", bg: "#f5f5f4", border: "#d6d3d1" },
  screening: { label: "Screening", fg: "#1d4ed8", bg: "#eff4ff", border: "#bfdbfe" },
  interview: { label: "Interview", fg: "#4338ca", bg: "#eef2ff", border: "#c7d2fe" },
  assessment: { label: "Assessment", fg: "#4338ca", bg: "#eef2ff", border: "#c7d2fe" },
  offer: { label: "Offer", fg: "#15803d", bg: "#eefcf2", border: "#bbf7d0" },
  rejected: { label: "Rejected", fg: "#b91c1c", bg: "#fef2f2", border: "#fecaca" },
  other: { label: "Other", fg: "#8a8580", bg: "#fafaf9", border: "#e7e5e4" },
  no_response: { label: "No response", fg: "#8a8580", bg: "#fafaf9", border: "#e7e5e4" },
};

export const STAGE_OPTIONS = [
  "applied",
  "interview",
  "assessment",
  "offer",
  "rejected",
  "other",
] as const;

export function statusSwatch(stage: string | null | undefined): Swatch {
  const key = (stage ?? "other").toLowerCase();
  return STATUS[key] ?? STATUS.other;
}

const CLASSIFICATION: Record<string, Omit<Swatch, "border">> = {
  interview_invite: { label: "Interview invite", fg: "#15803d", bg: "#eefcf2" },
  acknowledgement: { label: "Acknowledgement", fg: "#1d4ed8", bg: "#eff4ff" },
  offer: { label: "Offer", fg: "#15803d", bg: "#eefcf2" },
  rejection: { label: "Rejection", fg: "#b91c1c", bg: "#fef2f2" },
  needs_review: { label: "Needs review", fg: "#b45309", bg: "#fff7ea" },
  not_relevant: { label: "Not relevant", fg: "#8a8580", bg: "#fafaf9" },
  unprocessed: { label: "Unprocessed", fg: "#8a8580", bg: "#fafaf9" },
};

/** Map a free-text stage onto the labels the emails list filters on. */
export function canonicalStage(stage: string | null | undefined): string | null {
  const value = (stage ?? "").trim().toLowerCase();
  if (!value || value === "null" || value === "none" || value === "n/a") return null;
  if (["applied", "rejected", "interview", "offer", "assessment", "other"].includes(value)) {
    return value;
  }
  if (/reject|declin|not selected|not moving forward|unsuccessful|other candidates/.test(value)) {
    return "rejected";
  }
  if (/\boffer\b/.test(value)) return "offer";
  if (/assess|take-home|take home|coding challenge|hackerrank|codility/.test(value)) {
    return "assessment";
  }
  if (/interview|phone screen|on-?site|screening/.test(value)) return "interview";
  if (/\bappl|\breceived\b|\bsubmitted\b|under review/.test(value)) return "applied";
  return null;
}

/**
 * Stage implied by a subject line. The promote form cannot see the body;
 * the API still reads the stored body and replaces a default "applied".
 */
export function inferStageFromText(text: string | null | undefined): string | null {
  const value = (text ?? "").toLowerCase();
  if (!value.trim()) return null;
  if (
    /regret to inform|not moving forward|other candidates|not selected|position has been filled|no longer considered/.test(
      value,
    )
  ) {
    return "rejected";
  }
  if (/offer letter|offer of employment|job offer|extend an offer|pleased to extend/.test(value)) {
    return "offer";
  }
  if (/coding challenge|take-home|technical assessment|online assessment/.test(value)) {
    return "assessment";
  }
  if (
    /interview invitation|invitation to interview|phone screen|your interview|onsite interview|on-site interview/.test(
      value,
    )
  ) {
    return "interview";
  }
  if (
    /thank you for applying|thanks for applying|thank you for your application|received your application|application was sent|you applied to|application received|application status/.test(
      value,
    )
  ) {
    return "applied";
  }
  return null;
}

/** Derive a classification tag for an email from its analysis fields. */
export function classifyEmail(email: EmailRow): Omit<Swatch, "border"> {
  if (email.is_application === null || email.is_application === undefined) {
    return CLASSIFICATION.unprocessed;
  }
  if (email.needs_review) return CLASSIFICATION.needs_review;
  if (email.is_application === false) return CLASSIFICATION.not_relevant;
  const stage = canonicalStage(email.detected_stage) ?? "";
  if (stage === "interview" || stage === "assessment") return CLASSIFICATION.interview_invite;
  if (stage === "offer") return CLASSIFICATION.offer;
  if (stage === "rejected") return CLASSIFICATION.rejection;
  return CLASSIFICATION.acknowledgement;
}
