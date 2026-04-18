"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Auto-refresh the current Server Component page every 10s while any
 *  match on screen is live. Mounted only conditionally from the page. */
export default function LivePoller({ intervalMs = 10_000 }: { intervalMs?: number }) {
  const router = useRouter();
  useEffect(() => {
    const id = setInterval(() => router.refresh(), intervalMs);
    return () => clearInterval(id);
  }, [router, intervalMs]);
  return null;
}
