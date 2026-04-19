"use client";

import { useRouter } from "next/navigation";
import { useLang } from "@/lib/i18n-client";
import { LANGS, LANG_LABELS, type Lang } from "@/lib/i18n";

export default function LangToggle() {
  const current = useLang();
  const router = useRouter();

  function set(l: Lang) {
    if (typeof document !== "undefined") {
      document.cookie = `lang=${l};path=/;max-age=${60 * 60 * 24 * 365};samesite=lax`;
    }
    router.refresh();
  }

  // 5 languages — a row of buttons gets noisy on mobile. Native <select>
  // scales and stays accessible without a JS dropdown lib.
  return (
    <select
      value={current}
      onChange={(e) => set(e.target.value as Lang)}
      aria-label="Language"
      className="bg-raised border border-border rounded-full px-2 py-1 font-mono text-[11px] uppercase tracking-wide text-secondary hover:border-neon focus:outline-none focus:border-neon"
    >
      {LANGS.map((l) => (
        <option key={l} value={l} className="bg-surface text-primary">
          {LANG_LABELS[l]}
        </option>
      ))}
    </select>
  );
}
