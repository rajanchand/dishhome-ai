import { useCallback, useEffect, useState } from "react";
import {
  api,
  type ActiveSession,
  type LoginActivityResponse,
  type LoginEvent,
  type AdminUser,
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
  const [users, setUsers] = useState<AdminUser[] | null>(null);
  const [filter, setFilter] = useState<"all" | "success" | "failure">("all");
  const errToast = useAsyncErrorToast();
  const toast = useToast();
  const { user: me } = useAuth();

  const isSuperAdmin = me?.role === "super_admin";

  const refresh = useCallback(async () => {
    try {
      const [d, s, u] = await Promise.all([
        api.get<LoginActivityResponse>("/admin/login-activity?limit=200"),
        api.get<ActiveSession[]>("/admin/active-sessions"),
        api.get<AdminUser[]>("/admin/users"),
      ]);
      setData(d);
      setSessions(s);
      setUsers(u);
    } catch (e) {
      errToast(e);
    }
  }, [errToast]);

  useEffect(() => {
    if (!isSuperAdmin) return;
    refresh();
    const t = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(t);
  }, [isSuperAdmin, refresh]);

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

  if (!isSuperAdmin) {
    return (
      <>
        <PageHeader title="Login Activity" />
        <PageBody>
          <Card title="Access Denied" className="border-l-4 border-dishhome-orange">
            <p className="text-sm text-dishhome-ink/70">
              Only a <span className="font-semibold text-dishhome-orange">super_admin</span> has permissions to view login activity records, operator status, and system active sessions.
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
        title="Security & Login Activity"
        subtitle="Live operator directory, active sessions, and detailed authentication logs."
        actions={<Button variant="ghost" onClick={refresh}>↻ Refresh</Button>}
      />
      <PageBody>
        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            label="Active Sessions"
            value={sessions?.length ?? "—"}
            accent="blue"
          />
          <StatCard
            label="Logins · 24h"
            value={data?.stats.logins_24h_success ?? "—"}
            accent="green"
          />
          <StatCard
            label="Failed attempts · 24h"
            value={data?.stats.logins_24h_failure ?? "—"}
            accent="red"
          />
          <StatCard
            label="Unique IPs · 24h"
            value={data?.stats.unique_ips_24h ?? "—"}
            accent="orange"
          />
        </div>

        {/* System Operators Last Login Directory */}
        <Card
          title="System Operators Directory & Last Login"
          className="mb-6"
          actions={
            <span className="text-xs text-dishhome-ink/50">
              {users?.length ?? 0} operators registered
            </span>
          }
        >
          {!users ? (
            <Skeleton className="h-40" />
          ) : users.length === 0 ? (
            <p className="text-sm text-dishhome-ink/60">No operators registered.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-xs uppercase tracking-widest text-dishhome-ink/60 border-b border-black/5">
                  <tr>
                    <th className="text-left py-3 px-2">Operator</th>
                    <th className="text-left">Role</th>
                    <th className="text-left">Last login time</th>
                    <th className="text-left">Last Login IP</th>
                    <th className="text-left">Last Login Location</th>
                    <th className="text-left">Last Device / User Agent</th>
                    <th className="text-center pr-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const isSessionActive = sessions?.some((s) => s.username === u.username);
                    const roleTone: "danger" | "warn" | "info" | "success" =
                      u.role === "super_admin"
                        ? "danger"
                        : u.role === "admin"
                        ? "warn"
                        : u.role === "supervisor"
                        ? "info"
                        : "success";
                    return (
                      <tr key={u.username} className="border-b border-black/5 hover:bg-black/[0.01] transition-colors">
                        <td className="py-3 px-2">
                          <div className="font-semibold text-dishhome-ink">{u.name}</div>
                          <div className="text-xs text-dishhome-ink/50 font-mono">@{u.username}</div>
                        </td>
                        <td>
                          <Badge tone={roleTone}>{u.role}</Badge>
                        </td>
                        <td className="text-xs text-dishhome-ink/80">
                          {u.last_login_at ? (
                            <>
                              <div>{timeAgo(u.last_login_at)}</div>
                              <div className="text-[10px] text-dishhome-ink/40">
                                {new Date(u.last_login_at * 1000).toLocaleString()}
                              </div>
                            </>
                          ) : (
                            <span className="text-dishhome-ink/40 italic">Never logged in</span>
                          )}
                        </td>
                        <td className="font-mono text-xs text-dishhome-ink/75">
                          {u.last_login_ip || "—"}
                        </td>
                        <td>
                          {u.last_login_location ? (
                            <span className="whitespace-nowrap flex items-center gap-1">
                              <span>🇳🇵</span>
                              <span>{u.last_login_location}</span>
                            </span>
                          ) : u.last_login_ip ? (
                            <span className="text-dishhome-ink/40">—</span>
                          ) : (
                            <span className="text-dishhome-ink/30 italic">No history</span>
                          )}
                        </td>
                        <td className="text-xs text-dishhome-ink/70 max-w-xs truncate" title={u.last_login_device || ""}>
                          {u.last_login_device || "—"}
                        </td>
                        <td className="text-center pr-2">
                          {isSessionActive ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 animate-pulse">
                              Active Now
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                              Offline
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Active sessions */}
        <Card
          title="Active Sessions"
          actions={
            <span className="text-xs text-dishhome-ink/50">
              {sessions?.length ?? 0} active tokens
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
                    <th className="text-left py-2 px-2">User</th>
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
                    <tr key={s.token_prefix} className="border-b border-black/5 hover:bg-black/[0.01]">
                      <td className="py-2 px-2">
                        <div className="font-mono font-semibold">{s.username}</div>
                        <div className="text-[10px] text-dishhome-ink/50 font-mono">
                          {s.token_prefix}…
                        </div>
                      </td>
                      <td className="text-xs text-dishhome-ink/80">{s.device || "—"}</td>
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
                          className="text-xs text-red-600 hover:text-red-800 hover:underline font-medium"
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

        {/* Login events */}
        <Card
          title="Authentication Log"
          className="mt-6"
          actions={
            <div className="flex gap-1">
              {(["all", "success", "failure"] as const).map((f) => (
                <button
                  key={f}
                  className={`text-xs px-3 py-1 rounded-full font-medium transition ${
                    filter === f
                      ? "bg-dishhome-blue text-white"
                      : "bg-dishhome-mist text-dishhome-ink/70 hover:bg-dishhome-blue/10"
                  }`}
                  onClick={() => setFilter(f)}
                >
                  {f.toUpperCase()}
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
                    <th className="text-left py-3 px-2">When</th>
                    <th className="text-left">User</th>
                    <th className="text-left">Result</th>
                    <th className="text-left">IP Address</th>
                    <th className="text-left">Device</th>
                    <th className="text-left">Location</th>
                    <th className="text-left">Reason / Prefix</th>
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
    <tr className="border-b border-black/5 hover:bg-black/[0.01]">
      <td className="py-2.5 px-2 text-xs whitespace-nowrap">
        <div className="text-dishhome-ink/80 font-semibold">{new Date(e.at * 1000).toLocaleTimeString()}</div>
        <div className="text-[10px] text-dishhome-ink/50 font-mono">
          {new Date(e.at * 1000).toLocaleDateString()}
        </div>
      </td>
      <td className="font-mono font-semibold text-dishhome-ink/90">{e.username}</td>
      <td>
        <Badge tone={e.result === "success" ? "success" : "danger"}>{e.result}</Badge>
      </td>
      <td className="font-mono text-xs text-dishhome-ink/75">{e.ip || "—"}</td>
      <td className="text-xs text-dishhome-ink/75">{e.device}</td>
      <td>
        <GeoCell geo={e.geo} />
      </td>
      <td className="text-xs text-dishhome-ink/60">
        {e.result === "success" ? (
          e.session_prefix ? (
            <span className="font-mono text-[10px] bg-black/5 px-1 py-0.5 rounded">
              session: {e.session_prefix}…
            </span>
          ) : (
            "—"
          )
        ) : (
          <span className="text-red-600 font-medium">{e.reason || "Invalid credentials"}</span>
        )}
      </td>
    </tr>
  );
}

function GeoCell({ geo }: { geo: { city: string; country: string; country_code: string } | null }) {
  if (!geo) return <span className="text-dishhome-ink/40">—</span>;
  const flag = countryFlag(geo.country_code);
  return (
    <span className="whitespace-nowrap flex items-center gap-1">
      {flag && <span>{flag}</span>}
      <span className="text-xs text-dishhome-ink/80">{geo.city}{geo.country && geo.country !== "—" ? `, ${geo.country}` : ""}</span>
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
