import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type Tone = "info" | "success" | "warn" | "error";

interface Toast {
  id: number;
  tone: Tone;
  title: string;
  description?: string;
  ttl: number;
}

interface ToastApi {
  push: (t: Omit<Toast, "id" | "ttl"> & { ttl?: number }) => void;
  success: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
  warn: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
}

const ToastCtx = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);

  const remove = useCallback(
    (id: number) => setItems((cur) => cur.filter((t) => t.id !== id)),
    [],
  );

  const push = useCallback<ToastApi["push"]>(
    (t) => {
      const id = Date.now() + Math.random();
      const item: Toast = { id, ttl: t.ttl ?? 4500, ...t };
      setItems((cur) => [...cur, item]);
      window.setTimeout(() => remove(id), item.ttl);
    },
    [remove],
  );

  const api: ToastApi = {
    push,
    success: (title, description) => push({ tone: "success", title, description }),
    info: (title, description) => push({ tone: "info", title, description }),
    warn: (title, description) => push({ tone: "warn", title, description }),
    error: (title, description) => push({ tone: "error", title, description, ttl: 7000 }),
  };

  return (
    <ToastCtx.Provider value={api}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
        {items.map((t) => (
          <ToastItem key={t.id} toast={t} onClose={() => remove(t.id)} />
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  const tone = {
    info: "border-sky-300 bg-sky-50 text-sky-900",
    success: "border-emerald-300 bg-emerald-50 text-emerald-900",
    warn: "border-amber-300 bg-amber-50 text-amber-900",
    error: "border-rose-300 bg-rose-50 text-rose-900",
  }[toast.tone];
  const dot = {
    info: "bg-sky-500",
    success: "bg-emerald-500",
    warn: "bg-amber-500",
    error: "bg-rose-500",
  }[toast.tone];
  return (
    <div
      role="status"
      className={`rounded-lg border shadow-sm px-4 py-3 flex items-start gap-3 ${tone} animate-in slide-in-from-right-4`}
    >
      <span className={`w-2 h-2 rounded-full mt-1.5 ${dot}`} />
      <div className="flex-1">
        <div className="font-semibold text-sm">{toast.title}</div>
        {toast.description && (
          <div className="text-xs opacity-80 mt-0.5">{toast.description}</div>
        )}
      </div>
      <button
        onClick={onClose}
        className="opacity-50 hover:opacity-100 text-sm leading-none"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}

// Convenience hook: surfaces unhandled fetch failures consistently
export function useAsyncErrorToast() {
  const t = useToast();
  return useCallback(
    (err: unknown, fallback = "Something went wrong") => {
      const msg = err instanceof Error ? err.message : fallback;
      const reqId =
        err && typeof err === "object" && "requestId" in err
          ? (err as { requestId?: string }).requestId
          : undefined;
      t.error(msg, reqId ? `Request ID: ${reqId}` : undefined);
    },
    [t],
  );
}

// Helper to bridge browser online/offline events
export function NetworkStatusBridge() {
  const t = useToast();
  useEffect(() => {
    const off = () => t.warn("You are offline", "Reconnecting…");
    const on = () => t.success("Back online");
    window.addEventListener("offline", off);
    window.addEventListener("online", on);
    return () => {
      window.removeEventListener("offline", off);
      window.removeEventListener("online", on);
    };
  }, [t]);
  return null;
}
