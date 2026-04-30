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
    <aside className="hidden w-64 shrink-0 border-r border-white/10 bg-[#070a0d] px-3 py-4 md:block">
      <div className="mb-5 border-b border-white/10 pb-4">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded border border-accent/30 bg-accent/10 text-accent">
            <Activity size={20} />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-normal">AIQ-BOT</div>
            <div className="font-mono text-[11px] text-secondary">SURVIVAL TERMINAL</div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2 font-mono text-[10px] uppercase text-muted">
          <div className="rounded border border-white/10 bg-white/[0.03] px-2 py-2">
            MODE
            <div className="mt-1 text-warning">PAPER</div>
          </div>
          <div className="rounded border border-white/10 bg-white/[0.03] px-2 py-2">
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
            className="flex h-9 items-center gap-3 rounded border border-transparent px-3 text-sm text-secondary transition hover:border-white/10 hover:bg-white/[0.04] hover:text-primary"
          >
            <item.icon size={17} />
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="mt-4 space-y-2 font-mono text-[11px] text-muted">
        <div className="flex justify-between">
          <span>WS</span>
          <span className="text-warning">STANDBY</span>
        </div>
        <div className="flex justify-between">
          <span>LATENCY</span>
          <span className="text-secondary">-- ms</span>
        </div>
        <div className="flex justify-between">
          <span>BUILD</span>
          <span className="text-secondary">v2.0-P0</span>
        </div>
      </div>
    </aside>
  );
}
