"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useLang } from "@/lib/i18n-client";

type Section = {
  title: { en: string; vi: string };
  links: { href: string; label: { en: string; vi: string } }[];
};

const SECTIONS: Section[] = [
  {
    title: { en: "Matches", vi: "Trận" },
    links: [
      { href: "/", label: { en: "Fixtures", vi: "Lịch đấu" } },
      { href: "/last-weekend", label: { en: "Last weekend", vi: "Tuần vừa rồi" } },
      { href: "/news", label: { en: "News", vi: "Tin tức" } },
      { href: "/leagues", label: { en: "Leagues", vi: "Giải đấu" } },
      { href: "/europe", label: { en: "Europe", vi: "Châu Âu" } },
    ],
  },
  {
    title: { en: "Stats", vi: "Số liệu" },
    links: [
      { href: "/table", label: { en: "xG Table", vi: "Bảng XH" } },
      { href: "/scorers", label: { en: "Top scorers", vi: "Vua phá lưới" } },
      { href: "/players", label: { en: "Players", vi: "Cầu thủ" } },
      { href: "/stats", label: { en: "Accuracy", vi: "Độ chính xác" } },
      { href: "/calibration", label: { en: "Calibration", vi: "Hiệu chỉnh" } },
      { href: "/history", label: { en: "History", vi: "Theo mùa" } },
    ],
  },
  {
    title: { en: "Bets", vi: "Kèo" },
    links: [
      { href: "/roi", label: { en: "ROI", vi: "ROI" } },
      { href: "/strategies", label: { en: "Strategies", vi: "Chiến thuật" } },
      { href: "/strategies/compare", label: { en: "Compare all", vi: "So sánh" } },
      { href: "/parlay", label: { en: "Parlay", vi: "Xiên" } },
      { href: "/arbs", label: { en: "Arbs", vi: "Arb" } },
      { href: "/fpl", label: { en: "FPL", vi: "FPL" } },
    ],
  },
  {
    title: { en: "Lab", vi: "Lab" },
    links: [
      { href: "/proof", label: { en: "Proof", vi: "Chứng minh" } },
      { href: "/tipsters", label: { en: "Tipsters", vi: "Tipsters" } },
      { href: "/docs/model", label: { en: "How the model works", vi: "Mô hình" } },
      { href: "/methodology", label: { en: "Methodology", vi: "Phương pháp" } },
      { href: "/blog", label: { en: "Blog", vi: "Blog" } },
      { href: "/changelog", label: { en: "Changelog", vi: "Nhật ký" } },
      { href: "/pricing", label: { en: "Pricing", vi: "Giá" } },
      { href: "/faq", label: { en: "FAQ", vi: "FAQ" } },
    ],
  },
];

export default function MobileNavDrawer() {
  const lang = useLang();
  const [open, setOpen] = useState(false);
  const k = (lang === "vi" ? "vi" : "en") as "vi" | "en";

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
                    {s.title[k]}
                  </p>
                  <ul className="space-y-1">
                    {s.links.map((l) => (
                      <li key={l.href}>
                        <Link
                          href={l.href}
                          onClick={() => setOpen(false)}
                          className="block rounded px-3 py-2 text-sm text-secondary hover:text-neon hover:bg-high/40"
                        >
                          {l.label[k]}
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
