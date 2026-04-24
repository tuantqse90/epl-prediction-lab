"use client";

import Link from "next/link";
import { useEffect } from "react";

// Global error boundary — catches any thrown error in a route segment
// that doesn't have a more local error.tsx. Payy-style dark page,
// neon-lime CTA, no stack traces surfaced to users.
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Silent client-side log; server-side errors are already captured by
    // the ErrorLogMiddleware on the API. We don't POST to /api/* here to
    // avoid cascade failures when the API itself is what's down.
    if (typeof window !== "undefined") {
      console.error("[route error]", error);
    }
  }, [error]);

  return (
    <main className="mx-auto max-w-2xl px-6 py-24 space-y-6 text-center">
      <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">error</p>
      <h1 className="headline-hero">Something broke.</h1>
      <p className="text-secondary">
        A request failed mid-render. This is almost always transient —
        usually an upstream odds API or a cold container start.
      </p>
      {error.digest && (
        <p className="font-mono text-[10px] text-muted">
          ref: {error.digest}
        </p>
      )}
      <div className="flex items-center justify-center gap-3 pt-4">
        <button onClick={reset} className="btn-primary text-sm">
          Try again
        </button>
        <Link href="/" className="btn-ghost text-sm">
          ← Home
        </Link>
      </div>
      <p className="text-xs text-muted pt-6">
        Still broken? → <Link href="/ops" className="hover:text-neon">/ops</Link> shows live service status.
      </p>
    </main>
  );
}
