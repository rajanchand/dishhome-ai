import { useState, type FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ApiError } from "../lib/api";
import { Button, Input } from "../components/ui";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("dishhome123");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(username, password);
      const from = (loc.state as { from?: string } | null)?.from ?? "/";
      nav(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-dishhome-mist">
      <div className="hidden lg:flex flex-col justify-between bg-dishhome-blue text-white p-12">
        <div className="flex items-center gap-3">
          <span className="inline-block w-3 h-3 rounded-full bg-dishhome-orange" />
          <div className="font-semibold text-lg">DishHome AI Call Center</div>
        </div>
        <div>
          <h1 className="text-4xl font-bold leading-tight">
            One platform.<br />
            Every customer call.<br />
            <span className="text-dishhome-orange">Resolved.</span>
          </h1>
          <p className="mt-6 text-white/70 max-w-md leading-relaxed">
            AI agents handle router diagnostics, billing, and ticket dispatch
            in Nepali and English — with seamless human handoff when needed.
          </p>
          <div className="mt-10 grid grid-cols-3 gap-6 max-w-md">
            <Stat n="50+" l="B2B clients" />
            <Stat n="10M" l="Interactions" />
            <Stat n="<1.2s" l="Turn latency" />
          </div>
        </div>
        <div className="text-xs text-white/40">
          © Dish Media Network · {new Date().getFullYear()}
        </div>
      </div>

      <div className="flex items-center justify-center p-8">
        <form
          onSubmit={onSubmit}
          className="w-full max-w-sm rounded-2xl bg-white border border-black/5 shadow-sm p-8"
        >
          <h2 className="text-xl font-semibold text-dishhome-blue">
            Sign in to portal
          </h2>
          <p className="text-sm text-dishhome-ink/60 mt-1">
            Agent, supervisor, and admin access.
          </p>

          <div className="mt-6 space-y-4">
            <Input
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              autoComplete="username"
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div className="mt-4 text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-md px-3 py-2">
              {error}
            </div>
          )}

          <Button type="submit" disabled={busy} className="w-full mt-6">
            {busy ? "Signing in..." : "Sign in"}
          </Button>

          <div className="mt-6 text-xs text-dishhome-ink/50 border-t border-black/5 pt-4">
            <div className="font-semibold uppercase tracking-widest mb-2">
              Demo credentials
            </div>
            <ul className="space-y-1">
              <li><code className="text-dishhome-blue">admin</code> / dishhome123 — Super admin</li>
              <li><code className="text-dishhome-blue">supervisor</code> / dishhome123 — Supervisor</li>
              <li><code className="text-dishhome-blue">agent</code> / dishhome123 — Agent</li>
            </ul>
          </div>
        </form>
      </div>
    </div>
  );
}

function Stat({ n, l }: { n: string; l: string }) {
  return (
    <div>
      <div className="text-2xl font-bold text-dishhome-orange">{n}</div>
      <div className="text-[11px] uppercase tracking-widest text-white/60 mt-1">
        {l}
      </div>
    </div>
  );
}
