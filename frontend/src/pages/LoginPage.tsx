import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { errorMessage } from "../components/ui/ErrorState";
import { LoadingState } from "../components/ui/LoadingState";
import { useAuth } from "../auth/AuthProvider";

type LocationState = {
  from?: {
    pathname?: string;
  };
};

export function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (auth.loading) {
    return <LoadingState label="Checking login..." />;
  }

  if (!auth.authEnabled || auth.authenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await auth.login(username, password);
      const state = location.state as LocationState | null;
      navigate(state?.from?.pathname ?? "/dashboard", { replace: true });
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-panel">
        <p className="eyebrow">Trading Lab</p>
        <h1>Sign in</h1>
        <p className="muted">
          This deployment is restricted to one configured account.
        </p>
        <form className="login-form" onSubmit={onSubmit}>
          <label>
            Username
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {error && <p className="inline-error">{error}</p>}
          <button className="button-primary" disabled={submitting} type="submit">
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
