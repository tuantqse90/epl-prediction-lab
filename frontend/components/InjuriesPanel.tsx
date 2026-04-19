import type { Injury, MatchInjuries } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

function dot(status: string | null): string {
  const s = (status || "").toLowerCase();
  if (s.includes("missing") || s.includes("out")) return "bg-error";
  if (s.includes("question") || s.includes("doubt")) return "bg-secondary";
  return "bg-muted";
}

function Column({
  title,
  rows,
  emptyLabel,
}: {
  title: string;
  rows: Injury[];
  emptyLabel: string;
}) {
  return (
    <div className="space-y-3 min-w-0">
      <h3 className="label truncate">{title}</h3>
      {rows.length === 0 ? (
        <p className="text-muted text-sm">{emptyLabel}</p>
      ) : (
        <ul className="space-y-1.5">
          {rows.map((r) => (
            <li
              key={`${r.team_slug}-${r.player_name}-${r.reason ?? ""}`}
              className="flex items-start gap-2 text-sm"
            >
              <span
                aria-hidden
                className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${dot(r.status_label)}`}
              />
              <span className="min-w-0">
                <span className="text-primary">{r.player_name}</span>
                {r.reason && (
                  <span className="text-muted font-mono text-xs ml-1">· {r.reason}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function InjuriesPanel({
  injuries,
  homeShort,
  awayShort,
  lang,
}: {
  injuries: MatchInjuries;
  homeShort: string;
  awayShort: string;
  lang: Lang;
}) {
  const total = injuries.home.length + injuries.away.length;
  if (total === 0) return null;

  const emptyLabel = lang === "vi" ? "Không có" : "None reported";
  const title = lang === "vi" ? "Chấn thương / nghỉ thi đấu" : "Injuries / absentees";

  return (
    <section className="card space-y-4">
      <h2 className="label">{title}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Column title={homeShort} rows={injuries.home} emptyLabel={emptyLabel} />
        <Column title={awayShort} rows={injuries.away} emptyLabel={emptyLabel} />
      </div>
    </section>
  );
}
