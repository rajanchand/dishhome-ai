import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type CallDetail } from "../lib/api";
import { Badge, Card, PageBody, PageHeader, statusTone } from "../components/ui";

export default function CallDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [call, setCall] = useState<CallDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api
      .get<CallDetail>(`/calls/${id}`)
      .then(setCall)
      .catch((e) => setErr(e.message));
  }, [id]);

  if (err)
    return (
      <PageBody>
        <p className="text-rose-600">Could not load call: {err}</p>
        <Link to="/calls" className="text-dishhome-blue text-sm">
          ← back
        </Link>
      </PageBody>
    );
  if (!call)
    return (
      <PageBody>
        <p className="text-dishhome-ink/50">Loading…</p>
      </PageBody>
    );

  return (
    <>
      <PageHeader
        title={`Call ${call.id}`}
        subtitle={`${call.caller_number} → ${call.called_number}`}
        actions={
          <Link
            to="/calls"
            className="text-sm text-dishhome-blue hover:underline"
          >
            ← All calls
          </Link>
        }
      />
      <PageBody>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card title="Conversation" className="lg:col-span-2">
            <div className="space-y-4">
              {call.transcript.map((t, i) => (
                <div
                  key={i}
                  className={`flex ${
                    t.role === "ai" ? "justify-start" : "justify-end"
                  }`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                      t.role === "ai"
                        ? "bg-dishhome-blue text-white"
                        : "bg-dishhome-mist border border-black/5 text-dishhome-ink"
                    }`}
                  >
                    <div
                      className={`text-[10px] uppercase tracking-widest mb-1 ${
                        t.role === "ai"
                          ? "text-white/60"
                          : "text-dishhome-ink/50"
                      }`}
                    >
                      {t.role === "ai" ? "AI Agent" : "Customer"}
                    </div>
                    {t.text}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <div className="space-y-4">
            <Card title="Summary">
              <div className="mb-4">
                <div className="flex items-center justify-between text-xs uppercase tracking-widest text-dishhome-ink/50 mb-1.5">
                  <span>Sentiment</span>
                  <span className="font-semibold text-dishhome-ink">
                    {call.sentiment_score > 0 ? "Positive" : call.sentiment_score < 0 ? "Negative" : "Neutral"}
                  </span>
                </div>
                <div className="h-2 w-full bg-black/5 rounded-full overflow-hidden flex">
                  <div 
                    className="h-full bg-emerald-500 transition-all duration-500" 
                    style={{ width: `${Math.max(0, call.sentiment_score * 100)}%` }} 
                  />
                  <div 
                    className="h-full bg-rose-500 transition-all duration-500" 
                    style={{ width: `${Math.max(0, -call.sentiment_score * 100)}%` }} 
                  />
                </div>
              </div>
              <dl className="text-sm space-y-3">
                <Row label="Status">
                  <div className="flex items-center gap-2">
                    <Badge tone={statusTone(call.status)}>
                      {call.status.replace("_", " ")}
                    </Badge>
                    {call.status === "in_progress" && (
                      <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" title="Live" />
                    )}
                  </div>
                </Row>
                <Row label="Intent">{call.intent.replace("_", " ")}</Row>
                <Row label="Resolution">
                  {call.resolution?.replace("_", " ") ?? "—"}
                </Row>
                <Row label="Language">{call.language.toUpperCase()}</Row>
                <Row label="Duration">{call.duration_sec}s</Row>
                <Row label="AI confidence">
                  {Math.round(call.ai_confidence * 100)}%
                </Row>
                <Row label="Started">
                  {new Date(call.started_at).toLocaleString()}
                </Row>
              </dl>
            </Card>

            {call.customer_id && (
              <Card title="Customer">
                <div className="text-sm">
                  <div className="font-medium text-dishhome-blue">
                    {call.customer_name}
                  </div>
                  <div className="font-mono text-xs text-dishhome-ink/60 mt-0.5">
                    {call.customer_id}
                  </div>
                  <Link
                    to={`/integrations?customer=${call.customer_id}`}
                    className="inline-block mt-3 text-xs text-dishhome-blue hover:underline"
                  >
                    Open in DishHome integration →
                  </Link>
                </div>
              </Card>
            )}
          </div>
        </div>
      </PageBody>
    </>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-xs uppercase tracking-widest text-dishhome-ink/50">
        {label}
      </dt>
      <dd className="text-dishhome-ink">{children}</dd>
    </div>
  );
}
