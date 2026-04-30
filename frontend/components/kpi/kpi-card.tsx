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
    <section className="market-panel rounded p-3">
      <div className="font-mono text-[10px] uppercase tracking-normal text-muted">{label}</div>
      <div className={`mt-2 font-mono text-xl font-semibold ${toneClass[tone]}`}>{value}</div>
    </section>
  );
}
