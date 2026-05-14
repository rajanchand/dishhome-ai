export function DishHomeLogo({
  variant = "dark",
  className = "",
}: {
  variant?: "dark" | "light";
  className?: string;
}) {
  // Logo PNG lives in /public — fetched once from dishhome.com.np/logo.png and
  // committed to the repo so the portal works offline.
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <img
        src="/dishhome-logo.png"
        alt="DishHome"
        width={28}
        height={28}
        className="rounded-md bg-white/10 p-0.5"
      />
      <span className="leading-tight">
        <span
          className={`block font-semibold tracking-tight ${
            variant === "light" ? "text-dishhome-blue" : "text-white"
          }`}
        >
          DishHome AI
        </span>
        <span
          className={`block text-[10px] uppercase tracking-widest ${
            variant === "light" ? "text-dishhome-ink/60" : "text-white/60"
          }`}
        >
          Call Center
        </span>
      </span>
    </span>
  );
}
