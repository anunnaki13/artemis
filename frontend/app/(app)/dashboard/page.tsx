"use client";

import { useEffect, useState } from "react";
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Activity, 
  Clock, 
  Zap,
  Target,
  Shield,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Play,
  Pause,
  RefreshCw,
  Wallet,
  PieChart,
  LineChart
} from "lucide-react";

// API functions
async function fetchPnL() {
  try {
    const res = await fetch('/api/dashboard/pnl');
    if (!res.ok) throw new Error('Failed to fetch PnL');
    return await res.json();
  } catch (error) {
    console.error('Error fetching PnL:', error);
    return null;
  }
}

async function fetchBalance() {
  try {
    const res = await fetch('/api/dashboard/balance');
    if (!res.ok) throw new Error('Failed to fetch balance');
    return await res.json();
  } catch (error) {
    console.error('Error fetching balance:', error);
    return null;
  }
}

async function fetchPositions() {
  try {
    const res = await fetch('/api/dashboard/positions');
    if (!res.ok) throw new Error('Failed to fetch positions');
    return await res.json();
  } catch (error) {
    console.error('Error fetching positions:', error);
    return [];
  }
}

async function fetchRecentTrades(limit = 5) {
  try {
    const res = await fetch(`/api/dashboard/recent-trades?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch trades');
    return await res.json();
  } catch (error) {
    console.error('Error fetching trades:', error);
    return [];
  }
}

async function fetchBotStatus() {
  try {
    const res = await fetch('/api/dashboard/bot-status');
    if (!res.ok) throw new Error('Failed to fetch bot status');
    return await res.json();
  } catch (error) {
    console.error('Error fetching bot status:', error);
    return null;
  }
}

function KPICard({ 
  title, 
  value, 
  prefix = "", 
  suffix = "", 
  icon: Icon, 
  trend,
  trendValue,
  color = "purple"
}: any) {
  const isPositive = trend === "up";
  const isNegative = trend === "down";
  
  return (
    <div className="kpi-neu">
      <div className="flex items-start justify-between">
        <div>
          <p className="kpi-label">{title}</p>
          <div className={`kpi-value ${isPositive ? 'profit-display' : isNegative ? 'loss-display' : ''}`}>
            {prefix}{value}{suffix}
          </div>
          {trend && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${isPositive ? 'text-[var(--profit)]' : isNegative ? 'text-[var(--loss)]' : 'text-[var(--fg-secondary)]'}`}>
              {isPositive ? <ArrowUpRight size={16} /> : isNegative ? <ArrowDownRight size={16} /> : null}
              <span>{trendValue}</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-xl ${color === 'purple' ? 'bg-[var(--accent-primary)]/20 text-[var(--accent-primary)]' : color === 'green' ? 'bg-[var(--profit)]/20 text-[var(--profit)]' : color === 'red' ? 'bg-[var(--loss)]/20 text-[var(--loss)]' : 'bg-[var(--accent-secondary)]/20 text-[var(--accent-secondary)]'}`}>
          <Icon size={24} />
        </div>
      </div>
    </div>
  );
}

function PositionCard({ position }: { position: any }) {
  const isProfit = position.pnl >= 0;
  
  return (
    <div className="neu-card p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${position.side === 'LONG' ? 'bg-[var(--profit)]/20' : 'bg-[var(--loss)]/20'}`}>
            {position.side === 'LONG' ? <TrendingUp size={20} className="text-[var(--profit)]" /> : <TrendingDown size={20} className="text-[var(--loss)]" />}
          </div>
          <div>
            <h3 className="font-bold text-lg">{position.symbol}</h3>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${position.side === 'LONG' ? 'status-badge active' : 'status-badge inactive'}`}>
              {position.side}
            </span>
          </div>
        </div>
        <div className={`text-right ${isProfit ? 'profit-display' : 'loss-display'}`}>
          <div className="text-xl font-bold">
            {isProfit ? '+' : ''}${Math.abs(position.pnl).toFixed(2)}
          </div>
          <div className="text-sm opacity-80">
            {isProfit ? '+' : ''}{position.pnlPercent.toFixed(2)}%
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-2 mt-4 pt-4 border-t border-[var(--fg-muted)]/20">
        <div>
          <p className="text-xs text-[var(--fg-secondary)] mb-1">Size</p>
          <p className="font-mono font-semibold">{position.size}</p>
        </div>
        <div>
          <p className="text-xs text-[var(--fg-secondary)] mb-1">Entry</p>
          <p className="font-mono font-semibold">${position.entryPrice.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-[var(--fg-secondary)] mb-1">Current</p>
          <p className="font-mono font-semibold">${position.currentPrice.toLocaleString()}</p>
        </div>
      </div>
    </div>
  );
}

function TradeRow({ trade }: { trade: any }) {
  const isProfit = trade.pnl >= 0;
  
  return (
    <tr className="neu-card">
      <td>
        <div className="flex items-center gap-2">
          <span className="font-bold">{trade.symbol}</span>
          <span className={`text-xs px-2 py-0.5 rounded ${trade.side === 'LONG' ? 'status-badge active' : 'status-badge inactive'}`}>
            {trade.side}
          </span>
        </div>
      </td>
      <td className={`font-bold ${isProfit ? 'profit-display' : 'loss-display'}`}>
        {isProfit ? '+' : ''}${Math.abs(trade.pnl).toFixed(2)}
      </td>
      <td className="text-[var(--fg-secondary)] font-mono text-sm">{trade.timestamp}</td>
    </tr>
  );
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [pnlData, setPnLData] = useState<any>(null);
  const [balanceData, setBalanceData] = useState<any>(null);
  const [positions, setPositions] = useState<any[]>([]);
  const [recentTrades, setRecentTrades] = useState<any[]>([]);
  const [botStatus, setBotStatus] = useState<any>(null);
  const [isBotRunning, setIsBotRunning] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const refreshData = async () => {
    setLastUpdate(new Date());
    
    const [pnl, balance, pos, trades, bot] = await Promise.all([
      fetchPnL(),
      fetchBalance(),
      fetchPositions(),
      fetchRecentTrades(5),
      fetchBotStatus()
    ]);
    
    if (pnl) setPnLData(pnl);
    if (balance) setBalanceData(balance);
    if (pos) setPositions(pos);
    if (trades) setRecentTrades(trades);
    if (bot) setBotStatus(bot);
    
    setLoading(false);
  };

  useEffect(() => {
    refreshData();
    
    // Auto-refresh setiap 5 detik
    const interval = setInterval(refreshData, 5000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="neu-card p-8">
          <RefreshCw size={48} className="animate-spin text-[var(--accent-primary)] mx-auto mb-4" />
          <p className="text-center text-[var(--fg-secondary)]">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  const totalPnL = pnlData?.totalPnL || 0;
  const todayPnL = pnlData?.todayPnL || 0;
  const balance = balanceData?.balance || 0;
  const equity = balanceData?.equity || 0;

  return (
    <div className="min-h-screen p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold gradient-text mb-2">AIQ Trading Bot</h1>
            <p className="text-[var(--fg-secondary)]">Autonomous Trading System - Bybit</p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="neu-card-flat px-4 py-2 flex items-center gap-3">
              <div className={`pulse-dot ${botStatus?.isActive ? 'green' : 'red'}`} />
              <span className="font-semibold text-sm">
                {botStatus?.isActive ? 'BOT ACTIVE' : 'BOT STOPPED'}
              </span>
            </div>
            
            <button 
              onClick={() => setIsBotRunning(!isBotRunning)}
              className={`neu-btn ${isBotRunning ? 'neu-btn-danger' : 'neu-btn-success'}`}
            >
              {isBotRunning ? <Pause size={20} /> : <Play size={20} />}
              {isBotRunning ? 'Stop Bot' : 'Start Bot'}
            </button>
            
            <button onClick={refreshData} className="neu-btn">
              <RefreshCw size={20} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Main PnL Display - SUPER VISIBLE */}
      <div className="mb-8">
        <div className="neu-card p-8 glow-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[var(--fg-secondary)] text-lg mb-2">Total Profit & Loss</p>
              <div className={`text-6xl font-black ${totalPnL >= 0 ? 'profit-display' : 'loss-display'}`}>
                {totalPnL >= 0 ? '+' : ''}{formatCurrency(totalPnL)}
              </div>
              <div className={`flex items-center gap-2 mt-3 text-xl ${todayPnL >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'}`}>
                {todayPnL >= 0 ? <TrendingUp size={24} /> : <TrendingDown size={24} />}
                <span className="font-bold">Today: {todayPnL >= 0 ? '+' : ''}{formatCurrency(todayPnL)}</span>
              </div>
            </div>
            <div className="text-right">
              <div className="neu-card-flat p-4 mb-3">
                <p className="text-[var(--fg-secondary)] text-sm mb-1">Balance</p>
                <p className="text-2xl font-bold font-mono">{formatCurrency(balance)}</p>
              </div>
              <div className="neu-card-flat p-4">
                <p className="text-[var(--fg-secondary)] text-sm mb-1">Equity</p>
                <p className="text-2xl font-bold font-mono">{formatCurrency(equity)}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <KPICard
          title="Win Rate"
          value={(pnlData?.winRate || 0).toFixed(1)}
          suffix="%"
          icon={Target}
          trend="up"
          trendValue={`${pnlData?.winningTrades || 0}W / ${pnlData?.losingTrades || 0}L`}
          color="green"
        />
        <KPICard
          title="Total Trades"
          value={pnlData?.totalTrades || 0}
          icon={Activity}
          trend="up"
          trendValue="Last 24h"
          color="purple"
        />
        <KPICard
          title="Profit Factor"
          value={(pnlData?.profitFactor || 0).toFixed(2)}
          icon={BarChart3}
          trend={pnlData?.profitFactor >= 2 ? "up" : "down"}
          trendValue={pnlData?.profitFactor >= 2 ? "Excellent" : "Good"}
          color="purple"
        />
        <KPICard
          title="Open Positions"
          value={positions.length}
          icon={PieChart}
          color="purple"
        />
      </div>

      {/* Additional Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="neu-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Wallet className="text-[var(--accent-primary)]" size={24} />
            <h3 className="font-bold text-lg">Performance Metrics</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-[var(--fg-secondary)]">Avg Win</span>
              <span className="profit-display font-bold">+${(pnlData?.avgWin || 0).toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--fg-secondary)]">Avg Loss</span>
              <span className="loss-display font-bold">-${Math.abs(pnlData?.avgLoss || 0).toFixed(2)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--fg-secondary)]">Win/Loss Ratio</span>
              <span className="font-bold text-[var(--accent-primary)]">
                {pnlData?.losingTrades > 0 
                  ? ((pnlData?.winningTrades || 0) / pnlData?.losingTrades).toFixed(2) 
                  : '∞'}
              </span>
            </div>
          </div>
        </div>

        <div className="neu-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Zap className="text-[var(--warning)]" size={24} />
            <h3 className="font-bold text-lg">Bot Status</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-[var(--fg-secondary)]">Strategy</span>
              <span className="font-semibold">{botStatus?.strategy || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--fg-secondary)]">Last Signal</span>
              <span className="font-mono text-sm">{botStatus?.lastSignal || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--fg-secondary)]">Uptime</span>
              <span className="status-badge active">{botStatus?.uptime || 'N/A'}</span>
            </div>
          </div>
        </div>

        <div className="neu-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Clock className="text-[var(--info)]" size={24} />
            <h3 className="font-bold text-lg">Session Info</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-[var(--fg-secondary)]">Market</span>
              <span className="font-semibold">Bybit Futures</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--fg-secondary)]">Last Update</span>
              <span className="font-mono text-sm">{lastUpdate.toLocaleTimeString()}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[var(--fg-secondary)]">Auto-Refresh</span>
              <span className="status-badge active">Every 5s</span>
            </div>
          </div>
        </div>
      </div>

      {/* Open Positions & Recent Trades */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Open Positions */}
        <div className="neu-card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <PieChart className="text-[var(--accent-primary)]" size={24} />
              <h3 className="font-bold text-xl">Open Positions ({positions.length})</h3>
            </div>
          </div>
          
          {positions.length > 0 ? (
            <div className="space-y-4">
              {positions.map((pos: any, idx: number) => (
                <PositionCard key={idx} position={pos} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-[var(--fg-secondary)]">
              <LineChart size={48} className="mx-auto mb-4 opacity-50" />
              <p>No open positions</p>
            </div>
          )}
        </div>

        {/* Recent Trades */}
        <div className="neu-card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <DollarSign className="text-[var(--profit)]" size={24} />
              <h3 className="font-bold text-xl">Recent Trades</h3>
            </div>
            <button className="neu-btn text-sm py-2 px-4">
              View All
            </button>
          </div>
          
          {recentTrades.length > 0 ? (
            <table className="neu-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>P&L</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {recentTrades.map((trade: any) => (
                  <TradeRow key={trade.id} trade={trade} />
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-12 text-[var(--fg-secondary)]">
              <Activity size={48} className="mx-auto mb-4 opacity-50" />
              <p>No recent trades</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
