"use client";

import { useEffect, useState } from "react";

// Handles vim-style navigation on pages that have a grid of `<a>` match
// cards: j/k move highlight through anchors under [data-kbd-target],
// Enter opens the current, Esc clears. A small hint chip shows up at
// bottom-right the first time the user presses '?' to reveal the keys.
export default function KeyboardNavHint() {
  const [cursor, setCursor] = useState<number>(-1);
  const [showHint, setShowHint] = useState(false);

  useEffect(() => {
    function nodes(): HTMLAnchorElement[] {
      return Array.from(
        document.querySelectorAll<HTMLAnchorElement>(
          "[data-kbd-target] a[href^='/match/']",
        ),
      );
    }
    function focus(idx: number) {
      const list = nodes();
      if (list.length === 0) return;
      const target = list[Math.max(0, Math.min(list.length - 1, idx))];
      target.scrollIntoView({ block: "nearest", behavior: "smooth" });
      target.focus();
      setCursor(idx);
    }
    function onKey(e: KeyboardEvent) {
      // Skip when user is typing in an input/textarea/search modal.
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if ((e.target as HTMLElement)?.isContentEditable) return;
      if (e.key === "j") {
        e.preventDefault();
        focus((cursor < 0 ? -1 : cursor) + 1);
      } else if (e.key === "k") {
        e.preventDefault();
        focus((cursor < 0 ? 0 : cursor) - 1);
      } else if (e.key === "?") {
        e.preventDefault();
        setShowHint((v) => !v);
      } else if (e.key === "Escape") {
        setCursor(-1);
        (document.activeElement as HTMLElement | null)?.blur();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cursor]);

  if (!showHint) return null;
  return (
    <div
      className="fixed bottom-4 right-4 z-40 rounded-lg border border-neon/40 bg-black/80 backdrop-blur px-4 py-3 font-mono text-[11px] text-secondary shadow-xl"
      role="dialog"
      aria-label="Keyboard shortcuts"
    >
      <p className="text-neon uppercase tracking-wide mb-2">Keyboard</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        <dt className="text-primary">j / k</dt>
        <dd>next / prev match</dd>
        <dt className="text-primary">↵</dt>
        <dd>open focused match</dd>
        <dt className="text-primary">⌘K</dt>
        <dd>search</dd>
        <dt className="text-primary">?</dt>
        <dd>toggle this help</dd>
        <dt className="text-primary">esc</dt>
        <dd>clear focus / close</dd>
      </dl>
    </div>
  );
}
