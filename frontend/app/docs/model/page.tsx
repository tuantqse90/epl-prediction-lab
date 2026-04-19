import Link from "next/link";

import { getLang, tFor } from "@/lib/i18n-server";

export const dynamic = "force-dynamic";

type Content = {
  title: string;
  subhead: string;
  sections: Array<{ heading: string; body: string }>;
};

const EN: Content = {
  title: "How the model works",
  subhead:
    "A short tour of the math and data behind every prediction on this site.",
  sections: [
    {
      heading: "1 · xG, not scores",
      body:
        "Goals are noisy — a single bad deflection can flip a 0-1. Expected goals (xG) measure shot *quality* regardless of whether the ball went in. We ingest every team's xG for and against across the last 12 matches from Understat, then split each team's strength into an attack coefficient (how much xG they generate vs league average) and a defense coefficient (how much xG they concede). Recent matches count more than ancient ones.",
    },
    {
      heading: "2 · Poisson + Dixon-Coles",
      body:
        "Given each side's attack/defense plus league average, we compute expected goals for this match: λ_home and λ_away. A pair of Poisson distributions then gives every possible scoreline's probability. Because 1-1/0-0/1-0/0-1 draws are slightly more common than independent Poisson assumes (teams play conservatively at low scores), we apply a Dixon-Coles correction (ρ = −0.15) to nudge those four cells up, keeping the rest honest.",
    },
    {
      heading: "3 · Temperature scaling",
      body:
        "Raw model probabilities tend to be too confident on chalk and too hesitant on underdogs. We scale the final 3-way distribution through a softmax temperature T = 1.35 — a one-parameter fix fitted on historical accuracy that flattens confidence into better-calibrated numbers. You see the effect in the ratios displayed, not in the scoreline heatmap.",
    },
    {
      heading: "4 · Injury adjustment",
      body:
        "Each team's λ is shrunk by a fraction of the xG currently missing to reported absentees. If Salah (15 xG) and Saka (9 xG) are out on a team whose total season xG is 100, that's 24% missing → λ cut by INJURY_ALPHA (0.6) × 24% = 14%. Capped at 50% so a single key injury never nukes the whole forecast. Only applies to upcoming fixtures; backtests use unshrunken λ so comparisons stay fair.",
    },
    {
      heading: "5 · Live probability recompute",
      body:
        "When a match goes live, we hold each team's pre-match λ and shrink the *remaining* Poisson by (90 − minute) / 90. Add the current score on top, redo the outcome distribution. That's why you'll see a team's win probability jump on a 1-0 lead at minute 60 but not at minute 3 — the remaining-λ is much smaller by the 60th minute.",
    },
    {
      heading: "6 · Commitment hashing",
      body:
        "Every prediction carries a SHA-256 commitment hash over the canonical (probabilities + lambdas + model version + kickoff time). Anyone can recompute the hash from the public data and verify the prediction wasn't altered after the match settled. No auth, no onchain posting — just a publicly-verifiable fingerprint in plain sight.",
    },
    {
      heading: "7 · What we don't model (yet)",
      body:
        "Referee cards · weather · pitch size · recent travel fatigue · manager changes · derby intensity. Each of these is a 1–3% effect that rarely moves a 52% model to 55%. We track the gap between model accuracy and bookmaker-implied accuracy in /history — if that gap ever closes, it's time to add the next factor.",
    },
  ],
};

const VI: Content = {
  title: "Mô hình hoạt động thế nào",
  subhead:
    "Tóm tắt ngắn về toán + dữ liệu đằng sau mỗi dự đoán trên site.",
  sections: [
    {
      heading: "1 · xG, không phải tỷ số",
      body:
        "Bàn thắng ồn — một cú chạm trúng xà thôi cũng đảo 0-1. Expected goals (xG) đo *chất lượng* cú sút, không quan tâm vào lưới hay không. Site ingest xG-tạo và xG-nhận của từng đội trong 12 trận gần nhất từ Understat, tách sức mạnh mỗi đội thành hệ số tấn công (xG sinh ra so với trung bình giải) + hệ số phòng thủ (xG cho phép). Trận gần hơn nặng hơn trận xa.",
    },
    {
      heading: "2 · Poisson + Dixon-Coles",
      body:
        "Có attack/defense của mỗi bên + trung bình giải, ta tính λ_chủ và λ_khách cho trận này. Hai phân phối Poisson cho xác suất mọi tỷ số. Vì 1-1/0-0/1-0/0-1 thực tế xảy ra hơi nhiều hơn Poisson độc lập (đội chơi thủ khi tỷ số thấp), ta áp chỉnh sửa Dixon-Coles (ρ = −0.15) đẩy nhẹ 4 ô này lên, giữ phần còn lại đúng xác suất.",
    },
    {
      heading: "3 · Temperature scaling",
      body:
        "Xác suất thô của mô hình thường quá tự tin với kèo bìa và quá rụt với underdog. Ta scale phân phối 3-chiều qua softmax với T = 1.35 — một tham số fit từ accuracy lịch sử, làm phẳng độ tự tin về mức calibrated tốt hơn. Bạn thấy hiệu ứng trong % hiển thị, không ảnh hưởng score heatmap.",
    },
    {
      heading: "4 · Điều chỉnh theo chấn thương",
      body:
        "λ mỗi đội bị giảm theo tỷ lệ xG bị vắng do chấn thương. Nếu Salah (15 xG) + Saka (9 xG) vắng trên team có 100 xG cả mùa = 24% vắng → λ giảm INJURY_ALPHA (0.6) × 24% = 14%. Cap 50% để một sao vắng không đánh sập hẳn forecast. Chỉ áp cho trận sắp tới; backtest dùng λ không chỉnh để so sánh công bằng.",
    },
    {
      heading: "5 · Recompute xác suất live",
      body:
        "Khi trận live, giữ λ pre-match của mỗi bên rồi scale phần *còn lại* theo (90 − phút) / 90. Cộng tỷ số hiện tại lên, tính lại phân phối outcome. Đó là lý do % thắng của 1 đội nhảy mạnh ở 1-0 phút 60 nhưng ít ở phút 3 — remaining-λ nhỏ hơn nhiều tới phút 60.",
    },
    {
      heading: "6 · Commitment hash",
      body:
        "Mỗi dự đoán có SHA-256 commitment trên canonical (xác suất + lambdas + model version + giờ kick-off). Bất kỳ ai cũng recompute được hash từ public data, verify dự đoán không bị sửa sau trận. Không auth, không onchain — dấu vân tay public ai cũng kiểm được.",
    },
    {
      heading: "7 · Những gì chưa mô hình hoá",
      body:
        "Trọng tài (thẻ) · thời tiết · kích thước sân · mệt mỏi do di chuyển · thay HLV · derby. Mỗi cái effect 1-3%, hiếm khi nâng mô hình 52% thành 55%. /history theo dõi gap giữa accuracy mô hình vs bookmaker — khi gap đóng mới cần thêm factor tiếp.",
    },
  ],
};

export default async function ModelDocsPage() {
  const lang = await getLang();
  const t = tFor(lang);
  const c = lang === "vi" ? VI : EN;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {t("common.back")}
      </Link>

      <header className="space-y-3">
        <h1 className="headline-section">{c.title}</h1>
        <p className="text-secondary max-w-2xl">{c.subhead}</p>
      </header>

      <div className="space-y-8">
        {c.sections.map((s) => (
          <section key={s.heading} className="card space-y-3">
            <h2 className="font-display font-semibold uppercase tracking-tight text-xl">
              {s.heading}
            </h2>
            <p className="text-primary leading-relaxed">{s.body}</p>
          </section>
        ))}
      </div>
    </main>
  );
}
