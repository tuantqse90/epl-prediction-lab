import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Cache-Control policy. Cloudflare (the CDN in front of this site) honors
// s-maxage and serves from edge, dramatically reducing origin load during
// traffic surges. Dynamic pages keep s-maxage low + SWR so user-visible
// staleness is bounded while burst load stays manageable.
const POLICIES: Array<{ match: RegExp; value: string }> = [
  // Blog posts: content rarely changes, happy to cache edge for 1h
  { match: /^\/blog(\/[^/]+)?$/, value: "public, s-maxage=3600, stale-while-revalidate=86400" },
  // Static-ish pages: about / faq / docs
  { match: /^\/(about|faq|docs\/[^/]+)$/, value: "public, s-maxage=3600, stale-while-revalidate=86400" },
  // Leagues index + per-league: real data, refresh every 5 min
  { match: /^\/leagues(\/[a-z]+)?$/, value: "public, s-maxage=300, stale-while-revalidate=900" },
  // Proof: trust page, ok to cache 5 min
  { match: /^\/proof$/, value: "public, s-maxage=300, stale-while-revalidate=900" },
  // Last-weekend: daily-moving numbers, 5 min
  { match: /^\/last-weekend$/, value: "public, s-maxage=300, stale-while-revalidate=900" },
  // Compare h2h: exploratory, 10 min
  { match: /^\/compare\/[^/]+\/[^/]+$/, value: "public, s-maxage=600, stale-while-revalidate=1800" },
  // History / stats / roi / scorers: weekly-moving, cache 10 min
  { match: /^\/(history|stats|roi|scorers|table)$/, value: "public, s-maxage=600, stale-while-revalidate=1800" },
];

// Routes that must NEVER be edge-cached. These either mutate state, read
// cookies, or serve user-specific data.
const NO_CACHE: RegExp[] = [
  /^\/admin/,
  /^\/betslip/,
  /^\/api\/(.*)/,
  /^\/match\/[0-9]+$/, // live probability updates during matches
];

export function middleware(req: NextRequest) {
  const res = NextResponse.next();
  const { pathname } = req.nextUrl;

  if (NO_CACHE.some((r) => r.test(pathname))) {
    res.headers.set("Cache-Control", "private, no-cache, no-store, must-revalidate");
    return res;
  }

  for (const p of POLICIES) {
    if (p.match.test(pathname)) {
      res.headers.set("Cache-Control", p.value);
      res.headers.set("CDN-Cache-Control", p.value);
      return res;
    }
  }

  // Default: 60s edge cache with generous SWR. Homepage and anything else.
  res.headers.set("Cache-Control", "public, s-maxage=60, stale-while-revalidate=600");
  return res;
}

// Skip Next's static file server and image optimizer — we only care about
// route handlers and page paths.
export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon|icon|apple-icon|manifest|robots.txt|sitemap|.*\\.(?:png|jpg|jpeg|svg|webp|ico|xml|txt)$).*)",
  ],
};
