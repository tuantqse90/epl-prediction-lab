"use client";

import { useEffect, useState } from "react";

type Props = {
  value: number;
  decimals?: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
};

// Ease-out cubic so the count decelerates — feels like the number
// "lands" on its final value instead of slamming through it.
function easeOutCubic(t: number): number {
  return 1 - (1 - t) ** 3;
}

export default function AnimatedNumber({
  value,
  decimals = 0,
  duration = 900,
  prefix = "",
  suffix = "",
  className,
}: Props) {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const from = 0;
    const to = value;
    const tick = (now: number) => {
      const elapsed = now - start;
      const t = Math.min(1, elapsed / duration);
      setCurrent(from + (to - from) * easeOutCubic(t));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);

  const shown = decimals > 0 ? current.toFixed(decimals) : Math.round(current).toString();
  return (
    <span className={className} suppressHydrationWarning>
      {prefix}
      {shown}
      {suffix}
    </span>
  );
}
