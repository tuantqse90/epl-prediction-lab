import Link from "next/link";
import { notFound } from "next/navigation";

import TeamLogo from "@/components/TeamLogo";
import { formatKickoff } from "@/lib/date";
import type { Lang } from "@/lib/i18n";
import type { MatchOut } from "@/lib/types";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

// Embed is intentionally self-contained — a partner blog pastes one
// iframe and we render the full picture without pulling in the rest of
// the site chrome.

async function fetchMatch(id: string): Promise<MatchOut | null> {
  try {
    const res = await fetch(`${BASE}/api/matches/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as MatchOut;
  } catch {
    return null;
  }
}

export default async function EmbedMatchPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ lang?: string }>;
}) {
  const { id } = await params;
  const sp = await searchParams;
  const lang = (sp.lang as Lang) || "en";
  const match = await fetchMatch(id);
  if (!match) return notFound();

  const pred = match.prediction;
  const probs = pred
    ? { H: pred.p_home_win, D: pred.p_draw, A: pred.p_away_win }
    : null;
  const pick =
    probs != null
      ? (Object.entries(probs) as Array<[keyof typeof probs, number]>).reduce((a, b) =>
          b[1] > a[1] ? b : a,
        )
      : null;
  const pickLabel = pick
    ? pick[0] === "H"
      ? match.home.short_name
      : pick[0] === "A"
        ? match.away.short_name
        : "Draw"
    : null;

  const pct = (x: number) => `${Math.round(x * 100)}%`;
  const canonicalUrl = `https://predictor.nullshift.sh/match/${match.id}`;

  return (
    <main className="p-4 min-h-screen flex items-center justify-center">
      <section className="w-full max-w-md rounded-lg border border-border bg-surface p-5 space-y-4 shadow-lg">
        <header className="flex items-baseline justify-between">
          <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
            {match.league_code}
          </p>
          <p className="font-mono text-xs text-muted">{formatKickoff(match.kickoff_time, lang)}</p>
        </header>

        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <TeamLogo slug={match.home.slug} name={match.home.name} size={28} />
            <span className="font-display text-xl font-semibold uppercase tracking-tighter truncate">
              {match.home.short_name}
            </span>
          </div>
          <span className="font-mono text-muted text-sm">vs</span>
          <div className="flex items-center gap-2 min-w-0 justify-end">
            <span className="font-display text-xl font-semibold uppercase tracking-tighter truncate text-right">
              {match.away.short_name}
            </span>
            <TeamLogo slug={match.away.slug} name={match.away.name} size={28} />
          </div>
        </div>

        {pred ? (
          <>
            <div className="rounded-full bg-neon/15 px-3 py-1 font-mono text-xs uppercase tracking-wide text-neon text-center">
              Model picks <b>{pickLabel}</b> · {pick ? pct(pick[1]) : ""}
            </div>
            <div className="flex text-xs font-mono">
              <div
                className="py-1 text-center bg-secondary/20"
                style={{ width: `${pred.p_home_win * 100}%` }}
              >
                {pct(pred.p_home_win)}
              </div>
              <div
                className="py-1 text-center bg-muted/20"
                style={{ width: `${pred.p_draw * 100}%` }}
              >
                {pct(pred.p_draw)}
              </div>
              <div
                className="py-1 text-center bg-secondary/20"
                style={{ width: `${pred.p_away_win * 100}%` }}
              >
                {pct(pred.p_away_win)}
              </div>
            </div>
          </>
        ) : (
          <p className="text-muted text-sm">Prediction pending.</p>
        )}

        <footer className="flex items-center justify-between">
          <Link
            href={canonicalUrl}
            target="_blank"
            rel="noopener"
            className="font-mono text-[10px] uppercase tracking-wide text-muted hover:text-neon"
          >
            predictor.nullshift.sh →
          </Link>
        </footer>
      </section>
      {/* Auto-height message to the embed-loader on partner pages. */}
      <script
        dangerouslySetInnerHTML={{
          __html: `
            (function(){
              function post(){
                if (window.parent === window) return;
                var h = document.body.scrollHeight;
                window.parent.postMessage({type:"predlab-height",height:h}, "*");
              }
              window.addEventListener("load", post);
              window.addEventListener("resize", post);
              setTimeout(post, 100);
            })();
          `,
        }}
      />
    </main>
  );
}
