import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { setToken } from "../lib/auth";
import { authApi } from "../lib/api";

export function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const body = new URLSearchParams({
        username,
        password,
      });
      const response = await authApi.post("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      const token = response.data.access_token as string | undefined;
      if (!token) {
        throw new Error("Token missing in login response");
      }
      setToken(token);
      navigate("/", { replace: true });
    } catch {
      setError("Login failed. Check your credentials and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-[70vh] items-center justify-center p-4">
      <section className="grid w-full max-w-5xl overflow-hidden rounded-2xl border border-slate-200/80 bg-white/95 shadow-lg ring-1 ring-white md:grid-cols-2">
        <div className="bg-gradient-to-br from-indigo-600 to-teal-600 p-7 text-white">
          <p className="text-xs font-semibold uppercase tracking-wider text-indigo-100">
            Showcase project
          </p>
          <h1 className="mt-3 text-3xl font-semibold leading-tight">Email Application Tracker</h1>
          <p className="mt-3 text-sm leading-6 text-indigo-50">
            Built to transform inbox updates into a clean application pipeline with stage tracking, role-based
            access, and auditable job processing metrics.
          </p>
          <div className="mt-6 rounded-lg bg-white/10 p-4 text-sm leading-6 text-indigo-50">
            <p className="font-medium text-white">Privacy first access model</p>
            <p className="mt-1">
              Insights are intentionally scoped. Sensitive job-search and email data stays protected while demo
              users get a safe preview of platform capabilities.
            </p>
          </div>
        </div>

        <div className="p-7">
          <h2 className="text-2xl font-semibold text-slate-900">Sign in</h2>
          <p className="mt-2 text-sm text-slate-600">
            Authenticate to view dashboard metrics and protected application data.
          </p>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">Username</span>
              <input
                className="w-full rounded-md border border-slate-300 px-3 py-2 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-sm font-medium text-slate-700">Password</span>
              <input
                className="w-full rounded-md border border-slate-300 px-3 py-2 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </label>

            {error ? <p className="text-sm text-red-600">{error}</p> : null}

            <button
              className="w-full rounded-md bg-gradient-to-r from-indigo-600 to-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:opacity-95 disabled:opacity-60"
              type="submit"
              disabled={submitting}
            >
              {submitting ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}
