/** 5-match form indicator — tiny colored dots, newest first. */
export default function FormDots({ form, size = "sm" }: { form: string[]; size?: "sm" | "md" }) {
  if (!form || form.length === 0) return null;
  const cls = size === "md" ? "w-2.5 h-2.5" : "w-1.5 h-1.5";
  return (
    <span className="inline-flex items-center gap-[3px]" aria-label={`form ${form.join("")}`}>
      {form.map((r, i) => {
        const bg = r === "W" ? "bg-neon" : r === "D" ? "bg-muted" : "bg-error";
        return <span key={i} className={`${cls} rounded-full ${bg}`} />;
      })}
    </span>
  );
}
