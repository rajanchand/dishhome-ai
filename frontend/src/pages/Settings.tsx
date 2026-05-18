import { useEffect, useState } from "react";
import { Card, PageBody, PageHeader } from "../components/ui";
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

export default function Settings() {
  const { user } = useAuth();
  const [cfg, setCfg] = useState<SystemConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<SystemConfig>("/admin/system-config")
      .then((data) => {
        if (!cancelled) setCfg(data);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(
          e instanceof ApiError
            ? `${e.status}: ${e.message}`
            : "Failed to load system config",
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <PageHeader
        title="Settings"
        subtitle="Live system configuration. Values come from environment variables; edit them via the Vercel dashboard or backend/.env."
      />
      <PageBody>
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card title="AI engine">
            <dl className="text-sm space-y-2">
              <Row label="App env">
                <Pill tone={cfg?.app_env === "production" ? "success" : "info"}>
                  {cfg?.app_env ?? "…"}
                </Pill>
              </Row>
              <Row label="LLM (Ollama model)">
                <Mono>{cfg?.ai.ollama_model ?? "…"}</Mono>
              </Row>
              <Row label="Ollama host">
                <Mono>{cfg?.ai.ollama_host ?? "…"}</Mono>
              </Row>
              <Row label="TTS engine">{cfg?.ai.tts_engine ?? "…"}</Row>
              <Row label="ElevenLabs model">
                <Mono>{cfg?.ai.elevenlabs_model_id ?? "—"}</Mono>
              </Row>
            </dl>
          </Card>

          <Card title="Telephony">
            <dl className="text-sm space-y-2">
              <Row label="SIP softphone">
                <Pill tone={cfg?.telephony.sip_enabled ? "success" : "warn"}>
                  {cfg?.telephony.sip_enabled ? "Configured" : "Not configured"}
                </Pill>
              </Row>
              <Row label="SIP WebSocket">
                <Mono>{cfg?.telephony.sip_ws_server ?? "—"}</Mono>
              </Row>
              <Row label="SIP domain">
                <Mono>{cfg?.telephony.sip_domain ?? "—"}</Mono>
              </Row>
              <Row label="AudioSocket">
                <Mono>
                  {cfg
                    ? `${cfg.telephony.audiosocket_host}:${cfg.telephony.audiosocket_port}`
                    : "…"}
                </Mono>
              </Row>
              <Row label="Audio server">
                <Pill tone={cfg?.telephony.audio_server_enabled ? "success" : "neutral"}>
                  {cfg?.telephony.audio_server_enabled ? "Running" : "Disabled"}
                </Pill>
              </Row>
              <Row label="Twilio outbound">
                <Pill tone={cfg?.telephony.twilio_enabled ? "success" : "warn"}>
                  {cfg?.telephony.twilio_enabled ? "Configured" : "Not configured"}
                </Pill>
              </Row>
              <Row label="Twilio from number">
                <Mono>{cfg?.telephony.twilio_from_number ?? "—"}</Mono>
              </Row>
              <Row label="Public base URL">
                <Mono className="truncate max-w-[260px]">
                  {cfg?.telephony.public_base_url ?? "—"}
                </Mono>
              </Row>
            </dl>
          </Card>

          <Card title="Integrations">
            <dl className="text-sm space-y-2">
              <Row label="ElevenLabs (voice clone + TTS)">
                <Pill tone={cfg?.integrations.elevenlabs_configured ? "success" : "warn"}>
                  {cfg?.integrations.elevenlabs_configured ? "Configured" : "Not configured"}
                </Pill>
              </Row>
              <Row label="Supabase (persistence)">
                <Pill tone={cfg?.integrations.supabase_configured ? "success" : "warn"}>
                  {cfg?.integrations.supabase_configured ? "Configured" : "Not configured"}
                </Pill>
              </Row>
              <Row label="Sentry (error tracking)">
                <Pill tone={cfg?.integrations.sentry_configured ? "success" : "neutral"}>
                  {cfg?.integrations.sentry_configured ? "Configured" : "Not configured"}
                </Pill>
              </Row>
              <Row label="CORS origins">
                <span className="text-xs text-dishhome-ink/70 dark:text-dishhome-mist/70">
                  {cfg ? cfg.cors_origins.length : 0} allowed
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
          To change a value, update the corresponding env var (e.g. <code>SIP_WS_SERVER</code>,
          <code> ELEVENLABS_API_KEY</code>) on Vercel and redeploy. Secrets are never
          returned by the API.
        </p>
      </PageBody>
    </>
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
