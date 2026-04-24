// Feature-flag client helper. Fetches /api/flags once per page and caches
// in sessionStorage. Not reactive — refresh to pick up flag changes.

type Flag = { key: string; enabled: boolean; rollout_pct: number };

const KEY = "epl-lab:flags-cache";

async function load(): Promise<Record<string, Flag>> {
  if (typeof window === "undefined") return {};
  const cached = window.sessionStorage.getItem(KEY);
  if (cached) {
    try { return JSON.parse(cached); } catch { /* fallthrough */ }
  }
  try {
    const res = await fetch("/api/flags");
    if (!res.ok) return {};
    const arr: Flag[] = await res.json();
    const map: Record<string, Flag> = {};
    for (const f of arr) map[f.key] = f;
    window.sessionStorage.setItem(KEY, JSON.stringify(map));
    return map;
  } catch {
    return {};
  }
}

let cachedPromise: Promise<Record<string, Flag>> | null = null;

export async function isEnabled(key: string): Promise<boolean> {
  cachedPromise ||= load();
  const flags = await cachedPromise;
  const f = flags[key];
  if (!f) return false;
  if (!f.enabled) return false;
  if (f.rollout_pct >= 100) return true;
  // Simple sticky bucket: hash session id mod 100 < rollout_pct.
  if (typeof window === "undefined") return false;
  const sid = window.localStorage.getItem("epl-lab:session-id") || "anon";
  let hash = 0;
  for (let i = 0; i < sid.length; i++) hash = (hash * 31 + sid.charCodeAt(i)) | 0;
  return Math.abs(hash) % 100 < f.rollout_pct;
}
