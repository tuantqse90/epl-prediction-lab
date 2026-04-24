"use client";

import { useEffect, useState } from "react";

const KEY = "epl-lab:theme";

export default function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const stored = typeof window !== "undefined" ? window.localStorage.getItem(KEY) : null;
    const t = (stored === "light" ? "light" : "dark") as "dark" | "light";
    setTheme(t);
    document.documentElement.dataset.theme = t;
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    window.localStorage.setItem(KEY, next);
    document.documentElement.dataset.theme = next;
  }

  return (
    <button
      type="button"
      onClick={toggle}
      className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-border text-xs hover:border-neon hover:text-neon transition-colors"
      aria-label="Toggle theme"
      title={theme === "dark" ? "Switch to light" : "Switch to dark"}
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
