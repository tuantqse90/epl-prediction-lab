import type { Config } from "tailwindcss";

// Payy design tokens — see docs/frontend.md for the full spec.
// One accent (`neon`) per viewport. Black text on any neon fill.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#000000",
        raised: "#161616",
        high: "#242424",
        max: "#363636",
        neon: "#E0FF32",
        "neon-dim": "#B8CC28",
        "on-neon": "#000000",
        charcoal: "#161616",
        primary: "#FFFFFF",
        secondary: "#D9D9D9",
        muted: "#778899",
        success: "#E0FF32",
        warning: "#FFB020",
        error: "#FF4D4F",
        danger: "#E8212D",
        border: "#242424",
        "border-muted": "#161616",
      },
      fontFamily: {
        display: ["Geist", "Inter", "system-ui", "sans-serif"],
        body: ["Geist", "Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.02em",
        tighter: "-0.01em",
      },
    },
  },
  plugins: [],
};

export default config;
