-- PostgreSQL: add cursor column for UID-based incremental IMAP fetches.
-- Apply once per database.

ALTER TABLE worker_runs
ADD COLUMN IF NOT EXISTS last_processed_uid INTEGER;
