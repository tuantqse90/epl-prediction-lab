// Fire-and-forget page-view pings. One per page load; re-uses a
// localStorage session_id so the server can tell unique sessions apart.

const SESSION_KEY = "epl-lab:session-id";

function sessionId(): string {
  if (typeof window === "undefined") return "";
  let s = window.localStorage.getItem(SESSION_KEY);
  if (!s) {
    s = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    window.localStorage.setItem(SESSION_KEY, s);
  }
  return s;
}

export function trackPageView(path: string): void {
  if (typeof window === "undefined") return;
  try {
    fetch("/api/analytics/pv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path,
        referrer: document.referrer || null,
        lang: document.documentElement.lang || "en",
        session_id: sessionId(),
      }),
      keepalive: true,
    }).catch(() => {});
  } catch {
    /* never throw from analytics */
  }
}
