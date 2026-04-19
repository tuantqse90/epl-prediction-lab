"use client";

import { useEffect, useState } from "react";

import { readFavorites } from "@/lib/favorites";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

function urlB64ToUint8Array(base64: string): Uint8Array {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const b64 = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(b64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

type State = "idle" | "unsupported" | "subscribed" | "denied";

export default function PushButton() {
  const [state, setState] = useState<State>("idle");
  const [publicKey, setPublicKey] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      setState("unsupported");
      return;
    }
    if (Notification.permission === "denied") {
      setState("denied");
      return;
    }
    navigator.serviceWorker.ready.then((reg) => {
      reg.pushManager.getSubscription().then((sub) => {
        if (sub) setState("subscribed");
      });
    });
    fetch(`${BASE}/api/push/config`)
      .then((r) => r.json())
      .then((d: { public_key: string | null }) => setPublicKey(d.public_key));
  }, []);

  async function subscribe() {
    if (!publicKey) return;
    try {
      const reg = await navigator.serviceWorker.register("/sw.js");
      const perm = await Notification.requestPermission();
      if (perm !== "granted") {
        setState("denied");
        return;
      }
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlB64ToUint8Array(publicKey) as BufferSource,
      });
      const payload = sub.toJSON();
      await fetch(`${BASE}/api/push/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint: payload.endpoint,
          keys: payload.keys,
          teams: readFavorites(),
          user_agent: navigator.userAgent,
        }),
      });
      setState("subscribed");
    } catch (e) {
      console.warn("push subscribe failed", e);
    }
  }

  async function unsubscribe() {
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
      const { endpoint } = sub.toJSON();
      await fetch(`${BASE}/api/push/unsubscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ endpoint }),
      });
      await sub.unsubscribe();
    }
    setState("idle");
  }

  if (state === "unsupported") {
    return (
      <span className="font-mono text-[10px] uppercase text-muted">
        Push not supported
      </span>
    );
  }
  if (state === "denied") {
    return (
      <span className="font-mono text-[10px] uppercase text-error">
        Notifications blocked
      </span>
    );
  }
  if (state === "subscribed") {
    return (
      <button
        type="button"
        onClick={unsubscribe}
        className="inline-flex items-center gap-1 rounded-full bg-neon px-3 py-1 font-mono text-xs uppercase tracking-wide text-on-neon hover:bg-neon-dim"
      >
        🔔 Notifications on
      </button>
    );
  }
  return (
    <button
      type="button"
      onClick={subscribe}
      disabled={!publicKey}
      className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1 font-mono text-xs uppercase tracking-wide text-secondary hover:border-neon hover:text-neon disabled:opacity-50"
    >
      🔔 Enable goal alerts
    </button>
  );
}
