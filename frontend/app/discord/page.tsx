"use client";

import Link from "next/link";
import { useState } from "react";

import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

const SITE = "https://predictor.nullshift.sh";

export default function DiscordPage() {
  const lang = useLang();
  const [url, setUrl] = useState("");
  const [label, setLabel] = useState("");
  const [teams, setTeams] = useState("");
  const [daily, setDaily] = useState(true);
  const [goals, setGoals] = useState(true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function register() {
    if (!url.startsWith("https://discord.com/api/webhooks/")) {
      setMsg({ ok: false, text: "Invalid webhook URL — must start with https://discord.com/api/webhooks/" });
      return;
    }
    setBusy(true); setMsg(null);
    try {
      const res = await fetch("/api/discord/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          label: label || null,
          team_slugs: teams ? teams.split(",").map((t) => t.trim()).filter(Boolean) : null,
          daily_digest: daily,
          goal_pings: goals,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setMsg({ ok: true, text: "✅ Registered. Goals + KO + HT/FT + drama events will fan out to your Discord channel." });
      setUrl(""); setLabel(""); setTeams("");
    } catch (e) {
      setMsg({ ok: false, text: String(e) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-neon">discord</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Pipe match alerts to your Discord server",
            vi: "Đẩy alert trận đấu thẳng vào Discord server",
            th: "ส่งการแจ้งเตือนแมตช์เข้า Discord ของคุณ",
            zh: "将比赛提醒推送到您的 Discord 服务器",
            ko: "경기 알림을 Discord 서버로 전달",
          })}
        </h1>
        <p className="text-secondary max-w-2xl">
          {tLang(lang, {
            en: "Every goal, red card, VAR reversal, kickoff, half-time and full-time fans out to registered Discord webhooks. Sub-second delivery, no bot install, no oAuth.",
            vi: "Mỗi bàn thắng, thẻ đỏ, VAR, kick-off, hết hiệp 1 và hết trận đều fan-out đến Discord webhook đã đăng ký. Dưới 1 giây độ trễ, không cần cài bot, không cần oAuth.",
            th: "ทุกประตู ใบแดง VAR เริ่มเกม พักครึ่ง และจบเกมจะส่งเข้า webhook ที่ลงทะเบียน",
            zh: "每个进球 · 红牌 · VAR · 开球 · 中场 · 终场 都会推送到已注册的 Discord webhook",
            ko: "모든 골 / 레드카드 / VAR / 킥오프 / 하프타임 / 풀타임 알림을 Discord webhook으로 전송",
          })}
        </p>
      </header>

      {/* How-to */}
      <section className="card space-y-4">
        <h2 className="font-display text-lg font-semibold">
          {tLang(lang, {
            en: "1 — Create the webhook in Discord",
            vi: "1 — Tạo webhook trong Discord",
            th: "1 — สร้าง webhook ใน Discord",
            zh: "1 — 在 Discord 创建 webhook",
            ko: "1 — Discord에서 webhook 생성",
          })}
        </h2>
        <ol className="space-y-2 text-sm text-secondary list-decimal pl-5">
          <li>
            {tLang(lang, {
              en: "Open your Discord server → Settings → Integrations → Webhooks → New Webhook",
              vi: "Mở Discord server → Settings → Integrations → Webhooks → New Webhook",
              th: "เปิด Discord server → Settings → Integrations → Webhooks → New Webhook",
              zh: "打开 Discord 服务器 → 设置 → 集成 → Webhook → 新建",
              ko: "Discord 서버 → 설정 → 통합 → Webhook → 새로 만들기",
            })}
          </li>
          <li>
            {tLang(lang, {
              en: "Pick the channel where alerts should land. Name it 'Match Alerts' or similar.",
              vi: "Chọn channel nhận alert. Đặt tên 'Match Alerts' hoặc tương tự.",
              th: "เลือก channel ที่จะรับการแจ้งเตือน",
              zh: "选择接收提醒的频道",
              ko: "알림을 받을 채널 선택",
            })}
          </li>
          <li>
            {tLang(lang, {
              en: "Click 'Copy Webhook URL' — it looks like https://discord.com/api/webhooks/…",
              vi: "Click 'Copy Webhook URL' — dạng https://discord.com/api/webhooks/…",
              th: "คัดลอก URL webhook",
              zh: "复制 Webhook URL",
              ko: "Webhook URL 복사",
            })}
          </li>
        </ol>
      </section>

      {/* Form */}
      <section className="card space-y-4">
        <h2 className="font-display text-lg font-semibold">
          {tLang(lang, {
            en: "2 — Register it here",
            vi: "2 — Đăng ký webhook ở đây",
            th: "2 — ลงทะเบียน webhook ที่นี่",
            zh: "2 — 在此注册",
            ko: "2 — 여기서 등록",
          })}
        </h2>

        <label className="block space-y-1">
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted">Webhook URL</span>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://discord.com/api/webhooks/..."
            className="w-full rounded border border-border bg-raised px-3 py-2 font-mono text-xs"
          />
        </label>

        <label className="block space-y-1">
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted">
            {tLang(lang, {
              en: "Label (optional)",
              vi: "Tên (tuỳ chọn)",
              th: "ชื่อ (ตัวเลือก)",
              zh: "标签（可选）",
              ko: "라벨 (선택)",
            })}
          </span>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="My football server"
            className="w-full rounded border border-border bg-raised px-3 py-2 text-sm"
          />
        </label>

        <label className="block space-y-1">
          <span className="font-mono text-[10px] uppercase tracking-wide text-muted">
            {tLang(lang, {
              en: "Team slugs to follow (comma-separated, leave blank for all)",
              vi: "Đội theo dõi (slug, ngăn cách dấu phẩy, để trống = tất cả)",
              th: "ทีมที่ติดตาม",
              zh: "关注球队",
              ko: "팔로우할 팀",
            })}
          </span>
          <input
            type="text"
            value={teams}
            onChange={(e) => setTeams(e.target.value)}
            placeholder="real-madrid, arsenal"
            className="w-full rounded border border-border bg-raised px-3 py-2 text-sm font-mono"
          />
        </label>

        <div className="flex flex-wrap gap-4">
          <label className="inline-flex items-center gap-2 text-sm text-secondary">
            <input
              type="checkbox"
              checked={goals}
              onChange={(e) => setGoals(e.target.checked)}
            />
            <span>
              {tLang(lang, {
                en: "Goal + KO + FT pings",
                vi: "Bàn + KO + FT",
                th: "ประตู + เริ่มเกม + จบเกม",
                zh: "进球 + 开球 + 终场",
                ko: "골 + 킥오프 + 종료",
              })}
            </span>
          </label>
          <label className="inline-flex items-center gap-2 text-sm text-secondary">
            <input
              type="checkbox"
              checked={daily}
              onChange={(e) => setDaily(e.target.checked)}
            />
            <span>
              {tLang(lang, {
                en: "Daily morning digest",
                vi: "Digest sáng",
                th: "ดิจสต์ตอนเช้า",
                zh: "每日晨报",
                ko: "아침 다이제스트",
              })}
            </span>
          </label>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button onClick={register} disabled={busy} className="btn-primary text-sm">
            {busy ? "…" : tLang(lang, {
              en: "Register webhook", vi: "Đăng ký", th: "ลงทะเบียน",
              zh: "注册", ko: "등록",
            })}
          </button>
          {msg && (
            <span className={msg.ok ? "text-neon text-sm" : "text-error text-sm"}>
              {msg.text}
            </span>
          )}
        </div>
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• {tLang(lang, {
          en: "We never see your webhook secret — Discord rotates it on demand.",
          vi: "Chúng tôi không thấy secret — Discord tự rotate.",
          th: "เราไม่เห็น webhook secret",
          zh: "我们看不到您的 webhook secret",
          ko: "우리는 webhook secret을 볼 수 없음",
        })}</p>
        <p>• {tLang(lang, {
          en: "Unsubscribe: DELETE /api/discord/register?url=…",
          vi: "Huỷ: DELETE /api/discord/register?url=…",
          th: "ยกเลิก",
          zh: "取消订阅",
          ko: "구독 취소",
        })} <code>{SITE}/api/discord/register?url=…</code></p>
        <p>• {tLang(lang, {
          en: "Same fan-out is also live on Telegram — see ",
          vi: "Cùng fan-out có trên Telegram — xem ",
          th: "เช่นเดียวกับ Telegram — ดู ",
          zh: "Telegram 也有同样推送 — 见 ",
          ko: "Telegram도 동일 — ",
        })}<a href="https://t.me/predictor_nullshift" className="hover:text-neon" target="_blank" rel="noopener">@predictor_nullshift</a></p>
      </section>
    </main>
  );
}
