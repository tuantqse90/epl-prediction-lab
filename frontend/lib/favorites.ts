// localStorage-backed favorites store. Client-only — the server renders
// without favorites knowledge, then the FollowStar/FavoritesSection
// components re-hydrate with the user's picks on mount.

const KEY = "epl-lab:favorites-v1";

export function readFavorites(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((x): x is string => typeof x === "string");
  } catch {
    return [];
  }
}

function writeFavorites(list: string[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(list));
  window.dispatchEvent(new Event("favorites-change"));
}

export function addFavorite(slug: string): void {
  const list = readFavorites();
  if (!list.includes(slug)) writeFavorites([...list, slug]);
}

export function removeFavorite(slug: string): void {
  writeFavorites(readFavorites().filter((s) => s !== slug));
}

export function toggleFavorite(slug: string): boolean {
  const list = readFavorites();
  if (list.includes(slug)) {
    writeFavorites(list.filter((s) => s !== slug));
    return false;
  }
  writeFavorites([...list, slug]);
  return true;
}
