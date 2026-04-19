import type { Metadata } from "next";
import Link from "next/link";

import { listPosts } from "@/lib/blog";
import { getLang, tFor } from "@/lib/i18n-server";

export const metadata: Metadata = {
  title: "Blog · predictor.nullshift.sh",
  description: "Technical writeups on the model, the ensemble weights, and the honest gaps.",
};

export default async function BlogIndex() {
  const posts = await listPosts();
  const lang = await getLang();
  const t = tFor(lang);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-10">
      <Link href="/" className="btn-ghost text-sm">
        {t("common.back")}
      </Link>
      <header className="space-y-3">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-neon">blog</p>
        <h1 className="headline-hero">Writeups</h1>
        <p className="text-secondary text-base md:text-lg max-w-xl">
          Notes on the model — why specific weights, why specific corrections,
          what the numbers do and don&apos;t prove. No fluff, no roadmap promises.
        </p>
      </header>

      <section className="space-y-6">
        {posts.map((p) => (
          <Link
            key={p.slug}
            href={`/blog/${p.slug}`}
            className="card block space-y-3 hover:border-neon transition-colors"
          >
            <div className="flex items-baseline justify-between gap-3 flex-wrap">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">
                {p.date}
              </span>
              {p.tags.length > 0 && (
                <span className="font-mono text-[10px] text-muted">
                  {p.tags.map((tag) => `#${tag}`).join(" ")}
                </span>
              )}
            </div>
            <h2 className="font-display text-xl md:text-2xl font-semibold text-primary leading-tight">
              {p.title}
            </h2>
            <p className="text-secondary text-sm leading-relaxed">{p.excerpt}</p>
          </Link>
        ))}
      </section>
    </main>
  );
}
