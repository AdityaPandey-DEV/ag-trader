"use client";

import { useEffect, useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import {
  Activity, Shield, TrendingUp, AlertCircle, BarChart3, Database,
  Search, Briefcase, Zap, Power, Coins, MousePointer2
} from 'lucide-react';

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [connected, setConnected] = useState(false);
  const [capitalInput, setCapitalInput] = useState("");

  const getBaseUrl = () => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'localhost:8000';
    const httpProtocol = apiBase.includes('localhost') ? 'http' : 'https';
    return apiBase.startsWith('http') ? apiBase : `${httpProtocol}://${apiBase}`;
  };

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
    await fetch(`${getBaseUrl()}/killswitch`, { method: 'POST' });
  };

  const togglePaperMode = async () => {
    await fetch(`${getBaseUrl()}/toggle_paper`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !data.paper_mode })
    });
  };

  const updateCapital = async () => {
    if (!capitalInput) return;
    await fetch(`${getBaseUrl()}/set_capital`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: parseFloat(capitalInput) })
    });
    setCapitalInput("");
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

        <div className="header-actions" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {/* CAPITAL INPUT (Only visible in Paper Mode) */}
          {data.paper_mode && (
            <div className="glass-card" style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '8px', border: '1px solid #334155' }}>
              <Coins size={16} color="#fbbf24" />
              <input
                type="number"
                placeholder={`\u20b9${data.initial_capital}`}
                value={capitalInput}
                onChange={(e) => setCapitalInput(e.target.value)}
                onBlur={updateCapital}
                onKeyDown={(e) => e.key === 'Enter' && updateCapital()}
                style={{ background: 'transparent', border: 'none', color: '#fff', width: '80px', fontSize: '0.85rem', outline: 'none' }}
              />
            </div>
          )}

          {/* PAPER TOGGLE */}
          <button
            onClick={togglePaperMode}
            className={`secondary`}
            style={{
              backgroundColor: data.paper_mode ? 'rgba(16, 185, 129, 0.1)' : 'transparent',
              borderColor: data.paper_mode ? '#10b981' : '#334155',
              color: data.paper_mode ? '#10b981' : '#94a3b8',
              display: 'flex', alignItems: 'center', gap: '8px'
            }}
          >
            <MousePointer2 size={16} />
            {data.paper_mode ? 'PAPER MODE' : 'LIVE MODE'}
          </button>

          <button
            className={`primary ${data.kill_switch ? 'danger' : ''}`}
            onClick={toggleKillSwitch}
            style={{ backgroundColor: data.kill_switch ? '#ef4444' : '#6366f1', border: 'none' }}
          >
            <Power size={18} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
            {data.kill_switch ? 'SYSTEM STOPPED' : 'SYSTEM ARMED'}
          </button>

          <div className="live-tag">
            <span className="pulse"></span> LIVE: {data.current_symbol} {new Date().toLocaleTimeString()}
          </div>
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
          <p className="stat-label">Execution Engine</p>
          <p className="stat-value" style={{ color: data.paper_mode ? '#94a3b8' : '#fbbf24' }}>
            {data.paper_mode ? 'PAPER (MOCK)' : 'DHAN LIVE'}
          </p>
          <p style={{ fontSize: '0.7rem', color: '#10b981', marginTop: '8px' }}>● Connected via Dhan Cloud</p>
        </div>
      </div>

      <main className="main-layout">
        <div className="center-panel">
          <div className="glass-card chart-card">
            <h3 className="stat-label"><BarChart3 size={16} style={{ marginBottom: '-3px', marginRight: '8px' }} /> Session Equity Curve</h3>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.equity_history || []}>
                  <defs>
                    <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Tooltip
                    contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '2px' }}
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
                {data.positions && data.positions.map((pos: any, i: number) => (
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
                {(!data.positions || data.positions.length === 0) && (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>No active positions</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="glass-card" style={{ marginTop: '1.5rem' }}>
            <h3 className="stat-label"><Zap size={16} style={{ marginBottom: '-3px', marginRight: '8px' }} /> Strategic Trade Planning</h3>
            <div className="split-tables">
              {/* LONG SETUPS */}
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: '0.7rem', color: '#10b981', fontWeight: 700, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <TrendingUp size={12} /> BULLISH SETUPS (LONG)
                </p>
                <div style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid #1e293b', borderRadius: '2px' }}>
                  <table className="position-table compact">
                    <thead style={{ position: 'sticky', top: 0, background: '#0f172a', zIndex: 1 }}>
                      <tr>
                        <th>Symbol</th>
                        <th>LTP</th>
                        <th>Entry</th>
                        <th>Target</th>
                        <th>SL</th>
                        <th>Dist.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.planned_trades && data.planned_trades
                        .filter((t: any) => t.side === 'LONG')
                        .sort((a: any, b: any) => a.symbol.localeCompare(b.symbol))
                        .map((trade: any, i: number) => {
                          const hasPrice = trade.current && trade.current > 0;
                          const dist = hasPrice ? ((trade.current - trade.entry) / trade.entry * 100).toFixed(2) : "--";
                          return (
                            <tr key={`${trade.symbol}-LONG`}>
                              <td style={{ fontWeight: 700 }}>{trade.symbol}</td>
                              <td style={{ color: '#94a3b8' }}>₹{trade.current || "--"}</td>
                              <td style={{ color: '#10b981', fontWeight: 600 }}>₹{trade.entry}</td>
                              <td style={{ color: '#34d399', fontSize: '0.75rem' }}>{trade.target}</td>
                              <td style={{ color: '#f87171', fontSize: '0.75rem' }}>{trade.stop}</td>
                              <td style={{ color: hasPrice && trade.current <= trade.entry * 1.002 ? '#10b981' : '#64748b', fontWeight: 600 }}>
                                {dist}{hasPrice ? '%' : ''}
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SHORT SETUPS */}
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: '0.7rem', color: '#ef4444', fontWeight: 700, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <TrendingUp size={12} style={{ transform: 'rotate(90deg)' }} /> BEARISH SETUPS (SHORT)
                </p>
                <div style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid #1e293b', borderRadius: '2px' }}>
                  <table className="position-table compact">
                    <thead style={{ position: 'sticky', top: 0, background: '#0f172a', zIndex: 1 }}>
                      <tr>
                        <th>Symbol</th>
                        <th>LTP</th>
                        <th>Entry</th>
                        <th>Target</th>
                        <th>SL</th>
                        <th>Dist.</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.planned_trades && data.planned_trades
                        .filter((t: any) => t.side === 'SHORT')
                        .sort((a: any, b: any) => a.symbol.localeCompare(b.symbol))
                        .map((trade: any, i: number) => {
                          const hasPrice = trade.current && trade.current > 0;
                          const dist = hasPrice ? ((trade.entry - trade.current) / trade.entry * 100).toFixed(2) : "--";
                          return (
                            <tr key={`${trade.symbol}-SHORT`}>
                              <td style={{ fontWeight: 700 }}>{trade.symbol}</td>
                              <td style={{ color: '#94a3b8' }}>₹{trade.current || "--"}</td>
                              <td style={{ color: '#ef4444', fontWeight: 600 }}>₹{trade.entry}</td>
                              <td style={{ color: '#34d399', fontSize: '0.75rem' }}>{trade.target}</td>
                              <td style={{ color: '#f87171', fontSize: '0.75rem' }}>{trade.stop}</td>
                              <td style={{ color: hasPrice && trade.current >= trade.entry * 0.998 ? '#ef4444' : '#64748b', fontWeight: 600 }}>
                                {dist}{hasPrice ? '%' : ''}
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="side-panel">
          <div className="glass-card">
            <h3 className="stat-label" style={{ marginBottom: '1rem' }}><Search size={16} style={{ marginBottom: '-3px', marginRight: '8px' }} /> Live Watchlist</h3>
            <div className="watchlist-grid" style={{ maxHeight: '500px', overflowY: 'auto' }}>
              {data.watchlist && data.watchlist.map((symbol: string, i: number) => (
                <div className="watchlist-item" key={i}>
                  <div>
                    <p style={{ fontWeight: 700, fontSize: '0.9rem' }}>{symbol}</p>
                    <p style={{ fontSize: '0.7rem', color: '#64748b' }}>Ready</p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p className="badge badge-long">NSE</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-card" style={{ marginTop: '1.5rem' }}>
            <h3 className="stat-label"><Database size={16} style={{ marginBottom: '-3px', marginRight: '8px' }} /> System Logs</h3>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontFamily: 'monospace', maxHeight: '180px', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {data.logs && data.logs.map((log: string, i: number) => (
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
