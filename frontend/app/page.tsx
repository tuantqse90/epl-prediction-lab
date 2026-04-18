import MatchCard from "@/components/MatchCard";
import QuickPicks from "@/components/QuickPicks";
import { listMatches } from "@/lib/api";
import { getLang, tFor } from "@/lib/i18n-server";
import type { MatchOut } from "@/lib/types";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Accuracy = {
  season: string;
  scored: number;
  correct: number;
  accuracy: number;
  baseline_home_accuracy: number;
  mean_log_loss: number;
  uniform_log_loss: number;
};

async function fetchAccuracy(): Promise<Accuracy | null> {
  try {
    const res = await fetch(`${BASE}/api/stats/accuracy?season=2025-26`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as Accuracy;
  } catch {
    return null;
  }
}

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const lang = await getLang();
  const t = tFor(lang);

  let matches: MatchOut[] = [];
  let error: string | null = null;
  try {
    matches = await listMatches({ upcomingOnly: true, limit: 20 });
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }
  const acc = await fetchAccuracy();

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-10">
      <header className="space-y-3">
        <h1 className="headline-hero">{t("dash.headline")}</h1>
        <p className="max-w-2xl text-secondary text-base md:text-lg">{t("dash.subhead")}</p>
      </header>

      {error && (
        <div className="card text-error font-mono text-sm">
          <span className="label block mb-1">{t("dash.apiError")}</span>
          {error}
        </div>
      )}

      {!error && matches.length === 0 && (
        <div className="card text-secondary">{t("dash.empty")}</div>
      )}

      {matches.length > 0 && <QuickPicks matches={matches} lang={lang} />}

      {acc && acc.scored > 0 && (
        <section className="card grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="label">{t("dash.stat.accuracy")}</p>
            <p className="stat text-neon">{Math.round(acc.accuracy * 100)}%</p>
          </div>
          <div>
            <p className="label">{t("dash.stat.baseline")}</p>
            <p className="stat">{Math.round(acc.baseline_home_accuracy * 100)}%</p>
          </div>
          <div>
            <p className="label">{t("dash.stat.logloss")}</p>
            <p className="stat">{acc.mean_log_loss.toFixed(3)}</p>
          </div>
          <div>
            <p className="label">{t("dash.stat.matches")}</p>
            <p className="stat">{acc.scored}</p>
          </div>
        </section>
      )}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {matches.map((m) => (
          <MatchCard key={m.id} match={m} lang={lang} />
        ))}
      </section>
    </main>
  );
}
