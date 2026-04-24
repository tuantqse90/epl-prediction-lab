"use client";

import Link from "next/link";
import { useState } from "react";

import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

type Status = {
  tier: "free" | "pro" | "pro-free";
  subscription_status: string | null;
  current_period_end: string | null;
  api_key_prefix: string | null;
  grandfather_until: string | null;
};

export default function BillingPage() {
  const lang = useLang();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    if (!email.trim()) { setErr("Enter an email"); return; }
    setBusy(true); setErr("");
    try {
      const res = await fetch(`/api/billing/status?email=${encodeURIComponent(email)}`);
      if (res.status === 404) {
        setStatus(null);
        setErr("No account on this email yet. Subscribe at /pricing first.");
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setStatus(await res.json());
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (!confirm("Cancel your Pro subscription at period end?")) return;
    setBusy(true); setErr("");
    try {
      const res = await fetch("/api/billing/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await load();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">billing · your subscription</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Your subscription",
            vi: "Gói của bạn",
            th: "การสมัครสมาชิกของคุณ",
            zh: "您的订阅",
            ko: "구독 정보",
          })}
        </h1>
      </header>

      <section className="card space-y-3">
        <p className="font-mono text-[10px] uppercase tracking-wide text-muted">
          {tLang(lang, { en: "Look up by email", vi: "Tra cứu theo email", th: "ค้นหาด้วยอีเมล", zh: "按邮箱查询", ko: "이메일로 조회" })}
        </p>
        <div className="flex gap-2">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="flex-1 rounded border border-border bg-raised px-3 py-2 font-mono text-sm"
          />
          <button onClick={load} disabled={busy} className="btn-primary text-xs">
            {busy ? "…" : tLang(lang, { en: "Load", vi: "Tải", th: "โหลด", zh: "加载", ko: "불러오기" })}
          </button>
        </div>
        {err && <p className="text-error text-xs">{err}</p>}
      </section>

      {status && (
        <section className="card space-y-4">
          <div className="flex items-baseline justify-between">
            <p className="font-mono text-[10px] uppercase tracking-wide text-muted">Tier</p>
            <p className={`stat text-3xl ${status.tier !== "free" ? "text-neon" : ""}`}>
              {status.tier}
            </p>
          </div>

          {status.subscription_status && (
            <div className="flex items-baseline justify-between border-t border-border pt-3">
              <p className="font-mono text-[10px] uppercase tracking-wide text-muted">Status</p>
              <p className="text-sm">{status.subscription_status}</p>
            </div>
          )}

          {status.current_period_end && (
            <div className="flex items-baseline justify-between border-t border-border pt-3">
              <p className="font-mono text-[10px] uppercase tracking-wide text-muted">Renews</p>
              <p className="text-sm font-mono tabular-nums">{status.current_period_end.slice(0, 10)}</p>
            </div>
          )}

          {status.api_key_prefix && (
            <div className="flex items-baseline justify-between border-t border-border pt-3">
              <p className="font-mono text-[10px] uppercase tracking-wide text-muted">API key</p>
              <p className="text-sm font-mono">{status.api_key_prefix}…</p>
            </div>
          )}

          {status.grandfather_until && (
            <p className="text-xs text-muted border-t border-border pt-3">
              {tLang(lang, {
                en: `Grandfathered as pro-free until ${status.grandfather_until.slice(0, 10)}.`,
                vi: `Được giữ pro-free đến ${status.grandfather_until.slice(0, 10)}.`,
                th: `Pro-free ถึง ${status.grandfather_until.slice(0, 10)}`,
                zh: `pro-free 至 ${status.grandfather_until.slice(0, 10)}`,
                ko: `${status.grandfather_until.slice(0, 10)}까지 pro-free`,
              })}
            </p>
          )}

          {status.tier === "pro" && status.subscription_status === "active" && (
            <button onClick={cancel} disabled={busy} className="btn-ghost text-xs border-error text-error">
              {tLang(lang, { en: "Cancel at period end", vi: "Huỷ cuối kỳ", th: "ยกเลิกปลายรอบ", zh: "期末取消", ko: "기간 만료 시 취소" })}
            </button>
          )}
        </section>
      )}

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• Want to upgrade? → <Link href="/pricing" className="hover:text-neon">/pricing</Link></p>
        <p>• Stripe handles payment · we never see your card.</p>
        <p>• All predictions are free forever regardless of tier.</p>
      </section>
    </main>
  );
}
