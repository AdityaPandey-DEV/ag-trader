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
from brokers.dhan import DhanBroker
from brokers.kite import KiteBroker
import pandas as pd
import os

from utils.tax_calculator import TaxCalculator
from utils.ai_analyzer import AITrendAnalyzer
from utils.screenshot import ChartScreenshotter
from utils.screenshot import ChartScreenshotter
from core.screener import StockScreener
from core.persistence import PersistenceManager

class TradingEngine:
    def __init__(self):
        self.risk_manager = RiskManager(
            max_drawdown=config.MAX_SESSION_DRAWDOWN_PCT,
            max_trades=config.MAX_TRADES_PER_SESSION,
            max_losses=config.MAX_CONSECUTIVE_LOSSES
        )
        self.strategy = mean_reversion_strategy(config)
        self.tax_calculator = TaxCalculator()
        self.ai_analyzer = AITrendAnalyzer(api_key=config.GEMINI_API_KEY)
        self.screenshotter = ChartScreenshotter()
        self.screener = StockScreener()
        
        # State
        self.paper_mode = True # Default to paper for safety
        self.initial_capital = 100000.0
        
        # Load Persistence if in Paper Mode
        saved_state = PersistenceManager.load_paper_state()
        if saved_state:
            print(f"[PERSISTENCE] Loaded Paper State: ₹{saved_state.get('capital', 100000)}")
            self.initial_capital = saved_state.get('capital', 100000.0)
            self.session_pnl = saved_state.get('pnl', 0.0)
            # We will load positions/history in a moment
        
        self.tsd_count = 0
        self.watchlist = []
        self.planned_trades = []
        self.logs = ["[SYSTEM] Engine initializing..."]
        if not saved_state: self.session_pnl = 0.0
        self.lock = threading.Lock()
        self.levels = {} 
        self.kill_switch = False
        self.on_update = lambda symbol="MULTI": None
        
        # Dashboard Data
        self.equity_history = saved_state.get('equity_history', [{"time": datetime.datetime.now().strftime("%H:%M:%S"), "equity": self.initial_capital}])
        self.last_equity_update = time.time()
        self.last_persistence_save = time.time()
        
        # Brokers
        self.mock_broker = MockBroker()
        self.dhan_broker = None
        self.kite_broker = None
        
        if config.DHAN_CLIENT_ID and "your_" not in config.DHAN_CLIENT_ID:
            self.dhan_broker = DhanBroker(config.DHAN_CLIENT_ID, config.DHAN_ACCESS_TOKEN)
            
        if config.KITE_API_KEY and "your_" not in config.KITE_API_KEY:
            self.kite_broker = KiteBroker(config.KITE_API_KEY, config.KITE_ACCESS_TOKEN)

        # Unified Data Feed & Execution
        # HYBRID MODE: Prefer Dhan, but allow Mock (yfinance) if Dhan Data is inactive
        self.data_feed = self.dhan_broker or self.kite_broker
        
        # Force Hybrid if Dhan Data is failing (User has inactive plan)
        # Uncomment below to force yfinance data while keeping Dhan Execution
        self.data_feed = self.mock_broker 

        if not self.data_feed:
             self.log("[CRITICAL] NO DATA FEED AVAILABLE.")
             self.log("Please check .env or internet.")
             self.data_feed = self.mock_broker
        
        self.broker = self.mock_broker # Execution starts in MOCK
        
        self.api_url = os.getenv("NEXT_PUBLIC_API_URL", "localhost:8000")
        if "://" not in self.api_url:
            protocol = "http" if "localhost" in self.api_url else "https"
            self.api_full_url = f"{protocol}://{self.api_url}"
        else:
            self.api_full_url = self.api_url

        self.log(f"[SYSTEM] Hybrid Engine ready. Data: {type(self.data_feed).__name__}, Execution: {type(self.broker).__name__}")

    def log(self, message: str):
        with self.lock:
            timestamp = datetime.datetime.now().strftime("%H:%M")
            full_msg = f"[{timestamp}] {message}"
            self.logs.append(full_msg)
            if len(self.logs) > 50: self.logs.pop(0)
            print(full_msg)

    def toggle_paper_mode(self, enabled: bool):
        with self.lock:
            self.paper_mode = enabled
            if enabled:
                self.broker = self.mock_broker
                self.log("MODE: Switched to PAPER TRADING (Mock Execution)")
            else:
                if self.dhan_broker:
                    self.broker = self.dhan_broker
                    self.log("MODE: Switched to LIVE TRADING (Dhan Execution)")
                    
                    # Auto-fetch balance
                    balance = self.broker.get_balance()
                    if balance > 0:
                        self.initial_capital = balance
                        self.log(f"CAPITAL: Synced with Dhan (₹{balance:.2f})")
                else:
                    self.paper_mode = True
                    self.log("ERROR: No live broker configured. Staying in PAPER mode.")
            self.update_dashboard()

    def set_initial_capital(self, amount: float):
        with self.lock:
            self.initial_capital = amount
            # Reset history on capital change
            self.equity_history = [{"time": datetime.datetime.now().strftime("%H:%M:%S"), "equity": amount}]
            PersistenceManager.reset_paper_state()
            self.log(f"CAPITAL: Set to ₹{amount:.2f}")
            self.update_dashboard()

    def update_dashboard(self, current_symbol: str = "MULTI"):
        try:
            # Periodic Equity Update (Every 5 seconds for smoother demo, usually 60s)
            now = time.time()
            if now - self.last_equity_update > 5:
                # Keep history manageable
                if len(self.equity_history) > 500: self.equity_history.pop(0)
                
                self.equity_history.append({
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "equity": self.initial_capital + self.session_pnl
                })
                self.last_equity_update = now

            # Persistence Save (Every 30s) if Paper Mode
            if self.paper_mode and now - self.last_persistence_save > 30:
                PersistenceManager.save_paper_state({
                    "capital": self.initial_capital,
                    "pnl": self.session_pnl,
                    "equity_history": self.equity_history
                })
                self.last_persistence_save = now

            self.on_update(current_symbol)
        except Exception as e:
            print(f"Dashboard update error: {e}")

    def get_state(self):
        with self.lock:
            return {
                "regime": get_regime(self.tsd_count),
                "tsd_count": self.tsd_count,
                "risk_consumed": abs(self.risk_manager.daily_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0,
                "max_drawdown": config.MAX_SESSION_DRAWDOWN_PCT,
                "kill_switch": self.kill_switch,
                "paper_mode": self.paper_mode,
                "initial_capital": self.initial_capital,
                "pnl": round(self.session_pnl, 2),
                "current_symbol": "MULTI",
                "watchlist": self.watchlist,
                "positions": self.broker.get_positions(),
                "planned_trades": self.planned_trades,
                "logs": self.logs,
                "equity_history": self.equity_history
            }

    def run_tick(self, symbol: str, pre_fetched_data=None):
        if self.kill_switch: return

        try:
            market_data = pre_fetched_data
            # CRITICAL: Do NOT fetch individually if batch missing. This causes Rate Limit (805) explosion.
            if not market_data:
                return 
            
            if 'close' not in market_data: return
            current_price = market_data['close']

            # Levels logic
            if symbol not in self.levels:
                high_24h = market_data.get('high', current_price * 1.01)
                low_24h = market_data.get('low', current_price * 0.99)
                vol_range = max(0.002, (high_24h - low_24h) / current_price * 0.15)
                self.levels[symbol] = {
                    "resistance": current_price * (1 + vol_range),
                    "support": current_price * (1 - vol_range),
                    "base_range": current_price * (vol_range * 0.5)
                }

            lvl = self.levels[symbol]
            resistance, support = lvl['resistance'], lvl['support']
            base_range = lvl['base_range']
            
            # Simplified trend shift for tick-by-tick
            trend_shift = (current_price - market_data.get('open', current_price)) 
            regime = get_regime(self.tsd_count)
            
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

            # Reversion Signal
            signal = self.strategy.generate_signal(
                market_data, market_data.get('prior', market_data), 
                resistance, support, regime, base_range, trend_shift
            )
            
            if signal:
                if current_price <= support:
                    self.log(f"⚡ TOUCH: {symbol} hit SUPPORT. Evaluating...")
                elif current_price >= resistance:
                    self.log(f"⚡ TOUCH: {symbol} hit RESISTANCE. Evaluating...")

                qty = int(self.initial_capital * 0.1 / current_price) if current_price > 0 else 1
                costs = self.tax_calculator.calculate_costs(signal['entry'], signal['target'], qty)
                
                summary = f"Symbol: {symbol}, Side: {signal['side']}, LTP: {current_price}"
                ai_confirmed = self.ai_analyzer.confirm_trend(summary)
                
                if ai_confirmed and (costs['net_profit_pct'] > -0.01 or self.paper_mode):
                    self.broker.place_order(symbol, signal['side'], "MARKET", qty)
                    self.log(f"ORDER: {symbol} {signal['side']} at ₹{current_price} (Qty: {qty})")
                else:
                    reason = "AI" if not ai_confirmed else "Profitability"
                    print(f"[ENGINE] {symbol} signal filtered by {reason}.")

        except Exception as e:
            print(f"Error in tick for {symbol}: {e}")

    def start(self):
        universe = [
            "ABB","ACC","APLAPOLLO","AUBANK","ADANIENSOL","ADANIENT","ADANIGREEN",
            "ADANIPORTS","ADANIPOWER","ATGL","ABCAPITAL","ALKEM","AMBUJACEM","APOLLOHOSP",
            "ASHOKLEY","ASIANPAINT","ASTRAL","AUROPHARMA","DMART","AXISBANK","BSE",
            "BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BAJAJHLDNG","BAJAJHFL","BANKBARODA",
            "BANKINDIA","BDL","BEL","BHARATFORG","BHEL","BPCL","BHARTIARTL","BHARTIHEXA",
            "BIOCON","BLUESTARCO","BOSCHLTD","BRITANNIA","CGPOWER","CANBK","CHOLAFIN",
            "CIPLA","COALINDIA","COCHINSHIP","COFORGE","COLPAL","CONCOR","COROMANDEL",
            "CUMMINSIND","DLF","DABUR","DIVISLAB","DIXON","DRREDDY",
            "EICHERMOT","ETERNAL","EXIDEIND","NYKAA","FEDERALBNK","FORTIS","GAIL",
            "GMRAIRPORT","GLENMARK","GODFRYPHLP","GODREJCP","GODREJPROP","GRASIM","HCLTECH",
            "HDFCAMC","HDFCBANK","HDFCLIFE","HAVELLS","HEROMOTOCO","HINDALCO","HAL",
            "HINDPETRO","HINDUNILVR","HINDZINC","POWERINDIA","HUDCO","HYUNDAI","ICICIBANK",
            "ICICIGI","IDFCFIRSTB","IRB","ITC","INDIANB","INDHOTEL","IOC","IRCTC","IRFC",
            "IREDA","IGL","INDUSTOWER","INDUSINDBK","NAUKRI","INFY","INDIGO","JSWENERGY",
            "JSWSTEEL","JINDALSTEL","JIOFIN","JUBLFOOD","KEI","KPITTECH","KALYANKJIL",
            "KOTAKBANK","LTF","LICHSGFIN","LTIM","LT","LICI","LODHA","LUPIN","MRF",
            "M&MFIN","M&M","MANKIND","MARICO","MARUTI","MFSL","MAXHEALTH","MAZDOCK",
            "MOTILALOFS","MPHASIS","MUTHOOTFIN","NHPC","NMDC","NTPC","NATIONALUM",
            "NESTLEIND","OBEROIRLTY","ONGC","OIL","PAYTM","OFSS","POLICYBZR","PIIND",
            "PAGEIND","PATANJALI","PERSISTENT","PHOENIXLTD","PIDILITIND","POLYCAB",
            "PFC","POWERGRID","PREMIERENE","PRESTIGE","PNB","RECLTD","RVNL","RELIANCE",
            "SBICARD","SBILIFE","SRF","MOTHERSON","SHREECEM","SHRIRAMFIN","ENRIN",
            "SIEMENS","SOLARINDS","SONACOMS","SBIN","SAIL","SUNPHARMA","SUPREMEIND",
            "SUZLON","SWIGGY","TVSMOTOR","TATACOMM","TCS","TATACONSUM","TATAELXSI",
            "TMPV","TATAPOWER","TATASTEEL","TATATECH","TECHM","TITAN","TORNTPHARM",
            "TORNTPOWER","TRENT","TIINDIA","UPL","ULTRACEMCO","UNIONBANK","UNITDSPR",
            "VBL","VEDL","VMM","IDEA","VOLTAS","WAAREEENER","WIPRO","YESBANK","ZYDUSLIFE"
        ]

        self.log(f"Screening universe of {len(universe)} symbols...")
        # BYPASS SCREENER FOR SPEED (It blocks for too long)
        # screened = self.screener.screen(universe)
        # self.watchlist = [s['symbol'] for s in screened][:250]
        self.watchlist = universe # Load all directly
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            while True:
                try:
                    now = time.time()
                    if not self.risk_manager.check_constraints():
                        self.log("Risk limit reached. Halting.")
                        break
                        
                    # Batch fetch from data feed
                    all_data = {}
                    if hasattr(self.data_feed, "get_market_data_batch"):
                        for i in range(0, len(self.watchlist), 50):
                            chunk = self.watchlist[i:i+50]
                            all_data.update(self.data_feed.get_market_data_batch(chunk))
                            time.sleep(0.2) # Rate limit protection
                    
                    # Update Regime (TSD Logic) using Nifty/Index proxy or avg move
                    if all_data:
                        avg_move = sum(abs(v['close'] - v.get('open', v['close'])) for v in all_data.values()) / len(all_data)
                        avg_range = sum(v['high'] - v['low'] for v in all_data.values()) / len(all_data)
                        self.tsd_count = update_tsd_count(self.tsd_count, avg_move, avg_range)

                    # Parallel process ticks
                    futures = [executor.submit(self.run_tick, s, all_data.get(s)) for s in self.watchlist]
                    for f in futures:
                        try: f.result(timeout=1)
                        except: pass
                    
                    self.update_dashboard()
                    
                    if int(time.time()) % 20 == 0:
                        self.log(f"SCANNING: {len(all_data)}/{len(self.watchlist)} stocks active. Regime: {get_regime(self.tsd_count)}")

                    # Enforce minimum 3-second loop duration to prevent rate limits
                    elapsed = time.time() - now
                    time.sleep(max(1.0, 3.0 - elapsed))
                except KeyboardInterrupt: break
                except Exception as e: self.log(f"ENGINE ERROR: {e}")

if __name__ == "__main__":
    engine = TradingEngine()
    engine.start()
