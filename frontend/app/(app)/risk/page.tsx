"use client";

import { useEffect, useState } from "react";

import {
  type CapitalProfileResponse,
  type RiskPolicyResponse,
  type SignalRiskEvaluateResponse,
  type StrategyEvaluationResponse,
  evaluateOrderbookImbalance,
  evaluateSignalRisk,
  getCapitalProfile,
  getRiskPolicy,
} from "@/lib/api";

function formatNumber(value: string | number | null | undefined, digits = 2) {
  if (value === null || value === undefined) return "--";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "--";
  return parsed.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="market-panel rounded">
      <div className="flex h-10 items-center border-b border-white/10 px-3">
        <h2 className="font-mono text-[11px] uppercase text-secondary">{title}</h2>
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}

export default function RiskPage() {
  const [policy, setPolicy] = useState<RiskPolicyResponse | null>(null);
  const [profile, setProfile] = useState<CapitalProfileResponse | null>(null);
  const [signalEval, setSignalEval] = useState<StrategyEvaluationResponse | null>(null);
  const [riskEval, setRiskEval] = useState<SignalRiskEvaluateResponse | null>(null);

  useEffect(() => {
    let active = true;
    void Promise.allSettled([
      getRiskPolicy(),
      getCapitalProfile("1000"),
      evaluateOrderbookImbalance({ symbol: "BTCUSDT", lookback: 20 }),
    ]).then(async ([policyResult, profileResult, signalResult]) => {
      if (!active) return;
      if (policyResult.status === "fulfilled") setPolicy(policyResult.value);
      if (profileResult.status === "fulfilled") setProfile(profileResult.value);
      if (signalResult.status === "fulfilled") {
        setSignalEval(signalResult.value);
        if (signalResult.value.signal) {
          const signal = signalResult.value.signal;
          const risk = await evaluateSignalRisk({
            signal,
            current_equity: "1000",
            entry_price: signal.metadata?.entry_price ? String(signal.metadata.entry_price) : "100",
            proposed_notional: "100",
            daily_pnl_pct: "0",
            leverage: "1",
            quote_volume_usd: "5000000",
            use_futures: false,
          }).catch(() => null);
          if (active) setRiskEval(risk);
        }
      }
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-3">
      <div className="market-panel rounded px-4 py-3">
        <div className="font-mono text-[11px] uppercase text-muted">Risk Command Center</div>
        <h1 className="mt-1 text-2xl font-semibold">Policy, Profile, and Gate Review</h1>
        <p className="mt-1 text-sm text-secondary">
          This page now reads the live policy, active capital profile, and a real signal risk decision from the backend.
        </p>
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <Panel title="Hard Limits">
          {policy ? (
            <div className="space-y-2 font-mono text-xs">
              <Metric label="Risk / trade" value={`${formatNumber(policy.risk_per_trade * 100, 2)}%`} />
              <Metric label="Max daily loss" value={`${formatNumber(policy.max_daily_loss * 100, 2)}%`} />
              <Metric label="Max position %" value={`${formatNumber(policy.hard_limits.max_position_pct * 100, 2)}%`} />
              <Metric label="Max total exposure %" value={`${formatNumber(policy.hard_limits.max_total_exposure_pct * 100, 2)}%`} />
              <Metric label="Max leverage" value={`${formatNumber(policy.hard_limits.max_leverage, 2)}x`} />
              <Metric label="Absolute daily loss" value={`${formatNumber(policy.hard_limits.absolute_max_daily_loss * 100, 2)}%`} />
            </div>
          ) : (
            <div className="text-sm text-muted">Policy unavailable.</div>
          )}
        </Panel>

        <Panel title="Active Capital Profile">
          {profile ? (
            <div className="space-y-2 font-mono text-xs">
              <Metric label="Profile" value={profile.active_profile.name} />
              <Metric label="Equity window" value={`${formatNumber(profile.active_profile.equity_min, 0)} - ${profile.active_profile.equity_max ?? "inf"}`} />
              <Metric label="Max concurrent" value={String(profile.active_profile.max_concurrent_positions)} />
              <Metric label="Risk / trade" value={`${formatNumber(profile.active_profile.risk_per_trade_pct, 4)}%`} />
              <Metric label="Min target R" value={formatNumber(profile.active_profile.min_trade_target_r, 2)} />
              <Metric label="Volume floor" value={formatNumber(profile.active_profile.avoid_pairs_below_volume, 0)} />
              <Metric label="Use futures" value={String(profile.active_profile.use_futures)} />
            </div>
          ) : (
            <div className="text-sm text-muted">Capital profile unavailable.</div>
          )}
        </Panel>

        <Panel title="Live Risk Gate">
          {signalEval?.signal && riskEval ? (
            <div className="space-y-2 font-mono text-xs">
              <Metric label="Signal" value={`${signalEval.signal.side.toUpperCase()} ${signalEval.signal.symbol}`} />
              <Metric label="Allowed" value={riskEval.allowed ? "YES" : "NO"} />
              <Metric label="Profile" value={riskEval.profile_name} />
              <Metric label="Recommended max notional" value={formatNumber(riskEval.recommended_max_notional, 2)} />
              <Metric label="Recommended risk amount" value={formatNumber(riskEval.recommended_risk_amount, 2)} />
              <Metric label="Open positions" value={String(riskEval.evaluated_open_positions)} />
              <Metric label="Current exposure" value={formatNumber(riskEval.evaluated_total_exposure_notional, 2)} />
              <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
                {riskEval.reasons.length > 0 ? riskEval.reasons.join("; ") : "No gate objections"}
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted">No signal has passed through the risk gate yet.</div>
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
