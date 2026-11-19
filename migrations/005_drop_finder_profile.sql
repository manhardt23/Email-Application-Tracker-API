-- Phase 40: stop storing the job-finder profile.
-- A dismissed suggestion stays in the table so a later search does not
-- put it back on the list. Dismiss does not create an application.
DROP TABLE IF EXISTS qualification_profiles;

ALTER TABLE job_suggestions
    ADD COLUMN IF NOT EXISTS dismissed BOOLEAN NOT NULL DEFAULT FALSE;
