"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { trackPageView } from "@/lib/analytics";

export default function PageViewTracker() {
  const pathname = usePathname();
  useEffect(() => {
    if (!pathname) return;
    if (pathname.startsWith("/embed")) return;
    if (pathname.startsWith("/api/")) return;
    trackPageView(pathname);
  }, [pathname]);
  return null;
}
