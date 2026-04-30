const ladder = [
  ["ASK", "62,424.2", "12.80", "799K"],
  ["ASK", "62,423.4", "8.40", "524K"],
  ["ASK", "62,421.9", "21.15", "1.31M"],
  ["BID", "62,417.6", "17.20", "1.07M"],
  ["BID", "62,416.1", "14.03", "875K"],
  ["BID", "62,414.8", "19.64", "1.22M"]
];

const trades = [
  ["16:04:21", "BUY", "62,418.5", "0.084"],
  ["16:04:19", "SELL", "62,417.9", "0.122"],
  ["16:04:18", "BUY", "62,418.1", "0.031"],
  ["16:04:16", "BUY", "62,419.0", "0.205"],
  ["16:04:14", "SELL", "62,416.8", "0.044"]
];

function Box({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`market-panel rounded ${className}`}>
      <div className="flex h-10 items-center justify-between border-b border-white/10 px-3">
        <h2 className="font-mono text-[11px] uppercase text-secondary">{title}</h2>
        <span className="font-mono text-[10px] uppercase text-muted">paper locked</span>
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}

export default function TerminalPage() {
  return (
    <div className="grid gap-3 xl:grid-cols-[1fr_340px]">
      <div className="space-y-3">
        <div className="market-panel rounded px-4 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="font-mono text-[11px] text-muted">BTCUSDT PERP / PAPER TERMINAL</div>
              <div className="mt-1 font-mono text-3xl font-semibold text-primary">62,418.50 <span className="text-base text-profit">+1.24%</span></div>
            </div>
            <div className="grid grid-cols-3 gap-2 font-mono text-[11px] text-secondary">
              <span className="rounded border border-white/10 bg-black/25 px-3 py-2">VOL 1.42B</span>
              <span className="rounded border border-white/10 bg-black/25 px-3 py-2">FUND 0.010%</span>
              <span className="rounded border border-warning/30 bg-warning/10 px-3 py-2 text-warning">EXEC PAUSED</span>
            </div>
          </div>
        </div>

        <Box title="Price Action">
          <div className="relative h-[520px] overflow-hidden rounded border border-white/10 bg-black/40">
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1000 520" preserveAspectRatio="none">
              {Array.from({ length: 11 }).map((_, index) => (
                <line key={`h-${index}`} x1="0" x2="1000" y1={index * 52} y2={index * 52} stroke="rgba(255,255,255,.055)" />
              ))}
              {Array.from({ length: 16 }).map((_, index) => (
                <line key={`v-${index}`} y1="0" y2="520" x1={index * 66} x2={index * 66} stroke="rgba(255,255,255,.04)" />
              ))}
              <path
                d="M0 410 L60 390 L120 422 L180 350 L240 372 L300 286 L360 304 L420 250 L480 275 L540 210 L600 235 L660 188 L720 206 L780 142 L840 168 L900 120 L1000 94"
                fill="none"
                stroke="#22f5a5"
                strokeWidth="3"
              />
              <path d="M0 348 L1000 348" stroke="#ff4d5e" strokeDasharray="10 10" strokeOpacity=".65" />
              <path d="M0 182 L1000 182" stroke="#49c6ff" strokeDasharray="6 8" strokeOpacity=".55" />
            </svg>
            <div className="absolute right-3 top-3 rounded border border-profit/30 bg-black/70 px-3 py-2 font-mono text-xs text-profit">
              SIGNAL WATCH / NO LIVE ORDER
            </div>
          </div>
        </Box>
      </div>

      <div className="space-y-3">
        <Box title="Depth Ladder">
          <div className="space-y-1 font-mono text-xs">
            {ladder.map(([side, price, qty, notional]) => (
              <div key={`${side}-${price}`} className={`grid grid-cols-4 rounded px-2 py-2 ${side === "ASK" ? "bg-loss/10 text-loss" : "bg-profit/10 text-profit"}`}>
                <span>{side}</span>
                <span className="text-right">{price}</span>
                <span className="text-right">{qty}</span>
                <span className="text-right">{notional}</span>
              </div>
            ))}
          </div>
        </Box>

        <Box title="Recent Prints">
          <div className="space-y-1 font-mono text-xs">
            {trades.map(([time, side, price, size]) => (
              <div key={`${time}-${price}-${size}`} className="grid grid-cols-4 border-b border-white/10 py-2 last:border-0">
                <span className="text-muted">{time}</span>
                <span className={side === "BUY" ? "text-profit" : "text-loss"}>{side}</span>
                <span className="text-right text-secondary">{price}</span>
                <span className="text-right text-muted">{size}</span>
              </div>
            ))}
          </div>
        </Box>

        <Box title="Guarded Actions">
          <div className="space-y-2">
            <button className="h-11 w-full rounded border border-warning/40 bg-warning/10 font-mono text-xs text-warning">PAUSE ALL</button>
            <button className="h-11 w-full rounded border border-loss/40 bg-loss/10 font-mono text-xs text-loss">FLATTEN REQUIRES CONFIRMATION</button>
            <button className="h-11 w-full rounded border border-white/10 bg-black/30 font-mono text-xs text-secondary">ORDER ENTRY DISABLED IN PHASE 0</button>
          </div>
        </Box>
      </div>
    </div>
  );
}
