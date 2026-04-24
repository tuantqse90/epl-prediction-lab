import Link from "next/link";

import TeamLogo from "@/components/TeamLogo";
import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type TeamAccuracy = {
  slug: string;
  short_name: string;
  name: string;
  league_code: string | null;
  scored: number;
  correct: number;
  accuracy: number;
  mean_log_loss: number;
};

type Response = {
  season: string | null;
  min_sample: number;
  teams: TeamAccuracy[];
};

async function fetchData(): Promise<Response | null> {
  try {
    const res = await fetch(`${BASE}/api/stats/accuracy-by-team?min_sample=10`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return (await res.json()) as Response;
  } catch {
    return null;
  }
}

function pct(x: number) { return `${(x * 100).toFixed(1)}%`; }

export default async function ByTeamPage() {
  const lang = await getLang();
  const data = await fetchData();
  if (!data || data.teams.length === 0) {
    return <main className="mx-auto max-w-3xl px-6 py-12"><div className="card text-muted">—</div></main>;
  }

  const overall = {
    scored: data.teams.reduce((s, t) => s + Number(t.scored), 0),
    correct: data.teams.reduce((s, t) => s + t.correct, 0),
  };
  const overall_acc = overall.scored > 0 ? overall.correct / overall.scored : 0;

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-10">
      <Link href="/benchmark" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Benchmark", vi: "← Benchmark", th: "← Benchmark", zh: "← 基准", ko: "← 벤치마크" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">benchmark · by team</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Where the model is strong — and where it isn't",
            vi: "Model mạnh ở đội nào — và yếu ở đâu",
            th: "โมเดลเก่งกับทีมไหน และอ่อนกับทีมไหน",
            zh: "模型在哪些球队预测好,哪些差",
            ko: "모델이 강한 팀과 약한 팀",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: `Overall accuracy across all tracked teams: ${pct(overall_acc)} (${overall.correct}/${overall.scored}). Teams with unusually high accuracy = easy-to-predict (dominant or predictably bad); unusually low = chaotic (high-variance).`,
            vi: `Accuracy toàn bộ đội theo dõi: ${pct(overall_acc)} (${overall.correct}/${overall.scored}). Đội accuracy cao = dễ dự đoán; thấp = nhiễu.`,
            th: `ความแม่นรวม: ${pct(overall_acc)}`,
            zh: `整体准确度: ${pct(overall_acc)}`,
            ko: `전체 정확도: ${pct(overall_acc)}`,
          })}
        </p>
      </header>

      <section className="card p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[10px] uppercase tracking-wide text-muted">
            <tr className="border-b border-border">
              <th className="px-3 py-3 text-left">
                {tLang(lang, { en: "Team", vi: "Đội", th: "ทีม", zh: "球队", ko: "팀" })}
              </th>
              <th className="px-3 py-3 text-right">n</th>
              <th className="px-3 py-3 text-right">
                {tLang(lang, { en: "Correct", vi: "Đúng", th: "ถูก", zh: "正确", ko: "정답" })}
              </th>
              <th className="px-3 py-3 text-right">
                {tLang(lang, { en: "Accuracy", vi: "Accuracy", th: "ความแม่น", zh: "准确度", ko: "정확도" })}
              </th>
              <th className="px-3 py-3 text-right">log-loss</th>
            </tr>
          </thead>
          <tbody>
            {data.teams.map((t) => {
              const accColor =
                t.accuracy > 0.55 ? "text-neon"
                : t.accuracy < 0.4 ? "text-error"
                : "";
              return (
                <tr key={t.slug} className="border-t border-border-muted">
                  <td className="px-3 py-2">
                    <Link href={`/teams/${t.slug}`} className="flex items-center gap-2 hover:text-neon">
                      <TeamLogo slug={t.slug} name={t.name} size={20} />
                      <span className="font-display uppercase tracking-tighter">{t.short_name}</span>
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">{t.scored}</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">{t.correct}</td>
                  <td className={`px-3 py-2 text-right font-mono tabular-nums ${accColor}`}>
                    {pct(t.accuracy)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums text-muted">
                    {t.mean_log_loss.toFixed(3)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• Every match involving a team counts toward that team's scored+correct</p>
        <p>• Teams with ≥ 10 graded matches only; min_sample param = {data.min_sample}</p>
        <p>• Neon = ≥ 55% accuracy (easy to predict); red = ≤ 40% (chaotic)</p>
      </section>
    </main>
  );
}
