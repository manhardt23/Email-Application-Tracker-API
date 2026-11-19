-- Phase 34: job finder suggestions and the qualification profile.
-- Fresh databases also get these tables from SQLAlchemy create_all on startup.
CREATE TABLE IF NOT EXISTS qualification_profiles (
    id SERIAL PRIMARY KEY,
    target_titles TEXT NOT NULL DEFAULT '',
    skills TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_suggestions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    pay VARCHAR(255),
    requirements_summary TEXT NOT NULL DEFAULT '',
    apply_url VARCHAR(2000) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_job_suggestions_company_name ON job_suggestions (company_name);
