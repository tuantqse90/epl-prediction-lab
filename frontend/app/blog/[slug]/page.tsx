import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getPost, listPosts, renderMarkdown } from "@/lib/blog";
import { getLang, tFor } from "@/lib/i18n-server";
import { alternatesFor, breadcrumbLd } from "@/lib/seo";

const SITE = "https://predictor.nullshift.sh";

export async function generateStaticParams() {
  const posts = await listPosts();
  return posts.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) return { title: "Post not found" };
  return {
    title: `${post.title} · predictor.nullshift.sh`,
    description: post.excerpt,
    openGraph: {
      title: post.title,
      description: post.excerpt,
      type: "article",
      publishedTime: post.date,
      tags: post.tags,
    },
    twitter: { card: "summary_large_image", title: post.title, description: post.excerpt },
    alternates: alternatesFor(`/blog/${post.slug}`),
  };
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) notFound();
  const lang = await getLang();
  const t = tFor(lang);
  const html = renderMarkdown(post.body);

  const articleLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.excerpt,
    datePublished: post.date,
    dateModified: post.date,
    author: { "@type": "Organization", name: "EPL Prediction Lab", url: SITE },
    publisher: { "@type": "Organization", name: "EPL Prediction Lab", url: SITE },
    mainEntityOfPage: `${SITE}/blog/${post.slug}`,
    keywords: post.tags.join(", "),
  };

  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-8">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleLd) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(
            breadcrumbLd([
              { name: "Home", path: "/" },
              { name: "Blog", path: "/blog" },
              { name: post.title, path: `/blog/${post.slug}` },
            ]),
          ),
        }}
      />
      <Link href="/blog" className="btn-ghost text-sm">
        ← blog
      </Link>

      <header className="space-y-4">
        <div className="flex items-baseline gap-3 flex-wrap">
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-neon">
            {post.date}
          </span>
          {post.tags.length > 0 && (
            <span className="font-mono text-[10px] text-muted">
              {post.tags.map((tag) => `#${tag}`).join(" ")}
            </span>
          )}
        </div>
        <h1 className="font-display text-3xl md:text-4xl font-semibold leading-tight">
          {post.title}
        </h1>
      </header>

      <article className="blog-prose" dangerouslySetInnerHTML={{ __html: html }} />

      <footer className="pt-8 border-t border-border-muted">
        <Link
          href="/"
          className="inline-flex items-center rounded-full bg-neon px-4 py-2 font-mono text-xs uppercase tracking-wide text-on-neon font-semibold hover:opacity-90 transition-opacity"
        >
          {t("common.back")}
        </Link>
      </footer>
    </main>
  );
}
