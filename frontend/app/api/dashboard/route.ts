import { NextResponse } from 'next/server';

// Mock data for dashboard - In production, this would fetch from backend/Bybit API
let mockData = {
  totalPnL: 127.45,
  todayPnL: 23.80,
  balance: 1127.45,
  equity: 1142.30,
  winRate: 68.5,
  winningTrades: 12,
  losingTrades: 5,
  totalTrades: 17,
  profitFactor: 2.34,
  avgWin: 45.20,
  avgLoss: -18.50,
  positions: [
    {
      symbol: 'BTCUSDT',
      side: 'LONG',
      size: 0.025,
      entryPrice: 48500,
      currentPrice: 49200,
      pnl: 17.50,
      pnlPercent: 1.44
    }
  ],
  recentTrades: [
    { symbol: 'ETHUSDT', side: 'LONG', pnl: 32.50, timestamp: '2024-01-15 14:30' },
    { symbol: 'BTCUSDT', side: 'SHORT', pnl: -12.30, timestamp: '2024-01-15 12:15' },
    { symbol: 'SOLUSDT', side: 'LONG', pnl: 18.90, timestamp: '2024-01-15 10:45' },
    { symbol: 'BTCUSDT', side: 'LONG', pnl: 45.20, timestamp: '2024-01-15 08:20' },
    { symbol: 'ETHUSDT', side: 'SHORT', pnl: 28.70, timestamp: '2024-01-15 06:00' }
  ],
  botStatus: {
    isActive: true,
    strategy: 'Multi-Strategy Ensemble',
    lastSignal: 'BUY BTCUSDT',
    uptime: '4h 23m'
  }
};

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get('type') || 'all';
  
  // Simulate real-time data updates
  if (type === 'pnl' || type === 'all') {
    mockData.totalPnL += (Math.random() - 0.5) * 5;
    mockData.todayPnL = mockData.totalPnL * 0.3;
  }
  
  if (type === 'positions' || type === 'all') {
    mockData.positions.forEach(pos => {
      const change = (Math.random() - 0.5) * 100;
      pos.currentPrice += change;
      pos.pnl = pos.side === 'LONG' 
        ? (pos.currentPrice - pos.entryPrice) * pos.size
        : (pos.entryPrice - pos.currentPrice) * pos.size;
      pos.pnlPercent = (pos.pnl / (pos.entryPrice * pos.size)) * 100;
    });
    mockData.equity = mockData.balance + mockData.positions.reduce((sum, p) => sum + p.pnl, 0);
  }
  
  return NextResponse.json(mockData);
}
