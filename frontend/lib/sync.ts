// Client-side sync helpers — bundle every localStorage key we own into
// a single JSON blob, POST to /api/sync/:pin. Pull replaces local
// state with the server payload.

const OWNED_KEYS = [
  "epl-lab:favorites-v1",
  "epl-lab:betslip-v1",
  "epl-lab:my-picks-v1",
];

export type SyncPayload = Record<string, unknown>;

export function bundleLocalState(): SyncPayload {
  if (typeof window === "undefined") return {};
  const out: SyncPayload = {};
  for (const k of OWNED_KEYS) {
    const raw = window.localStorage.getItem(k);
    if (raw == null) continue;
    try { out[k] = JSON.parse(raw); } catch { out[k] = raw; }
  }
  return out;
}

export function applyPayload(payload: SyncPayload): number {
  if (typeof window === "undefined") return 0;
  let count = 0;
  for (const k of OWNED_KEYS) {
    const v = payload[k];
    if (v === undefined) continue;
    window.localStorage.setItem(k, JSON.stringify(v));
    count += 1;
  }
  // Fire all the change events so pages re-render.
  window.dispatchEvent(new Event("favorites-change"));
  window.dispatchEvent(new Event("betslip-change"));
  window.dispatchEvent(new Event("my-picks-change"));
  return count;
}

export async function pushToPin(pin: string, version = 1): Promise<{ ok: boolean; version?: number; error?: string }> {
  try {
    const res = await fetch(`/api/sync/${encodeURIComponent(pin)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload: bundleLocalState(), version }),
    });
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    const body = await res.json();
    return { ok: true, version: body.version };
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

export async function pullFromPin(pin: string): Promise<{ ok: boolean; applied: number; error?: string }> {
  try {
    const res = await fetch(`/api/sync/${encodeURIComponent(pin)}`);
    if (!res.ok) return { ok: false, applied: 0, error: `HTTP ${res.status}` };
    const body = await res.json();
    if (!body.payload) return { ok: false, applied: 0, error: "PIN has no data yet" };
    const applied = applyPayload(body.payload);
    return { ok: true, applied };
  } catch (e) {
    return { ok: false, applied: 0, error: String(e) };
  }
}
