"use client";

import { useEffect, useState } from "react";

import { useLang } from "@/lib/i18n-client";
import { tLang } from "@/lib/i18n-fallback";

// beforeinstallprompt isn't typed in lib.dom — cast via this shape.
type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

const DISMISS_KEY = "epl-lab:install-dismissed";

export default function InstallPrompt() {
  const lang = useLang();
  const [evt, setEvt] = useState<BeforeInstallPromptEvent | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.localStorage.getItem(DISMISS_KEY)) {
      setDismissed(true);
      return;
    }
    // Already installed? Hide.
    if (window.matchMedia?.("(display-mode: standalone)")?.matches) {
      return;
    }
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setEvt(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt as EventListener);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt as EventListener);
  }, []);

  async function install() {
    if (!evt) return;
    await evt.prompt();
    const choice = await evt.userChoice;
    if (choice.outcome === "dismissed") {
      window.localStorage.setItem(DISMISS_KEY, "1");
    }
    setEvt(null);
  }

  function dismiss() {
    window.localStorage.setItem(DISMISS_KEY, "1");
    setDismissed(true);
  }

  if (!evt || dismissed) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-xs rounded-lg border border-neon/50 bg-surface p-4 shadow-lg space-y-3">
      <p className="font-mono text-[10px] uppercase tracking-wide text-neon">
        {tLang(lang, {
          en: "Install to home screen",
          vi: "Cài đặt vào home screen",
          th: "ติดตั้งที่หน้าหลัก",
          zh: "添加到主屏幕",
          ko: "홈 화면에 설치",
        })}
      </p>
      <p className="text-sm text-secondary">
        {tLang(lang, {
          en: "Faster load, goal pings on subscribed teams, no app store.",
          vi: "Load nhanh hơn, nhận goal push trên team đã subscribe, không cần store.",
          th: "โหลดเร็ว, รับแจ้งเตือนประตู",
          zh: "加载更快,支持进球通知",
          ko: "빠른 로딩, 구독 팀 골 알림",
        })}
      </p>
      <div className="flex gap-2">
        <button onClick={install} className="btn-primary text-xs flex-1">
          {tLang(lang, { en: "Install", vi: "Cài đặt", th: "ติดตั้ง", zh: "安装", ko: "설치" })}
        </button>
        <button onClick={dismiss} className="btn-ghost text-xs">
          {tLang(lang, { en: "Later", vi: "Sau", th: "ภายหลัง", zh: "稍后", ko: "나중에" })}
        </button>
      </div>
    </div>
  );
}
