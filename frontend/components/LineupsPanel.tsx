import type { MatchLineups, TeamLineup } from "@/lib/api";
import type { Lang } from "@/lib/i18n";

function TeamColumn({ lineup, teamName }: { lineup: TeamLineup | null; teamName: string }) {
  if (!lineup) {
    return (
      <div className="space-y-3 min-w-0">
        <h3 className="label truncate">{teamName}</h3>
        <p className="text-muted text-sm">Pending</p>
      </div>
    );
  }
  return (
    <div className="space-y-3 min-w-0">
      <h3 className="label truncate flex items-center gap-2">
        <span>{teamName}</span>
        {lineup.formation && (
          <span className="text-muted font-mono text-[10px]">{lineup.formation}</span>
        )}
      </h3>
      <ul className="space-y-1 text-sm">
        {lineup.starting.map((p) => (
          <li key={p.player_name} className="flex items-center gap-2">
            <span className="w-6 shrink-0 font-mono text-xs text-muted tabular-nums text-right">
              {p.player_number ?? "–"}
            </span>
            <span className="w-6 shrink-0 font-mono text-[10px] uppercase text-muted">
              {p.position ?? ""}
            </span>
            <span className="truncate">{p.player_name}</span>
          </li>
        ))}
      </ul>
      {lineup.bench.length > 0 && (
        <div>
          <p className="label text-[10px] mb-1">Bench</p>
          <ul className="space-y-0.5 text-xs text-muted">
            {lineup.bench.slice(0, 12).map((p) => (
              <li key={p.player_name} className="truncate">
                {p.player_number ?? "–"} · {p.player_name}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function LineupsPanel({
  lineups,
  homeName,
  awayName,
  lang,
}: {
  lineups: MatchLineups;
  homeName: string;
  awayName: string;
  lang: Lang;
}) {
  const any = (lineups.home && lineups.home.starting.length > 0) ||
    (lineups.away && lineups.away.starting.length > 0);
  if (!any) return null;

  const title = lang === "vi" ? "Đội hình ra sân" : "Starting XI";

  return (
    <section className="card space-y-4">
      <h2 className="label">{title}</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <TeamColumn lineup={lineups.home} teamName={homeName} />
        <TeamColumn lineup={lineups.away} teamName={awayName} />
      </div>
    </section>
  );
}
