import Link from "next/link";

import { getLang } from "@/lib/i18n-server";
import { tLang } from "@/lib/i18n-fallback";

export const metadata = {
  title: "Embed — partner widget · predictor.nullshift.sh",
  description: "Paste one snippet to show a Prediction Lab match card on your site.",
};

export default async function EmbedDocsPage() {
  const lang = await getLang();
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-2">
        <p className="font-mono text-xs text-muted">Developer docs · embed widget</p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Embed a prediction card on your site",
            vi: "Nhúng card dự đoán vào site của bạn",
            th: "ฝังการ์ดพยากรณ์บนเว็บของคุณ",
            zh: "在您的网站嵌入预测卡片",
            ko: "귀하의 사이트에 예측 카드 임베드",
          })}
        </h1>
        <p className="text-secondary">
          {tLang(lang, {
            en: "Two steps, no auth, no key. The widget renders as an iframe; your page stays fully sandboxed.",
            vi: "2 bước, không auth, không cần key. Widget chạy trong iframe; trang bạn vẫn sandbox hoàn toàn.",
            th: "2 ขั้นตอน ไม่ต้อง auth ไม่ต้องใช้ key",
            zh: "两步,无需认证,无需 API key。",
            ko: "2단계, 인증/키 불필요.",
          })}
        </p>
      </header>

      <section className="card space-y-4">
        <p className="font-mono text-xs uppercase tracking-wide text-muted">
          {tLang(lang, { en: "Step 1 · Paste the container", vi: "Bước 1 · Dán div chứa", th: "ขั้น 1", zh: "步骤 1", ko: "1단계" })}
        </p>
        <pre className="bg-raised p-3 rounded overflow-x-auto text-sm font-mono">
{`<div data-predlab-match="4321" data-predlab-lang="en"></div>`}
        </pre>
        <p className="text-sm text-secondary">
          {tLang(lang, {
            en: "data-predlab-match is the match id from any predictor.nullshift.sh/match/:id URL. data-predlab-lang accepts en, vi, th, zh, ko.",
            vi: "data-predlab-match là match id lấy từ URL predictor.nullshift.sh/match/:id. data-predlab-lang nhận en, vi, th, zh, ko.",
            th: "data-predlab-match คือ id ของแมตช์ จาก URL /match/:id",
            zh: "data-predlab-match 是来自 /match/:id 的比赛 id",
            ko: "data-predlab-match는 /match/:id URL의 경기 id",
          })}
        </p>
      </section>

      <section className="card space-y-4">
        <p className="font-mono text-xs uppercase tracking-wide text-muted">
          {tLang(lang, { en: "Step 2 · Add the loader", vi: "Bước 2 · Thêm loader", th: "ขั้น 2", zh: "步骤 2", ko: "2단계" })}
        </p>
        <pre className="bg-raised p-3 rounded overflow-x-auto text-sm font-mono">
{`<script async src="https://predictor.nullshift.sh/embed.js"></script>`}
        </pre>
        <p className="text-sm text-secondary">
          {tLang(lang, {
            en: "~1.5 KB gzipped. Auto-mounts every matching div on page load. Height auto-adjusts via postMessage.",
            vi: "~1.5 KB gzip. Tự mount mọi div khớp khi page load. Chiều cao tự chỉnh qua postMessage.",
            th: "~1.5 KB gzip ขนาดอัตโนมัติผ่าน postMessage",
            zh: "~1.5 KB gzip。页面加载时自动挂载所有匹配的 div。",
            ko: "~1.5 KB gzip. 페이지 로드 시 자동 마운트.",
          })}
        </p>
      </section>

      <section className="card space-y-3">
        <p className="font-mono text-xs uppercase tracking-wide text-muted">
          {tLang(lang, { en: "Live preview", vi: "Xem thử", th: "ดูตัวอย่าง", zh: "实时预览", ko: "미리 보기" })}
        </p>
        <iframe
          src="/embed/match/4321"
          className="w-full max-w-md border-0 rounded-lg"
          style={{ minHeight: 260 }}
          title="Prediction Lab embed preview"
        />
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• iframe + sandbox — CSS-isolated, no leakage into your site.</p>
        <p>• Cached 60s at the edge. Live probabilities surface within a minute of ingest.</p>
        <p>• If match id doesn't exist the iframe shows a 404 card.</p>
        <p>• Free. If you use it in a commercial product, please credit predictor.nullshift.sh.</p>
      </section>
    </main>
  );
}
