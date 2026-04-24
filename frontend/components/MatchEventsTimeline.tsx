import type { Lang } from "@/lib/i18n";
import type { MatchEvent } from "@/lib/types";

// Horizontal 0-90+ min strip. Home events plot above the centerline,
// away events below. Iconified per event type. Positioned by minute
// (extra-time minutes clamp to 90/105 visually but keep their label).
//
// Pure CSS + absolute positioning — no SVG. Keeps the bundle small and
// makes mobile-screen scaling a non-issue.

function icon(ev: MatchEvent): string {
  if (ev.event_type === "Goal") {
    const d = (ev.event_detail || "").toLowerCase();
    if (d.includes("own goal")) return "⚽";
    if (d.includes("penalty") && d.includes("missed")) return "⛔";
    if (d.includes("penalty")) return "🎯";
    return "⚽";
  }
  if (ev.event_type === "Card") {
    return ev.event_detail === "Red Card" ? "🟥" : "🟨";
  }
  if (ev.event_type === "subst") return "🔄";
  if (ev.event_type === "Var") return "🎥";
  return "•";
}

function minuteLabel(ev: MatchEvent): string {
  if (ev.minute == null) return "—";
  if (ev.extra_minute) return `${ev.minute}+${ev.extra_minute}'`;
  return `${ev.minute}'`;
}

function xPercent(ev: MatchEvent): number {
  // Map minute → 0..100 across a nominal 0..90 pitch clock with extra
  // time pinned to the end. Anything past 90 (ET in cups) compresses
  // into the final 10 % so it stays visible without blowing up the bar.
  if (ev.minute == null) return 0;
  const base = Math.min(ev.minute, 90);
  const et = ev.minute > 90 ? Math.min(ev.minute - 90, 30) : 0;
  return (base / 90) * 90 + (et / 30) * 10;
}

export default function MatchEventsTimeline({
  events,
  lang,
  homeSlug,
  homeShort,
  awayShort,
}: {
  events: MatchEvent[];
  lang: Lang;
  homeSlug: string;
  homeShort: string;
  awayShort: string;
}) {
  const timed = events
    .filter((e) => e.minute != null)
    .sort((a, b) => (a.minute ?? 0) - (b.minute ?? 0));
  if (timed.length === 0) return null;

  const home = timed.filter((e) => e.team_slug === homeSlug);
  const away = timed.filter((e) => e.team_slug && e.team_slug !== homeSlug);

  const ticks = [0, 15, 30, 45, 60, 75, 90];

  return (
    <section className="card space-y-4">
      <div className="flex items-baseline justify-between">
        <h2 className="font-display font-semibold uppercase tracking-tight">
          {lang === "vi" ? "Dòng thời gian" : "Timeline"}
        </h2>
        <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
          {lang === "vi" ? "⚽ bàn · 🟨🟥 thẻ · 🔄 thay người" : "⚽ goal · 🟨🟥 card · 🔄 sub"}
        </p>
      </div>

      <div className="relative px-2 py-10">
        {/* Home label (left) + away label (right) */}
        <div className="absolute left-0 top-1/2 -translate-y-1/2 font-mono text-[10px] uppercase tracking-[0.18em] text-muted">
          {homeShort}
        </div>
        <div className="absolute right-0 top-1/2 -translate-y-1/2 font-mono text-[10px] uppercase tracking-[0.18em] text-muted">
          {awayShort}
        </div>

        {/* Plotting area */}
        <div className="relative mx-10 h-20">
          {/* Centerline — home above, away below */}
          <div className="absolute left-0 right-0 top-1/2 h-px bg-border" />
          {/* Halftime divider + tick marks */}
          {ticks.map((t) => (
            <div
              key={t}
              className="absolute top-0 bottom-0 border-l border-dashed"
              style={{
                left: `${(t / 90) * 90}%`,
                borderColor: t === 45 ? "rgb(120 120 120 / 0.6)" : "rgb(120 120 120 / 0.2)",
              }}
            >
              <span className="absolute -bottom-5 -translate-x-1/2 font-mono text-[9px] text-muted tabular-nums">
                {t === 90 ? "90+" : t}
              </span>
            </div>
          ))}

          {/* Home events — above the line */}
          {home.map((e, i) => {
            const leftPct = xPercent(e);
            return (
              <div
                key={`h-${i}`}
                className="absolute -translate-x-1/2"
                style={{ left: `${leftPct}%`, top: "6px" }}
                title={`${minuteLabel(e)} · ${e.player_name ?? "—"}${
                  e.event_detail ? " · " + e.event_detail : ""
                }`}
              >
                <span className="block text-lg leading-none">{icon(e)}</span>
                <span className="block text-center font-mono text-[9px] tabular-nums text-muted">
                  {minuteLabel(e)}
                </span>
              </div>
            );
          })}

          {/* Away events — below the line */}
          {away.map((e, i) => {
            const leftPct = xPercent(e);
            return (
              <div
                key={`a-${i}`}
                className="absolute -translate-x-1/2"
                style={{ left: `${leftPct}%`, bottom: "6px" }}
                title={`${minuteLabel(e)} · ${e.player_name ?? "—"}${
                  e.event_detail ? " · " + e.event_detail : ""
                }`}
              >
                <span className="block text-center font-mono text-[9px] tabular-nums text-muted">
                  {minuteLabel(e)}
                </span>
                <span className="block text-lg leading-none">{icon(e)}</span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
