// Minimal SVG radial-arc gauge. 0..2 domain centered at 1 (league avg).
// Neon when better-than-avg, red when worse. Renders SSR-clean.

export default function RadialGauge({
  value,
  label,
  higherIsBetter = true,
  size = 140,
}: {
  value: number;
  label: string;
  higherIsBetter?: boolean;
  size?: number;
}) {
  // Map 0..2 → 0..1 progress. Treat >2 as 1, <0 as 0.
  const progress = Math.max(0, Math.min(1, value / 2));
  const good = higherIsBetter ? value > 1.05 : value < 0.95;
  const bad = higherIsBetter ? value < 0.95 : value > 1.05;
  const color = good ? "#E0FF32" : bad ? "#FF4D4F" : "#A1A1A1";

  // Arc geometry: 3/4 circle, starting from -225° to +45° (bottom-left to bottom-right).
  const r = size / 2 - 10;
  const cx = size / 2;
  const cy = size / 2;
  const start = -225 * (Math.PI / 180);
  const sweep = 270 * (Math.PI / 180);
  const tx = (a: number) => cx + r * Math.cos(a);
  const ty = (a: number) => cy + r * Math.sin(a);

  const end = start + sweep * progress;
  const largeArc = sweep * progress > Math.PI ? 1 : 0;

  const bgPath = [
    `M ${tx(start)} ${ty(start)}`,
    `A ${r} ${r} 0 1 1 ${tx(start + sweep)} ${ty(start + sweep)}`,
  ].join(" ");
  const fgPath = progress > 0 ? [
    `M ${tx(start)} ${ty(start)}`,
    `A ${r} ${r} 0 ${largeArc} 1 ${tx(end)} ${ty(end)}`,
  ].join(" ") : "";

  return (
    <div className="flex flex-col items-center gap-1">
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
        <path d={bgPath} stroke="#242424" strokeWidth="6" fill="none" strokeLinecap="round" />
        {fgPath && (
          <path d={fgPath} stroke={color} strokeWidth="6" fill="none" strokeLinecap="round" />
        )}
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="middle"
          className="font-mono"
          fill={color}
          fontSize={size / 5}
          fontWeight="700"
        >
          {value.toFixed(2)}
        </text>
        <text
          x="50%"
          y={size * 0.72}
          textAnchor="middle"
          dominantBaseline="middle"
          className="font-mono"
          fill="#707070"
          fontSize={size / 12}
          letterSpacing="1"
        >
          vs avg (1.00)
        </text>
      </svg>
      <p className="label">{label}</p>
    </div>
  );
}
