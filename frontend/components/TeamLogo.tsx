import { logoFor } from "@/lib/team-logos";

export default function TeamLogo({
  slug,
  name,
  size = 24,
  className = "",
}: {
  slug: string;
  name: string;
  size?: number;
  className?: string;
}) {
  const src = logoFor(slug);
  if (!src) {
    return (
      <span
        aria-label={name}
        className={`inline-flex items-center justify-center rounded-full bg-high font-mono text-[10px] uppercase text-muted ${className}`}
        style={{ width: size, height: size }}
      >
        {name.slice(0, 2)}
      </span>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={name}
      width={size}
      height={size}
      loading="lazy"
      className={`inline-block shrink-0 ${className}`}
      style={{ width: size, height: size }}
    />
  );
}
