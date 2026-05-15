import { Link } from "react-router-dom";

export function ForbiddenPage() {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-semibold text-slate-900">Forbidden</h1>
      <p className="mt-2 text-sm text-slate-600">
        You do not have permission to view this page. Sign in with an admin account to access
        Applications.
      </p>
      <div className="mt-4">
        <Link
          to="/"
          className="inline-flex rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          Back to Dashboard
        </Link>
      </div>
    </section>
  );
}
