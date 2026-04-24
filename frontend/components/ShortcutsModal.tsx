"use client";

import { useEffect, useState } from "react";

const SHORTCUTS: Array<{ keys: string; label: string }> = [
  { keys: "?",     label: "This cheat sheet" },
  { keys: "⌘K",    label: "Open search" },
  { keys: "/",     label: "Focus search" },
  { keys: "w",     label: "Go to watchlist" },
  { keys: "t",     label: "Go to table" },
  { keys: "m",     label: "Go to my picks" },
  { keys: "r",     label: "Go to ROI" },
  { keys: "Esc",   label: "Close modal / dropdown" },
];

export default function ShortcutsModal() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      // Don't swallow typing in inputs.
      if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      if (target.isContentEditable) return;

      if (e.key === "?" && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setOpen((p) => !p);
        return;
      }
      if (e.key === "Escape") setOpen(false);

      // Simple letter nav
      const navMap: Record<string, string> = {
        w: "/watchlist",
        t: "/table",
        m: "/my-picks",
        r: "/roi",
      };
      if (!e.metaKey && !e.ctrlKey && navMap[e.key] && !open) {
        window.location.href = navMap[e.key];
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur flex items-center justify-center p-4"
      onClick={() => setOpen(false)}
    >
      <div
        className="card max-w-md w-full space-y-3"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-baseline justify-between">
          <h2 className="label">Keyboard shortcuts</h2>
          <button onClick={() => setOpen(false)} className="text-muted hover:text-error text-sm">✕</button>
        </div>
        <ul className="space-y-1 font-mono text-xs">
          {SHORTCUTS.map((s) => (
            <li key={s.keys} className="flex justify-between">
              <kbd className="rounded border border-border bg-raised px-1.5 py-0.5">{s.keys}</kbd>
              <span className="text-secondary">{s.label}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
