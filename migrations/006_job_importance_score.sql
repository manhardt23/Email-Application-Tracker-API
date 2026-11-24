-- Phase 49: assistant-set importance score on job suggestions.
-- Null means the suggestion has not been scored. 0 is a real low score.
-- The application does not calculate this value.
ALTER TABLE job_suggestions
    ADD COLUMN IF NOT EXISTS importance_score INTEGER;
