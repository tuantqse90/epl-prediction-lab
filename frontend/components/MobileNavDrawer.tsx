"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useLang } from "@/lib/i18n-client";
import type { Lang } from "@/lib/i18n";

type L = Record<Lang, string>;
type Section = { title: L; links: { href: string; label: L }[] };

const SECTIONS: Section[] = [
  {
    title: { en: "Matches", vi: "Trận", th: "แข่ง", zh: "比赛", ko: "경기" },
    links: [
      { href: "/", label: { en: "Fixtures", vi: "Lịch đấu", th: "ตาราง", zh: "赛程", ko: "일정" } },
      { href: "/last-weekend", label: { en: "Last weekend", vi: "Tuần vừa rồi", th: "สุดสัปดาห์", zh: "上周", ko: "지난 주" } },
      { href: "/news", label: { en: "News", vi: "Tin tức", th: "ข่าว", zh: "新闻", ko: "뉴스" } },
      { href: "/leagues", label: { en: "Leagues", vi: "Giải đấu", th: "ลีก", zh: "联赛", ko: "리그" } },
      { href: "/europe", label: { en: "Europe", vi: "Châu Âu", th: "ยุโรป", zh: "欧洲", ko: "유럽" } },
    ],
  },
  {
    title: { en: "Stats", vi: "Số liệu", th: "สถิติ", zh: "统计", ko: "통계" },
    links: [
      { href: "/table", label: { en: "xG Table", vi: "Bảng XH", th: "ตาราง xG", zh: "xG 榜", ko: "xG 순위" } },
      { href: "/scorers", label: { en: "Top scorers", vi: "Vua phá lưới", th: "ดาวซัลโว", zh: "射手榜", ko: "득점왕" } },
      { href: "/players", label: { en: "Players", vi: "Cầu thủ", th: "นักเตะ", zh: "球员", ko: "선수" } },
      { href: "/stats", label: { en: "Accuracy", vi: "Độ chính xác", th: "ความแม่นยำ", zh: "准确率", ko: "정확도" } },
      { href: "/calibration", label: { en: "Calibration", vi: "Hiệu chỉnh", th: "การสอบเทียบ", zh: "校准", ko: "보정" } },
      { href: "/history", label: { en: "History", vi: "Theo mùa", th: "ฤดูกาล", zh: "赛季", ko: "시즌" } },
    ],
  },
  {
    title: { en: "Bets", vi: "Kèo", th: "แทง", zh: "投注", ko: "베팅" },
    links: [
      { href: "/roi", label: { en: "ROI", vi: "ROI", th: "ROI", zh: "ROI", ko: "ROI" } },
      { href: "/strategies", label: { en: "Strategies", vi: "Chiến thuật", th: "กลยุทธ์", zh: "策略", ko: "전략" } },
      { href: "/strategies/compare", label: { en: "Compare all", vi: "So sánh", th: "เทียบทั้งหมด", zh: "全部对比", ko: "전체 비교" } },
      { href: "/parlay", label: { en: "Parlay", vi: "Xiên", th: "พาร์เลย์", zh: "串关", ko: "병행" } },
      { href: "/arbs", label: { en: "Arbs", vi: "Arb", th: "อาร์บิ", zh: "套利", ko: "차익" } },
      { href: "/fpl", label: { en: "FPL", vi: "FPL", th: "FPL", zh: "FPL", ko: "FPL" } },
    ],
  },
  {
    title: { en: "Lab", vi: "Lab", th: "Lab", zh: "实验", ko: "연구" },
    links: [
      { href: "/proof", label: { en: "Proof", vi: "Chứng minh", th: "พิสูจน์", zh: "证明", ko: "증명" } },
      { href: "/tipsters", label: { en: "Tipsters", vi: "Tipsters", th: "เซียน", zh: "贴士", ko: "팁스터" } },
      { href: "/docs/model", label: { en: "How the model works", vi: "Mô hình", th: "โมเดล", zh: "模型", ko: "모델" } },
      { href: "/methodology", label: { en: "Methodology", vi: "Phương pháp", th: "วิธีการ", zh: "方法论", ko: "방법론" } },
      { href: "/blog", label: { en: "Blog", vi: "Blog", th: "บล็อก", zh: "博客", ko: "블로그" } },
      { href: "/stories", label: { en: "Match stories", vi: "Câu chuyện", th: "เรื่องราว", zh: "故事", ko: "이야기" } },
      { href: "/changelog", label: { en: "Changelog", vi: "Nhật ký", th: "บันทึก", zh: "变更日志", ko: "변경 이력" } },
      { href: "/pricing", label: { en: "Pricing", vi: "Giá", th: "ราคา", zh: "价格", ko: "가격" } },
      { href: "/faq", label: { en: "FAQ", vi: "FAQ", th: "FAQ", zh: "FAQ", ko: "FAQ" } },
    ],
  },
];

export default function MobileNavDrawer() {
  const lang = useLang();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="md:hidden inline-flex h-8 w-8 items-center justify-center rounded border border-border/60 text-secondary hover:text-neon"
        aria-label="Open menu"
      >
        <span aria-hidden className="font-mono text-base">☰</span>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 md:hidden"
          role="dialog"
          aria-modal="true"
        >
          <button
            type="button"
            className="absolute inset-0 bg-black/70"
            onClick={() => setOpen(false)}
            aria-label="Close menu"
          />
          <div className="absolute right-0 top-0 h-full w-[84%] max-w-[360px] overflow-y-auto bg-surface border-l border-border/60 pb-20">
            <div className="sticky top-0 flex items-center justify-between border-b border-border/40 bg-surface px-4 py-3">
              <p className="font-mono text-xs uppercase tracking-wide text-muted">menu</p>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="font-mono text-xs text-secondary hover:text-neon"
                aria-label="Close"
              >
                close ✕
              </button>
            </div>
            <div className="p-4 space-y-6">
              {SECTIONS.map((s) => (
                <div key={s.title.en} className="space-y-2">
                  <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
                    {s.title[lang]}
                  </p>
                  <ul className="space-y-1">
                    {s.links.map((l) => (
                      <li key={l.href}>
                        <Link
                          href={l.href}
                          onClick={() => setOpen(false)}
                          className="block rounded px-3 py-2 text-sm text-secondary hover:text-neon hover:bg-high/40"
                        >
                          {l.label[lang]}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              <div className="border-t border-border/40 pt-4">
                <a
                  href="https://ko-fi.com/predictor"
                  target="_blank"
                  rel="noopener"
                  className="inline-block rounded px-3 py-2 text-sm text-secondary hover:text-neon"
                  onClick={() => setOpen(false)}
                >
                  ☕ Tip on Ko-Fi
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
