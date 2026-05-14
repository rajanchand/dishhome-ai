import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  type CallStats,
  type CallSummary,
} from "../lib/api";
import {
  Badge,
  Card,
  PageBody,
  PageHeader,
  StatCard,
  statusTone,
} from "../components/ui";

export default function Dashboard() {
  const [stats, setStats] = useState<CallStats | null>(null);
  const [calls, setCalls] = useState<CallSummary[]>([]);

  useEffect(() => {
    api.get<CallStats>("/calls/stats").then(setStats);
    api.get<CallSummary[]>("/calls").then(setCalls);
  }, []);

  const recent = [...calls]
    .sort((a, b) => b.started_at.localeCompare(a.started_at))
    .slice(0, 6);

  return (
    <>
      <PageHeader
        title="Operations Dashboard"
        subtitle="Live view of AI-handled customer calls across the network."
      />
      <PageBody>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <StatCard
            label="In Progress"
            value={stats?.in_progress ?? "—"}
            hint="Active AI conversations"
            accent="orange"
          />
          <StatCard
            label="Resolved (AI)"
            value={stats?.resolved ?? "—"}
            hint="No human needed"
            accent="green"
          />
          <StatCard
            label="Tickets Created"
            value={stats?.ticketed ?? "—"}
            hint="Dispatched to field teams"
            accent="blue"
          />
          <StatCard
            label="AI Resolution Rate"
            value={
              stats ? `${Math.round(stats.ai_resolution_rate * 100)}%` : "—"
            }
            hint={`Avg handle: ${stats?.avg_handle_sec ?? 0}s`}
            accent="blue"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-6">
          <Card title="Recent calls" className="lg:col-span-2">
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
          </Card>

          <Card title="System health">
            <ul className="space-y-3 text-sm">
              <Health label="FreeSWITCH SIP trunk" tone="success" detail="connected" />
              <Health label="Ollama LLM" tone="success" detail="llama3.1:70b · 712ms p50" />
              <Health label="faster-whisper STT" tone="success" detail="large-v3 · 280ms p50" />
              <Health label="Piper TTS" tone="success" detail="anjali-ne · 110ms p50" />
              <Health label="DishHome Billing API" tone="info" detail="mock · 67ms" />
              <Health label="Network OSS" tone="warn" detail="degraded · Pokhara" />
            </ul>
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
