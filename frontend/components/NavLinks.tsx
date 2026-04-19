"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { Lang } from "@/lib/i18n";

type NavItem = {
  href: string;
  icon: string;          // single emoji / symbol used as a small decorator
  labels: Record<Lang, string>;
  matches: (path: string) => boolean;
};

const ITEMS: NavItem[] = [
  {
    href: "/",
    icon: "⚽",
    labels: {
      en: "Fixtures", vi: "Lịch đấu",
      th: "ตารางแข่งขัน", zh: "赛程", ko: "경기 일정",
    },
    matches: (p) => p === "/" || p.startsWith("/match/"),
  },
  {
    href: "/table",
    icon: "▦",
    labels: {
      en: "Table", vi: "Bảng XH",
      th: "ตารางคะแนน", zh: "积分榜", ko: "순위",
    },
    matches: (p) => p.startsWith("/table"),
  },
  {
    href: "/last-weekend",
    icon: "↩",
    labels: {
      en: "Last weekend", vi: "Tuần vừa rồi",
      th: "สัปดาห์ที่แล้ว", zh: "上周", ko: "지난 주",
    },
    matches: (p) => p.startsWith("/last-weekend"),
  },
  {
    href: "/scorers",
    icon: "◎",
    labels: {
      en: "Top scorers", vi: "Vua phá lưới",
      th: "ดาวซัลโว", zh: "射手榜", ko: "득점왕",
    },
    matches: (p) => p.startsWith("/scorers") || p.startsWith("/players/"),
  },
  {
    href: "/news",
    icon: "▣",
    labels: {
      en: "News", vi: "Tin tức",
      th: "ข่าว", zh: "新闻", ko: "뉴스",
    },
    matches: (p) => p.startsWith("/news"),
  },
  {
    href: "/stats",
    icon: "Σ",
    labels: {
      en: "Stats", vi: "Thống kê",
      th: "สถิติ", zh: "统计", ko: "통계",
    },
    matches: (p) => p.startsWith("/stats"),
  },
];

export default function NavLinks({ lang }: { lang: Lang }) {
  const pathname = usePathname() ?? "/";
  return (
    <>
      {ITEMS.map((item) => {
        const active = item.matches(pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={
              "group relative inline-flex items-center gap-1.5 whitespace-nowrap px-0.5 py-1 transition-colors " +
              (active ? "text-neon" : "text-secondary hover:text-neon")
            }
          >
            <span
              aria-hidden
              className={
                "font-mono text-[11px] " +
                (active ? "text-neon" : "text-muted group-hover:text-neon")
              }
            >
              {item.icon}
            </span>
            <span>{item.labels[lang]}</span>
            {/* Underline accent: filled on active, slides in on hover */}
            <span
              aria-hidden
              className={
                "pointer-events-none absolute -bottom-1 left-0 h-[2px] bg-neon transition-all duration-200 " +
                (active
                  ? "w-full opacity-100"
                  : "w-0 opacity-0 group-hover:w-full group-hover:opacity-70")
              }
            />
          </Link>
        );
      })}
    </>
  );
}
