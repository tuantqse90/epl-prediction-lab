"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

type Hit = { type: string; label: string; sublabel: string | null; href: string };

export default function SearchModal() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
    else {
      setQ("");
      setHits([]);
    }
  }, [open]);

  useEffect(() => {
    if (q.trim().length < 2) {
      setHits([]);
      return;
    }
    const ctl = new AbortController();
    setLoading(true);
    fetch(`${BASE}/api/search?q=${encodeURIComponent(q.trim())}&limit=10`, { signal: ctl.signal })
      .then((r) => (r.ok ? r.json() : []))
      .then((data: Hit[]) => setHits(data))
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => ctl.abort();
  }, [q]);

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        title="Search (Ctrl+K)"
        className="rounded-full border border-border px-3 py-1 font-mono text-xs text-muted hover:border-neon hover:text-neon transition-colors"
      >
        ⌘K
      </button>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-start justify-center pt-20 px-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) setOpen(false);
      }}
    >
      <div className="w-full max-w-xl rounded-xl border border-border bg-raised shadow-2xl overflow-hidden">
        <div className="border-b border-border">
          <input
            ref={inputRef}
            type="text"
            placeholder="Search teams, players, matches…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="w-full bg-transparent px-5 py-4 text-lg outline-none placeholder:text-muted"
          />
        </div>
        <div className="max-h-80 overflow-y-auto">
          {q.trim().length < 2 && (
            <p className="p-5 text-muted text-sm">Type at least 2 characters.</p>
          )}
          {q.trim().length >= 2 && hits.length === 0 && !loading && (
            <p className="p-5 text-muted text-sm">No results.</p>
          )}
          {hits.map((h, i) => (
            <Link
              key={`${h.type}-${i}-${h.href}`}
              href={h.href}
              onClick={() => setOpen(false)}
              className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-high transition-colors"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="rounded bg-high px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-muted">
                  {h.type}
                </span>
                <span className="truncate">{h.label}</span>
              </div>
              {h.sublabel && (
                <span className="font-mono text-xs text-muted shrink-0">{h.sublabel}</span>
              )}
            </Link>
          ))}
        </div>
        <div className="border-t border-border px-5 py-2 flex justify-between font-mono text-[10px] text-muted">
          <span>↵ open</span>
          <span>esc close</span>
        </div>
      </div>
    </div>
  );
}
