import { getMatchStory } from "@/lib/api";

export default async function MatchStoryCard({ matchId }: { matchId: number }) {
  const data = await getMatchStory(matchId);
  if (!data) return null;

  const paragraphs = data.story
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <section className="card space-y-4">
      <div className="flex items-baseline justify-between">
        <p className="font-mono text-[10px] uppercase tracking-wide text-muted">story</p>
        <p className="font-mono text-[10px] text-muted">
          {data.model?.split("/").pop() ?? "ai"}
        </p>
      </div>
      <div className="space-y-3 text-secondary leading-relaxed">
        {paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    </section>
  );
}
