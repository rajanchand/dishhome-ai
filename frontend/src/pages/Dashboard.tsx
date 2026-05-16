import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  type CallStats,
  type CallSummary,
  type MetricsSnapshot,
} from "../lib/api";
import {
  Badge,
  Card,
  PageBody,
  PageHeader,
  StatCard,
  statusTone,
} from "../components/ui";
import { SkeletonStat, SkeletonRows, Skeleton } from "../components/Skeleton";
import { useAsyncErrorToast } from "../components/Toast";

export default function Dashboard() {
  const [stats, setStats] = useState<CallStats | null>(null);
  const [calls, setCalls] = useState<CallSummary[] | null>(null);
  const [metrics, setMetrics] = useState<MetricsSnapshot | null>(null);
  const errToast = useAsyncErrorToast();

  useEffect(() => {
    let stopped = false;
    const stop = (e: unknown) => {
      // If it's a 401, don't show toast — the global handler redirects
      if (e && typeof e === "object" && "status" in e && (e as { status: number }).status === 401) return;
      errToast(e);
    };
    api.get<CallStats>("/calls/stats").then(setStats).catch(stop);
    api.get<CallSummary[]>("/calls").then(setCalls).catch(stop);

    const loadMetrics = () => {
      if (stopped) return;
      api.get<MetricsSnapshot>("/metrics").then(setMetrics).catch((e) => {
        // Stop polling on auth failure
        if (e && typeof e === "object" && "status" in e && (e as { status: number }).status === 401) {
          stopped = true;
        }
      });
    };
    loadMetrics();
    const i = window.setInterval(loadMetrics, 5000);
    return () => { stopped = true; window.clearInterval(i); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const recent = calls
    ? [...calls]
        .sort((a, b) => b.started_at.localeCompare(a.started_at))
        .slice(0, 6)
    : [];

  return (
    <>
      <PageHeader
        title="Operations Dashboard"
        subtitle="Live view of AI-handled customer calls across the network."
      />
      <PageBody>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {stats ? (
            <>
              <StatCard
                label="In Progress"
                value={stats.in_progress}
                hint="Active AI conversations"
                accent="orange"
              />
              <StatCard
                label="Resolved (AI)"
                value={stats.resolved}
                hint="No human needed"
                accent="green"
              />
              <StatCard
                label="Tickets Created"
                value={stats.ticketed}
                hint="Dispatched to field teams"
                accent="blue"
              />
              <StatCard
                label="AI Resolution Rate"
                value={`${Math.round(stats.ai_resolution_rate * 100)}%`}
                hint={`Avg handle: ${stats.avg_handle_sec}s`}
                accent="blue"
              />
            </>
          ) : (
            [...Array(4)].map((_, i) => <SkeletonStat key={i} />)
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
          <Card title="Recent calls" className="lg:col-span-2">
            {!calls ? (
              <SkeletonRows rows={5} cols={5} />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-widest text-dishhome-ink/50 border-b border-black/5">
                    <th className="py-2">Caller</th>
                    <th>Customer</th>
                    <th>Intent</th>
                    <th>Status</th>
                    <th>Lang</th>
                  </tr>
                </thead>
                <tbody>
                  {recent.map((c) => (
                    <tr
                      key={c.id}
                      className="border-b border-black/5 last:border-0"
                    >
                      <td className="py-3 font-mono text-xs text-dishhome-ink/80">
                        <Link
                          to={`/calls/${c.id}`}
                          className="hover:text-dishhome-blue"
                        >
                          {c.caller_number}
                        </Link>
                      </td>
                      <td>{c.customer_name ?? "—"}</td>
                      <td className="text-dishhome-ink/70">
                        {c.intent.replace("_", " ")}
                      </td>
                      <td>
                        <Badge tone={statusTone(c.status)}>
                          {c.status.replace("_", " ")}
                        </Badge>
                      </td>
                      <td className="uppercase text-xs text-dishhome-ink/60">
                        {c.language}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          <Card title="System health">
            <ul className="space-y-3 text-sm">
              <Health
                label="FreeSWITCH SIP trunk"
                tone="success"
                detail="connected"
              />
              <Health
                label="Ollama LLM"
                tone="success"
                detail="llama3.1:70b · 712ms p50"
              />
              <Health
                label="faster-whisper STT"
                tone="success"
                detail="large-v3 · 280ms p50"
              />
              <Health
                label="Piper TTS"
                tone="success"
                detail="anjali-ne · 110ms p50"
              />
              <Health
                label="DishHome Billing API"
                tone="info"
                detail="mock · 67ms"
              />
              <Health
                label="Network OSS"
                tone="warn"
                detail="degraded · Pokhara"
              />
            </ul>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
          <Card
            title="API performance (live)"
            className="lg:col-span-2"
            actions={
              metrics && (
                <span className="text-xs text-dishhome-ink/50">
                  rolling {metrics.window_size ?? metrics.total_requests} requests
                </span>
              )
            }
          >
            {!metrics ? (
              <Skeleton className="h-24" />
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Metric label="p50" value={`${metrics.p50_ms}ms`} accent="green" />
                <Metric
                  label="p95"
                  value={`${metrics.p95_ms}ms`}
                  accent={metrics.p95_ms < 200 ? "green" : "orange"}
                />
                <Metric
                  label="p99"
                  value={`${metrics.p99_ms}ms`}
                  accent={metrics.p99_ms < 500 ? "green" : "red"}
                />
                <Metric
                  label="Error rate"
                  value={`${(metrics.error_rate * 100).toFixed(2)}%`}
                  accent={metrics.error_rate < 0.01 ? "green" : "red"}
                />
              </div>
            )}
          </Card>

          <Card title="Top API routes">
            {!metrics ? (
              <Skeleton className="h-24" />
            ) : metrics.top_routes.length === 0 ? (
              <p className="text-sm text-dishhome-ink/50">No traffic yet.</p>
            ) : (
              <ul className="text-sm space-y-1.5">
                {metrics.top_routes.slice(0, 6).map(([route, n]) => (
                  <li
                    key={route}
                    className="flex items-center justify-between"
                  >
                    <code className="text-xs text-dishhome-ink/80">
                      {route}
                    </code>
                    <span className="text-xs text-dishhome-ink/60">{n}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </PageBody>
    </>
  );
}

function Health({
  label,
  tone,
  detail,
}: {
  label: string;
  tone: "success" | "warn" | "danger" | "info";
  detail: string;
}) {
  const dot = {
    success: "bg-emerald-500",
    warn: "bg-amber-500",
    danger: "bg-rose-500",
    info: "bg-sky-500",
  }[tone];
  return (
    <li className="flex items-center justify-between">
      <span className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${dot}`} />
        {label}
      </span>
      <span className="text-xs text-dishhome-ink/60">{detail}</span>
    </li>
  );
}

function Metric({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: "green" | "orange" | "red";
}) {
  const color = {
    green: "text-emerald-600",
    orange: "text-amber-600",
    red: "text-rose-600",
  }[accent];
  return (
    <div className="rounded-lg bg-dishhome-mist/50 border border-black/5 p-3">
      <div className="text-[10px] uppercase tracking-widest text-dishhome-ink/50">
        {label}
      </div>
      <div className={`mt-1 text-xl font-bold ${color}`}>{value}</div>
    </div>
  );
}
