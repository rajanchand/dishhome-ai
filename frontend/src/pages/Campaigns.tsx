import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Campaign, type Voice } from "../lib/api";
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

const STATUS_TONE: Record<string, "info" | "success" | "warn" | "neutral"> = {
  draft: "neutral",
  running: "info",
  paused: "warn",
  completed: "success",
};

export default function Campaigns() {
  const [list, setList] = useState<Campaign[] | null>(null);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [creating, setCreating] = useState(false);
  const errToast = useAsyncErrorToast();

  async function refresh() {
    try {
      const [cs, vs] = await Promise.all([
        api.get<Campaign[]>("/campaigns"),
        api.get<Voice[]>("/voice/voices"),
      ]);
      setList(cs);
      setVoices(vs);
    } catch (e) {
      errToast(e, "Could not load campaigns");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <PageHeader
        title="Voice Campaigns"
        subtitle="Run outbound AI voice calls to a list of contacts. Upload contacts as CSV, test with a demo call, then launch."
        actions={
          <Button onClick={() => setCreating(true)}>+ New campaign</Button>
        }
      />
      <PageBody>
        {creating && (
          <CreateCampaignModal
            voices={voices}
            onClose={() => setCreating(false)}
            onCreated={() => {
              setCreating(false);
              refresh();
            }}
          />
        )}

        {!list ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-40" />
            ))}
          </div>
        ) : list.length === 0 ? (
          <Card>
            <div className="text-center py-10">
              <div className="text-4xl mb-2">✈</div>
              <h3 className="text-dishhome-blue font-semibold">
                No campaigns yet
              </h3>
              <p className="text-sm text-dishhome-ink/60 mt-1">
                Create your first AI voice campaign to reach hundreds of
                customers at once — surveys, reminders, upgrade outreach.
              </p>
              <Button onClick={() => setCreating(true)} className="mt-4">
                + Create campaign
              </Button>
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {list.map((c) => (
              <CampaignCard key={c.id} c={c} />
            ))}
          </div>
        )}
      </PageBody>
    </>
  );
}

function CampaignCard({ c }: { c: Campaign }) {
  const pct = c.contacts_count
    ? Math.min(100, Math.round((c.stats.completed / c.contacts_count) * 100))
    : 0;
  return (
    <Link
      to={`/campaigns/${c.id}`}
      className="block rounded-2xl bg-white border border-black/5 shadow-sm p-4 hover:border-dishhome-blue/30 transition"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="font-semibold text-dishhome-blue">{c.name}</div>
        <Badge tone={STATUS_TONE[c.status] ?? "neutral"}>{c.status}</Badge>
      </div>
      <div className="mt-1 text-xs text-dishhome-ink/60">
        {c.language === "ne" ? "Nepali" : "English"} · {c.contacts_count} contacts
      </div>
      <p className="mt-3 text-xs text-dishhome-ink/70 line-clamp-2">
        {c.script}
      </p>
      <div className="mt-3">
        <div className="flex items-center justify-between text-[10px] uppercase tracking-widest text-dishhome-ink/50">
          <span>{c.stats.completed} / {c.contacts_count} completed</span>
          <span>{pct}%</span>
        </div>
        <div className="h-1.5 bg-black/5 rounded-full mt-1 overflow-hidden">
          <div
            className="h-full bg-dishhome-orange"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-center">
        <Mini n={c.stats.dialed} l="Dialed" />
        <Mini n={c.stats.connected} l="Conn." />
        <Mini n={c.stats.completed} l="Done" accent="green" />
        <Mini n={c.stats.failed} l="Fail" accent="red" />
      </div>
    </Link>
  );
}

function Mini({
  n,
  l,
  accent = "blue",
}: {
  n: number;
  l: string;
  accent?: "blue" | "green" | "red";
}) {
  const c = { blue: "text-dishhome-blue", green: "text-emerald-600", red: "text-rose-600" }[accent];
  return (
    <div className="rounded-md bg-dishhome-mist/60 py-1.5">
      <div className={`text-sm font-bold ${c}`}>{n}</div>
      <div className="text-[9px] uppercase tracking-widest text-dishhome-ink/50">
        {l}
      </div>
    </div>
  );
}

function CreateCampaignModal({
  voices,
  onClose,
  onCreated,
}: {
  voices: Voice[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [name, setName] = useState("");
  const [language, setLanguage] = useState<"ne" | "en">("ne");
  const [voiceId, setVoiceId] = useState(voices[0]?.id ?? "");
  const [script, setScript] = useState(
    "Namaste, DishHome bata. Yo ek important update ho — krapaya 1 minute ko lagi sunidinuhos.",
  );
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const errToast = useAsyncErrorToast();

  const langVoices = voices.filter((v) => v.language === language);

  async function submit() {
    setBusy(true);
    try {
      const c = await api.post<Campaign>("/campaigns", {
        name,
        language,
        voice_id: voiceId || langVoices[0]?.id,
        script,
      });
      toast.success("Campaign created", c.name);
      onCreated();
    } catch (e) {
      errToast(e, "Could not create campaign");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 bg-black/40 z-40 flex items-center justify-center p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg rounded-2xl bg-white shadow-xl p-6"
      >
        <h2 className="text-lg font-semibold text-dishhome-blue">
          New campaign
        </h2>
        <p className="text-sm text-dishhome-ink/60 mt-1">
          Define the AI voice, language, and opening script. Add contacts on the
          next screen.
        </p>
        <div className="mt-5 space-y-3">
          <Input
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Q3 bill reminder · Kathmandu"
          />
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
                Language
              </span>
              <select
                value={language}
                onChange={(e) => {
                  const l = e.target.value as "ne" | "en";
                  setLanguage(l);
                  setVoiceId(voices.find((v) => v.language === l)?.id ?? "");
                }}
                className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm"
              >
                <option value="ne">Nepali</option>
                <option value="en">English</option>
              </select>
            </label>
            <label className="block">
              <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
                Voice
              </span>
              <select
                value={voiceId}
                onChange={(e) => setVoiceId(e.target.value)}
                className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm"
              >
                {langVoices.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.gender})
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="block">
            <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
              Opening script
            </span>
            <textarea
              value={script}
              onChange={(e) => setScript(e.target.value)}
              rows={5}
              maxLength={600}
              className="w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dishhome-blue/30"
            />
            <span className="block text-[11px] text-dishhome-ink/50 mt-1">
              {script.length} / 600 characters
            </span>
          </label>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={busy || !name.trim() || !voiceId || !script.trim()}
          >
            {busy ? "Creating…" : "Create"}
          </Button>
        </div>
      </div>
    </div>
  );
}
