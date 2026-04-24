import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const metadata = {
  title: "Privacy policy · predictor.nullshift.sh",
  description: "What we collect, what we don't, how long we keep it.",
};

export default async function PrivacyPage() {
  const lang = await getLang();
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-6 blog-prose">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>
      <header>
        <p className="font-mono text-xs text-muted">docs · privacy</p>
        <h1 className="headline-section">Privacy policy</h1>
        <p className="text-muted text-sm">Last updated: 2026-04-24</p>
      </header>

      <section className="space-y-3">
        <h2>What we collect</h2>
        <ul>
          <li>
            <b>Page views</b> — path only, via <code>/api/analytics/pv</code>. No IP stored.
            Country when Cloudflare's <code>CF-IPCountry</code> header is available. Retention: 90 days.
          </li>
          <li>
            <b>Email addresses</b> — only if you subscribe to the weekly digest at <Link href="/subscribe" className="hover:text-neon">/subscribe</Link>. One-click unsubscribe.
          </li>
          <li>
            <b>Telegram chat_id</b> — only if you <code>/subscribe TEAM</code> with the bot.
          </li>
          <li>
            <b>Sync PIN payload</b> — stored hashed (SHA-256) if you opt into <Link href="/sync" className="hover:text-neon">/sync</Link>; we never see the 6 digits.
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2>What we DON'T collect</h2>
        <ul>
          <li>No names, addresses, phone numbers.</li>
          <li>No IP addresses in stored data.</li>
          <li>No third-party advertising trackers, social-network pixels, session replay.</li>
          <li>No behavioural profiling beyond anonymous path counts.</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2>Your rights (GDPR / VN PDPL / general)</h2>
        <p>
          You can request a data export or deletion at any time by emailing the repo owner.
          Email subscriptions: one-click unsubscribe via the link in each digest. Sync PIN:
          overwrite your slot by pushing an empty payload; data auto-pruned after 90 days of inactivity.
        </p>
      </section>

      <section className="space-y-3">
        <h2>Cookies</h2>
        <p>
          We use localStorage for favourites, betslip, my-picks, and preferences. No cookies
          for tracking. No cookie banner needed.
        </p>
      </section>
    </main>
  );
}
