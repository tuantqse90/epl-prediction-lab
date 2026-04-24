// Toggleable goal-alert sound. Web-native Audio() kept off by default;
// user opts in via /settings. Cheap 440Hz → 660Hz beep generated with
// the Web Audio API so we don't ship an MP3.

const KEY = "epl-lab:sound-on-goal";

export function isSoundOn(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(KEY) === "1";
}

export function setSoundOn(on: boolean): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, on ? "1" : "0");
}

export function playGoalChime(): void {
  if (!isSoundOn()) return;
  if (typeof window === "undefined") return;
  try {
    const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const tone = (hz: number, at: number, dur: number) => {
      const osc = ctx.createOscillator();
      const g = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = hz;
      g.gain.value = 0.15;
      osc.connect(g);
      g.connect(ctx.destination);
      osc.start(ctx.currentTime + at);
      osc.stop(ctx.currentTime + at + dur);
    };
    tone(440, 0, 0.15);
    tone(660, 0.15, 0.20);
    // Haptic on mobile if available.
    if ("vibrate" in navigator) navigator.vibrate?.([60, 30, 120]);
  } catch {
    // AudioContext can be blocked on first load until user interacts —
    // silently drop.
  }
}
