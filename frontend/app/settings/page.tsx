"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { isSoundOn, setSoundOn, playGoalChime } from "@/lib/sound";
import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

export default function SettingsPage() {
  const lang = useLang();
  const [sound, setSound] = useState(false);

  useEffect(() => setSound(isSoundOn()), []);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12 space-y-8">
      <Link href="/" className="btn-ghost text-sm">
        {tLang(lang, { en: "← Back", vi: "← Quay lại", th: "← กลับ", zh: "← 返回", ko: "← 뒤로" })}
      </Link>
      <header className="space-y-2">
        <p className="font-mono text-xs text-muted">preferences · localStorage only</p>
        <h1 className="headline-section">
          {tLang(lang, { en: "Settings", vi: "Cài đặt", th: "ตั้งค่า", zh: "设置", ko: "설정" })}
        </h1>
      </header>

      <section className="card space-y-3">
        <label className="flex items-center justify-between gap-4">
          <div>
            <p className="label">
              {tLang(lang, { en: "Sound on goal", vi: "Âm thanh khi có bàn", th: "เสียงเมื่อมีประตู", zh: "进球声音", ko: "골 사운드" })}
            </p>
            <p className="text-xs text-muted">
              {tLang(lang, {
                en: "Short beep + vibration when a team you're subscribed to scores.",
                vi: "Tiếng beep ngắn + rung khi đội bạn theo dõi ghi bàn.",
                th: "เสียงบี๊บสั้น + สั่น",
                zh: "短促提示音 + 震动",
                ko: "짧은 비프음 + 진동",
              })}
            </p>
          </div>
          <input
            type="checkbox"
            checked={sound}
            onChange={(e) => {
              setSound(e.target.checked);
              setSoundOn(e.target.checked);
            }}
            className="h-5 w-5"
          />
        </label>
        <button
          type="button"
          onClick={playGoalChime}
          disabled={!sound}
          className="btn-ghost text-xs"
        >
          {tLang(lang, { en: "Test", vi: "Thử", th: "ทดสอบ", zh: "测试", ko: "테스트" })}
        </button>
      </section>

      <section className="card space-y-3">
        <p className="label">
          {tLang(lang, { en: "Your data lives in your browser", vi: "Data của bạn ở trong trình duyệt", th: "ข้อมูลของคุณอยู่ในเบราว์เซอร์", zh: "您的数据在浏览器", ko: "데이터는 브라우저에" })}
        </p>
        <p className="text-sm text-secondary">
          {tLang(lang, {
            en: "Favorites, betslip, my-picks. No account needed. Sync across devices with /sync (6-digit PIN).",
            vi: "Favorites, betslip, my-picks. Không cần tài khoản. Sync bằng PIN 6 số qua /sync.",
            th: "ไม่ต้องมีบัญชี",
            zh: "无需账户",
            ko: "계정 불필요",
          })}
        </p>
        <div className="flex gap-2">
          <Link href="/sync" className="btn-primary text-xs">{tLang(lang, { en: "Open sync", vi: "Mở sync", th: "เปิด sync", zh: "打开同步", ko: "동기화 열기" })}</Link>
          <button
            type="button"
            onClick={() => {
              if (confirm("Clear all local data (favorites, betslip, my-picks, prefs)?")) {
                Object.keys(localStorage).filter((k) => k.startsWith("epl-lab:")).forEach((k) => localStorage.removeItem(k));
                window.location.href = "/";
              }
            }}
            className="btn-ghost text-xs text-error"
          >
            {tLang(lang, { en: "Reset all", vi: "Xoá tất cả", th: "ล้างทั้งหมด", zh: "全部重置", ko: "전체 초기화" })}
          </button>
        </div>
      </section>
    </main>
  );
}
