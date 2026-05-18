import { useEffect, useMemo, useState } from "react";
import { Button, Card, Input, PageBody, PageHeader } from "../components/ui";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

interface SystemConfig {
  app_env: string;
  ai: {
    ollama_model: string;
    ollama_host: string;
    tts_engine: string;
    elevenlabs_model_id: string | null;
  };
  telephony: {
    sip_enabled: boolean;
    sip_ws_server: string | null;
    sip_domain: string | null;
    audiosocket_host: string;
    audiosocket_port: number;
    audio_server_enabled: boolean;
    twilio_enabled: boolean;
    twilio_from_number: string | null;
    public_base_url: string | null;
  };
  integrations: {
    elevenlabs_configured: boolean;
    supabase_configured: boolean;
    sentry_configured: boolean;
  };
  cors_origins: string[];
}

type Source = "db" | "env" | "unset";

interface RuntimeConfigEntry {
  key: string;
  label: string;
  is_secret: boolean;
  source: Source;
  value: string;
  updated_at: string | null;
  updated_by: string | null;
}

// Per-card grouping for the editable UI.
const CARD_GROUPS: { title: string; keys: string[] }[] = [
  {
    title: "Telephony — SIP softphone",
    keys: ["sip_ws_server", "sip_domain", "sip_passwords_json"],
  },
  {
    title: "Telephony — Twilio outbound",
    keys: ["twilio_account_sid", "twilio_auth_token", "twilio_from_number", "public_base_url"],
  },
  {
    title: "Voice — ElevenLabs",
    keys: [
      "elevenlabs_api_key",
      "elevenlabs_voice_ne_female",
      "elevenlabs_voice_ne_male",
      "elevenlabs_voice_en_female",
      "elevenlabs_voice_en_male",
    ],
  },
  {
    title: "AI — Ollama",
    keys: ["ollama_host", "ollama_model"],
  },
  {
    title: "Observability",
    keys: ["sentry_dsn"],
  },
];

export default function Settings() {
  const { user } = useAuth();
  const isSuperAdmin = user?.role === "super_admin";

  const [sysCfg, setSysCfg] = useState<SystemConfig | null>(null);
  const [runtime, setRuntime] = useState<RuntimeConfigEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const [s, r] = await Promise.all([
        api.get<SystemConfig>("/admin/system-config"),
        api.get<RuntimeConfigEntry[]>("/admin/runtime-config"),
      ]);
      setSysCfg(s);
      setRuntime(r);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.message}` : "Failed to load settings");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const byKey = useMemo(() => {
    const m = new Map<string, RuntimeConfigEntry>();
    for (const e of runtime) m.set(e.key, e);
    return m;
  }, [runtime]);

  return (
    <>
      <PageHeader
        title="Settings"
        subtitle={
          isSuperAdmin
            ? "Provision integrations directly from here. Saved values override environment variables (DB > env)."
            : "Live system configuration. Only super_admin can edit values."
        }
      />
      <PageBody>
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {CARD_GROUPS.map((g) => (
            <ConfigCard
              key={g.title}
              title={g.title}
              entries={g.keys.map((k) => byKey.get(k)).filter((e): e is RuntimeConfigEntry => !!e)}
              canEdit={isSuperAdmin}
              onSaved={load}
            />
          ))}

          <Card title="System (read-only)">
            <dl className="text-sm space-y-2">
              <Row label="App env">
                <Pill tone={sysCfg?.app_env === "production" ? "success" : "info"}>
                  {sysCfg?.app_env ?? "…"}
                </Pill>
              </Row>
              <Row label="TTS engine">{sysCfg?.ai.tts_engine ?? "…"}</Row>
              <Row label="AudioSocket">
                <Mono>
                  {sysCfg
                    ? `${sysCfg.telephony.audiosocket_host}:${sysCfg.telephony.audiosocket_port}`
                    : "…"}
                </Mono>
              </Row>
              <Row label="Audio server">
                <Pill tone={sysCfg?.telephony.audio_server_enabled ? "success" : "neutral"}>
                  {sysCfg?.telephony.audio_server_enabled ? "Running" : "Disabled"}
                </Pill>
              </Row>
              <Row label="Supabase">
                <Pill tone={sysCfg?.integrations.supabase_configured ? "success" : "warn"}>
                  {sysCfg?.integrations.supabase_configured ? "Configured" : "Not configured"}
                </Pill>
              </Row>
              <Row label="CORS origins">
                <span className="text-xs text-dishhome-ink/70 dark:text-dishhome-mist/70">
                  {sysCfg ? sysCfg.cors_origins.length : 0} allowed
                </span>
              </Row>
            </dl>
          </Card>

          <Card title="Profile">
            <dl className="text-sm space-y-2">
              <Row label="Name">{user?.name}</Row>
              <Row label="Username"><code>{user?.username}</code></Row>
              <Row label="Email">{user?.email}</Row>
              <Row label="Role">
                <Pill tone={user?.role === "super_admin" ? "success" : "info"}>
                  {user?.role ?? "—"}
                </Pill>
              </Row>
            </dl>
          </Card>
        </div>

        <p className="mt-6 text-xs text-dishhome-ink/50 dark:text-dishhome-mist/50">
          Saved values live in <code>dh.system_config</code> and survive redeploys. Clear a field
          and save to fall back to the env var. Secrets are masked once stored — re-enter to update.
        </p>
      </PageBody>
    </>
  );
}

function ConfigCard({
  title,
  entries,
  canEdit,
  onSaved,
}: {
  title: string;
  entries: RuntimeConfigEntry[];
  canEdit: boolean;
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const startEdit = () => {
    // Pre-fill secrets as blank (user must re-enter to change); pre-fill
    // non-secrets with their effective value so they can tweak.
    const d: Record<string, string> = {};
    for (const e of entries) {
      d[e.key] = e.is_secret ? "" : e.source === "unset" ? "" : e.value;
    }
    setDraft(d);
    setSaveError(null);
    setEditing(true);
  };

  const cancel = () => {
    setEditing(false);
    setDraft({});
    setSaveError(null);
  };

  const save = async () => {
    setSaving(true);
    setSaveError(null);
    try {
      // For secrets, only send a change if the user typed something. An
      // empty string would clear the override — only do that when the user
      // explicitly cleared a non-secret field.
      const updates = entries
        .map((e) => ({ key: e.key, value: draft[e.key] ?? "" }))
        .filter((u) => {
          const entry = entries.find((e) => e.key === u.key)!;
          if (entry.is_secret && u.value === "") return false; // unchanged
          if (!entry.is_secret && entry.source !== "unset" && u.value === entry.value) return false;
          return true;
        });

      if (updates.length === 0) {
        setEditing(false);
        return;
      }
      await api.put<RuntimeConfigEntry[]>("/admin/runtime-config", { updates });
      setEditing(false);
      setDraft({});
      onSaved();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title={title}>
      <div className="space-y-3">
        {!editing && (
          <dl className="text-sm space-y-2">
            {entries.map((e) => (
              <div key={e.key} className="flex items-center justify-between gap-3">
                <div>
                  <dt className="text-xs uppercase tracking-widest text-dishhome-ink/50 dark:text-dishhome-mist/50">
                    {e.label}
                  </dt>
                  <div className="text-[10px] text-dishhome-ink/40 dark:text-dishhome-mist/40 mt-0.5">
                    <SourceBadge source={e.source} updated_by={e.updated_by} />
                  </div>
                </div>
                <dd className="text-right min-w-0">
                  {e.value ? (
                    <Mono className="break-all">{e.value}</Mono>
                  ) : (
                    <span className="text-xs text-dishhome-ink/40 italic">unset</span>
                  )}
                </dd>
              </div>
            ))}
          </dl>
        )}

        {editing && (
          <div className="space-y-3">
            {entries.map((e) => (
              <Input
                key={e.key}
                label={`${e.label}${e.is_secret ? " (secret)" : ""}`}
                type={e.is_secret ? "password" : "text"}
                placeholder={
                  e.is_secret
                    ? e.source !== "unset"
                      ? "(leave blank to keep current)"
                      : "Enter a value"
                    : e.source !== "unset"
                    ? `Current: ${e.value || "(env)"}`
                    : "Enter a value"
                }
                value={draft[e.key] ?? ""}
                onChange={(ev) =>
                  setDraft((prev) => ({ ...prev, [e.key]: ev.target.value }))
                }
                autoComplete="off"
              />
            ))}
            {saveError && (
              <div className="text-xs text-red-600">{saveError}</div>
            )}
            <div className="flex gap-2 justify-end pt-1">
              <Button variant="ghost" onClick={cancel} disabled={saving}>
                Cancel
              </Button>
              <Button onClick={save} disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </Button>
            </div>
          </div>
        )}

        {!editing && canEdit && (
          <div className="flex justify-end pt-1">
            <Button variant="ghost" onClick={startEdit}>
              Edit
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-xs uppercase tracking-widest text-dishhome-ink/50 dark:text-dishhome-mist/50 flex-shrink-0">
        {label}
      </dt>
      <dd className="text-right min-w-0">{children}</dd>
    </div>
  );
}

function Mono({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <code className={`text-xs font-mono text-dishhome-ink dark:text-dishhome-mist ${className}`}>
      {children}
    </code>
  );
}

function Pill({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "success" | "warn" | "info" | "neutral";
}) {
  const styles: Record<typeof tone, string> = {
    success: "bg-green-50 text-green-700 border-green-200",
    warn: "bg-amber-50 text-amber-700 border-amber-200",
    info: "bg-blue-50 text-blue-700 border-blue-200",
    neutral: "bg-slate-50 text-slate-600 border-slate-200",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${styles[tone]}`}
    >
      {children}
    </span>
  );
}

function SourceBadge({ source, updated_by }: { source: Source; updated_by: string | null }) {
  if (source === "db") {
    return (
      <span className="text-green-600">
        from DB{updated_by ? ` · by ${updated_by}` : ""}
      </span>
    );
  }
  if (source === "env") return <span className="text-blue-600">from env</span>;
  return <span className="text-slate-400">unset</span>;
}
