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
    <div className="px-8 py-6 border-b border-black/5 dark:border-white/5 bg-white dark:bg-dishhome-ink flex items-center justify-between transition-colors">
      <div>
        <h1 className="text-2xl font-semibold text-dishhome-blue dark:text-dishhome-mist">{title}</h1>
        {subtitle && (
          <p className="text-sm text-dishhome-ink/60 dark:text-dishhome-mist/60 mt-1">{subtitle}</p>
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
      className={`rounded-2xl bg-white dark:bg-dishhome-ink/50 border border-black/5 dark:border-white/5 shadow-sm transition-all hover:-translate-y-1 hover:shadow-md ${className}`}
    >
      {(title || actions) && (
        <header className="px-5 py-3 border-b border-black/5 dark:border-white/5 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-dishhome-blue dark:text-dishhome-mist uppercase tracking-widest">
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
    blue: "text-dishhome-blue dark:text-blue-400",
    orange: "text-dishhome-orange dark:text-orange-400",
    green: "text-emerald-600 dark:text-emerald-400",
    red: "text-rose-600 dark:text-rose-400",
  }[accent];
  return (
    <div className="rounded-2xl bg-white dark:bg-dishhome-ink/50 border border-black/5 dark:border-white/5 shadow-sm p-5 transition-all hover:-translate-y-1 hover:shadow-md group">
      <div className="text-xs uppercase tracking-widest text-dishhome-ink/50 dark:text-dishhome-mist/50">
        {label}
      </div>
      <div className={`mt-2 text-3xl font-bold ${accentClass}`}>{value}</div>
      {hint && (
        <div className="mt-1 text-xs text-dishhome-ink/60 dark:text-dishhome-mist/60 group-hover:text-dishhome-ink/80 dark:group-hover:text-dishhome-mist/80 transition-colors">{hint}</div>
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
    "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all active:scale-95 focus:outline-none focus:ring-2 focus:ring-offset-1 dark:focus:ring-offset-dishhome-ink disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100";
  const styles = {
    primary:
      "bg-dishhome-blue dark:bg-dishhome-blue/80 text-white hover:bg-dishhome-blue/90 dark:hover:bg-dishhome-blue focus:ring-dishhome-blue/30",
    secondary:
      "bg-dishhome-orange dark:bg-dishhome-orange/80 text-white hover:bg-dishhome-orange/90 dark:hover:bg-dishhome-orange focus:ring-dishhome-orange/30",
    ghost:
      "bg-white dark:bg-transparent text-dishhome-blue dark:text-dishhome-mist border border-dishhome-blue/20 dark:border-white/10 hover:bg-dishhome-blue/5 dark:hover:bg-white/5",
    danger: "bg-rose-600 dark:bg-rose-600/80 text-white hover:bg-rose-700 dark:hover:bg-rose-600",
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
        <span className="block text-xs uppercase tracking-widest text-dishhome-ink/60 dark:text-dishhome-mist/60 mb-1.5">
          {label}
        </span>
      )}
      <input
        {...props}
        className={`w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-black/20 dark:text-white px-3 py-2 text-sm placeholder:text-dishhome-ink/40 dark:placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-dishhome-blue/30 transition-colors ${
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
