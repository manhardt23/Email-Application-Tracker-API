import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { useLogin } from "../hooks/useAuth";
import { getValidToken } from "../lib/auth";
import { errorMessage } from "../lib/format";

export function Login() {
  const navigate = useNavigate();
  const login = useLogin();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  if (getValidToken()) {
    return <Navigate to="/" replace />;
  }

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    login.mutate(
      { username, password },
      { onSuccess: () => navigate("/", { replace: true }) },
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-page p-4">
      <div className="w-full max-w-[340px] rounded-[10px] border border-line bg-surface p-6">
        <div className="mb-6 flex items-center gap-2.5">
          <div
            className="flex size-[26px] items-center justify-center rounded-[5px] border-[1.5px] border-text text-[13px] font-bold text-text"
            aria-hidden
          >
            A
          </div>
          <div className="leading-tight">
            <div className="text-[14px] font-semibold text-text">App Tracker</div>
            <div className="font-mono text-[11px] text-text-3">Email Application Tracker</div>
          </div>
        </div>

        <h1 className="text-[18px] font-semibold text-text">Sign in</h1>
        <p className="mt-1 text-[12px] text-text-3">
          Authenticate to view your application pipeline.
        </p>

        <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
          {login.isError ? (
            <p
              role="alert"
              className="rounded-md border px-3 py-2 text-[12px]"
              style={{
                color: "var(--color-danger-fg)",
                backgroundColor: "var(--color-danger-bg)",
                borderColor: "var(--color-danger-border)",
              }}
            >
              {errorMessage(login.error, "Incorrect username or password.")}
            </p>
          ) : null}

          <label className="block">
            <span className="mb-1 block text-[12px] font-medium text-text-2">Username</span>
            <Input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              autoFocus
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-[12px] font-medium text-text-2">Password</span>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </label>

          <Button
            type="submit"
            variant="primary"
            loading={login.isPending}
            className="w-full"
          >
            {login.isPending ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </main>
  );
}
