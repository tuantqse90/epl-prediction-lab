"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import type { Lang } from "@/lib/i18n";

type NavLink = {
  href: string;
  labels: Record<Lang, string>;
  desc?: Record<Lang, string>;  // one-line explanation in dropdown
};

type NavGroup = {
  key: string;
  icon: string;
  labels: Record<Lang, string>;  // intentionally kept ≤ 6 chars so every
                                 // locale stays on one line on mobile
  links: NavLink[];
  // Prefix-match for active state so clicks inside a group surface the group.
  pathPrefixes: readonly string[];
};

// Short, durable labels — every locale picked so the top-level chip fits in a
// ~60-px slot on mobile without wrapping. Longer prose lives inside the dropdown.
const GROUPS: readonly NavGroup[] = [
  {
    key: "matches",
    icon: "⚽",
    labels: { en: "Matches", vi: "Trận", th: "แข่ง", zh: "比赛", ko: "경기" },
    pathPrefixes: ["/", "/match/", "/last-weekend", "/news", "/teams", "/leagues"],
    links: [
      {
        href: "/",
        labels: { en: "Fixtures", vi: "Lịch đấu", th: "ตารางแข่ง", zh: "赛程", ko: "경기 일정" },
        desc: {
          en: "Upcoming + live fixtures with model picks",
          vi: "Trận sắp đá + trực tiếp kèm pick của model",
          th: "การแข่งที่กำลังจะมาถึง", zh: "即将进行的比赛", ko: "다가오는 경기",
        },
      },
      {
        href: "/last-weekend",
        labels: { en: "Last weekend", vi: "Tuần vừa rồi", th: "สัปดาห์ที่แล้ว", zh: "上周", ko: "지난 주" },
        desc: {
          en: "Finished matches vs model — hits + misses",
          vi: "Trận đã đá vs model — trúng/trật",
          th: "ผลเทียบกับโมเดล", zh: "赛果对比模型", ko: "최근 적중률",
        },
      },
      {
        href: "/news",
        labels: { en: "News", vi: "Tin tức", th: "ข่าว", zh: "新闻", ko: "뉴스" },
      },
      {
        href: "/leagues",
        labels: { en: "Leagues", vi: "Giải đấu", th: "ลีก", zh: "联赛", ko: "리그" },
      },
    ],
  },
  {
    key: "stats",
    icon: "Σ",
    labels: { en: "Stats", vi: "Số liệu", th: "สถิติ", zh: "统计", ko: "통계" },
    pathPrefixes: ["/table", "/scorers", "/players", "/stats", "/history", "/benchmark", "/compare"],
    links: [
      {
        href: "/table",
        labels: { en: "xG Table", vi: "Bảng XH (xG)", th: "ตารางคะแนน xG", zh: "xG 积分榜", ko: "xG 순위" },
      },
      {
        href: "/scorers",
        labels: { en: "Top scorers", vi: "Vua phá lưới", th: "ดาวซัลโว", zh: "射手榜", ko: "득점왕" },
      },
      {
        href: "/players",
        labels: { en: "Players", vi: "Cầu thủ", th: "นักเตะ", zh: "球员", ko: "선수" },
      },
      {
        href: "/stats",
        labels: { en: "Accuracy", vi: "Độ chính xác", th: "ความแม่นยำ", zh: "准确率", ko: "정확도" },
        desc: {
          en: "Log-loss + accuracy + calibration",
          vi: "Log-loss + accuracy + calibration",
          th: "ความแม่นยำ + การสอบเทียบ", zh: "对数损失 + 准确率", ko: "로그 손실 + 정확도",
        },
      },
      {
        href: "/benchmark",
        labels: { en: "Benchmark", vi: "So baseline", th: "เกณฑ์มาตรฐาน", zh: "基准对比", ko: "벤치마크" },
        desc: {
          en: "Model vs bookmakers vs home-baseline",
          vi: "Model vs nhà cái vs luôn chủ nhà",
          th: "โมเดลเทียบกับเจ้ามือ", zh: "模型对比庄家", ko: "모델 vs 북메이커",
        },
      },
      {
        href: "/history",
        labels: { en: "Season history", vi: "Theo mùa", th: "ตามฤดูกาล", zh: "历届赛季", ko: "시즌별" },
      },
      {
        href: "/compare",
        labels: { en: "Head-to-head", vi: "So đầu đối đầu", th: "เจอกันตัวต่อตัว", zh: "交锋战绩", ko: "상대 전적" },
      },
    ],
  },
  {
    key: "bets",
    icon: "¤",
    labels: { en: "Bets", vi: "Kèo", th: "แทง", zh: "投注", ko: "베팅" },
    pathPrefixes: ["/roi", "/strategies", "/parlay", "/betslip", "/fpl"],
    links: [
      {
        href: "/roi",
        labels: { en: "ROI · flat vs Kelly", vi: "ROI · Flat vs Kelly", th: "ROI · flat vs Kelly", zh: "ROI · 固定 vs 凯利", ko: "ROI · 플랫 vs 켈리" },
      },
      {
        href: "/roi/by-league",
        labels: { en: "ROI by league", vi: "ROI theo giải", th: "ROI ตามลีก", zh: "各联赛 ROI", ko: "리그별 ROI" },
      },
      {
        href: "/strategies",
        labels: { en: "Strategies", vi: "Chiến thuật", th: "กลยุทธ์", zh: "策略", ko: "전략" },
        desc: {
          en: "Value ladder · Kelly · Martingale · fade",
          vi: "Bậc thang · Kelly · Martingale · ngược",
          th: "กลยุทธ์ต่างๆ ในข้อมูลจริง", zh: "多种投注策略对比", ko: "여러 전략 비교",
        },
      },
      {
        href: "/strategies/compare",
        labels: { en: "Compare all", vi: "So sánh tất cả", th: "เทียบทั้งหมด", zh: "全部对比", ko: "전체 비교" },
        desc: {
          en: "4 strategies · one chart · real 2025-26",
          vi: "4 chiến thuật · 1 biểu đồ · data 2025-26",
          th: "4 กลยุทธ์ในหนึ่งกราฟ", zh: "4 种策略同图对比", ko: "4 전략 한 차트",
        },
      },
      {
        href: "/parlay",
        labels: { en: "Parlay builder", vi: "Dựng xiên", th: "สร้างพาร์เลย์", zh: "串关构建", ko: "병행 조합" },
      },
      {
        href: "/fpl",
        labels: { en: "FPL picks", vi: "FPL picks", th: "FPL", zh: "FPL", ko: "FPL" },
      },
    ],
  },
  {
    key: "lab",
    icon: "⌬",
    labels: { en: "Lab", vi: "Lab", th: "Lab", zh: "实验", ko: "연구" },
    pathPrefixes: ["/proof", "/tipsters", "/docs", "/about", "/faq", "/blog"],
    links: [
      {
        href: "/proof",
        labels: { en: "Proof", vi: "Chứng minh", th: "พิสูจน์", zh: "证明", ko: "증명" },
        desc: {
          en: "Methodology + 7-season accuracy + CLV",
          vi: "Methodology + 7 mùa accuracy + CLV",
          th: "วิธีการ + ความแม่นยำ", zh: "方法与 7 季准确率", ko: "방법론 + 시즌별 정확도",
        },
      },
      {
        href: "/tipsters",
        labels: { en: "Tipsters", vi: "Tipsters", th: "เซียนมวย", zh: "贴士榜", ko: "팁스터" },
      },
      {
        href: "/docs/model",
        labels: { en: "How the model works", vi: "Model hoạt động thế nào", th: "โมเดลทำงานยังไง", zh: "模型原理", ko: "모델 구조" },
      },
      {
        href: "/about",
        labels: { en: "About", vi: "Giới thiệu", th: "เกี่ยวกับ", zh: "关于", ko: "소개" },
      },
      {
        href: "/faq",
        labels: { en: "FAQ", vi: "FAQ", th: "FAQ", zh: "常见问题", ko: "FAQ" },
      },
    ],
  },
];

function useClickOutside(active: boolean, onClose: () => void) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!active) return;
    const handle = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent) {
        if (e.key === "Escape") onClose();
        return;
      }
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("mousedown", handle);
    document.addEventListener("keydown", handle);
    return () => {
      document.removeEventListener("mousedown", handle);
      document.removeEventListener("keydown", handle);
    };
  }, [active, onClose]);
  return ref;
}

export default function NavLinks({ lang }: { lang: Lang }) {
  const pathname = usePathname() ?? "/";
  const [openKey, setOpenKey] = useState<string | null>(null);
  const containerRef = useClickOutside(openKey !== null, () => setOpenKey(null));

  return (
    <div ref={containerRef} className="flex items-center gap-4">
      {GROUPS.map((g) => {
        const active = g.pathPrefixes.some((p) =>
          p === "/" ? pathname === "/" : pathname.startsWith(p),
        );
        const isOpen = openKey === g.key;
        return (
          <div key={g.key} className="relative">
            <button
              type="button"
              onClick={() => setOpenKey((k) => (k === g.key ? null : g.key))}
              aria-expanded={isOpen}
              aria-haspopup="menu"
              className={
                "group inline-flex items-center gap-1.5 whitespace-nowrap py-1 transition-colors focus:outline-none " +
                (active || isOpen ? "text-neon" : "text-secondary hover:text-neon")
              }
            >
              <span
                aria-hidden
                className={
                  "font-mono text-[11px] " +
                  (active || isOpen ? "text-neon" : "text-muted group-hover:text-neon")
                }
              >
                {g.icon}
              </span>
              <span>{g.labels[lang]}</span>
              <span aria-hidden className="text-[9px] font-mono text-muted group-hover:text-neon">
                {isOpen ? "▴" : "▾"}
              </span>
              <span
                aria-hidden
                className={
                  "pointer-events-none absolute -bottom-1 left-0 h-[2px] bg-neon transition-all duration-200 " +
                  (active || isOpen
                    ? "w-full opacity-100"
                    : "w-0 opacity-0 group-hover:w-full group-hover:opacity-70")
                }
              />
            </button>

            {isOpen && (
              <div
                role="menu"
                className="absolute left-0 top-full z-50 mt-3 min-w-[280px] rounded-xl border border-border/80 bg-raised shadow-lg"
                style={{ boxShadow: "0 8px 24px rgba(0,0,0,0.45)" }}
              >
                <ul className="py-2">
                  {g.links.map((link) => {
                    const linkActive = pathname === link.href
                      || (link.href !== "/" && pathname.startsWith(link.href));
                    return (
                      <li key={link.href}>
                        <Link
                          href={link.href}
                          role="menuitem"
                          onClick={() => setOpenKey(null)}
                          className={
                            "block px-4 py-2 text-sm transition-colors " +
                            (linkActive
                              ? "text-neon bg-high/60"
                              : "text-secondary hover:text-neon hover:bg-high/40")
                          }
                        >
                          <span className="block leading-tight">{link.labels[lang]}</span>
                          {link.desc && (
                            <span className="mt-0.5 block text-[11px] text-muted leading-snug">
                              {link.desc[lang]}
                            </span>
                          )}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
