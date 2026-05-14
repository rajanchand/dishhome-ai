export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-md bg-black/5 ${className}`}
      aria-hidden
    />
  );
}

export function SkeletonRows({ rows = 4, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-3">
          {Array.from({ length: cols }).map((__, j) => (
            <Skeleton key={j} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function SkeletonStat() {
  return (
    <div className="rounded-2xl bg-white border border-black/5 shadow-sm p-5">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-16 mt-3" />
      <Skeleton className="h-3 w-32 mt-2" />
    </div>
  );
}
