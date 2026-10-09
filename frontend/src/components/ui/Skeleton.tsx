interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return <div className={`skeleton ${className}`} />;
}

export function SkeletonCard() {
  return (
    <div className="card p-5 space-y-3">
      <Skeleton className="h-3 w-24 rounded" />
      <Skeleton className="h-8 w-32 rounded" />
      <Skeleton className="h-3 w-16 rounded" />
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full rounded" />
      ))}
    </div>
  );
}
