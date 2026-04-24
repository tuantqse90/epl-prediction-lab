import type { Metadata } from "next";
import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { getLang, tFor } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

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
          {tLang(lang, {
            en: "Stories, match by match",
            vi: "Câu chuyện mỗi trận",
            th: "เรื่องราวทุกแมตช์",
            zh: "每场比赛的故事",
            ko: "경기별 이야기",
          })}
        </h1>
        <p className="text-secondary max-w-2xl">
          {tLang(lang, {
            en: "Every finished match has a short narrative — what xG said, whether the model was right, where the turning point was. AI-written, numbers are real.",
            vi: "Mỗi trận đã kết thúc có một bài narrative ngắn — xG nói gì, model đoán đúng hay sai, và bước ngoặt nằm ở đâu. AI viết, số liệu là thật.",
            th: "ทุกแมตช์ที่จบแล้วมีเรื่องเล่า xG + model ถูกหรือผิด",
            zh: "每场已结束的比赛都有一篇简短叙事 · xG 说了什么 · 模型是否正确",
            ko: "끝난 경기마다 짧은 서사 · xG + 모델 적중 여부",
          })}
        </p>
        <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
          {total.toLocaleString()} {tLang(lang, {
            en: "stories live",
            vi: "bài đã viết",
            th: "เรื่อง",
            zh: "篇",
            ko: "개",
          })}
        </p>
      </header>

      <section className="space-y-4">
        {stories.length === 0 ? (
          <div className="card text-muted">
            {tLang(lang, {
              en: "No stories yet. Daily cron populates these.",
              vi: "Chưa có bài nào. Cron daily sẽ generate dần.",
              th: "ยังไม่มีเรื่อง",
              zh: "暂无故事",
              ko: "아직 이야기 없음",
            })}
          </div>
        ) : (
          stories.map((s) => {
            const hit =
              s.home_goals > s.away_goals
                ? "H"
                : s.home_goals < s.away_goals
                ? "A"
                : "D";
            return (
              <Link
                key={s.match_id}
                href={`/match/${s.match_id}`}
                className="card block space-y-4 hover:border-neon transition-colors"
              >
                <div className="flex items-baseline justify-between gap-3 flex-wrap">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-muted">
                    {s.league_code ? `${LEAGUE_EMOJI[s.league_code] ?? "⚽"} ${s.league_code}` : "⚽"}
                  </span>
                  <span className="font-mono text-[10px] text-muted">
                    {s.kickoff.slice(0, 10)}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <TeamLogo slug={s.home_slug} name={s.home_short} size={40} />
                    <span
                      className={`font-display text-xl md:text-2xl font-semibold uppercase tracking-tight truncate ${
                        hit === "H" ? "text-primary" : "text-secondary"
                      }`}
                    >
                      {s.home_short}
                    </span>
                  </div>
                  <div className="font-display text-3xl md:text-4xl font-bold tabular-nums shrink-0 text-primary">
                    {s.home_goals}
                    <span className="text-muted mx-2">–</span>
                    {s.away_goals}
                  </div>
                  <div className="flex items-center gap-3 flex-1 min-w-0 justify-end">
                    <span
                      className={`font-display text-xl md:text-2xl font-semibold uppercase tracking-tight truncate text-right ${
                        hit === "A" ? "text-primary" : "text-secondary"
                      }`}
                    >
                      {s.away_short}
                    </span>
                    <TeamLogo slug={s.away_slug} name={s.away_short} size={40} />
                  </div>
                </div>
                <p className="text-secondary text-sm leading-relaxed">{s.excerpt}</p>
              </Link>
            );
          })
        )}
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• <Link href="/docs/model" className="hover:text-neon">
            {tLang(lang, {
              en: "How the model works",
              vi: "Cách model hoạt động",
              th: "โมเดลทำงานยังไง",
              zh: "模型原理",
              ko: "모델 구조",
            })}
          </Link>
        </p>
        <p>• {tLang(lang, {
          en: "Stats from Understat + API-Football",
          vi: "Số liệu từ Understat + API-Football",
          th: "ข้อมูลจาก Understat + API-Football",
          zh: "数据来自 Understat + API-Football",
          ko: "데이터 Understat + API-Football",
        })}</p>
      </section>
    </main>
  );
}
