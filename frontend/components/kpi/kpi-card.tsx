type KpiCardProps = {
  label: string;
  value: string;
  tone?: "neutral" | "profit" | "loss" | "warning";
};

const toneClass = {
  neutral: "text-primary",
  profit: "text-profit",
  loss: "text-loss",
  warning: "text-warning"
};

export function KpiCard({ label, value, tone = "neutral" }: KpiCardProps) {
  return (
    <section className="market-panel rounded px-3 py-3">
      <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">{label}</div>
      <div className={`numeric mt-2 text-xl font-semibold ${toneClass[tone]}`}>{value}</div>
    </section>
  );
}
