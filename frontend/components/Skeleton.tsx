// Lightweight skeleton placeholder. Render while async data loads.
export default function Skeleton({
  className = "",
  lines = 3,
}: {
  className?: string;
  lines?: number;
}) {
  return (
    <div className={`animate-pulse space-y-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-3 rounded bg-high/60" />
      ))}
    </div>
  );
}
