import Link from "next/link";

import MatchCard from "@/components/MatchCard";
import type { MatchOut } from "@/lib/types";
import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

async function fetchFixtures(leagueCode: string): Promise<MatchOut[]> {
  const qs = new URLSearchParams({
    upcoming_only: "true",
    limit: "20",
    league: leagueCode,
  });
  try {
    const res = await fetch(`${BASE}/api/matches?${qs}`, { cache: "no-store" });
    if (!res.ok) return [];
    return (await res.json()) as MatchOut[];
  } catch {
    return [];
  }
}

export default async function EuropePage() {
  const lang = await getLang();
  const [ucl, uel] = await Promise.all([
    fetchFixtures("UEFA-Champions League"),
    fetchFixtures("UEFA-Europa League"),
  ]);

  return (
    <main className="mx-auto max-w-6xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">europe · club competitions</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "European nights — UCL + UEL",
            vi: "Đêm châu Âu — UCL + UEL",
            th: "คืนแห่งยุโรป",
            zh: "欧战之夜",
            ko: "유럽 경기의 밤",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: "Champions League + Europa League predictions + odds. Model is weaker here than on league play — shorter format, rotated squads, knockout variance. Cup prior (Block 21.6) pulls strengths toward neutral by 10%.",
            vi: "Dự đoán + odds UCL + UEL. Mô hình yếu hơn so với giải VĐQG — format ngắn, xoay vòng cầu thủ, biến động knockout. Cup prior kéo strengths về trung tính 10%.",
            th: "การคาดการณ์ UCL + UEL · โมเดลอ่อนกว่าลีก",
            zh: "欧冠 + 欧联预测 · 模型在欧战弱于联赛",
            ko: "UCL + UEL 예측 · 모델은 리그보다 약함",
          })}
        </p>
      </header>

      <section className="space-y-4">
        <div className="flex items-baseline justify-between">
          <h2 className="font-display text-2xl font-semibold uppercase tracking-tighter">⭐ UCL</h2>
          <p className="font-mono text-xs text-muted">{ucl.length} upcoming</p>
        </div>
        {ucl.length === 0 ? (
          <div className="card text-muted">No upcoming UCL fixtures — run the ingest.</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {ucl.slice(0, 12).map((m) => (
              <MatchCard key={m.id} match={m} lang={lang} />
            ))}
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div className="flex items-baseline justify-between">
          <h2 className="font-display text-2xl font-semibold uppercase tracking-tighter">🏆 UEL</h2>
          <p className="font-mono text-xs text-muted">{uel.length} upcoming</p>
        </div>
        {uel.length === 0 ? (
          <div className="card text-muted">No upcoming UEL fixtures.</div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {uel.slice(0, 12).map((m) => (
              <MatchCard key={m.id} match={m} lang={lang} />
            ))}
          </div>
        )}
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• Fixtures + odds refresh via API-Football Ultra.</p>
        <p>• Every match tagged `competition_type='europe'` → cup prior (Block 21.6) softens favourites.</p>
        <p>• Audience on UCL nights is typically 10× league-night levels.</p>
      </section>
    </main>
  );
}
