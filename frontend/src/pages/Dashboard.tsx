import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  BASE,
  type CallStats,
  type CallSummary,
  type MetricsSnapshot,
} from "../lib/api";
import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  Card,
  PageBody,
  PageHeader,
  StatCard,
  statusTone,
} from "../components/ui";
import { SkeletonStat, SkeletonRows, Skeleton } from "../components/Skeleton";

export default function Dashboard() {

  const { data: stats } = useQuery({
    queryKey: ["calls", "stats"],
    queryFn: () => api.get<CallStats>("/calls/stats"),
  });

  const { data: calls } = useQuery({
    queryKey: ["calls"],
    queryFn: () => api.get<CallSummary[]>("/calls"),
  });

  const { data: metrics } = useQuery({
    queryKey: ["metrics"],
    queryFn: () => api.get<MetricsSnapshot>("/metrics"),
    refetchInterval: 5000,
  });

  const [liveTranscripts, setLiveTranscripts] = useState<any[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("dh_token");
    if (!token) return;

    const wsUrl = BASE.replace(/^http/, "ws") + `/calls/live?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLiveTranscripts((prev) => [data, ...prev].slice(0, 50));
      } catch (e) {
        console.error("Failed to parse websocket message", e);
      }
    };

    return () => {
      ws.close();
    };
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
              <RingStatCard
                label="AI Resolution Rate"
                value={`${Math.round(stats.ai_resolution_rate * 100)}%`}
                percentage={Math.round(stats.ai_resolution_rate * 100)}
                hint={`Avg handle: ${stats.avg_handle_sec}s`}
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

          <Card title="Live Intelligence Feed">
            <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 scrollbar-thin">
              {liveTranscripts.length > 0 ? (
                liveTranscripts.map((t, idx) => (
                  <div key={idx} className={`flex items-start gap-3 p-3 rounded-xl border animate-in fade-in slide-in-from-right-4 ${
                    idx === 0 ? "bg-dishhome-blue/5 border-dishhome-blue/10" : "bg-black/5 dark:bg-white/5 border-black/5 dark:border-white/5 opacity-80"
                  }`}>
                    <div className={`w-2 h-2 mt-1.5 rounded-full shrink-0 ${idx === 0 ? "bg-dishhome-blue animate-pulse" : "bg-dishhome-ink/20 dark:bg-dishhome-mist/20"}`} />
                    <div>
                      <div className="text-[10px] uppercase tracking-widest text-dishhome-ink/40 dark:text-dishhome-mist/40 mb-1">
                        {t.caller_number} · Now
                      </div>
                      <p className="text-xs text-dishhome-ink dark:text-dishhome-mist italic">"{t.text}"</p>
                      {t.intent && (
                        <div className="mt-2 flex items-center gap-1.5">
                          <Badge tone="info">{t.intent}</Badge>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-dishhome-ink/50 dark:text-dishhome-mist/50 italic py-4">
                  Waiting for live calls...
                </div>
              )}
            </div>
            <button className="w-full mt-4 text-[10px] uppercase tracking-widest text-dishhome-blue font-bold hover:underline">
              View All Transcripts →
            </button>
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

function RingStatCard({ label, value, percentage, hint }: { label: string, value: string, percentage: number, hint: string }) {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="rounded-2xl bg-white dark:bg-dishhome-ink/50 border border-black/5 dark:border-white/5 shadow-sm p-5 transition-all hover:-translate-y-1 hover:shadow-md group">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs uppercase tracking-widest text-dishhome-ink/50 dark:text-dishhome-mist/50">
            {label}
          </div>
          <div className="mt-2 text-3xl font-bold text-dishhome-blue dark:text-blue-400">{value}</div>
        </div>
        <div className="relative w-16 h-16 shrink-0">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 64 64">
            <circle className="text-black/5 dark:text-white/10 stroke-current" strokeWidth="6" cx="32" cy="32" r={radius} fill="transparent"></circle>
            <circle className="text-dishhome-blue dark:text-blue-400 stroke-current transition-all duration-1000 ease-out" strokeWidth="6" strokeLinecap="round" cx="32" cy="32" r={radius} fill="transparent" strokeDasharray={circumference} strokeDashoffset={strokeDashoffset}></circle>
          </svg>
        </div>
      </div>
      <div className="mt-1 text-xs text-dishhome-ink/60 dark:text-dishhome-mist/60 group-hover:text-dishhome-ink/80 dark:group-hover:text-dishhome-mist/80 transition-colors">
        {hint}
      </div>
    </div>
  );
}
