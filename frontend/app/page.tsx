"use client";

import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import {
  Activity, Shield, TrendingUp, AlertCircle, BarChart3, Database,
  Search, Briefcase, Zap, Power
} from 'lucide-react';

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'localhost:8000';
    const wsProtocol = apiBase.includes('localhost') ? 'ws' : 'wss';

    const wsUrl = apiBase.startsWith('http')
      ? apiBase.replace(/^http/, 'ws') + '/ws'
      : `${wsProtocol}://${apiBase}/ws`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => setConnected(true);
    ws.onmessage = (event) => setData(JSON.parse(event.data));
    ws.onclose = () => setConnected(false);

    return () => ws.close();
  }, []);

  const toggleKillSwitch = async () => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'localhost:8000';
    const httpProtocol = apiBase.includes('localhost') ? 'http' : 'https';
    const baseUrl = apiBase.startsWith('http') ? apiBase : `${httpProtocol}://${apiBase}`;
    await fetch(`${baseUrl}/killswitch`, { method: 'POST' });
  };

  if (!data) return (
    <div className="loading">
      <div className="spinner"></div>
      <p>Syncing with Trading Engine...</p>
    </div>
  );

  const pnlColor = data.pnl >= 0 ? '#10b981' : '#ef4444';

  return (
    <div className="dashboard-container">
      <header>
        <div className="title-section">
          <h1><Shield size={32} /> AG_TRADER <span className="regime-badge">{data.regime}</span></h1>
        </div>
        <div className="header-actions">
          <button
            className={`primary ${data.kill_switch ? 'danger' : ''}`}
            onClick={toggleKillSwitch}
          >
            <Power size={18} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
            {data.kill_switch ? 'FORCE SHUTDOWN' : 'SYSTEM ARMED'}
          </button>
        </div>
      </header>

      <div className="stats-grid">
        <div className="glass-card">
          <p className="stat-label">Daily Net PnL</p>
          <p className="stat-value" style={{ color: pnlColor }}>
            ₹{data.pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className="glass-card">
          <p className="stat-label">Risk Consumed</p>
          <p className="stat-value">
            {data.risk_consumed.toFixed(2)}% <span style={{ fontSize: '0.8rem', color: '#64748b' }}>/ {data.max_drawdown}%</span>
          </p>
          <div style={{ width: '100%', height: '4px', background: '#1e293b', marginTop: '10px', borderRadius: '2px' }}>
            <div style={{ width: `${(data.risk_consumed / data.max_drawdown) * 100}%`, height: '100%', background: 'var(--primary)', borderRadius: '2px' }}></div>
          </div>
        </div>
        <div className="glass-card">
          <p className="stat-label">Market Regime</p>
          <p className="stat-value" style={{ borderBottom: `2px solid var(--primary)`, display: 'inline-block' }}>
            {data.regime.replace('_', ' ')}
          </p>
          <p style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '8px' }}>TSD Count: {data.tsd_count} Days</p>
        </div>
        <div className="glass-card">
          <p className="stat-label">Trading Mode</p>
          <p className="stat-value">MOCK LIVE</p>
          <p style={{ fontSize: '0.7rem', color: '#10b981', marginTop: '8px' }}>● Connected to NSE via yfinance</p>
        </div>
      </div>

      <main className="main-layout">
        <div className="center-panel">
          <div className="glass-card chart-card">
            <h3 className="stat-label"><BarChart3 size={16} style={{ marginBottom: '-3px', marginRight: '8px' }} /> Session Equity Curve</h3>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.equity_history}>
                  <defs>
                    <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Tooltip
                    contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Area type="monotone" dataKey="equity" stroke="#6366f1" fillOpacity={1} fill="url(#colorEquity)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="glass-card">
            <h3 className="stat-label"><Briefcase size={16} style={{ marginBottom: '-3px', marginRight: '8px' }} /> Active Positions</h3>
            <table className="position-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Entry</th>
                  <th>LTP</th>
                  <th>Qty</th>
                  <th>PnL</th>
                </tr>
              </thead>
              <tbody>
                {data.positions.map((pos: any, i: number) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 700 }}>{pos.symbol}</td>
                    <td><span className={`badge ${pos.side === 'SHORT' ? 'badge-short' : 'badge-long'}`}>{pos.side}</span></td>
                    <td>{pos.entry.toFixed(2)}</td>
                    <td>{pos.current.toFixed(2)}</td>
                    <td>{pos.qty}</td>
                    <td style={{ color: pos.pnl >= 0 ? '#10b981' : '#ef4444', fontWeight: 700 }}>
                      ₹{pos.pnl.toFixed(2)}
                    </td>
                  </tr>
                ))}
                {data.positions.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>No active positions</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="glass-card" style={{ marginTop: '1.5rem' }}>
            <h3 className="stat-label"><Zap size={16} style={{ marginBottom: '-3px', marginRight: '8px' }} /> Planned Trades (Upcoming)</h3>
            <table className="position-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Limit Entry</th>
                  <th>Target</th>
                  <th>Stop Loss</th>
                </tr>
              </thead>
              <tbody>
                {data.planned_trades && data.planned_trades.map((trade: any, i: number) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 700 }}>{trade.symbol}</td>
                    <td><span className={`badge ${trade.side === 'SHORT' ? 'badge-short' : 'badge-long'}`}>{trade.side}</span></td>
                    <td style={{ color: 'var(--primary)', fontWeight: 600 }}>₹{trade.entry.toFixed(2)}</td>
                    <td style={{ color: '#10b981' }}>{trade.target.toFixed(2)}</td>
                    <td style={{ color: '#ef4444' }}>{trade.stop.toFixed(2)}</td>
                  </tr>
                ))}
                {(!data.planned_trades || data.planned_trades.length === 0) && (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', color: '#64748b', padding: '1.5rem' }}>Analyzing market for setups...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="side-panel">
          <div className="glass-card">
            <h3 className="stat-label" style={{ marginBottom: '1rem' }}><Search size={16} style={{ marginBottom: '-3px', marginRight: '8px' }} /> Live Watchlist</h3>
            <div className="watchlist-grid">
              {data.watchlist.map((stock: any, i: number) => (
                <div className="watchlist-item" key={i}>
                  <div>
                    <p style={{ fontWeight: 700, fontSize: '0.9rem' }}>{stock.symbol}</p>
                    <p style={{ fontSize: '0.7rem', color: '#64748b' }}>Score: {stock.score}</p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontSize: '0.8rem', color: (stock.sentiment_score || 0) >= 0 ? '#10b981' : '#ef4444' }}>
                      {(stock.sentiment_score || 0) >= 0 ? '+' : ''}
                      {((stock.sentiment_score || 0) * 100).toFixed(0)}% Sent.
                    </p>
                    <p className="badge badge-long">READY</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card" style={{ marginTop: '1.5rem' }}>
            <h3 className="stat-label"><Database size={16} style={{ marginBottom: '-3px', marginRight: '8px' }} /> System Logs</h3>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontFamily: 'monospace', maxHeight: '180px', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {data.logs.map((log: string, i: number) => (
                <p key={i} style={{ borderLeft: '2px solid var(--primary)', paddingLeft: '8px', background: 'rgba(255,255,255,0.02)' }}>
                  {log}
                </p>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
