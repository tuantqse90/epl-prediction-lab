import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const metadata = {
  title: "Prediction Lab — xG doesn't lie. But the bookies do.",
  description:
    "Football match predictions for EPL, La Liga, Serie A, Bundesliga, Ligue 1 and UCL. Monte Carlo + Poisson + XGBoost ensemble. 7 seasons of backtested ROI. No custody, no gambling, just math.",
};

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Accuracy = { scored: number; correct: number; accuracy: number };

async function fetchAccuracy(): Promise<Accuracy | null> {
  try {
    const res = await fetch(`${BASE}/api/stats/accuracy?season=2025-26`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as Accuracy;
  } catch {
    return null;
  }
}

export default async function WelcomePage() {
  const lang = await getLang();
  const acc = await fetchAccuracy();
  const pct = (x: number) => `${Math.round(x * 100)}%`;

  return (
    <main className="mx-auto max-w-4xl px-6 py-16 space-y-24">
      {/* Hero */}
      <header className="space-y-6 text-center">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neon">
          xg · elo · xgboost · monte carlo
        </p>
        <h1 className="font-display text-5xl md:text-7xl font-bold leading-[0.95] tracking-tighter">
          {tLang(lang, {
            en: "xG doesn't lie.\nBut the bookies do.",
            vi: "xG không nói dối.\nNhưng bookmaker có.",
            th: "xG ไม่โกหก\nแต่เจ้ามือโกหก",
            zh: "xG 不会骗人\n但赔率公司会",
            ko: "xG는 거짓말을 하지 않는다\n하지만 북메이커는 한다",
          })}
        </h1>
        <p className="max-w-2xl mx-auto text-secondary text-lg">
          {tLang(lang, {
            en: "Every EPL · La Liga · Serie A · Bundesliga · Ligue 1 · UCL match — predicted by a 3-leg ensemble of Poisson + Elo + XGBoost. Odds comparison. Value-bet edges. Live probability during play. Transparent calibration.",
            vi: "Mọi trận EPL · La Liga · Serie A · Bundesliga · Ligue 1 · UCL — dự đoán bằng ensemble 3 mô hình Poisson + Elo + XGBoost. So odds. Tìm edge. Xác suất live trong trận. Calibration minh bạch.",
            th: "ทุกแมตช์จาก 5 ลีกใหญ่ยุโรป + UCL — คาดการณ์โดยเอนเซมเบิล 3 โมเดล",
            zh: "欧洲五大联赛 + 欧冠 每场比赛 — Poisson + Elo + XGBoost 三合一预测",
            ko: "유럽 5대 리그 + UCL 모든 경기 — Poisson + Elo + XGBoost 3-leg 앙상블",
          })}
        </p>
        <div className="flex justify-center gap-3 pt-4 flex-wrap">
          <Link href="/" className="btn-primary">
            {tLang(lang, { en: "Today's picks", vi: "Picks hôm nay", th: "พิกวันนี้", zh: "今日推荐", ko: "오늘의 픽" })}
          </Link>
          <Link href="/bracket" className="btn-ghost">
            ⭐ UCL bracket →
          </Link>
        </div>
      </header>

      {/* Proof strip */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card text-center space-y-2">
          <p className="font-mono text-[10px] uppercase tracking-wide text-neon">Track record</p>
          {acc ? (
            <>
              <p className="stat text-5xl text-neon">{pct(acc.accuracy)}</p>
              <p className="text-xs text-muted">
                {acc.correct.toLocaleString()} / {acc.scored.toLocaleString()} this season
              </p>
            </>
          ) : (
            <>
              <p className="stat text-5xl text-muted">—</p>
              <p className="text-xs text-muted">loading</p>
            </>
          )}
        </div>
        <div className="card text-center space-y-2">
          <p className="font-mono text-[10px] uppercase tracking-wide text-neon">Seasons backtested</p>
          <p className="stat text-5xl text-neon">7</p>
          <p className="text-xs text-muted">2019-20 → 2025-26</p>
        </div>
        <div className="card text-center space-y-2">
          <p className="font-mono text-[10px] uppercase tracking-wide text-neon">Languages</p>
          <p className="stat text-5xl text-neon">5</p>
          <p className="text-xs text-muted">EN · VI · TH · ZH · KO</p>
        </div>
      </section>

      {/* What you get */}
      <section className="space-y-6">
        <h2 className="font-display text-3xl font-bold tracking-tighter">
          {tLang(lang, {
            en: "What you get",
            vi: "Bạn nhận được gì",
            th: "คุณจะได้รับ",
            zh: "你会得到什么",
            ko: "제공되는 기능",
          })}
        </h2>
        <ul className="grid md:grid-cols-2 gap-4">
          {[
            { en: "Every match predicted with a P(H/D/A) triple + expected goals.",
              vi: "Mỗi trận có P(H/D/A) + xG dự đoán." },
            { en: "Value-bet flags when the model edge ≥ 5pp vs best-of-books odds.",
              vi: "Value bet flag khi edge ≥ 5pp so best-of-books." },
            { en: "Live probabilities that re-derive in real time during the match.",
              vi: "Live probability — cập nhật real-time trong trận." },
            { en: "Arbitrage + middle detectors across 67 bookmakers.",
              vi: "Arbitrage + middle detector trên 67 nhà cái." },
            { en: "Monte Carlo title race, relegation race, UCL bracket.",
              vi: "Monte Carlo đua vô địch, trụ hạng, UCL bracket." },
            { en: "Free Telegram bot: /pick PSG — instant model pick in chat.",
              vi: "Telegram bot miễn phí: /pick PSG — pick ngay trong chat." },
          ].map((item, i) => (
            <li key={i} className="card">
              <p className="text-secondary">{lang === "vi" ? item.vi : item.en}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* Transparency */}
      <section className="card space-y-4">
        <p className="font-mono text-[10px] uppercase tracking-wide text-neon">Transparency</p>
        <h2 className="font-display text-2xl font-bold tracking-tighter">
          {tLang(lang, {
            en: "We show you the ugly numbers too",
            vi: "Minh bạch cả số xấu",
            th: "เราแสดงตัวเลขที่แย่ด้วย",
            zh: "坏数据也一并公开",
            ko: "나쁜 숫자도 공개합니다",
          })}
        </h2>
        <p className="text-secondary">
          {tLang(lang, {
            en: "7-year flat-stake ROI at 5pp edge: −83u. Model is slightly under-confident at 50% bands. La Liga-specific ρ = 0.00; Bundesliga ρ = −0.25. All of this is live on the site.",
            vi: "ROI 7 năm flat-stake tại ngưỡng 5pp: −83u. Model hơi thiếu tự tin ở dải 50%. La Liga ρ = 0.00, Bundesliga ρ = −0.25. Mọi thứ hiển thị công khai trên site.",
            th: "ROI 7 ปี flat-stake ที่ 5pp: −83u · แสดงทั้งหมดบนเว็บ",
            zh: "7 年平注 5pp ROI: −83u · 全部在站上公开",
            ko: "7년 플랫 5pp ROI: −83u · 사이트에 전부 공개",
          })}
        </p>
        <div className="flex gap-2 flex-wrap">
          <Link href="/calibration" className="btn-ghost text-xs">→ /calibration</Link>
          <Link href="/equity-curve" className="btn-ghost text-xs">→ /equity-curve</Link>
          <Link href="/benchmark/by-team" className="btn-ghost text-xs">→ /benchmark/by-team</Link>
          <Link href="/methodology" className="btn-ghost text-xs">→ /methodology</Link>
        </div>
      </section>

      {/* CTAs */}
      <section className="space-y-6">
        <h2 className="font-display text-3xl font-bold tracking-tighter text-center">
          {tLang(lang, {
            en: "Try it",
            vi: "Thử ngay",
            th: "ลองเลย",
            zh: "试试",
            ko: "시작하기",
          })}
        </h2>
        <div className="grid md:grid-cols-3 gap-4">
          <Link href="/" className="card block hover:border-neon transition-colors space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-wide text-neon">#1</p>
            <p className="font-display font-semibold">
              {tLang(lang, { en: "Browse today's matches", vi: "Xem trận hôm nay", th: "ดูแมตช์วันนี้", zh: "浏览今日比赛", ko: "오늘 경기 보기" })}
            </p>
            <p className="text-xs text-muted">
              {tLang(lang, {
                en: "Homepage lists every upcoming fixture with the model pick + odds + edge.",
                vi: "Trang chủ liệt kê mọi trận sắp tới với pick + odds + edge.",
                th: "หน้าหลักแสดงทุกแมตช์ที่จะมาถึง",
                zh: "主页列出所有即将进行的比赛",
                ko: "홈에서 모든 예정 경기 확인",
              })}
            </p>
          </Link>
          <Link href="/subscribe" className="card block hover:border-neon transition-colors space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-wide text-neon">#2</p>
            <p className="font-display font-semibold">
              {tLang(lang, { en: "Monday email digest", vi: "Email digest thứ 2", th: "อีเมลสรุป", zh: "每周一邮件", ko: "월요일 이메일" })}
            </p>
            <p className="text-xs text-muted">
              {tLang(lang, {
                en: "Top edges for the week + last week's hits/misses. Unsubscribe in one click.",
                vi: "Top edges tuần tới + hit/miss tuần trước. Huỷ đăng ký 1-click.",
                th: "เอดจ์ท็อปของสัปดาห์",
                zh: "一周顶级 edge",
                ko: "주간 최고 엣지",
              })}
            </p>
          </Link>
          <a
            href="https://t.me/worldcup_predictor_bot"
            target="_blank"
            rel="noopener"
            className="card block hover:border-neon transition-colors space-y-2"
          >
            <p className="font-mono text-[10px] uppercase tracking-wide text-neon">#3</p>
            <p className="font-display font-semibold">
              {tLang(lang, { en: "Telegram bot", vi: "Telegram bot", th: "บอท Telegram", zh: "Telegram 机器人", ko: "Telegram 봇" })}
            </p>
            <p className="text-xs text-muted">
              /pick today · /edge · /roi 30d · /subscribe arsenal
            </p>
          </a>
        </div>
      </section>

      {/* Disclaimer */}
      <section className="font-mono text-[11px] uppercase tracking-wide text-muted text-center space-y-1">
        <p>• Entertainment-grade forecasting. Not financial advice.</p>
        <p>• Free. No custody. No stake placement.</p>
      </section>
    </main>
  );
}
