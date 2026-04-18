"use client";

import { useRouter } from "next/navigation";
import { useLang } from "@/lib/i18n-client";
import type { Lang } from "@/lib/i18n";

export default function LangToggle() {
  const current = useLang();
  const router = useRouter();

  function set(l: Lang) {
    if (typeof document !== "undefined") {
      document.cookie = `lang=${l};path=/;max-age=${60 * 60 * 24 * 365};samesite=lax`;
    }
    router.refresh();
  }

  const item = (l: Lang, label: string) => (
    <button
      key={l}
      onClick={() => set(l)}
      className={
        current === l
          ? "text-neon font-semibold"
          : "text-muted hover:text-primary transition-colors"
      }
      aria-current={current === l ? "true" : undefined}
    >
      {label}
    </button>
  );

  return (
    <div className="inline-flex items-center gap-2 font-mono text-xs">
      {item("vi", "VI")}
      <span className="text-muted">/</span>
      {item("en", "EN")}
    </div>
  );
}
