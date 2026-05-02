import { Bell, CirclePause, Radio, Search, ShieldCheck } from "lucide-react";

export function Topbar() {
  return (
    <header className="flex min-h-16 items-center justify-between border-b border-white/10 bg-[#050610]/75 px-4 backdrop-blur-xl md:px-6">
      <div className="flex h-10 w-full max-w-md items-center gap-2 rounded border border-cyan/10 bg-black/30 px-3 text-sm text-muted">
        <Search size={16} />
        <span>Search symbol, signal, order, risk event</span>
      </div>
      <div className="ml-4 hidden items-center gap-3 font-mono text-[11px] text-secondary lg:flex">
        <span className="flex items-center gap-1 text-profit"><Radio size={14} /> API HEALTHY</span>
        <span>BTCUSDT 62,418.50 <b className="font-normal text-profit">+1.24%</b></span>
        <span>ETHUSDT 3,114.20 <b className="font-normal text-loss">-0.42%</b></span>
        <span>SOLUSDT 142.80 <b className="font-normal text-profit">+0.18%</b></span>
      </div>
      <div className="ml-4 flex items-center gap-2">
        <button className="grid h-10 w-10 place-items-center rounded border border-cyan/10 bg-black/20 text-secondary hover:text-primary" aria-label="Alerts">
          <Bell size={17} />
        </button>
        <button className="hidden h-10 items-center gap-2 rounded border border-profit/30 bg-profit/10 px-3 text-sm text-profit sm:flex">
          <ShieldCheck size={16} />
          VETO READY
        </button>
        <button className="flex h-10 items-center gap-2 rounded border border-warning/30 bg-warning/10 px-3 text-sm text-warning">
          <CirclePause size={16} />
          PAUSED
        </button>
      </div>
    </header>
  );
}
