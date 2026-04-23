import fs from "node:fs/promises";
import path from "node:path";

const CONTENT_DIR = path.join(process.cwd(), "content", "blog");

export type BlogFrontmatter = {
  slug: string;
  title: string;
  date: string;
  excerpt: string;
  tags: string[];
};

export type BlogPost = BlogFrontmatter & {
  body: string;
};

function parseFrontmatter(raw: string): { meta: BlogFrontmatter; body: string } {
  const match = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) {
    throw new Error("missing frontmatter block");
  }
  const [, fm, body] = match;
  const meta: Record<string, string | string[]> = {};
  for (const line of fm.split("\n")) {
    const m = line.match(/^([A-Za-z_]+):\s*(.*)$/);
    if (!m) continue;
    const [, key, valueRaw] = m;
    let value = valueRaw.trim();
    if (value.startsWith("[") && value.endsWith("]")) {
      meta[key] = value
        .slice(1, -1)
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
    } else {
      meta[key] = value;
    }
  }
  return {
    meta: {
      slug: String(meta.slug ?? ""),
      title: String(meta.title ?? ""),
      date: String(meta.date ?? ""),
      excerpt: String(meta.excerpt ?? ""),
      tags: Array.isArray(meta.tags) ? meta.tags : [],
    },
    body,
  };
}

const BASE = process.env.SERVER_API_URL ?? "http://localhost:8000";

type AutoPost = {
  slug: string;
  title: string;
  excerpt: string;
  body_md: string;
  tags: string[];
  lang: string;
  generated_at: string;
  model: string | null;
};

async function listAutoPosts(): Promise<BlogFrontmatter[]> {
  try {
    const res = await fetch(`${BASE}/api/blog?limit=50`, { next: { revalidate: 600 } });
    if (!res.ok) return [];
    const rows: AutoPost[] = await res.json();
    return rows.map((r) => ({
      slug: r.slug,
      title: r.title,
      date: r.generated_at.slice(0, 10),
      excerpt: r.excerpt,
      tags: r.tags,
    }));
  } catch {
    return [];
  }
}

async function getAutoPost(slug: string): Promise<BlogPost | null> {
  try {
    const res = await fetch(`${BASE}/api/blog/${encodeURIComponent(slug)}`, {
      next: { revalidate: 600 },
    });
    if (!res.ok) return null;
    const r: AutoPost | null = await res.json();
    if (!r) return null;
    return {
      slug: r.slug,
      title: r.title,
      date: r.generated_at.slice(0, 10),
      excerpt: r.excerpt,
      tags: r.tags,
      body: r.body_md,
    };
  } catch {
    return null;
  }
}

export async function listPosts(): Promise<BlogFrontmatter[]> {
  const files = await fs.readdir(CONTENT_DIR).catch(() => [] as string[]);
  const filePosts: BlogFrontmatter[] = [];
  for (const f of files) {
    if (!f.endsWith(".md")) continue;
    const raw = await fs.readFile(path.join(CONTENT_DIR, f), "utf8");
    const { meta } = parseFrontmatter(raw);
    filePosts.push(meta);
  }
  const autoPosts = await listAutoPosts();
  const merged = [...filePosts, ...autoPosts];
  // Dedupe by slug — file-based wins over auto if they share a slug.
  const seen = new Set<string>();
  const out: BlogFrontmatter[] = [];
  for (const p of merged) {
    if (seen.has(p.slug)) continue;
    seen.add(p.slug);
    out.push(p);
  }
  out.sort((a, b) => b.date.localeCompare(a.date));
  return out;
}

export async function getPost(slug: string): Promise<BlogPost | null> {
  // File-based first (authored content), DB fallback (auto-generated).
  try {
    const raw = await fs.readFile(path.join(CONTENT_DIR, `${slug}.md`), "utf8");
    const { meta, body } = parseFrontmatter(raw);
    return { ...meta, body };
  } catch {
    return await getAutoPost(slug);
  }
}

// Minimal markdown → HTML. Supports headings, paragraphs, fenced code blocks,
// inline code, bold, italic, links, and simple table rows. Enough for our
// three seed posts; full markdown later.
export function renderMarkdown(md: string): string {
  const lines = md.split("\n");
  const out: string[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++;
      const cls = lang ? ` class="language-${lang}"` : "";
      out.push(`<pre><code${cls}>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
      continue;
    }
    if (line.startsWith("## ")) {
      out.push(`<h2>${inline(line.slice(3))}</h2>`);
      i++;
      continue;
    }
    if (line.startsWith("### ")) {
      out.push(`<h3>${inline(line.slice(4))}</h3>`);
      i++;
      continue;
    }
    if (line.startsWith("# ")) {
      out.push(`<h1>${inline(line.slice(2))}</h1>`);
      i++;
      continue;
    }
    if (line.startsWith("|")) {
      // consume consecutive table lines
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      out.push(renderTable(tableLines));
      continue;
    }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      const items: string[] = [];
      while (i < lines.length && (lines[i].startsWith("- ") || lines[i].startsWith("* "))) {
        items.push(`<li>${inline(lines[i].slice(2))}</li>`);
        i++;
      }
      out.push(`<ul>${items.join("")}</ul>`);
      continue;
    }
    if (line.trim() === "") {
      i++;
      continue;
    }
    // paragraph: consume until blank line
    const para: string[] = [line];
    i++;
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !lines[i].startsWith("#") &&
      !lines[i].startsWith("```") &&
      !lines[i].startsWith("|") &&
      !lines[i].startsWith("- ") &&
      !lines[i].startsWith("* ")
    ) {
      para.push(lines[i]);
      i++;
    }
    out.push(`<p>${inline(para.join(" "))}</p>`);
  }
  return out.join("\n");
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function inline(s: string): string {
  // escape first, then re-apply markers
  let out = escapeHtml(s);
  // bold **text**
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  // italic *text*
  out = out.replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, "$1<em>$2</em>");
  // inline code `x`
  out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
  // links [text](url)
  out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  return out;
}

function renderTable(lines: string[]): string {
  const rows = lines
    .map((l) => l.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim()));
  if (rows.length < 2) return "";
  // rows[1] is the separator like ---|---|---; drop it
  const header = rows[0];
  const body = rows.slice(2);
  const head = `<thead><tr>${header.map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead>`;
  const tbody = `<tbody>${body
    .map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`)
    .join("")}</tbody>`;
  return `<table>${head}${tbody}</table>`;
}
