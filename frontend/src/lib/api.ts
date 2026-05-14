const BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function getToken(): string | null {
  return localStorage.getItem("dh_token");
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem("dh_token", token);
  else localStorage.removeItem("dh_token");
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  const tok = getToken();
  if (tok) headers["authorization"] = `Bearer ${tok}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const data = await res.json();
      msg = data.detail ?? msg;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(p: string) => request<T>("GET", p),
  post: <T>(p: string, body?: unknown) => request<T>("POST", p, body),
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
}

export interface VoicePreviewResponse {
  voice_id: string;
  text: string;
  language: string;
  gender: string;
  rate: number;
  pitch: number;
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
