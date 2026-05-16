const _isIP = typeof window !== "undefined" && /^[0-9.]+$/.test(window.location.hostname);
const BASE = (typeof window !== "undefined" && (window.location.hostname.includes("vercel.app") || _isIP)) 
  ? "/api" 
  : "http://127.0.0.1:8000";

export class ApiError extends Error {
  requestId?: string;
  code?: string;
  constructor(
    public status: number,
    message: string,
    opts: { requestId?: string; code?: string } = {},
  ) {
    super(message);
    this.requestId = opts.requestId;
    this.code = opts.code;
  }
}

function getToken(): string | null {
  return localStorage.getItem("dh_token");
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem("dh_token", token);
  else localStorage.removeItem("dh_token");
}

interface RequestOpts {
  body?: unknown;
  formData?: FormData;
  signal?: AbortSignal;
}

async function request<T>(
  method: string,
  path: string,
  opts: RequestOpts = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["content-type"] = "application/json";
  const tok = getToken();
  if (tok) headers["authorization"] = `Bearer ${tok}`;

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: opts.formData ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
      signal: opts.signal,
    });
  } catch (e) {
    throw new ApiError(0, e instanceof Error ? e.message : "Network error", {
      code: "network",
    });
  }
  const reqId = res.headers.get("x-request-id") ?? undefined;

  if (!res.ok) {
    let msg = res.statusText;
    let code: string | undefined;
    try {
      const data = await res.json();
      msg = data?.error?.message ?? data?.detail ?? msg;
      code = data?.error?.code;
    } catch {
      /* ignore */
    }
    if (res.status === 401) setToken(null);
    throw new ApiError(res.status, msg, { requestId: reqId, code });
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(p: string, signal?: AbortSignal) => request<T>("GET", p, { signal }),
  post: <T>(p: string, body?: unknown, signal?: AbortSignal) =>
    request<T>("POST", p, { body, signal }),
  patch: <T>(p: string, body?: unknown) => request<T>("PATCH", p, { body }),
  delete: <T>(p: string) => request<T>("DELETE", p),
  upload: <T>(p: string, formData: FormData, signal?: AbortSignal) =>
    request<T>("POST", p, { formData, signal }),
};

// ---- typed endpoints ----
export interface User {
  username: string;
  name: string;
  email: string;
  role: string;
  permissions?: string[];
}

// ---- Admin / RBAC ----
export interface AdminUser {
  username: string;
  name: string;
  email: string;
  role: string;
  permissions: string[];
  created_at?: string | null;
  created_by?: string | null;
}

export interface Role {
  id: string;
  name: string;
  permissions: string[];
  user_count: number;
}

// ---- Telephony ----
export interface TelephonyHealth {
  twilio_enabled: boolean;
  from_number: string | null;
  public_base_url: string | null;
  elevenlabs_enabled: boolean;
}

export interface CallSession {
  session_id: string;
  call_sid: string | null;
  to: string;
  from_: string;
  voice_id: string;
  language: string;
  text: string;
  status: string;
  error: string | null;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  duration_sec: number | null;
  campaign_id: string | null;
  recording_url: string | null;
}

export interface DemoCallResponse {
  mode: "twilio" | "mock";
  campaign_id: string;
  to: string;
  voice_id: string;
  language: string;
  session_id: string;
  call_sid?: string | null;
  status: string;
  script_preview?: string;
  hint?: string;
}

export interface VoiceHealth {
  elevenlabs_enabled: boolean;
  model_id: string;
  defaults_set: Record<string, boolean>;
}

// ---- Monitoring (login activity + active sessions) ----
export interface GeoInfo {
  city: string;
  country: string;
  country_code: string;
  region: string;
  lat: number | null;
  lon: number | null;
}

export interface LoginEvent {
  at: number;
  username: string;
  ip: string;
  user_agent: string;
  device: string;
  result: "success" | "failure";
  reason: string;
  session_prefix: string;
  geo: GeoInfo | null;
}

export interface LoginActivityStats {
  total_events: number;
  logins_24h_success: number;
  logins_24h_failure: number;
  unique_ips_24h: number;
  unique_users_24h: number;
}

export interface LoginActivityResponse {
  events: LoginEvent[];
  stats: LoginActivityStats;
}

export interface ActiveSession {
  token_prefix: string;
  username: string;
  issued_at: number;
  expires_at: number;
  last_seen: number;
  issued_ip: string;
  last_ip: string;
  user_agent: string;
  device: string;
  geo: GeoInfo | null;
}

export interface LoginResponse {
  token: string;
  user: User;
  expires_in: number;
}

export interface CallSummary {
  id: string;
  caller_number: string;
  called_number: string;
  customer_id: string | null;
  customer_name: string | null;
  language: string;
  started_at: string;
  ended_at: string | null;
  duration_sec: number;
  status: string;
  intent: string;
  ai_confidence: number;
}

export interface TranscriptTurn {
  role: string;
  text: string;
}

export interface CallDetail extends CallSummary {
  resolution: string | null;
  transcript: TranscriptTurn[];
}

export interface CallStats {
  total: number;
  in_progress: number;
  resolved: number;
  ticketed: number;
  avg_handle_sec: number;
  ai_resolution_rate: number;
}

export interface Voice {
  id: string;
  name: string;
  language: string;
  gender: string;
  tone: string;
  source?: "builtin" | "uploaded";
  sample_url?: string | null;
  created_at?: string | null;
  elevenlabs_voice_id?: string | null;
  cloned?: boolean;
}

export interface VoicePreviewResponse {
  voice_id: string;
  text: string;
  language: string;
  gender: string;
  rate: number;
  pitch: number;
  sample_url?: string | null;
  audio_url?: string | null;
  engine?: "elevenlabs" | "browser-tts";
}

export interface Customer {
  customer_id: string;
  name: string;
  mobile: string;
  smartcard: string;
  address: string;
  package: string;
  balance_npr: number;
  due_date: string;
  status: string;
  ont_id: string;
}

export interface RouterStatus {
  ont_id: string;
  online: boolean;
  rx_power_dbm: number | null;
  tx_power_dbm: number | null;
  uptime_hours: number;
  last_reboot: string;
  pppoe_session: string;
  area_outage: boolean;
}

export interface Ticket {
  id: string;
  customer_id: string;
  issue: string;
  priority: string;
  status: string;
  assigned_team: string;
  eta_minutes: number;
  created_at: string;
}

export interface MetricsSnapshot {
  total_requests: number;
  error_rate: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  errors_by_status: Record<string, number>;
  top_routes: [string, number][];
  window_size?: number;
}

// ---- Huawei ----
export interface HuaweiOnt {
  ont_id: string;
  device_model: string;
  serial_number: string;
  firmware_version: string;
  hardware_version: string;
  olt_id: string;
  olt_port: string;
  ont_index: number;
  online: boolean;
  rx_power_dbm: number | null;
  tx_power_dbm: number | null;
  line_attenuation_db: number | null;
  uptime_hours: number;
  last_reboot: string;
  pppoe_session: string;
  wifi_radio_2g: boolean;
  wifi_radio_5g: boolean;
  error_state: string | null;
  area_outage: boolean;
}

export interface HuaweiOlt {
  olt_id: string;
  site: string;
  online: boolean;
  active_onts: number;
  uptime_hours: number;
  degraded?: boolean;
}

export interface Diagnosis {
  customer_id: string;
  ont_id: string;
  scenario: string;
  headline: string;
  tone: "info" | "warn" | "danger" | "success";
  advice: string;
  recommended_action:
    | "remote_reboot"
    | "wait_for_outage"
    | "escalate_noc"
    | "dispatch_field"
    | "reauth_pppoe"
    | "remote_wifi_toggle"
    | "none";
  ont: HuaweiOnt;
  olt: HuaweiOlt | null;
}

export interface DemoCustomer {
  customer_id: string;
  name: string;
  mobile: string;
  address: string;
  package: string;
  ont_id: string;
  device_model: string | null;
  scenario: string;
  headline: string;
  tone: "info" | "warn" | "danger" | "success";
  online: boolean;
  rx_power_dbm: number | null;
}

// ---- FAQs ----
export interface Faq {
  id: string;
  question_en?: string | null;
  question_ne?: string | null;
  answer_en?: string | null;
  answer_ne?: string | null;
  category?: string | null;
  tags: string[];
}

export interface FaqAskResponse {
  query: string;
  language: string;
  answer: string | null;
  matched: { faq: Faq; score: number }[];
}

// ---- Campaigns ----
export interface CampaignStats {
  dialed: number;
  connected: number;
  completed: number;
  failed: number;
}

export interface Campaign {
  id: string;
  name: string;
  language: "ne" | "en";
  voice_id: string;
  script: string;
  status: "draft" | "running" | "paused" | "completed";
  contacts_count: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  stats: CampaignStats;
}

export interface CampaignContact {
  id: string;
  name: string;
  mobile: string;
  status: string;
  attempts: number;
  outcome: string | null;
}

// ---- Inbox ----
export interface Label {
  id: string;
  name: string;
  color: string;
}

export interface SavedReply {
  id: string;
  title: string;
  body: string;
  language: "ne" | "en";
}

export interface Contact {
  id: string;
  name: string;
  mobile: string;
  email: string | null;
  customer_id: string | null;
  labels: string[];
  last_contacted_at: string | null;
  notes?: string | null;
}

export interface Message {
  author: "customer" | "ai" | "agent";
  at: string;
  body: string;
}

export interface Conversation {
  id: string;
  channel: "voice" | "sms" | "whatsapp" | "web";
  contact_id: string;
  subject: string;
  labels: string[];
  status: "open" | "closed";
  last_message_at: string;
  messages: Message[];
}

// Resolve absolute URL for sample playback (audio elements need full URL)
export function absUrl(p: string): string {
  return p.startsWith("http") ? p : `${BASE}${p}`;
}

// Audio fetch needs the token too — return a blob URL
export async function fetchAudioBlobUrl(path: string): Promise<string> {
  const tok = getToken();
  const res = await fetch(absUrl(path), {
    headers: tok ? { authorization: `Bearer ${tok}` } : undefined,
  });
  if (!res.ok) throw new ApiError(res.status, "Failed to load sample");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
