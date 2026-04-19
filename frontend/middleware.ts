import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Cache-Control policy. Cloudflare (the CDN in front of this site) honors
// s-maxage and serves from edge, dramatically reducing origin load during
// traffic surges. Dynamic pages keep s-maxage low + SWR so user-visible
// staleness is bounded while burst load stays manageable.
// Routes that read the `league` cookie must NOT be shared-cached — two
// users with different cookie values would otherwise be served each
// other's HTML. `private, no-store` forces both browsers and CDNs to
// bypass caching entirely for these paths.
const LEAGUE_SCOPED_NOCACHE = "private, no-store, no-cache, must-revalidate";

const POLICIES: Array<{ match: RegExp; value: string }> = [
  // Blog posts: content rarely changes, happy to cache edge for 1h
  { match: /^\/blog(\/[^/]+)?$/, value: "public, s-maxage=3600, stale-while-revalidate=86400" },
  // Static-ish pages: about / faq / docs
  { match: /^\/(about|faq|docs\/[^/]+)$/, value: "public, s-maxage=3600, stale-while-revalidate=86400" },
  // Leagues index — static list of leagues, safe to cache
  { match: /^\/leagues$/, value: "public, s-maxage=3600, stale-while-revalidate=86400" },
  // Per-league page: league in URL, not cookie → safe to cache
  { match: /^\/leagues\/[a-z]+$/, value: "public, s-maxage=300, stale-while-revalidate=900" },
  // Proof: reads league cookie → cannot be shared-cached
  { match: /^\/proof$/, value: LEAGUE_SCOPED_NOCACHE },
  // Last-weekend: reads league cookie
  { match: /^\/last-weekend$/, value: LEAGUE_SCOPED_NOCACHE },
  // Compare h2h: URL-param driven, safe to cache
  { match: /^\/compare\/[^/]+\/[^/]+$/, value: "public, s-maxage=600, stale-while-revalidate=1800" },
  // History / stats / roi / scorers / table / news: all read league cookie
  { match: /^\/(history|stats|roi|scorers|table|news)$/, value: LEAGUE_SCOPED_NOCACHE },
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

  // Homepage also reads the league cookie — explicit no-store policy.
  if (pathname === "/") {
    res.headers.set("Cache-Control", LEAGUE_SCOPED_NOCACHE);
    return res;
  }
  // Default: 60s edge cache with generous SWR. Anything not matched above
  // is assumed cookie-independent (marketing/static content).
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
