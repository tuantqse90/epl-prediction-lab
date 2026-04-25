import { getMatchStory } from "@/lib/api";
import { getLang } from "@/lib/i18n-server";

const SITE = "https://predictor.nullshift.sh";

export default async function MatchStoryCard({ matchId }: { matchId: number }) {
  const lang = await getLang();
  const data = await getMatchStory(matchId, lang);
  if (!data) return null;

  const paragraphs = data.story
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);

  // NewsArticle schema — Google picks up the body + date and can index
  // the story under the /match/:id URL.
  const ld = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: paragraphs[0]?.slice(0, 110) ?? "Match story",
    articleBody: data.story,
    datePublished: data.generated_at ?? undefined,
    dateModified: data.generated_at ?? undefined,
    author: {
      "@type": "Organization",
      name: "EPL Prediction Lab",
      url: SITE,
    },
    publisher: {
      "@type": "Organization",
      name: "EPL Prediction Lab",
      url: SITE,
    },
    mainEntityOfPage: `${SITE}/match/${matchId}`,
  };

  return (
    <section className="card space-y-4">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(ld) }}
      />
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
