import type { Lang } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import type { MatchEvent } from "@/lib/types";

function icon(ev: MatchEvent): string {
  if (ev.event_type === "Goal") {
    const d = (ev.event_detail || "").toLowerCase();
    if (d.includes("own goal")) return "⚽️";
    if (d.includes("penalty") && d.includes("missed")) return "⛔️";
    if (d.includes("penalty")) return "🎯";
    return "⚽️";
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

export default function MatchEventsList({
  events,
  lang,
  homeSlug,
}: {
  events: MatchEvent[];
  lang: Lang;
  homeSlug: string;
}) {
  if (events.length === 0) return null;
  const goals = events.filter((e) => e.event_type === "Goal");
  const cards = events.filter((e) => e.event_type === "Card");
  const subs = events.filter((e) => e.event_type === "subst");

  return (
    <section className="card space-y-4">
      <h2 className="font-display font-semibold uppercase tracking-tight">
        {t(lang, "events.title")}
      </h2>

      {goals.length > 0 && (
        <div>
          <p className="label mb-2">{t(lang, "events.goals")}</p>
          <ul className="space-y-2 font-mono text-sm">
            {goals.map((e, i) => {
              const side = e.team_slug === homeSlug ? "left" : "right";
              return (
                <li
                  key={`g-${i}`}
                  className={`flex items-center gap-2 ${side === "right" ? "flex-row-reverse text-right" : ""}`}
                >
                  <span className="text-lg">{icon(e)}</span>
                  <span className="text-muted tabular-nums w-12">{minuteLabel(e)}</span>
                  <span className="text-primary font-semibold">{e.player_name ?? "—"}</span>
                  {e.assist_name && (
                    <span className="text-muted text-xs">({e.assist_name})</span>
                  )}
                  {e.event_detail && e.event_detail !== "Normal Goal" && (
                    <span className="text-neon text-xs uppercase tracking-wide">{e.event_detail}</span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {cards.length > 0 && (
        <div>
          <p className="label mb-2">{t(lang, "events.cards")}</p>
          <ul className="space-y-1 font-mono text-xs text-secondary">
            {cards.map((e, i) => (
              <li key={`c-${i}`} className="flex items-center gap-2">
                <span>{icon(e)}</span>
                <span className="text-muted tabular-nums w-12">{minuteLabel(e)}</span>
                <span>{e.player_name ?? "—"}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {subs.length > 0 && (
        <div>
          <p className="label mb-2">{t(lang, "events.subs")}</p>
          <ul className="space-y-1 font-mono text-xs text-secondary">
            {subs.map((e, i) => (
              <li key={`s-${i}`} className="flex items-center gap-2">
                <span>{icon(e)}</span>
                <span className="text-muted tabular-nums w-12">{minuteLabel(e)}</span>
                <span className="text-primary">{e.assist_name ?? "—"}</span>
                <span className="text-muted">↔</span>
                <span className="text-muted">{e.player_name ?? "—"}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
