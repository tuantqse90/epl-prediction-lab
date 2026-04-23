"use client";

import Link from "next/link";
import { useState } from "react";

import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

export default function SubscribePage() {
  const lang = useLang();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "ok" | "err">("idle");
  const [err, setErr] = useState<string>("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setStatus("sending");
    setErr("");
    try {
      const res = await fetch("/api/email/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, lang }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setStatus("ok");
    } catch (e) {
      setStatus("err");
      setErr(String(e));
    }
  }

  const back = tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" });

  if (status === "ok") {
    return (
      <main className="mx-auto max-w-xl px-6 py-16 space-y-6">
        <Link href="/" className="btn-ghost text-sm">{back}</Link>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Check your inbox",
            vi: "Kiểm tra hộp thư",
            th: "เช็คอีเมลของคุณ",
            zh: "查看您的邮箱",
            ko: "이메일을 확인하세요",
          })}
        </h1>
        <p className="text-secondary">
          {tLang(lang, {
            en: `We sent a confirmation link to ${email}. Click it to start receiving the Monday digest.`,
            vi: `Đã gửi link xác nhận tới ${email}. Bấm link để bắt đầu nhận digest thứ 2 hàng tuần.`,
            th: `ส่งลิงก์ยืนยันไปที่ ${email} แล้ว คลิกเพื่อเริ่มรับสรุปประจำวันจันทร์`,
            zh: `已发送确认链接到 ${email}。点击链接开始接收每周一摘要。`,
            ko: `${email}로 확인 링크를 보냈습니다. 클릭하시면 월요일 요약을 받기 시작합니다.`,
          })}
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-xl px-6 py-16 space-y-6">
      <Link href="/" className="btn-ghost text-sm">{back}</Link>
      <header className="space-y-2">
        <p className="font-mono text-xs text-muted">
          {tLang(lang, {
            en: "Weekly digest · Monday 09:00 UTC",
            vi: "Digest hàng tuần · Thứ 2 09:00 UTC",
            th: "สรุปประจำสัปดาห์ · จันทร์ 09:00 UTC",
            zh: "每周摘要 · 周一 09:00 UTC",
            ko: "주간 요약 · 월요일 09:00 UTC",
          })}
        </p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Get the model's top edges by email",
            vi: "Nhận top edges của model qua email",
            th: "รับเอดจ์ท็อปของโมเดลทางอีเมล",
            zh: "通过邮件获取模型顶级 edge",
            ko: "이메일로 모델 상위 엣지 받기",
          })}
        </h1>
        <p className="text-secondary">
          {tLang(lang, {
            en: "One short email every Monday. Top fixtures by model edge + last week's accuracy + P&L. No spam, unsubscribe in one click.",
            vi: "1 email ngắn mỗi thứ 2. Top trận có edge + accuracy tuần trước + P&L. Không spam, bỏ đăng ký 1 click.",
            th: "อีเมลสั้นๆ ทุกจันทร์ แมตช์ท็อปตามเอดจ์ + ความแม่นสัปดาห์ก่อน + P&L",
            zh: "每周一简讯。模型 edge 最大的比赛 + 上周准确率 + P&L。一键取消。",
            ko: "매주 월요일 짧은 이메일. 최고 엣지 경기 + 지난주 정확도 + 손익",
          })}
        </p>
      </header>

      <form onSubmit={submit} className="card space-y-3">
        <label className="label" htmlFor="email">
          {tLang(lang, { en: "Email", vi: "Email", th: "อีเมล", zh: "邮箱", ko: "이메일" })}
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded border border-border bg-raised px-3 py-2 font-mono text-sm"
          placeholder="you@example.com"
        />
        <button
          type="submit"
          disabled={status === "sending"}
          className="btn-primary w-full"
        >
          {status === "sending"
            ? tLang(lang, { en: "Sending…", vi: "Đang gửi…", th: "กำลังส่ง…", zh: "发送中…", ko: "전송 중…" })
            : tLang(lang, { en: "Subscribe", vi: "Đăng ký", th: "สมัคร", zh: "订阅", ko: "구독" })}
        </button>
        {status === "err" && (
          <p className="text-error text-sm">
            {tLang(lang, { en: "Something went wrong:", vi: "Có lỗi:", th: "เกิดข้อผิดพลาด:", zh: "出错:", ko: "오류:" })}
            {" "}{err}
          </p>
        )}
      </form>

      <p className="font-mono text-[11px] uppercase tracking-wide text-muted">
        {tLang(lang, {
          en: "By subscribing you agree this is entertainment-grade forecasting, not financial advice.",
          vi: "Đăng ký nghĩa là bạn đồng ý đây là dự báo giải trí, không phải lời khuyên tài chính.",
          th: "การสมัครหมายถึงคุณยอมรับว่านี่คือการพยากรณ์เพื่อความบันเทิง ไม่ใช่คำแนะนำทางการเงิน",
          zh: "订阅即表示您同意这是娱乐性质的预测,而非财务建议。",
          ko: "구독은 이것이 엔터테인먼트 목적의 예측이며 재정 조언이 아님에 동의하는 것입니다.",
        })}
      </p>
    </main>
  );
}
