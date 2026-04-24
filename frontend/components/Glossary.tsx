"use client";

// Hover-tooltip for our jargon. Wrap any term:
//   <Term slug="xg">xG</Term>
// Renders a hoverable underline; on hover shows the 2-line definition.

import { useState } from "react";

const DEFS: Record<string, { en: string; vi: string }> = {
  xg: {
    en: "Expected goals — quality of chances, independent of whether they scored.",
    vi: "Expected goals — chất lượng cơ hội, không phụ thuộc vào có ghi bàn hay không.",
  },
  clv: {
    en: "Closing-line value — positive CLV means the market later agreed with our pick.",
    vi: "Closing-line value — CLV dương nghĩa là thị trường sau đó đồng ý với pick của mô hình.",
  },
  kelly: {
    en: "Kelly stake — growth-optimal bankroll fraction. Fractional Kelly (<1) reduces variance.",
    vi: "Kelly stake — phần bankroll tối ưu tăng trưởng. Fractional Kelly (<1) giảm biến động.",
  },
  edge: {
    en: "Edge — model prob × odds − 1. Edge > 0 = positive expected value at that price.",
    vi: "Edge — model prob × odds − 1. Edge > 0 = EV dương tại giá đó.",
  },
  devig: {
    en: "Devigged — implied probs scaled to sum to 1, removing the bookmaker's margin.",
    vi: "Devigged — xác suất ngầm chia đều để tổng bằng 1, loại margin nhà cái.",
  },
  brier: {
    en: "Brier score — mean squared error on probabilistic predictions. Lower is better.",
    vi: "Brier score — sai số bình phương trung bình trên dự đoán xác suất. Thấp hơn = tốt hơn.",
  },
};

export function Term({ slug, children, lang = "en" }: {
  slug: string;
  children: React.ReactNode;
  lang?: "en" | "vi";
}) {
  const [show, setShow] = useState(false);
  const def = DEFS[slug];
  if (!def) return <>{children}</>;
  return (
    <span
      className="relative inline-block border-b border-dotted border-neon/40 cursor-help"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
      onFocus={() => setShow(true)}
      onBlur={() => setShow(false)}
      tabIndex={0}
    >
      {children}
      {show && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded border border-border bg-surface p-3 text-xs text-secondary shadow-lg z-50 pointer-events-none">
          {def[lang === "vi" ? "vi" : "en"]}
        </span>
      )}
    </span>
  );
}
