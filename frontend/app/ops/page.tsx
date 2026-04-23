import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const dynamic = "force-dynamic";

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type Alert = { match_id?: number; message: string };

type Checker = { name: string; ok: boolean; count: number; alerts: Alert[] };

type Status = {
  checked_at: string;
  overall_ok: boolean;
  checkers: Checker[];
};

async function fetchStatus(): Promise<Status | null> {
  try {
    const res = await fetch(`${BASE}/api/ops/status`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as Status;
  } catch {
    return null;
  }
}

const CHECKER_META: Record<string, { icon: string; label: { en: string; vi: string } }> = {
  fixture_drift:     { icon: "🛑", label: { en: "Fixture drift",       vi: "Lịch thi đấu lệch" } },
  stale_live:        { icon: "⚠️", label: { en: "Live feed",           vi: "Feed live" } },
  missing_recap:     { icon: "📝", label: { en: "Post-match recap",    vi: "Recap sau trận" } },
  stale_predictions: { icon: "🔮", label: { en: "Upcoming predictions", vi: "Dự đoán sắp tới" } },
  low_quota:         { icon: "📉", label: { en: "API quota",            vi: "Hạn ngạch API" } },
};

export default async function OpsPage() {
  const lang = await getLang();
  const status = await fetchStatus();

  if (!status) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8">
        <h1 className="font-display text-3xl font-bold tracking-tighter">/ops</h1>
        <p className="mt-4 text-error">
          {tLang(lang, { en: "API unreachable.", vi: "Không kết nối được API." })}
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 space-y-6">
      <header className="flex items-baseline justify-between">
        <h1 className="font-display text-3xl font-bold tracking-tighter">
          /ops
        </h1>
        <span className={`font-mono text-xs uppercase tracking-wider ${status.overall_ok ? "text-neon" : "text-error"}`}>
          {status.overall_ok
            ? tLang(lang, { en: "ALL GREEN", vi: "TẤT CẢ OK" })
            : tLang(lang, { en: "DEGRADED",  vi: "CÓ LỖI" })}
        </span>
      </header>

      <p className="text-sm text-muted">
        {tLang(lang, {
          en: "Public status page. Runs the same checks the Telegram watchdog emits every 5 min.",
          vi: "Trang trạng thái công khai. Chạy cùng các check mà watchdog Telegram gửi mỗi 5 phút.",
        })}
        {" "}
        <span className="font-mono text-xs text-muted">· {new Date(status.checked_at).toISOString()}</span>
      </p>

      <section className="card space-y-3">
        {status.checkers.map((c) => {
          const meta = CHECKER_META[c.name] ?? { icon: "•", label: { en: c.name, vi: c.name } };
          const label = tLang(lang, meta.label);
          return (
            <div key={c.name} className="border-t border-white/5 first:border-t-0 pt-3 first:pt-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span>{meta.icon}</span>
                  <span className="font-display font-semibold">{label}</span>
                </div>
                {c.ok ? (
                  <span className="rounded-full bg-neon/15 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-neon">
                    OK
                  </span>
                ) : (
                  <span className="rounded-full bg-error/15 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-error">
                    {c.count} {tLang(lang, { en: "issue" + (c.count === 1 ? "" : "s"), vi: "lỗi" })}
                  </span>
                )}
              </div>
              {!c.ok && c.alerts.length > 0 && (
                <ul className="mt-2 space-y-1 pl-6 text-sm text-secondary">
                  {c.alerts.slice(0, 10).map((a, i) => (
                    <li key={i} className="font-mono text-xs">
                      {a.match_id ? `#${a.match_id} — ` : ""}{a.message}
                    </li>
                  ))}
                  {c.alerts.length > 10 && (
                    <li className="font-mono text-xs text-muted">
                      … +{c.alerts.length - 10} {tLang(lang, { en: "more", vi: "nữa" })}
                    </li>
                  )}
                </ul>
              )}
            </div>
          );
        })}
      </section>

      <p className="text-xs text-muted">
        {tLang(lang, {
          en: "API-Football quota check runs only in the Telegram version (needs the API key).",
          vi: "Check hạn ngạch API-Football chỉ chạy trong bản Telegram (cần API key).",
        })}
      </p>
    </main>
  );
}
