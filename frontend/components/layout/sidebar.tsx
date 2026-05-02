import {
  Activity,
  BarChart3,
  Bot,
  ClipboardList,
  Gauge,
  LayoutDashboard,
  LineChart,
  Settings,
  ScrollText,
  Shield,
  Terminal
} from "lucide-react";
import Link from "next/link";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/terminal", label: "Terminal", icon: Terminal },
  { href: "/strategies", label: "Strategies", icon: LineChart },
  { href: "/backtest", label: "Backtest", icon: BarChart3 },
  { href: "/risk", label: "Risk", icon: Shield },
  { href: "/ai-analyst", label: "AI Analyst", icon: Bot },
  { href: "/journal", label: "Journal", icon: ClipboardList },
  { href: "/execution-quality", label: "Execution", icon: Gauge },
  { href: "/logs", label: "Logs", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings }
];

export function Sidebar() {
  return (
    <aside className="hidden w-72 shrink-0 border-r border-white/10/80 bg-[#050610]/70 px-4 py-4 backdrop-blur-xl md:block">
      <div className="mb-5 border-b border-white/10 pb-4">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded border border-accent/30 bg-accent/10 text-accent shadow-[0_0_24px_rgba(0,245,200,0.18)]">
            <Activity size={20} />
          </div>
          <div>
            <div className="font-mono text-sm font-semibold tracking-[0.18em] text-primary">AIQ // QUANTUM</div>
            <div className="font-mono text-[11px] uppercase text-secondary">Bybit Operator Terminal</div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2 font-mono text-[10px] uppercase text-muted">
          <div className="rounded border border-cyan/20 bg-cyan/10 px-2 py-2">
            MODE
            <div className="mt-1 text-warning">PAPER</div>
          </div>
          <div className="rounded border border-profit/20 bg-profit/10 px-2 py-2">
            RISK
            <div className="mt-1 text-profit">ARMED</div>
          </div>
        </div>
      </div>
      <nav className="space-y-1 border-b border-white/10 pb-4">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex h-10 items-center gap-3 rounded border border-transparent px-3 text-sm text-secondary transition hover:border-cyan/20 hover:bg-cyan/10 hover:text-primary"
          >
            <item.icon size={17} />
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="mt-4 space-y-2 font-mono text-[11px] text-muted">
        <div className="flex justify-between">
          <span>WS</span>
          <span className="text-warning">BOOTSTRAP</span>
        </div>
        <div className="flex justify-between">
          <span>LATENCY</span>
          <span className="text-secondary">-- ms</span>
        </div>
        <div className="flex justify-between">
          <span>BUILD</span>
          <span className="text-secondary">v2.1-Q</span>
        </div>
      </div>
    </aside>
  );
}
