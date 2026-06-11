-- Phase 31: follow-up tracking columns on applications
ALTER TABLE applications ADD COLUMN IF NOT EXISTS last_contact_at TIMESTAMPTZ;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS follow_up_status VARCHAR(20) NOT NULL DEFAULT 'open';
ALTER TABLE applications ADD COLUMN IF NOT EXISTS snoozed_until DATE;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS next_event_at TIMESTAMPTZ;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS contact_name TEXT;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS contact_title TEXT;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS contact_linkedin_url TEXT;

-- Backfill last_contact_at from applied_date and linked emails
UPDATE applications a
SET last_contact_at = GREATEST(
    a.applied_date,
    COALESCE(
        (
            SELECT MAX(e.received_date)
            FROM email_analyses ea
            JOIN emails e ON e.id = ea.email_id
            WHERE ea.application_id = a.id
        ),
        a.applied_date
    )
)
WHERE a.last_contact_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_applications_follow_up_active
    ON applications (follow_up_status, last_contact_at)
    WHERE stage IN ('applied', 'screening', 'interview');
