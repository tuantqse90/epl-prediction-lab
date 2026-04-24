import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const metadata = {
  title: "Public API · predictor.nullshift.sh",
  description: "Curated subset of the Prediction Lab API with curl / Python / JS examples.",
};

type Endpoint = {
  method: "GET" | "POST";
  path: string;
  desc: string;
  example_path: string;
};

const ENDPOINTS: Endpoint[] = [
  { method: "GET", path: "/api/matches", desc: "Upcoming matches + predictions + best odds.", example_path: "/api/matches?upcoming_only=true&limit=10" },
  { method: "GET", path: "/api/matches/:id", desc: "Full match detail — prediction, odds, lineups, events.", example_path: "/api/matches/3352" },
  { method: "GET", path: "/api/stats/roi", desc: "Running ROI on flat-stake 5pp+ edges.", example_path: "/api/stats/roi?threshold=0.05&window=30" },
  { method: "GET", path: "/api/stats/title-race", desc: "Monte Carlo finish probabilities per team.", example_path: "/api/stats/title-race?league=ENG-Premier+League&n=5000" },
  { method: "GET", path: "/api/stats/top-scorer-race", desc: "Golden Boot / Pichichi projection.", example_path: "/api/stats/top-scorer-race?league=ENG-Premier+League" },
  { method: "GET", path: "/api/stats/power-rankings", desc: "Elo-sorted table + week-over-week deltas.", example_path: "/api/stats/power-rankings?league=ENG-Premier+League" },
  { method: "GET", path: "/api/stats/arbs", desc: "Positive-profit cross-book arbs.", example_path: "/api/stats/arbs?min_profit_pct=0.2" },
  { method: "GET", path: "/api/stats/middles", desc: "O/U middle pairs.", example_path: "/api/stats/middles" },
  { method: "GET", path: "/api/stats/calibration", desc: "Accuracy + log-loss per season-week.", example_path: "/api/stats/calibration?season=2025-26" },
  { method: "GET", path: "/api/stats/reliability", desc: "Reliability diagram data (Brier + per-decile hit rate).", example_path: "/api/stats/reliability?n_bins=10" },
  { method: "GET", path: "/api/stats/equity-curve", desc: "7-season flat-stake P&L.", example_path: "/api/stats/equity-curve" },
  { method: "GET", path: "/api/developer/status", desc: "Your API key's remaining quota.", example_path: "/api/developer/status" },
];

export default async function ApiDocsPage() {
  const lang = await getLang();
  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-8 blog-prose">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>
      <header>
        <p className="font-mono text-xs text-muted">docs · public API</p>
        <h1 className="headline-section">Public API</h1>
        <p className="text-secondary">
          The curated subset below returns JSON you can build on. Unauthenticated access is
          rate-limited at the Cloudflare edge; a per-key tier with 60 req/min is available —
          contact for an API key. Full OpenAPI schema at <a href="/openapi.json" className="hover:text-neon">/openapi.json</a>.
        </p>
      </header>

      <section className="space-y-4">
        <h2>Authentication</h2>
        <p>Pass your key in an <code>Authorization: Bearer pl_xxx</code> header. The key quota, prefix, and remaining budget are available at <code>GET /api/developer/status</code>.</p>
        <pre className="bg-raised p-3 rounded overflow-x-auto text-sm font-mono">{`curl -H "Authorization: Bearer pl_xxx" \\
     https://predictor.nullshift.sh/api/developer/status`}</pre>
      </section>

      <section className="space-y-4">
        <h2>Endpoints</h2>
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-wide text-muted">
            <tr className="border-b border-border">
              <th className="py-2 text-left">Method</th>
              <th className="py-2 text-left">Path</th>
              <th className="py-2 text-left">Description</th>
              <th className="py-2 text-left">Try</th>
            </tr>
          </thead>
          <tbody>
            {ENDPOINTS.map((e) => (
              <tr key={e.path} className="border-t border-border-muted">
                <td className="py-2 pr-3 font-mono text-xs text-neon">{e.method}</td>
                <td className="py-2 pr-3 font-mono text-xs">{e.path}</td>
                <td className="py-2 pr-3 text-secondary">{e.desc}</td>
                <td className="py-2 pr-3">
                  <a className="font-mono text-xs hover:text-neon" target="_blank" href={e.example_path} rel="noopener">open →</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="space-y-4">
        <h2>Example — Python</h2>
        <pre className="bg-raised p-3 rounded overflow-x-auto text-sm font-mono">{`import httpx

r = httpx.get(
    "https://predictor.nullshift.sh/api/stats/title-race",
    params={"league": "ENG-Premier League", "n": 5000},
    headers={"Authorization": "Bearer pl_xxx"},
)
for team in r.json()["teams"][:5]:
    print(team["short_name"], f'{team["p_champions"]*100:.1f}%')`}</pre>
      </section>

      <section className="space-y-4">
        <h2>Webhooks</h2>
        <p>
          Register a URL via <code>POST /api/developer/webhooks</code> (bearer-auth'd) to receive POSTs
          on <code>prediction_created</code> and <code>match_final</code> events.
        </p>
      </section>
    </main>
  );
}
