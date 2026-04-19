"use client";

import { useEffect, useState } from "react";

// Minimal share row: copy, Telegram, X. Uses native Web Share on mobile
// when available (drops all three with one tap); falls back to the three
// explicit targets on desktop where Web Share rarely exists.
export default function ShareButtons({
  url,
  title,
}: {
  url: string;
  title: string;
}) {
  const [copied, setCopied] = useState(false);
  const [canNativeShare, setCanNativeShare] = useState(false);

  useEffect(() => {
    setCanNativeShare(typeof navigator !== "undefined" && "share" in navigator);
  }, []);

  async function copy() {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function nativeShare() {
    try {
      await (navigator as Navigator & { share: (data: ShareData) => Promise<void> }).share({
        title,
        url,
      });
    } catch {
      /* user cancelled */
    }
  }

  const tgUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`;
  const xUrl = `https://x.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {canNativeShare && (
        <button
          onClick={nativeShare}
          className="rounded-full border border-border px-3 py-1 font-mono text-xs uppercase tracking-wide text-secondary hover:border-neon hover:text-neon transition-colors"
        >
          Share
        </button>
      )}
      <button
        onClick={copy}
        className="rounded-full border border-border px-3 py-1 font-mono text-xs uppercase tracking-wide text-secondary hover:border-neon hover:text-neon transition-colors"
      >
        {copied ? "Copied!" : "Copy link"}
      </button>
      <a
        href={tgUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="rounded-full border border-border px-3 py-1 font-mono text-xs uppercase tracking-wide text-secondary hover:border-neon hover:text-neon transition-colors"
      >
        Telegram
      </a>
      <a
        href={xUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="rounded-full border border-border px-3 py-1 font-mono text-xs uppercase tracking-wide text-secondary hover:border-neon hover:text-neon transition-colors"
      >
        X
      </a>
    </div>
  );
}
