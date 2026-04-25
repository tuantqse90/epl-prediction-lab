"use client";

import Link from "next/link";
import { useState } from "react";

import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

export default function PricingPage() {
  const lang = useLang();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function upgrade() {
    if (!email.trim()) { setErr("Enter an email"); return; }
    setBusy(true); setErr("");
    try {
      const res = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = await res.json();
      const dest = body.checkout_url || body.fallback;
      if (dest) {
        window.location.href = dest;
      } else {
        setErr("No checkout URL returned");
      }
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  const productLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: "EPL Prediction Lab Pro",
    description:
      "Higher API rate limits, early access to new features, priority email digest, optional supporter badge.",
    brand: { "@type": "Brand", name: "EPL Prediction Lab" },
    offers: [
      {
        "@type": "Offer",
        name: "Free",
        price: "0",
        priceCurrency: "USD",
        availability: "https://schema.org/InStock",
        description: "Every prediction across 5 leagues + UCL/UEL · 60 req/min",
      },
      {
        "@type": "Offer",
        name: "Pro",
        price: "9",
        priceCurrency: "USD",
        availability: "https://schema.org/InStock",
        priceSpecification: {
          "@type": "UnitPriceSpecification",
          price: "9",
          priceCurrency: "USD",
          billingIncrement: 1,
          unitCode: "MON",
        },
        description: "10× API rate limit · early access · cancel anytime",
      },
    ],
  };

  return (
    <main className="mx-auto max-w-4xl px-6 py-12 space-y-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(productLd) }}
      />
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-3 text-center">
        <p className="font-mono text-xs text-muted">pricing · free forever, pro optional</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Free. Pro if you want the extras.",
            vi: "Miễn phí. Pro nếu muốn thêm.",
            th: "ฟรี. Pro ถ้าต้องการเพิ่มเติม.",
            zh: "免费。Pro 可选。",
            ko: "무료. Pro는 선택.",
          })}
        </h1>
        <p className="max-w-2xl mx-auto text-secondary">
          {tLang(lang, {
            en: "Every prediction stays free forever. Pro just gets you higher API limits + early access to new features. Cancel anytime.",
            vi: "Mọi dự đoán miễn phí mãi mãi. Pro chỉ cho bạn API rate cao hơn + truy cập sớm tính năng mới. Huỷ bất kỳ lúc nào.",
            th: "การคาดการณ์ฟรีตลอดไป · Pro แค่เพิ่ม rate API",
            zh: "所有预测永久免费 · Pro 仅提升 API 限额",
            ko: "모든 예측은 영구 무료 · Pro는 API 한도 상향만",
          })}
        </p>
      </header>

      <section className="grid md:grid-cols-2 gap-4">
        <div className="card space-y-3">
          <p className="font-mono text-[10px] uppercase tracking-wide text-muted">Free</p>
          <p className="stat text-5xl">$0</p>
          <p className="text-xs text-muted">forever</p>
          <ul className="space-y-1 text-sm text-secondary pt-3">
            <li>✓ Every prediction across 5 leagues + UCL/UEL</li>
            <li>✓ Live odds, edge flags, live probs</li>
            <li>✓ Title race / bracket Monte Carlo</li>
            <li>✓ Telegram bot + email digest</li>
            <li>✓ Embed widget on your site</li>
            <li>✓ Public API — 60 req/min</li>
          </ul>
          <Link href="/" className="btn-ghost text-xs">
            {tLang(lang, { en: "Use for free", vi: "Dùng miễn phí", th: "ใช้ฟรี", zh: "免费使用", ko: "무료 사용" })}
          </Link>
        </div>

        <div className="card space-y-3 border-neon">
          <p className="font-mono text-[10px] uppercase tracking-wide text-neon">Pro</p>
          <p className="stat text-5xl text-neon">
            $9
            <span className="text-xl text-muted">/mo</span>
          </p>
          <p className="text-xs text-muted">billed monthly · cancel anytime</p>
          <ul className="space-y-1 text-sm text-secondary pt-3">
            <li>✓ Everything in Free</li>
            <li>✓ API rate limit 600 req/min (10×)</li>
            <li>✓ Early access to Phase 42 content engine</li>
            <li>✓ Priority email digest</li>
            <li>✓ CLV-per-match drilldown when enough data</li>
            <li>✓ Supporter badge on embed partners (optional)</li>
          </ul>
          <div className="flex gap-2 pt-2">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="flex-1 rounded border border-border bg-raised px-3 py-2 font-mono text-sm"
            />
            <button onClick={upgrade} disabled={busy} className="btn-primary text-xs">
              {busy
                ? tLang(lang, { en: "…", vi: "…", th: "…", zh: "…", ko: "…" })
                : tLang(lang, { en: "Upgrade", vi: "Nâng cấp", th: "อัปเกรด", zh: "升级", ko: "업그레이드" })}
            </button>
          </div>
          {err && <p className="text-error text-xs">{err}</p>}
        </div>
      </section>

      <section className="card space-y-2">
        <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
          {tLang(lang, { en: "Or just tip", vi: "Hoặc donate", th: "หรือทิป", zh: "或小费", ko: "또는 팁" })}
        </p>
        <p className="text-sm text-secondary">
          {tLang(lang, {
            en: "Not ready for recurring? One-off support keeps the VPS + API quotas running.",
            vi: "Chưa muốn subscribe? One-off donate giúp duy trì VPS + quota API.",
            th: "การบริจาคครั้งเดียวช่วยดูแล VPS",
            zh: "一次性支持帮助维持 VPS",
            ko: "일회성 후원은 VPS 유지에 도움",
          })}
        </p>
        <a
          href="https://ko-fi.com/predictor"
          target="_blank"
          rel="noopener"
          className="btn-ghost text-xs inline-block"
        >
          ☕ Buy me a coffee
        </a>
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• Already signed up? → <Link href="/billing" className="hover:text-neon">/billing</Link></p>
        <p>• Stripe handles payment — we never see your card.</p>
        <p>• Cancel anytime from /billing. Pro-free grandfather until 2027-01-01.</p>
      </section>
    </main>
  );
}
