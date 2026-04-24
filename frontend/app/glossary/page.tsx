import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const metadata = {
  title: "Glossary — xG, CLV, Kelly, Devig · predictor.nullshift.sh",
  description: "Plain-language definitions of every analytics term on this site.",
};

type Term = {
  term: string;
  def_en: string;
  def_vi: string;
  example_en?: string;
};

const TERMS: Term[] = [
  {
    term: "xG (expected goals)",
    def_en:
      "A per-shot estimate of the probability it becomes a goal, given location, body part, assist type, and defensive pressure. Summed across a match, xG measures the quality of chances, independent of whether they actually scored.",
    def_vi:
      "Ước lượng xác suất mỗi cú sút thành bàn, dựa vào vị trí, bộ phận, kiểu kiến tạo, áp lực. Cộng cả trận → đo chất lượng cơ hội, không phụ thuộc việc ghi bàn.",
    example_en: "Team scores 3 goals from 1.4 xG → lucky finishing. Regresses over time.",
  },
  {
    term: "Edge",
    def_en:
      "model_prob × odds − 1. A positive edge means the odds offered more than what the model thinks the true probability is. Edge > 0 = positive expected value, before variance.",
    def_vi:
      "model_prob × odds − 1. Edge dương = odds được trả lớn hơn xác suất mô hình nghĩ là thật. Edge > 0 = EV dương (chưa tính variance).",
  },
  {
    term: "Closing-line value (CLV)",
    def_en:
      "The gap between the odds you got and the odds when the line closed at kickoff. Positive CLV means the market moved toward your side after you bet — strongest long-term signal of a sharp pick.",
    def_vi:
      "Khoảng cách giữa odds bạn đặt và odds khi line đóng lúc kickoff. CLV dương = thị trường di chuyển về phía bạn sau khi bạn bet.",
  },
  {
    term: "Devig (devigged probability)",
    def_en:
      "Book odds come with the bookmaker's margin baked in (Σ(1/odds) ≈ 1.05 typical). Devigging rescales the three implied probabilities to sum to 1, giving an estimate of the 'true' market-implied probability.",
    def_vi:
      "Odds có margin của nhà cái trong đó (Σ(1/odds) ≈ 1.05). Devig chia đều để tổng = 1, cho xác suất thị trường 'thật'.",
  },
  {
    term: "Kelly stake",
    def_en:
      "The growth-optimal fraction of bankroll to wager, given edge and odds. Full Kelly punishes estimate error; most practitioners use fractional (0.25 Kelly) to reduce variance.",
    def_vi:
      "Phần bankroll tối ưu tăng trưởng, dựa vào edge + odds. Full Kelly trừng phạt sai số; đa số dùng Fractional (0.25 Kelly) để giảm biến động.",
  },
  {
    term: "Brier score",
    def_en:
      "Mean squared error on probabilistic predictions. 0 = perfect, 0.25 = random coin-flip on binary outcomes. Lower is better.",
    def_vi:
      "Sai số bình phương trung bình trên dự đoán xác suất. 0 = hoàn hảo, 0.25 = coin-flip. Thấp hơn = tốt hơn.",
  },
  {
    term: "Log-loss",
    def_en:
      "Penalty on predicted probability for the actual outcome: -log(p_actual). Uniform 3-way baseline = 1.099. Strongly punishes confident misses.",
    def_vi:
      "Phạt theo xác suất mô hình gán cho kết quả thật: -log(p_actual). Baseline uniform 3-way = 1.099.",
  },
  {
    term: "Poisson + Dixon-Coles",
    def_en:
      "We model goals as independent Poisson(λ) draws per side (λ from team attack × opponent defense). Dixon-Coles correction ρ adjusts low-scoreline probabilities where independence breaks down.",
    def_vi:
      "Mỗi bên bốc Poisson(λ) bàn. λ = tấn công × phòng ngự đối. Dixon-Coles ρ điều chỉnh xác suất tỷ số thấp nơi giả định độc lập bị phá.",
  },
  {
    term: "Elo",
    def_en:
      "Chess-style rating updated per match, weighted by goal difference. Home-field advantage baked in. One of the three ensemble legs.",
    def_vi:
      "Rating kiểu cờ vua, cập nhật mỗi trận, trọng số theo hiệu số bàn. Home advantage built-in. 1 trong 3 leg của ensemble.",
  },
  {
    term: "Asian handicap (AH)",
    def_en:
      "A spread-betting line: team starts with ±X goals. Eliminates the draw. Common values ±0.25 / ±0.5 / ±0.75 let bookmakers price tight favourites.",
    def_vi:
      "Cược chấp: đội được +/- X bàn. Loại trừ hoà. Giá trị ±0.25 / ±0.5 / ±0.75 để nhà cái định giá đội mạnh.",
  },
];

export default async function GlossaryPage() {
  const lang = await getLang();
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>
      <header>
        <p className="font-mono text-xs text-muted">docs · glossary</p>
        <h1 className="headline-section">
          {tLang(lang, { en: "Glossary", vi: "Từ điển thuật ngữ", th: "อภิธานศัพท์", zh: "术语表", ko: "용어집" })}
        </h1>
      </header>
      <dl className="space-y-6">
        {TERMS.map((t) => (
          <div key={t.term} className="card space-y-2">
            <dt className="font-display font-semibold text-lg">{t.term}</dt>
            <dd className="text-secondary">{lang === "vi" ? t.def_vi : t.def_en}</dd>
            {t.example_en && lang !== "vi" && (
              <p className="font-mono text-[11px] text-muted italic">Example: {t.example_en}</p>
            )}
          </div>
        ))}
      </dl>
    </main>
  );
}
