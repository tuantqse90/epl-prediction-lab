"use client";

import { useMemo } from "react";

import type { MyPick } from "@/lib/my-picks";
import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

type Prediction = {
  p_home_win: number;
  p_draw: number;
  p_away_win: number;
};

type MatchMeta = {
  id: number;
  home_goals: number | null;
  away_goals: number | null;
  status: string;
  prediction: Prediction | null;
};

function modelSide(pred: Prediction | null | undefined): "H" | "D" | "A" | null {
  if (!pred) return null;
  const probs = { H: pred.p_home_win, D: pred.p_draw, A: pred.p_away_win } as const;
  return (Object.keys(probs) as Array<keyof typeof probs>)
    .reduce((a, b) => (probs[b] > probs[a] ? b : a));
}

export default function MyPicksVsModel({
  picks,
  meta,
}: {
  picks: MyPick[];
  meta: Record<number, MatchMeta>;
}) {
  const lang = useLang();
  const data = useMemo(() => {
    let user_pnl = 0;
    let model_pnl = 0;
    let user_bets = 0;
    let model_bets = 0;
    let user_hits = 0;
    let model_hits = 0;
    const series: { i: number; user: number; model: number; date: string }[] = [];

    const ordered = picks
      .filter((p) => p.settled && p.pnl != null)
      .sort((a, b) => a.placed_at.localeCompare(b.placed_at));

    ordered.forEach((p, i) => {
      // User side
      user_bets += 1;
      user_pnl += p.pnl ?? 0;
      if (p.hit) user_hits += 1;
      // Model-simulated side: if model had picked the same odds on its own
      // pick at the same stake, did it win?
      const m = meta[p.match_id];
      const mSide = modelSide(m?.prediction);
      if (
        mSide && m?.home_goals != null && m?.away_goals != null
      ) {
        model_bets += 1;
        const actual: "H" | "D" | "A" =
          m.home_goals > m.away_goals ? "H"
          : m.home_goals < m.away_goals ? "A" : "D";
        if (mSide === actual) {
          // Model hit — we assume it gets user's odds (rough parity)
          model_pnl += p.stake * (p.odds - 1);
          model_hits += 1;
        } else {
          model_pnl -= p.stake;
        }
      }
      series.push({
        i,
        user: user_pnl,
        model: model_pnl,
        date: p.placed_at.slice(0, 10),
      });
    });

    return {
      series,
      user_pnl, model_pnl,
      user_bets, model_bets,
      user_hits, model_hits,
      user_acc: user_bets > 0 ? user_hits / user_bets : 0,
      model_acc: model_bets > 0 ? model_hits / model_bets : 0,
    };
  }, [picks, meta]);

  if (data.series.length === 0) {
    return null;
  }

  const W = 640, H = 220, PAD = 30;
  const xs = data.series.map((s) => s.i);
  const vs = data.series.flatMap((s) => [s.user, s.model, 0]);
  const minY = Math.min(...vs);
  const maxY = Math.max(...vs);
  const spanY = (maxY - minY) || 1;
  const toX = (i: number) =>
    PAD + (i / (Math.max(data.series.length - 1, 1))) * (W - 2 * PAD);
  const toY = (v: number) => H - PAD - ((v - minY) / spanY) * (H - 2 * PAD);

  const userLine = data.series.map((s) => `${toX(s.i)},${toY(s.user)}`).join(" ");
  const modelLine = data.series.map((s) => `${toX(s.i)},${toY(s.model)}`).join(" ");

  return (
    <section className="card space-y-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h2 className="label">
          {tLang(lang, {
            en: "You vs the model",
            vi: "Bạn vs Model",
            th: "คุณ vs โมเดล",
            zh: "你 vs 模型",
            ko: "당신 vs 모델",
          })}
        </h2>
        <p className="font-mono text-[11px] text-muted">
          {data.user_bets} bets settled
        </p>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
        <line x1={PAD} y1={toY(0)} x2={W - PAD} y2={toY(0)}
              stroke="#555" strokeDasharray="3 3" opacity="0.5" />
        <polyline fill="none" stroke="#E0FF32" strokeWidth="2.5" points={userLine} />
        <polyline fill="none" stroke="#4ea0ff" strokeWidth="2" points={modelLine}
                  strokeDasharray="2 4" opacity="0.9" />
      </svg>

      <div className="grid grid-cols-2 gap-3 text-sm font-mono">
        <div>
          <p className="inline-flex items-center gap-2">
            <span className="inline-block h-2 w-4 rounded bg-neon" />
            {tLang(lang, { en: "You", vi: "Bạn", th: "คุณ", zh: "你", ko: "당신" })}
          </p>
          <p className={`stat ${data.user_pnl > 0 ? "text-neon" : data.user_pnl < 0 ? "text-error" : ""}`}>
            {data.user_pnl > 0 ? "+" : ""}{data.user_pnl.toFixed(2)}u
          </p>
          <p className="text-muted text-[11px]">
            {data.user_hits}/{data.user_bets} hits · {(data.user_acc * 100).toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="inline-flex items-center gap-2">
            <span className="inline-block h-2 w-4 rounded bg-[#4ea0ff]" />
            {tLang(lang, { en: "Model if stake", vi: "Model (cùng stake)", th: "โมเดล (เดิมพันเหมือน)", zh: "模型 (同样下注)", ko: "모델 (같은 스테이크)" })}
          </p>
          <p className={`stat ${data.model_pnl > 0 ? "text-neon" : data.model_pnl < 0 ? "text-error" : ""}`}>
            {data.model_pnl > 0 ? "+" : ""}{data.model_pnl.toFixed(2)}u
          </p>
          <p className="text-muted text-[11px]">
            {data.model_hits}/{data.model_bets} hits · {(data.model_acc * 100).toFixed(1)}%
          </p>
        </div>
      </div>
    </section>
  );
}
