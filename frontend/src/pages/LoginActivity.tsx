import { useCallback, useEffect, useState } from "react";
import {
  api,
  type ActiveSession,
  type LoginActivityResponse,
  type LoginEvent,
} from "../lib/api";
import {
  Badge,
  Button,
  Card,
  PageBody,
  PageHeader,
  StatCard,
} from "../components/ui";
import { Skeleton } from "../components/Skeleton";
import { useAsyncErrorToast, useToast } from "../components/Toast";
import { useAuth } from "../lib/auth";

const REFRESH_MS = 15_000;

export default function LoginActivity() {
  const [data, setData] = useState<LoginActivityResponse | null>(null);
  const [sessions, setSessions] = useState<ActiveSession[] | null>(null);
  const [filter, setFilter] = useState<"all" | "success" | "failure">("all");
  const errToast = useAsyncErrorToast();
  const toast = useToast();
  const { user: me } = useAuth();

  const canManage = me?.permissions?.includes("users.manage") ?? false;

  const refresh = useCallback(async () => {
    try {
      const [d, s] = await Promise.all([
        api.get<LoginActivityResponse>("/admin/login-activity?limit=200"),
        api.get<ActiveSession[]>("/admin/active-sessions"),
      ]);
      setData(d);
      setSessions(s);
    } catch (e) {
      errToast(e);
    }
  }, [errToast]);

  useEffect(() => {
    if (!canManage) return;
    refresh();
    const t = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(t);
  }, [canManage, refresh]);

  async function revoke(s: ActiveSession) {
    if (
      !confirm(
        `Revoke session for ${s.username} (${s.token_prefix}…)? They will be logged out immediately.`,
      )
    )
      return;
    try {
      await api.post(`/admin/active-sessions/${s.token_prefix}/revoke`);
      toast.success("Session revoked", `${s.username} (${s.token_prefix}…)`);
      refresh();
    } catch (e) {
      errToast(e);
    }
  }

  if (!canManage) {
    return (
      <>
        <PageHeader title="Login Activity" />
        <PageBody>
          <Card title="Forbidden">
            <p className="text-sm text-dishhome-ink/70">
              You need the <span className="font-mono">users.manage</span>
              {" "}permission to view login activity.
            </p>
          </Card>
        </PageBody>
      </>
    );
  }

  const events = data?.events ?? null;
  const filtered = events?.filter((e) =>
    filter === "all" ? true : e.result === filter,
  );

  return (
    <>
      <PageHeader
        title="Login Activity"
        subtitle="Who logged in from where. Refreshes every 15 s."
        actions={<Button variant="ghost" onClick={refresh}>↻ Refresh</Button>}
      />
      <PageBody>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <StatCard
            label="Active sessions"
            value={sessions?.length ?? "—"}
            accent="blue"
          />
          <StatCard
            label="Logins · 24h"
            value={data?.stats.logins_24h_success ?? "—"}
            accent="green"
          />
          <StatCard
            label="Failed · 24h"
            value={data?.stats.logins_24h_failure ?? "—"}
            accent="red"
          />
          <StatCard
            label="Unique IPs · 24h"
            value={data?.stats.unique_ips_24h ?? "—"}
            accent="orange"
          />
        </div>

        <Card
          title="Active sessions"
          actions={
            <span className="text-xs text-dishhome-ink/50">
              {sessions?.length ?? 0} live
            </span>
          }
        >
          {!sessions ? (
            <Skeleton className="h-24" />
          ) : sessions.length === 0 ? (
            <p className="text-sm text-dishhome-ink/60">No active sessions.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-xs uppercase tracking-widest text-dishhome-ink/60 border-b border-black/5">
                  <tr>
                    <th className="text-left py-2">User</th>
                    <th className="text-left">Device</th>
                    <th className="text-left">IP</th>
                    <th className="text-left">Location</th>
                    <th className="text-left">Signed in</th>
                    <th className="text-left">Last seen</th>
                    <th className="text-right pr-2">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s) => (
                    <tr key={s.token_prefix} className="border-b border-black/5">
                      <td className="py-2">
                        <div className="font-mono">{s.username}</div>
                        <div className="text-[10px] text-dishhome-ink/50 font-mono">
                          {s.token_prefix}…
                        </div>
                      </td>
                      <td>{s.device || "—"}</td>
                      <td className="font-mono text-xs">{s.last_ip || s.issued_ip || "—"}</td>
                      <td>
                        <GeoCell geo={s.geo} />
                      </td>
                      <td className="text-xs text-dishhome-ink/70">
                        {timeAgo(s.issued_at)}
                      </td>
                      <td className="text-xs text-dishhome-ink/70">
                        {timeAgo(s.last_seen)}
                      </td>
                      <td className="text-right pr-2">
                        <button
                          className="text-xs text-red-600 hover:underline"
                          onClick={() => revoke(s)}
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card
          title="Login events"
          className="mt-6"
          actions={
            <div className="flex gap-1">
              {(["all", "success", "failure"] as const).map((f) => (
                <button
                  key={f}
                  className={`text-xs px-2.5 py-1 rounded-full transition ${
                    filter === f
                      ? "bg-dishhome-blue text-white"
                      : "bg-dishhome-mist text-dishhome-ink/70 hover:bg-dishhome-blue/10"
                  }`}
                  onClick={() => setFilter(f)}
                >
                  {f}
                </button>
              ))}
            </div>
          }
        >
          {!filtered ? (
            <Skeleton className="h-40" />
          ) : filtered.length === 0 ? (
            <p className="text-sm text-dishhome-ink/60">No matching events.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-xs uppercase tracking-widest text-dishhome-ink/60 border-b border-black/5">
                  <tr>
                    <th className="text-left py-2">When</th>
                    <th className="text-left">User</th>
                    <th className="text-left">Result</th>
                    <th className="text-left">IP</th>
                    <th className="text-left">Device</th>
                    <th className="text-left">Location</th>
                    <th className="text-left">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((e, i) => (
                    <EventRow key={i} e={e} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </PageBody>
    </>
  );
}

function EventRow({ e }: { e: LoginEvent }) {
  return (
    <tr className="border-b border-black/5">
      <td className="py-2 text-xs whitespace-nowrap">
        <div className="text-dishhome-ink/80">{new Date(e.at * 1000).toLocaleTimeString()}</div>
        <div className="text-[10px] text-dishhome-ink/50">
          {new Date(e.at * 1000).toLocaleDateString()}
        </div>
      </td>
      <td className="font-mono">{e.username}</td>
      <td>
        <Badge tone={e.result === "success" ? "success" : "danger"}>{e.result}</Badge>
      </td>
      <td className="font-mono text-xs">{e.ip || "—"}</td>
      <td>{e.device}</td>
      <td>
        <GeoCell geo={e.geo} />
      </td>
      <td className="text-xs text-dishhome-ink/60">{e.reason || "—"}</td>
    </tr>
  );
}

function GeoCell({ geo }: { geo: { city: string; country: string; country_code: string } | null }) {
  if (!geo) return <span className="text-dishhome-ink/40">—</span>;
  const flag = countryFlag(geo.country_code);
  return (
    <span className="whitespace-nowrap">
      {flag && <span className="mr-1">{flag}</span>}
      {geo.city}{geo.country && geo.country !== "—" ? `, ${geo.country}` : ""}
    </span>
  );
}

function countryFlag(code: string): string {
  if (!code || code.length !== 2) return "";
  const A = 0x1f1e6;
  return String.fromCodePoint(
    A + code.toUpperCase().charCodeAt(0) - 65,
    A + code.toUpperCase().charCodeAt(1) - 65,
  );
}

function timeAgo(ts: number): string {
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
