"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import TeamLogo from "@/components/TeamLogo";
import { readFavorites, removeFavorite } from "@/lib/favorites";
import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

type TeamSummary = {
  slug: string;
  name: string;
  short_name: string;
  league_code: string | null;
  stats: {
    played: number;
    wins: number;
    draws: number;
    losses: number;
    points: number;
    goals_for: number;
    goals_against: number;
    xg_for: number;
    xg_against: number;
  };
  form: string[];
  upcoming: Array<{
    id: number;
    kickoff_time: string;
    home_short: string;
    away_short: string;
    home_slug: string;
    away_slug: string;
    is_home: boolean;
  }>;
  recent: Array<{
    id: number;
    kickoff_time: string;
    home_short: string;
    away_short: string;
    home_goals: number | null;
    away_goals: number | null;
    is_home: boolean;
  }>;
};

function formDot(r: string) {
  return r === "W" ? "bg-neon" : r === "L" ? "bg-error" : "bg-muted";
}

export default function WatchlistPage() {
  const lang = useLang();
  const [favorites, setFavorites] = useState<string[]>([]);
  const [teams, setTeams] = useState<Record<string, TeamSummary>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = () => setFavorites(readFavorites());
    load();
    window.addEventListener("favorites-change", load);
    return () => window.removeEventListener("favorites-change", load);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      const entries = await Promise.all(
        favorites.map(async (slug) => {
          try {
            const res = await fetch(`/api/teams/${slug}`);
            if (!res.ok) return null;
            return [slug, (await res.json()) as TeamSummary] as const;
          } catch {
            return null;
          }
        }),
      );
      if (cancelled) return;
      const out: Record<string, TeamSummary> = {};
      for (const e of entries) if (e) out[e[0]] = e[1];
      setTeams(out);
      setLoading(false);
    }
    if (favorites.length > 0) run();
    else setLoading(false);
    return () => { cancelled = true; };
  }, [favorites]);

  if (favorites.length === 0) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12 space-y-6">
        <Link href="/" className="btn-ghost text-sm">
          {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
        </Link>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Your watchlist",
            vi: "Danh sách theo dõi",
            th: "รายการติดตาม",
            zh: "你的关注",
            ko: "관심 목록",
          })}
        </h1>
        <div className="card space-y-3">
          <p className="text-secondary">
            {tLang(lang, {
              en: "Empty. Click the star on any team page to add them here. No login needed — saved in your browser.",
              vi: "Trống. Bấm sao trên trang bất kỳ đội nào để thêm vào đây. Không cần đăng nhập — lưu trong trình duyệt.",
              th: "ว่างเปล่า คลิกดาวบนหน้าทีมเพื่อเพิ่ม ไม่ต้อง login เก็บในเบราว์เซอร์",
              zh: "空。点击任一球队页面的星号添加。无需登录 — 存在你的浏览器。",
              ko: "비어 있음. 팀 페이지에서 별을 눌러 추가. 로그인 불필요 — 브라우저에 저장.",
            })}
          </p>
          <div className="flex gap-3 pt-2">
            <Link href="/" className="btn-primary text-sm">
              {tLang(lang, { en: "Browse matches", vi: "Xem trận", th: "ดูแมตช์", zh: "浏览比赛", ko: "경기 보기" })}
            </Link>
            <Link href="/sync" className="btn-ghost text-sm">
              {tLang(lang, { en: "Sync across devices", vi: "Sync giữa thiết bị", th: "ซิงค์ข้ามเครื่อง", zh: "跨设备同步", ko: "기기 간 동기화" })}
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const teamList = favorites.map((slug) => ({ slug, t: teams[slug] })).filter((x) => !!x.t);

  return (
    <main className="mx-auto max-w-5xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-2">
        <p className="font-mono text-xs text-muted">
          {favorites.length} {tLang(lang, { en: "teams followed", vi: "đội đang theo dõi", th: "ทีมที่ติดตาม", zh: "关注球队", ko: "팔로우 팀" })}
        </p>
        <h1 className="headline-section">
          {tLang(lang, { en: "Your watchlist", vi: "Danh sách theo dõi", th: "รายการติดตาม", zh: "关注", ko: "관심 목록" })}
        </h1>
        <p className="text-secondary text-sm max-w-2xl">
          {tLang(lang, {
            en: "Next fixture + last result + current form per team. No login — saved in your browser. Use PIN sync to bring this list to another device.",
            vi: "Trận kế + kết quả gần nhất + phong độ mỗi đội. Không login — lưu trình duyệt. Dùng PIN sync để đưa list sang thiết bị khác.",
            th: "แมตช์ถัดไป + ผลล่าสุด + ฟอร์มปัจจุบัน",
            zh: "每队下一场 + 最近结果 + 当前状态",
            ko: "각 팀의 다음 경기 + 최근 결과 + 폼",
          })}
        </p>
      </header>

      {loading && teamList.length === 0 && (
        <div className="card text-muted">{tLang(lang, { en: "Loading…", vi: "Đang tải…", th: "กำลังโหลด…", zh: "加载中…", ko: "불러오는 중…" })}</div>
      )}

      <section className="grid gap-4 md:grid-cols-2">
        {teamList.map(({ slug, t }) => {
          if (!t) return null;
          const xgDiff = t.stats.xg_for - t.stats.xg_against;
          const next = t.upcoming[0];
          const last = t.recent[0];
          const result =
            last && last.home_goals != null && last.away_goals != null
              ? (last.is_home ? last.home_goals - last.away_goals : last.away_goals - last.home_goals)
              : null;
          const lastRes = result == null ? null : result > 0 ? "W" : result < 0 ? "L" : "D";
          return (
            <div key={slug} className="card space-y-4">
              <div className="flex items-start justify-between gap-3">
                <Link href={`/teams/${slug}`} className="flex items-center gap-3 flex-1 min-w-0 hover:text-neon">
                  <TeamLogo slug={slug} name={t.name} size={40} />
                  <div className="min-w-0">
                    <p className="font-display text-xl font-semibold uppercase tracking-tighter truncate">
                      {t.short_name}
                    </p>
                    <p className="font-mono text-[11px] text-muted">{t.league_code}</p>
                  </div>
                </Link>
                <button
                  onClick={() => removeFavorite(slug)}
                  className="text-muted hover:text-error font-mono text-xs"
                  aria-label={tLang(lang, { en: "Remove", vi: "Bỏ", th: "ลบ", zh: "移除", ko: "제거" })}
                >
                  ✕
                </button>
              </div>

              <div className="grid grid-cols-3 gap-3 font-mono text-xs">
                <div>
                  <p className="label">{tLang(lang, { en: "Pts", vi: "Điểm", th: "แต้ม", zh: "分", ko: "점" })}</p>
                  <p className="text-neon font-display text-lg">{t.stats.points}</p>
                </div>
                <div>
                  <p className="label">GD</p>
                  <p className="font-display text-lg">
                    {t.stats.goals_for - t.stats.goals_against > 0 ? "+" : ""}
                    {t.stats.goals_for - t.stats.goals_against}
                  </p>
                </div>
                <div>
                  <p className="label">xG Δ</p>
                  <p className={`font-display text-lg ${xgDiff > 0 ? "text-neon" : "text-error"}`}>
                    {xgDiff > 0 ? "+" : ""}{xgDiff.toFixed(1)}
                  </p>
                </div>
              </div>

              {t.form.length > 0 && (
                <div className="flex gap-1.5">
                  {t.form.slice(0, 10).map((r, i) => (
                    <span key={i} className={`h-2 w-2 rounded-full ${formDot(r)}`} />
                  ))}
                </div>
              )}

              <div className="space-y-2 pt-2 border-t border-border-muted">
                {next && (
                  <Link href={`/match/${next.id}`} className="flex items-center gap-2 text-sm hover:text-neon">
                    <span className="font-mono text-[10px] uppercase text-neon w-10">Next</span>
                    <span className="font-mono flex-1 truncate">
                      {next.is_home
                        ? `${t.short_name} vs ${next.away_short}`
                        : `${next.home_short} vs ${t.short_name}`}
                    </span>
                    <span className="font-mono text-[10px] text-muted">
                      {new Date(next.kickoff_time).toISOString().slice(5, 10)}
                    </span>
                  </Link>
                )}
                {last && last.home_goals != null && last.away_goals != null && (
                  <Link href={`/match/${last.id}`} className="flex items-center gap-2 text-sm hover:text-neon">
                    <span
                      className={`font-mono text-[10px] uppercase w-10 ${
                        lastRes === "W" ? "text-neon" : lastRes === "L" ? "text-error" : "text-secondary"
                      }`}
                    >
                      Last {lastRes}
                    </span>
                    <span className="font-mono flex-1 tabular-nums">
                      {last.home_short} {last.home_goals}-{last.away_goals} {last.away_short}
                    </span>
                  </Link>
                )}
              </div>
            </div>
          );
        })}
      </section>

      <footer className="font-mono text-[11px] uppercase tracking-wide text-muted">
        <Link href="/sync" className="hover:text-neon">
          {tLang(lang, {
            en: "→ Sync across devices with a 6-digit PIN",
            vi: "→ Sync giữa thiết bị bằng PIN 6 số",
            th: "→ ซิงค์ข้ามอุปกรณ์ด้วย PIN 6 หลัก",
            zh: "→ 6 位 PIN 跨设备同步",
            ko: "→ 6자리 PIN으로 기기 간 동기화",
          })}
        </Link>
      </footer>
    </main>
  );
}
