// ==================== API Base URL ====================
const BASE = import.meta.env.VITE_API_BASE 
  || (typeof window !== "undefined" && window.location.hostname.includes("vercel.app"))
  ? "/api" 
  : "http://127.0.0.1:8000";

// ==================== Error & Token ====================
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

// ==================== Request Helper ====================
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
    } catch {}
    if (res.status === 401) setToken(null);
    throw new ApiError(res.status, msg, { requestId: reqId, code });
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ==================== API Methods ====================
export const api = {
  get: <T>(p: string, signal?: AbortSignal) => request<T>("GET", p, { signal }),
  post: <T>(p: string, body?: unknown, signal?: AbortSignal) =>
    request<T>("POST", p, { body, signal }),
  patch: <T>(p: string, body?: unknown) => request<T>("PATCH", p, { body }),
  delete: <T>(p: string) => request<T>("DELETE", p),
  upload: <T>(p: string, formData: FormData, signal?: AbortSignal) =>
    request<T>("POST", p, { formData, signal }),
};

// ==================== Interfaces ====================
export interface User {
  username: string;
  name: string;
  email: string;
  role: string;
  permissions?: string[];
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

export interface Message {
  author: "customer" | "ai" | "agent";
  at: string;
  body: string;
}

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

export interface LoginActivityResponse {
  events: LoginEvent[];
  stats: any; // temporary
}

export interface GeoInfo {
  city: string;
  country: string;
  country_code: string;
  region: string;
  lat: number | null;
  lon: number | null;
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

// ==================== URL Helpers ====================
export function absUrl(p: string): string {
  return p.startsWith("http") ? p : `${BASE}${p}`;
}

export async function fetchAudioBlobUrl(path: string): Promise<string> {
  const tok = getToken();
  const res = await fetch(absUrl(path), {
    headers: tok ? { authorization: `Bearer ${tok}` } : undefined,
  });
  if (!res.ok) throw new ApiError(res.status, "Failed to load sample");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
