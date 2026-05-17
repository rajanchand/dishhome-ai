import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  api,
  type Campaign,
  type CampaignContact,
  type CallSession,
  type DemoCallResponse,
} from "../lib/api";
import {
  Badge,
  Button,
  Card,
  Input,
  PageBody,
  PageHeader,
} from "../components/ui";
import { Skeleton } from "../components/Skeleton";
import { useAsyncErrorToast, useToast } from "../components/Toast";
import { Play } from "lucide-react";

export default function CampaignDetail() {
  const { id } = useParams<{ id: string }>();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [contacts, setContacts] = useState<CampaignContact[] | null>(null);
  const toast = useToast();
  const errToast = useAsyncErrorToast();

  async function refresh() {
    if (!id) return;
    try {
      const [c, cc] = await Promise.all([
        api.get<Campaign>(`/campaigns/${id}`),
        api.get<CampaignContact[]>(`/campaigns/${id}/contacts`),
      ]);
      setCampaign(c);
      setContacts(cc);
    } catch (e) {
      errToast(e, "Could not load campaign");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function run() {
    if (!campaign) return;
    try {
      const c = await api.post<Campaign>(`/campaigns/${campaign.id}/run`);
      setCampaign(c);
      toast.success("Campaign launched", `${c.stats.dialed} numbers dialed in the first wave`);
      refresh();
    } catch (e) {
      errToast(e, "Could not start campaign");
    }
  }

  async function pause() {
    if (!campaign) return;
    try {
      const c = await api.post<Campaign>(`/campaigns/${campaign.id}/pause`);
      setCampaign(c);
      toast.info("Campaign paused");
    } catch (e) {
      errToast(e, "Could not pause");
    }
  }

  async function downloadReport() {
    if (!campaign) return;
    try {
      const r = await api.post<unknown>(`/campaigns/${campaign.id}/report`);
      const blob = new Blob([JSON.stringify(r, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${campaign.name.replace(/\s+/g, "_")}-report.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Report downloaded");
    } catch (e) {
      errToast(e, "Report failed");
    }
  }

  async function deleteContact(cid: string) {
    if (!campaign) return;
    try {
      await api.delete(`/campaigns/${campaign.id}/contacts/${cid}`);
      refresh();
      toast.success("Contact removed");
    } catch (e) {
      errToast(e, "Delete failed");
    }
  }

  async function deleteCampaign() {
    if (!campaign) return;
    if (!confirm(`Delete campaign "${campaign.name}"?`)) return;
    try {
      await api.delete(`/campaigns/${campaign.id}`);
      toast.success("Campaign deleted");
      window.location.href = "/campaigns";
    } catch (e) {
      errToast(e, "Delete failed");
    }
  }

  if (!campaign || !contacts) {
    return (
      <PageBody>
        <Skeleton className="h-40" />
      </PageBody>
    );
  }

  return (
    <>
      <PageHeader
        title={campaign.name}
        subtitle={`${campaign.language === "ne" ? "Nepali" : "English"} · voice ${campaign.voice_id} · ${campaign.contacts_count} contacts`}
        actions={
          <Link
            to="/campaigns"
            className="text-sm text-dishhome-blue hover:underline"
          >
            ← All campaigns
          </Link>
        }
      />
      <PageBody>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-4">
            <Card title="Opening script">
              <pre className="whitespace-pre-wrap text-sm text-dishhome-ink leading-relaxed font-sans">
                {campaign.script}
              </pre>
              <div className="mt-3 flex items-center gap-2">
                <Badge
                  tone={
                    campaign.status === "running"
                      ? "info"
                      : campaign.status === "completed"
                        ? "success"
                        : campaign.status === "paused"
                          ? "warn"
                          : "neutral"
                  }
                >
                  {campaign.status}
                </Badge>
                {campaign.started_at && (
                  <span className="text-xs text-dishhome-ink/50">
                    started {new Date(campaign.started_at).toLocaleString()}
                  </span>
                )}
              </div>
            </Card>

            <DemoCallCard campaign={campaign} />

            <ContactsCard
              campaign={campaign}
              contacts={contacts}
              onChange={refresh}
              onDeleteContact={deleteContact}
            />
          </div>

          <div className="space-y-4">
            <Card title="Controls">
              {campaign.status === "running" ? (
                <Button variant="secondary" onClick={pause} className="w-full">
                  Pause campaign
                </Button>
              ) : campaign.status === "completed" ? (
                <p className="text-sm text-dishhome-ink/60">
                  Campaign finished. Download the report below.
                </p>
              ) : (
                <Button onClick={run} className="w-full">
                  <Play size={16} /> Run campaign
                </Button>
              )}
              <Button
                variant="ghost"
                className="w-full mt-2"
                onClick={downloadReport}
              >
                Download report (JSON)
              </Button>
              <Button
                variant="ghost"
                className="w-full mt-2 !text-rose-600"
                onClick={deleteCampaign}
              >
                Delete campaign
              </Button>
            </Card>

            <Card title="Stats">
              <dl className="text-sm space-y-2">
                <Row label="Dialed">{campaign.stats.dialed}</Row>
                <Row label="Connected">{campaign.stats.connected}</Row>
                <Row label="Completed">
                  <span className="text-emerald-600 font-semibold">
                    {campaign.stats.completed}
                  </span>
                </Row>
                <Row label="Failed">
                  <span className="text-rose-600 font-semibold">
                    {campaign.stats.failed}
                  </span>
                </Row>
                <Row label="Pending">
                  {campaign.contacts_count -
                    campaign.stats.completed -
                    campaign.stats.failed}
                </Row>
              </dl>
            </Card>
          </div>
        </div>
      </PageBody>
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-xs uppercase tracking-widest text-dishhome-ink/50">
        {label}
      </dt>
      <dd>{children}</dd>
    </div>
  );
}

function DemoCallCard({ campaign }: { campaign: Campaign }) {
  const [mobile, setMobile] = useState("+447570731478");
  const [busy, setBusy] = useState(false);
  const [session, setSession] = useState<CallSession | null>(null);
  const [mode, setMode] = useState<"twilio" | "mock" | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const toast = useToast();
  const errToast = useAsyncErrorToast();

  async function call() {
    setBusy(true);
    setSession(null);
    setHint(null);
    try {
      const r = await api.post<DemoCallResponse>(
        `/campaigns/${campaign.id}/demo-call`,
        { mobile },
      );
      setMode(r.mode);
      if (r.mode === "twilio") {
        toast.success("Demo call placed", `Twilio CallSid ${r.call_sid} → ${mobile}`);
      } else {
        toast.info("Demo call (mock)", r.hint ?? `Session ${r.session_id} → ${mobile}`);
        setHint(r.hint ?? null);
      }
      // Kick off polling for telephony sessions only when Twilio actually placed the call.
      if (r.mode === "twilio") {
        pollSession(r.session_id);
      }
    } catch (e) {
      errToast(e, "Demo call failed");
    } finally {
      setBusy(false);
    }
  }

  async function pollSession(sid: string) {
    const terminal = new Set(["completed", "failed", "busy", "no-answer", "canceled"]);
    for (let i = 0; i < 60; i++) {
      try {
        const s = await api.get<CallSession>(`/telephony/sessions/${sid}`);
        setSession(s);
        if (terminal.has((s.status || "").toLowerCase())) return;
      } catch {
        // Silent: poll fail is recoverable.
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
  }

  return (
    <Card title="Demo call">
      <p className="text-xs text-dishhome-ink/60 mb-3">
        Dial any number (use E.164 like <span className="font-mono">+447570731478</span>) to
        QA the AI voice + script before launching the full campaign.
      </p>
      <div className="flex gap-2">
        <Input
          value={mobile}
          onChange={(e) => setMobile(e.target.value)}
          placeholder="+447570731478"
          className="flex-1"
        />
        <Button onClick={call} disabled={busy || !mobile.trim()}>
          {busy ? "Dialing…" : <><Play size={16} /> Demo call</>}
        </Button>
      </div>
      {mode === "mock" && hint && (
        <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 text-amber-900 px-3 py-2 text-xs">
          <div className="font-semibold mb-0.5">Running in mock mode</div>
          {hint}
        </div>
      )}
      {session && (
        <div className="mt-3 rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-xs space-y-0.5">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-sky-900">Live call</span>
            <span className="font-mono text-[10px] text-sky-700">{session.session_id}</span>
          </div>
          <div>Status: <span className="font-mono">{session.status}</span></div>
          {session.call_sid && (
            <div>Twilio SID: <span className="font-mono">{session.call_sid}</span></div>
          )}
          <div>To: <span className="font-mono">{session.to}</span></div>
          {session.duration_sec !== null && session.duration_sec !== undefined && (
            <div>Duration: {session.duration_sec}s</div>
          )}
          {session.error && (
            <div className="text-rose-700">Error: {session.error}</div>
          )}
        </div>
      )}
    </Card>
  );
}

function ContactsCard({
  campaign,
  contacts,
  onChange,
  onDeleteContact,
}: {
  campaign: Campaign;
  contacts: CampaignContact[];
  onChange: () => void;
  onDeleteContact: (id: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);
  const toast = useToast();
  const errToast = useAsyncErrorToast();

  async function upload(file: File) {
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await api.upload<{ added: number; skipped: number; total: number }>(
        `/campaigns/${campaign.id}/contacts/upload`,
        fd,
      );
      toast.success(
        "Contacts uploaded",
        `${r.added} added, ${r.skipped} skipped, total ${r.total}`,
      );
      onChange();
    } catch (e) {
      errToast(e, "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <Card
      title={`Contacts (${contacts.length})`}
      actions={
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) upload(f);
            }}
          />
          <Button
            variant="ghost"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "Uploading…" : "Upload CSV"}
          </Button>
        </div>
      }
    >
      <p className="text-[11px] text-dishhome-ink/50 mb-3">
        CSV columns:{" "}
        <code>name</code>, <code>mobile</code>
      </p>
      {contacts.length === 0 ? (
        <p className="text-sm text-dishhome-ink/50">
          No contacts in this campaign yet. Upload a CSV to get started.
        </p>
      ) : (
        <div className="max-h-72 overflow-y-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-widest text-dishhome-ink/50 border-b border-black/5">
                <th className="py-2">Name</th>
                <th>Mobile</th>
                <th>Status</th>
                <th>Outcome</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {contacts.map((c) => (
                <tr key={c.id} className="border-b border-black/5 last:border-0">
                  <td className="py-2">{c.name}</td>
                  <td className="font-mono text-xs">{c.mobile}</td>
                  <td>
                    <Badge
                      tone={
                        c.status === "completed"
                          ? "success"
                          : c.status === "no_answer" || c.status === "failed"
                            ? "warn"
                            : "neutral"
                      }
                    >
                      {c.status.replace("_", " ")}
                    </Badge>
                  </td>
                  <td className="text-xs text-dishhome-ink/70">
                    {c.outcome ?? "—"}
                  </td>
                  <td className="text-right">
                    <button
                      onClick={() => onDeleteContact(c.id)}
                      className="text-[11px] text-rose-600 hover:underline"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
