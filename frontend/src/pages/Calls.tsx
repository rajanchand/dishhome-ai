import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type CallSummary } from "../lib/api";
import {
  Badge,
  Card,
  PageBody,
  PageHeader,
  statusTone,
} from "../components/ui";

export default function Calls() {
  const [calls, setCalls] = useState<CallSummary[]>([]);
  const [filter, setFilter] = useState<string>("all");

  useEffect(() => {
    api.get<CallSummary[]>("/calls").then(setCalls);
  }, []);

  const visible = calls.filter((c) =>
    filter === "all" ? true : c.status === filter,
  );

  return (
    <>
      <PageHeader
        title="Live Calls"
        subtitle="All inbound calls handled by the AI agent. Click any row to view the full transcript and customer context."
        actions={
          <div className="flex items-center gap-1 bg-dishhome-mist rounded-lg p-1">
            {["all", "in_progress", "resolved", "ticket_created"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 text-xs uppercase tracking-widest rounded-md transition ${
                  filter === f
                    ? "bg-white text-dishhome-blue shadow-sm"
                    : "text-dishhome-ink/60 hover:text-dishhome-blue"
                }`}
              >
                {f.replace("_", " ")}
              </button>
            ))}
          </div>
        }
      />
      <PageBody>
        <Card>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-widest text-dishhome-ink/50 border-b border-black/5">
                <th className="py-2">Call ID</th>
                <th>Caller</th>
                <th>Customer</th>
                <th>Intent</th>
                <th>Duration</th>
                <th>Confidence</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((c) => (
                <tr
                  key={c.id}
                  className="border-b border-black/5 last:border-0 hover:bg-dishhome-mist/50 transition"
                >
                  <td className="py-3 font-mono text-xs">
                    <Link
                      to={`/calls/${c.id}`}
                      className="text-dishhome-blue hover:underline"
                    >
                      {c.id}
                    </Link>
                  </td>
                  <td className="font-mono text-xs text-dishhome-ink/80">
                    {c.caller_number}
                  </td>
                  <td>
                    {c.customer_name ?? (
                      <span className="text-dishhome-ink/40">unknown</span>
                    )}
                  </td>
                  <td className="text-dishhome-ink/70">
                    {c.intent.replace("_", " ")}
                  </td>
                  <td className="font-mono text-xs">
                    {formatDuration(c.duration_sec)}
                  </td>
                  <td>
                    <ConfidenceBar value={c.ai_confidence} />
                  </td>
                  <td>
                    <Badge tone={statusTone(c.status)}>
                      {c.status.replace("_", " ")}
                    </Badge>
                  </td>
                </tr>
              ))}
              {visible.length === 0 && (
                <tr>
                  <td
                    colSpan={7}
                    className="py-10 text-center text-sm text-dishhome-ink/50"
                  >
                    No calls in this view.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      </PageBody>
    </>
  );
}

function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 85 ? "bg-emerald-500" : pct >= 70 ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-black/5 rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-dishhome-ink/60 font-mono">{pct}%</span>
    </div>
  );
}
