/**
 * API response shapes — mirror the FastAPI backend (app/api/v1/*).
 * Kept hand-written and minimal; only fields the UI consumes.
 */

export type AuthMe = {
  username: string;
  role: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type HealthResponse = {
  status: string;
};

// --- Dashboard ---

export type DashboardMetrics = {
  total_applications: number;
  responses_received: number;
  interviews_scheduled: number;
  response_rate: number;
};

export type ApplicationsOverTimePoint = {
  day: string;
  label: string;
  applications: number;
};

export type StatusBreakdownSlice = {
  name: string;
  value: number;
};

export type RecentApplication = {
  company: string;
  role: string;
  status: string;
  date_applied: string;
};

export type TopCompany = {
  company: string;
  applications: number;
};

// --- Applications ---

export type Company = {
  id: number;
  name: string;
  domain?: string | null;
};

export type Application = {
  id: number;
  company_id: number;
  position: string;
  stage: string;
  applied_date: string;
  last_updated: string;
  notes?: string | null;
  company?: Company | null;
};

export type ApplicationUpdate = {
  stage?: string;
  notes?: string | null;
  company_name?: string;
  position?: string;
};

// --- Emails ---

export type EmailRow = {
  id: number;
  message_id: string | null;
  uid: string;
  sender: string;
  subject: string | null;
  received_date: string;
  created_at: string;
  is_application: boolean | null;
  detected_company: string | null;
  detected_position: string | null;
  detected_stage: string | null;
  confidence: string | null;
  needs_review: boolean | null;
  application_id?: number | null;
};

export type PromoteRequest = {
  company_name?: string;
  position?: string;
  stage?: string;
};

export type PromoteResponse = {
  email_id: number;
  application_id: number;
  created: boolean;
  company_name: string;
  position: string;
  stage: string;
};

// --- Jobs / stats ---

export type JobTriggerResponse = {
  job_id: string;
  status: string;
};

export type JobStatus = {
  job_id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  emails_fetched: number;
  emails_saved: number;
  applications_found: number;
  error_message: string | null;
};

export type SystemStats = {
  total_emails_processed: number;
  job_related_emails: number;
  worker_last_ran_at: string | null;
  worker_run_count_7d: number;
};

export type WorkerLimitResponse = {
  max_emails_per_run: number;
  source: string;
};
