import { AlertTriangle, Crosshair, LockKeyhole, Pause, RadioTower, Shield } from "lucide-react";

import { KpiCard } from "@/components/kpi/kpi-card";

const markets = [
  ["BTCUSDT", "62,418.50", "+1.24%", "1.42B", "profit"],
  ["ETHUSDT", "3,114.20", "-0.42%", "824M", "loss"],
  ["SOLUSDT", "142.78", "+2.08%", "312M", "profit"],
  ["BNBUSDT", "581.80", "+0.18%", "211M", "profit"],
  ["XRPUSDT", "0.5821", "-0.91%", "189M", "loss"],
  ["DOGEUSDT", "0.1324", "+0.66%", "144M", "profit"]
];

const orderbook = [
  ["62,421.8", "18.42", "1.15M", "ask"],
  ["62,420.6", "11.03", "688K", "ask"],
  ["62,419.4", "7.92", "494K", "ask"],
  ["62,418.5", "MID", "0.8 bps", "mid"],
  ["62,417.9", "15.11", "943K", "bid"],
  ["62,416.2", "21.48", "1.34M", "bid"],
  ["62,415.0", "9.05", "565K", "bid"]
];

const signals = [
  ["VWAP_REV", "ETHUSDT", "REJECTED", "choppy regime"],
  ["EMA_MOM", "BTCUSDT", "QUEUED", "paper only"],
  ["RSI_BOUNCE", "SOLUSDT", "WATCH", "conviction 0.61"],
  ["BREAK_VOL", "BNBUSDT", "COOLDOWN", "spread wide"]
];

const positions = [
  ["No live position", "PAPER", "0.00", "0.00", "0.00"],
  ["BTCUSDT model slot", "SIM", "0.00", "0.00", "0.00"],
  ["ETHUSDT model slot", "SIM", "0.00", "0.00", "0.00"]
];

const riskRows = [
  { label: "Daily loss budget", status: "CLEAR", tone: "text-profit", Icon: Shield },
  { label: "Weekly drawdown", status: "CLEAR", tone: "text-profit", Icon: Shield },
  { label: "Correlation exposure", status: "IDLE", tone: "text-secondary", Icon: Crosshair },
  { label: "API health breaker", status: "STANDBY", tone: "text-warning", Icon: RadioTower },
  { label: "Hard limits", status: "IMMUTABLE", tone: "text-cyan", Icon: LockKeyhole },
  { label: "Execution", status: "PAUSED", tone: "text-warning", Icon: Pause }
];

function Panel({
  title,
  action,
  children,
  className = ""
}: {
  title: string;
  action?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`market-panel scanline rounded ${className}`}>
      <div className="flex h-10 items-center justify-between border-b border-white/10 px-3">
        <h2 className="font-mono text-[11px] uppercase text-secondary">{title}</h2>
        {action ? <span className="font-mono text-[10px] uppercase text-muted">{action}</span> : null}
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-3">
      <div className="grid gap-3 xl:grid-cols-[1fr_360px]">
        <div className="market-panel rounded px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="font-mono text-[11px] uppercase text-muted">Command Deck / PAPER MODE</div>
              <h1 className="mt-1 text-2xl font-semibold tracking-normal">Institutional Risk Terminal</h1>
            </div>
            <div className="flex flex-wrap gap-2 font-mono text-[11px]">
              <span className="rounded border border-profit/30 bg-profit/10 px-2 py-1 text-profit">RISK VETO ONLINE</span>
              <span className="rounded border border-warning/30 bg-warning/10 px-2 py-1 text-warning">EXECUTION PAUSED</span>
              <span className="rounded border border-cyan/30 bg-cyan/10 px-2 py-1 text-cyan">NET PNL ONLY</span>
            </div>
          </div>
        </div>
        <div className="market-panel rounded px-4 py-3">
          <div className="grid grid-cols-3 gap-3 font-mono text-[11px]">
            <div>
              <div className="text-muted">UTC</div>
              <div className="mt-1 text-primary">16:04:00</div>
            </div>
            <div>
              <div className="text-muted">LATENCY</div>
              <div className="mt-1 text-profit">-- ms</div>
            </div>
            <div>
              <div className="text-muted">MODE</div>
              <div className="mt-1 text-warning">PAPER</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <KpiCard label="Total Equity" value="0.00 USDT" />
        <KpiCard label="Daily Net PnL" value="0.00" />
        <KpiCard label="Weekly Net PnL" value="0.00" />
        <KpiCard label="Exposure" value="0.0%" />
        <KpiCard label="Max DD" value="0.0%" />
        <KpiCard label="Sharpe 30D" value="--" />
      </div>

      <div className="grid gap-3 xl:grid-cols-[1.15fr_0.85fr_360px]">
        <Panel title="Equity / Drawdown Stream" action="live paper feed pending" className="min-h-[356px]">
          <div className="relative h-[292px] overflow-hidden rounded border border-white/10 bg-black/35">
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 900 280" preserveAspectRatio="none">
              <defs>
                <linearGradient id="equityGlow" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#22f5a5" stopOpacity="0.28" />
                  <stop offset="100%" stopColor="#22f5a5" stopOpacity="0" />
                </linearGradient>
              </defs>
              {Array.from({ length: 8 }).map((_, index) => (
                <line key={`h-${index}`} x1="0" x2="900" y1={35 + index * 32} y2={35 + index * 32} stroke="rgba(255,255,255,.06)" />
              ))}
              {Array.from({ length: 12 }).map((_, index) => (
                <line key={`v-${index}`} y1="0" y2="280" x1={index * 82} x2={index * 82} stroke="rgba(255,255,255,.045)" />
              ))}
              <path
                d="M0 220 L80 210 L160 226 L240 190 L320 196 L400 150 L480 164 L560 118 L640 130 L720 92 L800 104 L900 72 L900 280 L0 280 Z"
                fill="url(#equityGlow)"
              />
              <path
                d="M0 220 L80 210 L160 226 L240 190 L320 196 L400 150 L480 164 L560 118 L640 130 L720 92 L800 104 L900 72"
                fill="none"
                stroke="#22f5a5"
                strokeWidth="3"
              />
              <path d="M0 232 L900 232" stroke="#ff4d5e" strokeDasharray="8 8" strokeOpacity="0.7" />
            </svg>
            <div className="absolute left-3 top-3 rounded border border-white/10 bg-black/70 px-3 py-2 font-mono text-[11px]">
              <div className="text-muted">EXPECTED VS LIVE</div>
              <div className="mt-1 text-profit">BACKTEST CURVE PLACEHOLDER</div>
            </div>
          </div>
        </Panel>

        <Panel title="Market Tape" action="top symbols">
          <div className="overflow-hidden rounded border border-white/10">
            <table className="w-full font-mono text-xs">
              <thead className="bg-white/[0.04] text-muted">
                <tr>
                  <th className="px-2 py-2 text-left font-normal">SYMBOL</th>
                  <th className="px-2 py-2 text-right font-normal">LAST</th>
                  <th className="px-2 py-2 text-right font-normal">24H</th>
                  <th className="px-2 py-2 text-right font-normal">VOL</th>
                </tr>
              </thead>
              <tbody>
                {markets.map(([symbol, last, change, volume, tone]) => (
                  <tr key={symbol} className="border-t border-white/10">
                    <td className="px-2 py-2 text-primary">{symbol}</td>
                    <td className="px-2 py-2 text-right text-secondary">{last}</td>
                    <td className={`px-2 py-2 text-right ${tone === "profit" ? "text-profit" : "text-loss"}`}>{change}</td>
                    <td className="px-2 py-2 text-right text-muted">{volume}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Risk Stack" action="all gates visible">
          <div className="space-y-2 font-mono text-xs">
            {riskRows.map(({ label, status, tone, Icon }) => (
              <div key={label} className="flex items-center justify-between rounded border border-white/10 bg-black/25 px-3 py-2">
                <span className="flex items-center gap-2 text-secondary">
                  <Icon size={14} />
                  {label}
                </span>
                <span className={tone}>{status}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-3 xl:grid-cols-[0.75fr_1fr_0.85fr]">
        <Panel title="BTCUSDT Order Book" action="simulated display">
          <div className="space-y-1 font-mono text-xs">
            {orderbook.map(([price, size, notional, side]) => (
              <div
                key={`${price}-${side}`}
                className={`grid grid-cols-3 rounded px-2 py-1.5 ${
                  side === "ask" ? "bg-loss/10 text-loss" : side === "bid" ? "bg-profit/10 text-profit" : "bg-white/[0.06] text-cyan"
                }`}
              >
                <span>{price}</span>
                <span className="text-right">{size}</span>
                <span className="text-right">{notional}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Open Positions" action="binance truth source pending">
          <div className="overflow-hidden rounded border border-white/10">
            <table className="w-full font-mono text-xs">
              <thead className="bg-white/[0.04] text-muted">
                <tr>
                  <th className="px-2 py-2 text-left font-normal">POSITION</th>
                  <th className="px-2 py-2 text-left font-normal">MODE</th>
                  <th className="px-2 py-2 text-right font-normal">QTY</th>
                  <th className="px-2 py-2 text-right font-normal">ENTRY</th>
                  <th className="px-2 py-2 text-right font-normal">NET PNL</th>
                </tr>
              </thead>
              <tbody>
                {positions.map(([name, mode, qty, entry, pnl]) => (
                  <tr key={name} className="border-t border-white/10">
                    <td className="px-2 py-2 text-primary">{name}</td>
                    <td className="px-2 py-2 text-warning">{mode}</td>
                    <td className="px-2 py-2 text-right text-secondary">{qty}</td>
                    <td className="px-2 py-2 text-right text-secondary">{entry}</td>
                    <td className="px-2 py-2 text-right text-profit">{pnl}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel title="Signal Feed" action="risk veto audit">
          <div className="space-y-2 font-mono text-xs">
            {signals.map(([strategy, symbol, state, reason]) => (
              <div key={`${strategy}-${symbol}`} className="rounded border border-white/10 bg-black/25 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-primary">{strategy}</span>
                  <span className={state === "REJECTED" ? "text-loss" : state === "QUEUED" ? "text-warning" : "text-cyan"}>{state}</span>
                </div>
                <div className="mt-1 flex items-center justify-between text-[11px] text-muted">
                  <span>{symbol}</span>
                  <span>{reason}</span>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel title="Critical Audit Stream" action="append-only">
        <div className="grid gap-2 font-mono text-xs lg:grid-cols-4">
          <div className="rounded border border-warning/30 bg-warning/10 px-3 py-2 text-warning">
            <AlertTriangle size={14} className="mb-2" />
            Live execution disabled until promotion gates pass.
          </div>
          <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
            API keys must be trade-only and IP whitelisted before boot verification.
          </div>
          <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
            PnL surfaces are reserved for net values after fees, funding, and slippage.
          </div>
          <div className="rounded border border-white/10 bg-black/25 px-3 py-2 text-secondary">
            Phase 1 requires Binance public streams and 24h memory-leak validation.
          </div>
        </div>
      </Panel>
    </div>
  );
}
