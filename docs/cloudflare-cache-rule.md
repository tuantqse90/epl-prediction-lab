# Cloudflare Cache Rule — HTML route caching

On Cloudflare Free plan, HTML pages are NOT edge-cached by default, even if
the origin sets `Cache-Control: s-maxage=…`. The origin middleware in
`frontend/middleware.ts` emits the right headers but Cloudflare ignores them
unless you explicitly tell it to via a Cache Rule.

## One-time setup (5 minutes)

1. Cloudflare dashboard → pick `nullshift.sh` (or predictor subdomain) zone
2. Caching → Cache Rules → **Create rule**
3. Rule settings:
   - **Name:** `predictor html edge cache`
   - **If custom filter expression matches:**
     ```
     (http.host eq "predictor.nullshift.sh") and
     (http.request.uri.path matches "^/(proof|blog|leagues|about|faq|last-weekend|compare|stats|history|roi|scorers|table|docs)(/.*)?$")
     ```
   - **Then:**
     - Cache eligibility: **Eligible for cache**
     - Edge TTL: **Respect origin**  (this reads the s-maxage we send)
     - Browser TTL: **Respect origin**
4. Save + Deploy.

## Verify

After deploy, curl with `-I` and look for:

```
cf-cache-status: HIT      ← was DYNAMIC before the rule
age: 42                    ← non-zero means it's coming from edge
```

Expected by-path TTLs (from middleware.ts):

| route | s-maxage | SWR |
|---|---|---|
| /blog, /about, /faq, /docs/* | 3600 | 86400 |
| /proof, /leagues, /leagues/*, /last-weekend | 300 | 900 |
| /compare/*, /stats, /history, /roi, /scorers, /table | 600 | 1800 |
| / (homepage), everything else | 60 | 600 |

## When to bypass

Don't add /match/[id] — live probabilities update during matches, caching
those would serve stale probs. middleware.ts already marks them as `private,
no-cache, no-store` so even a broad Cloudflare rule would respect that.

API endpoints under /api/* are also in the no-cache set via middleware — no
further action needed.

## If CF surge >10k requests/min

Upgrade temporarily to Pro ($20/mo one-time) → enables Argo smart routing
+ higher cache priority. Revert after the spike.
