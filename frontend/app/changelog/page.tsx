import Link from "next/link";
import fs from "node:fs/promises";
import path from "node:path";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Changelog · predictor.nullshift.sh",
  description: "What shipped when. Pulled from PROGRESS.md.",
};

async function loadProgress(): Promise<string> {
  // PROGRESS.md lives at repo root. Read via relative path; falls back
  // to empty if the file isn't copied into the container.
  const candidates = [
    path.join(process.cwd(), "..", "PROGRESS.md"),
    path.join(process.cwd(), "PROGRESS.md"),
    "/app/PROGRESS.md",
  ];
  for (const p of candidates) {
    try {
      return await fs.readFile(p, "utf8");
    } catch {}
  }
  return "";
}

type Entry = { header: string; body: string };

function parseEntries(md: string): Entry[] {
  const sections = md.split(/^## /m).slice(1);
  return sections.map((s) => {
    const newline = s.indexOf("\n");
    return {
      header: s.slice(0, newline).trim(),
      body: s.slice(newline + 1).trim(),
    };
  });
}

export default async function ChangelogPage() {
  const lang = await getLang();
  const md = await loadProgress();
  const entries = parseEntries(md);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>
      <header>
        <p className="font-mono text-xs text-muted">docs · changelog</p>
        <h1 className="headline-section">
          {tLang(lang, { en: "Changelog", vi: "Nhật ký thay đổi", th: "บันทึกการเปลี่ยนแปลง", zh: "更新日志", ko: "변경 로그" })}
        </h1>
      </header>
      {entries.length === 0 ? (
        <div className="card text-muted">PROGRESS.md not mounted into the web container yet.</div>
      ) : (
        <ol className="space-y-6">
          {entries.slice(0, 50).map((e, i) => (
            <li key={i} className="card space-y-2">
              <h2 className="font-display text-lg font-semibold">{e.header}</h2>
              <div className="blog-prose text-sm text-secondary whitespace-pre-wrap">
                {e.body.slice(0, 1200)}
              </div>
            </li>
          ))}
        </ol>
      )}
    </main>
  );
}
