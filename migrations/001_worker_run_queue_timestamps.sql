-- PostgreSQL: align worker_runs with ORM (started_at NULL until claimed; queued_at set at enqueue).
-- Apply once per database. SQLite dev/test rely on SQLAlchemy create_all instead.

ALTER TABLE worker_runs ADD COLUMN IF NOT EXISTS queued_at TIMESTAMPTZ;

UPDATE worker_runs
SET queued_at = COALESCE(started_at, now())
WHERE queued_at IS NULL;

ALTER TABLE worker_runs ALTER COLUMN queued_at SET DEFAULT now();
ALTER TABLE worker_runs ALTER COLUMN queued_at SET NOT NULL;

ALTER TABLE worker_runs ALTER COLUMN started_at DROP NOT NULL;

UPDATE worker_runs SET started_at = NULL WHERE status = 'queued';
