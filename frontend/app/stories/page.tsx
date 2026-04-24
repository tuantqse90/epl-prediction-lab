import type { Metadata } from "next";
import Link from "next/link";

import { getLang, tFor } from "@/lib/i18n-server";

export const metadata: Metadata = {
  title: "Match Stories · predictor.nullshift.sh",
  description:
    "Post-match narratives for every finished fixture — what happened, what xG said, whether the model was right.",
};

type StoryCard = {
  match_id: number;
  kickoff: string;
  league_code: string | null;
  home_slug: string;
  home_short: string;
  home_goals: number;
  away_slug: string;
  away_short: string;
  away_goals: number;
  excerpt: string;
  generated_at: string | null;
};

type StoriesOut = { total: number; stories: StoryCard[] };

async function fetchStories(): Promise<StoriesOut> {
  const base =
    typeof window === "undefined"
      ? process.env.SERVER_API_URL ?? "http://localhost:8000"
      : process.env.NEXT_PUBLIC_API_URL ?? "";
  try {
    const res = await fetch(`${base}/api/stats/stories?limit=50`, {
      next: { revalidate: 600 },
    });
    if (!res.ok) return { total: 0, stories: [] };
    return (await res.json()) as StoriesOut;
  } catch {
    return { total: 0, stories: [] };
  }
}

const LEAGUE_EMOJI: Record<string, string> = {
  "ENG-Premier League": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
  "ESP-La Liga": "🇪🇸",
  "ITA-Serie A": "🇮🇹",
  "GER-Bundesliga": "🇩🇪",
  "FRA-Ligue 1": "🇫🇷",
  "UEFA-Champions League": "⭐",
  "UEFA-Europa League": "🏆",
};

export default async function StoriesIndex() {
  const lang = await getLang();
  const t = tFor(lang);
  const { total, stories } = await fetchStories();

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">
        {t("common.back")}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-neon">stories</p>
        <h1 className="headline-hero">
          {lang === "vi" ? "Câu chuyện mỗi trận" : "Stories, match by match"}
        </h1>
        <p className="text-secondary max-w-2xl">
          {lang === "vi"
            ? "Mỗi trận đã kết thúc có một bài narrative ngắn — xG nói gì, model đoán đúng hay sai, và bước ngoặt nằm ở đâu. AI viết, số liệu là thật."
            : "Every finished match has a short narrative — what xG said, whether the model was right, where the turning point was. AI-written, numbers are real."}
        </p>
        <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
          {total.toLocaleString()} {lang === "vi" ? "bài đã viết" : "stories live"}
        </p>
      </header>

      <section className="space-y-4">
        {stories.length === 0 ? (
          <div className="card text-muted">
            {lang === "vi"
              ? "Chưa có bài nào. Cron daily sẽ generate dần."
              : "No stories yet. Daily cron populates these."}
          </div>
        ) : (
          stories.map((s) => (
            <Link
              key={s.match_id}
              href={`/match/${s.match_id}`}
              className="card block space-y-3 hover:border-neon transition-colors"
            >
              <div className="flex items-baseline justify-between gap-3 flex-wrap">
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
                  {s.league_code ? `${LEAGUE_EMOJI[s.league_code] ?? "⚽"} ${s.league_code}` : "⚽"}
                </span>
                <span className="font-mono text-[10px] text-muted">
                  {s.kickoff.slice(0, 10)}
                </span>
              </div>
              <h2 className="font-display text-xl md:text-2xl font-semibold text-primary leading-tight">
                {s.home_short} {s.home_goals}
                <span className="text-muted mx-2">–</span>
                {s.away_goals} {s.away_short}
              </h2>
              <p className="text-secondary text-sm leading-relaxed">{s.excerpt}</p>
            </Link>
          ))
        )}
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• {lang === "vi" ? "Nguồn: " : "Source: "}
          <Link href="/docs/model" className="hover:text-neon">
            {lang === "vi" ? "Cách model hoạt động" : "How the model works"}
          </Link>
        </p>
        <p>• {lang === "vi" ? "Số liệu từ Understat + API-Football" : "Stats from Understat + API-Football"}</p>
      </section>
    </main>
  );
}
