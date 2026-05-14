import type { ButtonHTMLAttributes, ReactNode } from "react";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="px-8 py-6 border-b border-black/5 bg-white flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-semibold text-dishhome-blue">{title}</h1>
        {subtitle && (
          <p className="text-sm text-dishhome-ink/60 mt-1">{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function PageBody({ children }: { children: ReactNode }) {
  return <div className="px-8 py-6">{children}</div>;
}

export function Card({
  children,
  title,
  actions,
  className = "",
}: {
  children: ReactNode;
  title?: string;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl bg-white border border-black/5 shadow-sm ${className}`}
    >
      {(title || actions) && (
        <header className="px-5 py-3 border-b border-black/5 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-dishhome-blue uppercase tracking-widest">
            {title}
          </h2>
          {actions}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function StatCard({
  label,
  value,
  hint,
  accent = "blue",
}: {
  label: string;
  value: string | number;
  hint?: string;
  accent?: "blue" | "orange" | "green" | "red";
}) {
  const accentClass = {
    blue: "text-dishhome-blue",
    orange: "text-dishhome-orange",
    green: "text-emerald-600",
    red: "text-rose-600",
  }[accent];
  return (
    <div className="rounded-2xl bg-white border border-black/5 shadow-sm p-5">
      <div className="text-xs uppercase tracking-widest text-dishhome-ink/50">
        {label}
      </div>
      <div className={`mt-2 text-3xl font-bold ${accentClass}`}>{value}</div>
      {hint && (
        <div className="mt-1 text-xs text-dishhome-ink/60">{hint}</div>
      )}
    </div>
  );
}

interface BtnProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: BtnProps) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed";
  const styles = {
    primary:
      "bg-dishhome-blue text-white hover:bg-dishhome-blue/90 focus:ring-dishhome-blue/30",
    secondary:
      "bg-dishhome-orange text-white hover:bg-dishhome-orange/90 focus:ring-dishhome-orange/30",
    ghost:
      "bg-white text-dishhome-blue border border-dishhome-blue/20 hover:bg-dishhome-blue/5",
    danger: "bg-rose-600 text-white hover:bg-rose-700",
  }[variant];
  return <button className={`${base} ${styles} ${className}`} {...props} />;
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warn" | "danger" | "info";
}) {
  const t = {
    neutral: "bg-slate-100 text-slate-700",
    success: "bg-emerald-100 text-emerald-700",
    warn: "bg-amber-100 text-amber-800",
    danger: "bg-rose-100 text-rose-700",
    info: "bg-sky-100 text-sky-800",
  }[tone];
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${t}`}
    >
      {children}
    </span>
  );
}

export function Input({
  label,
  ...props
}: { label?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block">
      {label && (
        <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 mb-1.5">
          {label}
        </span>
      )}
      <input
        {...props}
        className={`w-full rounded-lg border border-black/10 bg-white px-3 py-2 text-sm placeholder:text-dishhome-ink/40 focus:outline-none focus:ring-2 focus:ring-dishhome-blue/30 ${
          props.className ?? ""
        }`}
      />
    </label>
  );
}

export function statusTone(status: string): "success" | "warn" | "info" | "neutral" | "danger" {
  switch (status) {
    case "resolved":
    case "active":
    case "dispatched":
      return "success";
    case "in_progress":
      return "info";
    case "ticket_created":
      return "warn";
    case "overdue":
    case "failed":
      return "danger";
    default:
      return "neutral";
  }
}
