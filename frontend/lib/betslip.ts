export type BetslipEntry = {
  match_id: number;
  outcome: "H" | "D" | "A";
  odds: number;
  stake: number;        // units, default 1
  added_at: string;     // ISO
};

const KEY = "epl-lab:betslip-v1";

export function readSlip(): BetslipEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (x): x is BetslipEntry =>
        x &&
        typeof x === "object" &&
        typeof x.match_id === "number" &&
        typeof x.odds === "number" &&
        ["H", "D", "A"].includes(x.outcome),
    );
  } catch {
    return [];
  }
}

function write(list: BetslipEntry[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(list));
  window.dispatchEvent(new Event("betslip-change"));
}

function key(entry: Pick<BetslipEntry, "match_id" | "outcome">): string {
  return `${entry.match_id}:${entry.outcome}`;
}

export function hasPick(match_id: number, outcome: "H" | "D" | "A"): boolean {
  return readSlip().some((e) => e.match_id === match_id && e.outcome === outcome);
}

export function addPick(entry: Omit<BetslipEntry, "added_at" | "stake">): void {
  const list = readSlip();
  if (list.some((e) => key(e) === key(entry))) return;
  write([
    ...list,
    { ...entry, stake: 1, added_at: new Date().toISOString() },
  ]);
}

export function removePick(match_id: number, outcome: "H" | "D" | "A"): void {
  write(readSlip().filter((e) => !(e.match_id === match_id && e.outcome === outcome)));
}

export function togglePick(entry: Omit<BetslipEntry, "added_at" | "stake">): boolean {
  if (hasPick(entry.match_id, entry.outcome)) {
    removePick(entry.match_id, entry.outcome);
    return false;
  }
  addPick(entry);
  return true;
}
