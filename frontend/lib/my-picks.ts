// My-picks ledger. Permanent record of real bets the user placed, vs the
// betslip which is a scratchpad for composing a new parlay. Keyed on
// (match_id, outcome, placed_at) so duplicate stakes on the same match
// don't collide. Fully localStorage — no server, no account.

const KEY = "epl-lab:my-picks-v1";

export type MyPick = {
  id: string;               // stable unique; generated at add time
  match_id: number;
  outcome: "H" | "D" | "A";
  odds: number;
  stake: number;            // in user-defined units, usually 1
  placed_at: string;        // ISO
  note?: string;
  // Resolution fields — written when the pick settles.
  settled: boolean;
  hit: boolean | null;      // null = pending, true = won, false = lost
  pnl: number | null;       // stake × (odds - 1) on hit, -stake on loss
};

export function readPicks(): MyPick[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (p): p is MyPick =>
        p && typeof p === "object" &&
        typeof p.id === "string" &&
        typeof p.match_id === "number" &&
        typeof p.odds === "number" &&
        ["H", "D", "A"].includes(p.outcome),
    );
  } catch {
    return [];
  }
}

function write(list: MyPick[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(list));
  window.dispatchEvent(new Event("my-picks-change"));
}

function newId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function addPick(p: Omit<MyPick, "id" | "placed_at" | "settled" | "hit" | "pnl">): MyPick {
  const picks = readPicks();
  const entry: MyPick = {
    ...p,
    id: newId(),
    placed_at: new Date().toISOString(),
    settled: false,
    hit: null,
    pnl: null,
  };
  write([...picks, entry]);
  return entry;
}

export function removePick(id: string): void {
  write(readPicks().filter((p) => p.id !== id));
}

export function settlePick(id: string, hit: boolean, odds?: number): void {
  const picks = readPicks();
  const next = picks.map((p) => {
    if (p.id !== id) return p;
    const o = odds ?? p.odds;
    return {
      ...p,
      settled: true,
      hit,
      pnl: hit ? p.stake * (o - 1) : -p.stake,
    };
  });
  write(next);
}

export function summary(picks: MyPick[]) {
  const settled = picks.filter((p) => p.settled);
  const hits = settled.filter((p) => p.hit).length;
  const pnl = settled.reduce((s, p) => s + (p.pnl ?? 0), 0);
  const staked = settled.reduce((s, p) => s + p.stake, 0);
  return {
    total: picks.length,
    settled: settled.length,
    hits,
    losses: settled.length - hits,
    pending: picks.length - settled.length,
    pnl,
    roi: staked > 0 ? (pnl / staked) * 100 : 0,
  };
}
