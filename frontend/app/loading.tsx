// Route-level loading skeleton. Next streams this while a page's
// server components are still awaiting data. Keeps LCP perceived-fast
// on cold cache hits; the neon dot mirrors the header's 'live service'
// signal so it doesn't feel like an error state.
export default function Loading() {
  return (
    <main className="mx-auto max-w-6xl px-6 py-24 space-y-10" aria-busy="true">
      <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-[0.18em] text-muted">
        <span aria-hidden className="relative inline-flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full rounded-full bg-neon opacity-70 animate-ping" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-neon" />
        </span>
        loading
      </div>
      <div className="space-y-6">
        <div className="h-10 w-2/3 max-w-lg animate-pulse rounded bg-high/50" />
        <div className="h-4 w-1/2 max-w-md animate-pulse rounded bg-high/30" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="card space-y-3">
            <div className="h-4 w-1/3 animate-pulse rounded bg-high/50" />
            <div className="h-8 w-2/3 animate-pulse rounded bg-high/40" />
            <div className="h-3 w-full animate-pulse rounded bg-high/30" />
            <div className="h-3 w-5/6 animate-pulse rounded bg-high/30" />
          </div>
        ))}
      </div>
    </main>
  );
}
