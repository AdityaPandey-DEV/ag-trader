import time
import requests
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor
from config.settings import config
from core.indicators import calculate_base_range, calculate_trend_shift_linreg, update_tsd_count, get_regime
from core.risk_manager import RiskManager
from strategies.mean_reversion import mean_reversion_strategy
from brokers.mock import MockBroker
import pandas as pd

from utils.tax_calculator import TaxCalculator
from utils.ai_analyzer import AITrendAnalyzer
from utils.screenshot import ChartScreenshotter
from core.screener import StockScreener

class TradingEngine:
    def __init__(self):
        self.risk_manager = RiskManager(
            max_drawdown=config.MAX_SESSION_DRAWDOWN_PCT,
            max_trades=config.MAX_TRADES_PER_SESSION,
            max_losses=config.MAX_CONSECUTIVE_LOSSES
        )
        self.strategy = mean_reversion_strategy(config)
        self.broker = MockBroker()
        self.tax_calculator = TaxCalculator()
        self.ai_analyzer = AITrendAnalyzer(api_key=config.GEMINI_API_KEY)
        self.screenshotter = ChartScreenshotter()
        self.screener = StockScreener(api_key=config.GEMINI_API_KEY)
        self.tsd_count = 0
        self.watchlist = []
        self.planned_trades = []
        self.logs = ["[SYSTEM] Multi-threaded Engine initialized."]
        self.session_pnl = 0.0
        self.lock = threading.Lock()
        self.levels = {} 
        self.kill_switch = False # Persistent state

    def log(self, message: str):
        with self.lock:
            timestamp = datetime.datetime.now().strftime("%H:%M")
            full_msg = f"[{timestamp}] {message}"
            self.logs.append(full_msg)
            if len(self.logs) > 25: self.logs.pop(0)
            print(full_msg)

    def update_dashboard(self, current_symbol: str = "MULTI"):
        """Pushes current state to the FastAPI dashboard."""
        try:
            with self.lock:
                state = {
                    "regime": get_regime(self.tsd_count),
                    "tsd_count": self.tsd_count,
                    "risk_consumed": self.risk_manager.daily_pnl,
                    "max_drawdown": config.MAX_SESSION_DRAWDOWN_PCT,
                    "kill_switch": False,
                    "pnl": round(self.session_pnl, 2),
                    "current_symbol": current_symbol,
                    "watchlist": self.watchlist,
                    "positions": self.broker.positions,
                    "planned_trades": self.planned_trades,
                    "logs": self.logs
                }
            requests.post("http://localhost:8000/update", json=state, timeout=1)
        except Exception:
            pass

    def run_pre_market(self, universe: list):
        """Screens the universe and prepares the watchlist."""
        self.log("Running pre-market stock screening...")
        self.watchlist = self.screener.screen(universe)
        self.log(f"Watchlist prepared: {[s['symbol'] for s in self.watchlist]}")
        self.update_dashboard()

    def run_tick(self, symbol: str):
        if self.kill_switch or not self.risk_manager.check_constraints():
            return

        try:
            market_data = self.broker.get_market_data(symbol, "5minute")
            
            if not market_data or 'close' not in market_data:
                self.log(f"WARNING: Could not fetch data for {symbol}. Skipping tick.")
                return

            # Current Market Price
            current_price = market_data['close']

            # Calculate Volatility levels ONLY ONCE if not exists
            if symbol not in self.levels:
                high_24h = market_data.get('high', current_price * 1.01)
                low_24h = market_data.get('low', current_price * 0.99)
                vol_range = max(0.005, (high_24h - low_24h) / current_price * 0.3)
                self.levels[symbol] = {
                    "resistance": current_price * (1 + vol_range),
                    "support": current_price * (1 - vol_range),
                    "base_range": current_price * (vol_range * 0.5)
                }

            lvl = self.levels[symbol]
            resistance, support = lvl['resistance'], lvl['support']
            base_range = lvl['base_range']
            trend_shift = current_price * 0.001
            regime = get_regime(self.tsd_count)
            
            # Update shared planned trades with STATIC entry but MOVING LTP
            with self.lock:
                self.planned_trades = [p for p in self.planned_trades if p['symbol'] != symbol]
                self.planned_trades.append({
                    "symbol": symbol, "side": "LONG", "current": round(current_price, 2),
                    "entry": round(support, 2), "target": round(resistance * 0.998, 2), "stop": round(support * 0.995, 2)
                })
                self.planned_trades.append({
                    "symbol": symbol, "side": "SHORT", "current": round(current_price, 2),
                    "entry": round(resistance, 2), "target": round(support * 1.002, 2), "stop": round(resistance * 1.005, 2)
                })

            # Level Touch Notification
            if current_price <= support:
                self.log(f"TOUCH: {symbol} at Support ₹{support}")
            elif current_price >= resistance:
                self.log(f"TOUCH: {symbol} at Resistance ₹{resistance}")

            # Extract prior data for strategy comparison
            prior_data = market_data.get('prior', market_data)

            signal = self.strategy.generate_signal(
                market_data, prior_data, resistance, support, 
                regime, base_range, trend_shift
            )
            
            if signal:
                quantity = 100
                if signal['side'] == "LONG":
                    costs = self.tax_calculator.calculate_costs(signal['entry'], signal['target'], quantity)
                else:
                    costs = self.tax_calculator.calculate_costs(signal['target'], signal['entry'], quantity)
                
                if costs['net_pnl'] > 0:
                    summary = f"Symbol: {symbol}, Side: {signal['side']}, Entry: {signal['entry']}, Target: {signal['target']}"
                    # Skip AI Analyzer for MOCK mode or if Key is missing for faster execution
                    is_confirmed = True
                    if config.DEFAULT_BROKER != "MOCK" and config.GEMINI_API_KEY:
                        is_confirmed = self.ai_analyzer.confirm_trend(summary)
                    
                    if is_confirmed:
                        self.broker.place_oco_order(symbol, signal['side'], quantity, signal['entry'], signal['target'], signal['stop_loss'])
                        with self.lock:
                            self.risk_manager.record_trade(costs['net_pnl'] / (signal['entry'] * quantity) * 100)
                            self.session_pnl += costs['net_pnl']
                        self.log(f"EXECUTION: {signal['side']} {symbol} at {signal['entry']} (Target: {signal['target']})")
                    else:
                        self.log(f"AI FILTER: {symbol} signal rejected by AITrendAnalyzer.")
                else:
                    self.log(f"COST FILTER: {symbol} signal skipped (Potential Net PnL ₹{costs['net_pnl']} <= 0)")
            elif current_price <= support or current_price >= resistance:
                # The price hit the level but strategy conditions (candle/volume) weren't met
                self.log(f"STRATEGY: {symbol} level hit but no Rejection Candle confirmation yet.")
            
            # Real-time dashboard push after EVERY stock update
            self.update_dashboard(symbol)
        except Exception as e:
            self.log(f"Error in {symbol} tick: {e}")

    def start(self):
        self.log("--- STARTING MULTI-STOCK SESSION ---")
        universe = list(set(["TCS", "RELIANCE", "INFY", "HDFCBANK", "ICICIBANK"]))
        self.run_pre_market(universe)
        
        symbols = [s['symbol'] for s in self.watchlist]
        
        with ThreadPoolExecutor(max_workers=len(symbols)) as executor:
            while True:
                try:
                    if not self.risk_manager.check_constraints():
                        self.log("CRITICAL: Max risk limit reached. Halting Engine.")
                        self.update_dashboard()
                        break
                        
                    # Execute all symbols in parallel
                    list(executor.map(self.run_tick, symbols))
                    
                    # Refresh every 1 second for a TRUE Real-Time feel
                    time.sleep(1)
                except KeyboardInterrupt:
                    self.log("Shutdown signal received.")
                    break
                except Exception as e:
                    self.log(f"ENGINE LOOP ERROR: {e}")
                    time.sleep(10)

if __name__ == "__main__":
    engine = TradingEngine()
    engine.start()
