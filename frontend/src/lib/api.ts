const BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

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
}

export interface LoginResponse {
  token: string;
  user: User;
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
}

export interface VoicePreviewResponse {
  voice_id: string;
  text: string;
  language: string;
  gender: string;
  rate: number;
  pitch: number;
  sample_url?: string | null;
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
