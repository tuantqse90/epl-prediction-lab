"use client";

import Link from "next/link";
import { useState } from "react";

import { pullFromPin, pushToPin } from "@/lib/sync";
import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

function randomPin(): string {
  return Math.floor(Math.random() * 1_000_000).toString().padStart(6, "0");
}

export default function SyncPage() {
  const lang = useLang();
  const [pin, setPin] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function doPush() {
    if (!/^\d{6}$/.test(pin)) { setStatus("PIN must be 6 digits"); return; }
    setBusy(true); setStatus(null);
    const res = await pushToPin(pin, Date.now());
    setBusy(false);
    setStatus(
      res.ok
        ? tLang(lang, {
            en: `Saved to PIN ${pin}. Type this PIN on another device to pull it in.`,
            vi: `Đã lưu vào PIN ${pin}. Nhập PIN này trên thiết bị khác để kéo về.`,
            th: `บันทึกไปยัง PIN ${pin}`,
            zh: `已保存到 PIN ${pin}`,
            ko: `PIN ${pin}에 저장됨`,
          })
        : `Failed: ${res.error ?? "?"}`,
    );
  }

  async function doPull() {
    if (!/^\d{6}$/.test(pin)) { setStatus("PIN must be 6 digits"); return; }
    setBusy(true); setStatus(null);
    const res = await pullFromPin(pin);
    setBusy(false);
    setStatus(
      res.ok
        ? tLang(lang, {
            en: `Imported ${res.applied} state groups from PIN ${pin}. Refresh pages to see.`,
            vi: `Đã nhập ${res.applied} nhóm trạng thái từ PIN ${pin}. F5 để xem.`,
            th: `นำเข้า ${res.applied} กลุ่ม`,
            zh: `已导入 ${res.applied} 组状态`,
            ko: `${res.applied}개 상태 그룹 가져옴`,
          })
        : `Failed: ${res.error ?? "?"}`,
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>

      <header className="space-y-3">
        <p className="font-mono text-xs text-muted">
          {tLang(lang, {
            en: "Cross-device sync · no login required",
            vi: "Sync thiết bị · không login",
            th: "ซิงค์ข้ามอุปกรณ์",
            zh: "跨设备同步",
            ko: "기기 간 동기화",
          })}
        </p>
        <h1 className="headline-section">
          {tLang(lang, {
            en: "Carry your watchlist + picks with a 6-digit PIN",
            vi: "Mang watchlist + picks qua thiết bị khác bằng PIN 6 số",
            th: "ใช้ PIN 6 หลักพกรายการของคุณข้ามเครื่อง",
            zh: "用 6 位 PIN 跨设备带上你的关注 + 选择",
            ko: "6자리 PIN으로 관심목록과 픽을 기기 간 이동",
          })}
        </h1>
        <p className="max-w-2xl text-secondary">
          {tLang(lang, {
            en: "Pick a 6-digit PIN on this device, tap Save. On another device, type the same PIN and tap Load. Your favorites, betslip, and my-picks come over. No email, no password, no account.",
            vi: "Chọn 1 PIN 6 số trên máy này, bấm Save. Trên máy khác, nhập cùng PIN, bấm Load. Favorites, betslip, my-picks sẽ qua. Không email, không password, không tài khoản.",
            th: "เลือก PIN 6 หลักบนเครื่องนี้แล้ว Save บนอีกเครื่องพิมพ์ PIN เดียวกัน Load",
            zh: "在此设备选择 6 位 PIN 保存;在另一设备输入相同 PIN 加载",
            ko: "이 기기에서 6자리 PIN 선택 후 저장; 다른 기기에서 같은 PIN 입력 후 불러오기",
          })}
        </p>
      </header>

      <section className="card space-y-4">
        <label className="space-y-1 block">
          <span className="label">PIN</span>
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              pattern="\d{6}"
              maxLength={6}
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
              className="flex-1 rounded border border-border bg-raised px-3 py-2 font-mono text-2xl tabular-nums tracking-widest"
              placeholder="123456"
            />
            <button type="button" onClick={() => setPin(randomPin())} className="btn-ghost text-xs">
              {tLang(lang, { en: "Random", vi: "Ngẫu nhiên", th: "สุ่ม", zh: "随机", ko: "랜덤" })}
            </button>
          </div>
        </label>

        <div className="flex gap-2">
          <button onClick={doPush} disabled={busy || pin.length !== 6} className="btn-primary text-sm flex-1">
            {tLang(lang, {
              en: "⬆ Save to PIN",
              vi: "⬆ Lưu theo PIN",
              th: "⬆ บันทึก",
              zh: "⬆ 保存",
              ko: "⬆ 저장",
            })}
          </button>
          <button onClick={doPull} disabled={busy || pin.length !== 6} className="btn-ghost text-sm flex-1">
            {tLang(lang, {
              en: "⬇ Load from PIN",
              vi: "⬇ Kéo theo PIN",
              th: "⬇ โหลด",
              zh: "⬇ 加载",
              ko: "⬇ 불러오기",
            })}
          </button>
        </div>

        {status && (
          <p className="font-mono text-sm text-secondary">{status}</p>
        )}
      </section>

      <section className="font-mono text-[11px] uppercase tracking-wide text-muted space-y-1">
        <p>• PIN is hashed server-side (SHA-256) — we never see the raw digits.</p>
        <p>• 30 requests/minute per IP. Brute-forcing 10⁶ PINs is slow.</p>
        <p>• Payload = favorites + betslip + my-picks. Nothing else is synced.</p>
      </section>
    </main>
  );
}
