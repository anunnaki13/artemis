export default function BacktestPage() {
  return <PageShell title="Backtest Center" description="Walk-forward, Monte Carlo, sensitivity, and cost shocks." />;
}

function PageShell({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="mt-1 text-sm text-secondary">{description}</p>
      <section className="mt-6 rounded border border-white/10 bg-elevated p-4 text-sm text-muted">
        Phase 0 placeholder
      </section>
    </div>
  );
}

