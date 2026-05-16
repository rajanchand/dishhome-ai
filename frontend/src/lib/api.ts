// API Base URL Configuration
const BASE = import.meta.env.VITE_API_BASE 
  || (typeof window !== "undefined" && window.location.hostname.includes("vercel.app"))
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

// Rest of your interfaces and functions remain the same...
export interface User {
  username: string;
  name: string;
  email: string;
  role: string;
  permissions?: string[];
}

// ... (all your other interfaces stay the same)

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
