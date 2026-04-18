export default function TerminalBlock({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="card space-y-2">
      <h2 className="font-display font-semibold uppercase tracking-tight">{title}</h2>
      <div className="font-mono text-sm leading-relaxed text-secondary whitespace-pre-wrap">
        {children}
      </div>
    </section>
  );
}
