"use client";

import { useEffect, useState } from "react";

import {
  type ExecutionIntentSubmitResponse,
  type SignalRiskEvaluateResponse,
  type StrategyEvaluationResponse,
  type UniverseRefreshResponse,
  evaluateOrderbookImbalance,
  evaluateSignalRisk,
  refreshUniverse,
  submitExecutionIntent,
} from "@/lib/api";

function formatNumber(value: string | number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "--";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "--";
  return parsed.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="market-panel scanline rounded-xl">
      <div className="flex h-10 items-center border-b border-white/10 px-3">
        <h2 className="font-mono text-[11px] uppercase text-secondary">{title}</h2>
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}

export default function StrategiesPage() {
  const [evaluation, setEvaluation] = useState<StrategyEvaluationResponse | null>(null);
  const [riskPreview, setRiskPreview] = useState<SignalRiskEvaluateResponse | null>(null);
  const [submitResult, setSubmitResult] = useState<ExecutionIntentSubmitResponse | null>(null);
  const [universe, setUniverse] = useState<UniverseRefreshResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void Promise.allSettled([evaluateOrderbookImbalance({ symbol: "BTCUSDT", lookback: 20 }), refreshUniverse()]).then(async ([evalResult, universeResult]) => {
      if (!active) return;
      if (evalResult.status === "fulfilled") {
        setEvaluation(evalResult.value);
        if (evalResult.value.signal) {
          const signal = evalResult.value.signal;
          const risk = await evaluateSignalRisk({
            signal,
            current_equity: "1000",
            entry_price: String(signal.metadata?.entry_price ?? 100),
            proposed_notional: "100",
            daily_pnl_pct: "0",
            leverage: "1",
            quote_volume_usd: "5000000",
            use_futures: false,
          }).catch(() => null);
          if (active) setRiskPreview(risk);
        }
      }
      if (universeResult.status === "fulfilled") setUniverse(universeResult.value);
      if (evalResult.status === "rejected" && universeResult.status === "rejected") {
        setError("strategy data load failed");
      }
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-3">
      <div className="quantum-hero rounded-2xl px-4 py-4">
        <div className="quantum-badge">Strategy Lab</div>
        <h1 className="mt-3 text-2xl font-semibold">Live Signal and Universe Review</h1>
        <p className="quantum-subtitle mt-2">
          This page now reads the active orderbook-imbalance strategy and the current Bybit universe filter instead of placeholder cards.
        </p>
        {error ? <div className="mt-3 text-sm text-loss">{error}</div> : null}
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Orderbook Imbalance Evaluation">
          {evaluation ? (
            <div className="space-y-3 font-mono text-xs">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                  <div className="text-muted">Signal</div>
                  <div className={`mt-1 ${evaluation.signal ? "text-profit" : "text-warning"}`}>
                    {evaluation.signal ? evaluation.signal.side.toUpperCase() : "NO TRADE"}
                  </div>
                </div>
                <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                  <div className="text-muted">Conviction</div>
                  <div className="mt-1 text-primary">{formatNumber(evaluation.signal?.conviction ?? null, 2)}</div>
                </div>
                <div className="rounded border border-white/10 bg-black/25 px-3 py-2">
                  <div className="text-muted">Sample</div>
                  <div className="mt-1 text-primary">{evaluation.diagnostics.sample_size}</div>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Metric label="Latest imbalance" value={formatNumber(evaluation.diagnostics.latest_imbalance_ratio, 4)} />
                <Metric label="Average imbalance" value={formatNumber(evaluation.diagnostics.average_imbalance_ratio, 4)} />
                <Metric label="Spread bps" value={formatNumber(evaluation.diagnostics.latest_spread_bps, 2)} />
                <Metric label="Bid depth" value={formatNumber(evaluation.diagnostics.bid_depth_notional_0p5pct, 2)} />
                <Metric label="Ask depth" value={formatNumber(evaluation.diagnostics.ask_depth_notional_0p5pct, 2)} />
                <Metric label="Persistence" value={formatNumber(evaluation.diagnostics.persistence_ratio_observed, 2)} />
              </div>
              <div className="rounded border border-white/10 bg-black/20 px-3 py-2 text-secondary">
                Latest snapshot: {evaluation.diagnostics.latest_timestamp ?? "--"}
              </div>
              <div className="rounded border border-cyan/20 bg-cyan/10 px-3 py-3">
                <div className="mb-2 font-mono text-[11px] uppercase text-cyan">Intent Preview Flow</div>
                <div className="grid gap-2 sm:grid-cols-3">
                  <Metric label="Risk allowed" value={riskPreview ? (riskPreview.allowed ? "YES" : "NO") : "--"} />
                  <Metric label="Max notional" value={formatNumber(riskPreview?.recommended_max_notional ?? null, 2)} />
                  <Metric label="Open positions" value={riskPreview ? String(riskPreview.evaluated_open_positions) : "--"} />
                </div>
                <button
                  type="button"
                  disabled={!evaluation.signal || !riskPreview?.allowed}
                  onClick={() => {
                    if (!evaluation.signal) return;
                    void submitExecutionIntent({
                      signal_risk: {
                        signal: evaluation.signal,
                        current_equity: "1000",
                        entry_price: String(evaluation.signal.metadata?.entry_price ?? 100),
                        proposed_notional: "100",
                        daily_pnl_pct: "0",
                        leverage: "1",
                        quote_volume_usd: "5000000",
                        use_futures: false,
                      },
                      notes: "submitted from strategy lab",
                    }).then(setSubmitResult).catch((submitError) => setError(submitError instanceof Error ? submitError.message : "intent submit failed"));
                  }}
                  className="mt-3 h-10 rounded border border-profit/30 bg-profit/10 px-3 font-mono text-[11px] text-profit disabled:opacity-50"
                >
                  CREATE EXECUTION INTENT
                </button>
                {submitResult?.intent ? (
                  <div className="mt-2 rounded border border-white/10 bg-black/20 px-3 py-2 text-secondary">
                    intent #{submitResult.intent.id} / {submitResult.intent.status} / {submitResult.intent.symbol}
                  </div>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted">No strategy evaluation returned yet.</div>
          )}
        </Panel>

        <Panel title="Universe Candidates">
          {universe ? (
            <div className="space-y-3 font-mono text-xs">
              <div className="grid gap-3 sm:grid-cols-3">
                <Metric label="Candidates" value={String(universe.candidate_count)} />
                <Metric label="Rejected" value={String(universe.rejected_count)} />
                <Metric label="Volume floor" value={formatNumber(universe.min_quote_volume_usd, 0)} />
              </div>
              <div className="overflow-hidden rounded border border-white/10">
                <table className="w-full text-xs">
                  <thead className="bg-white/[0.04] text-muted">
                    <tr>
                      <th className="px-2 py-2 text-left font-normal">Symbol</th>
                      <th className="px-2 py-2 text-right font-normal">24h Volume</th>
                      <th className="px-2 py-2 text-right font-normal">Change %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {universe.candidates.slice(0, 12).map((candidate) => (
                      <tr key={candidate.symbol} className="border-t border-white/10">
                        <td className="px-2 py-2 text-primary">{candidate.symbol}</td>
                        <td className="px-2 py-2 text-right text-secondary">{formatNumber(candidate.quote_volume, 0)}</td>
                        <td className={`px-2 py-2 text-right ${Number(candidate.price_change_pct) >= 0 ? "text-profit" : "text-loss"}`}>
                          {formatNumber(candidate.price_change_pct, 2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted">Universe manager has not returned candidates yet.</div>
          )}
        </Panel>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-white/10 bg-black/25 px-3 py-2 font-mono text-xs">
      <div className="text-muted">{label}</div>
      <div className="mt-1 text-primary">{value}</div>
    </div>
  );
}
