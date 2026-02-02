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
        
        # HYBRID LOGIC: Real-Time Data (Kite or Dhan) + Mock Execution
        self.broker = MockBroker() # Always Mock for Paper Trading
        
        # Prioritize Kite, then Dhan for high-speed data feed
        if config.KITE_API_KEY and "your_" not in config.KITE_API_KEY:
            self.data_feed = KiteBroker(config.KITE_API_KEY, config.KITE_ACCESS_TOKEN)
            feed_name = "Zerodha (Kite)"
        elif config.DHAN_CLIENT_ID and "your_" not in config.DHAN_CLIENT_ID:
            self.data_feed = DhanBroker(config.DHAN_CLIENT_ID, config.DHAN_ACCESS_TOKEN)
            feed_name = "Dhan"
        else:
            self.data_feed = self.broker # Fallback to Mock (yfinance)
            feed_name = "NSE (Mock/yfinance)"
            
        self.tsd_count = 0
        self.watchlist = []
        self.planned_trades = []
        self.logs = [f"[SYSTEM] Hybrid Engine initialized ({feed_name} Data + Mock Execution)."]
        self.session_pnl = 0.0
        self.lock = threading.Lock()
        self.levels = {} 
        self.kill_switch = False
        
        # Dashboard push function (set by api.py)
        self.on_update = lambda symbol="MULTI": None
        
        # API URL - Consolidated to NEXT_PUBLIC_API_URL (used by Vercel & Render)
        api_host = os.getenv("NEXT_PUBLIC_API_URL", "localhost:8000")
        # Ensure protocol is present
        if "://" not in api_host:
            protocol = "http" if "localhost" in api_host else "https"
            self.api_url = f"{protocol}://{api_host}"
        else:
            self.api_url = api_host

    def log(self, message: str):
        with self.lock:
            timestamp = datetime.datetime.now().strftime("%H:%M")
            full_msg = f"[{timestamp}] {message}"
            self.logs.append(full_msg)
            if len(self.logs) > 50: self.logs.pop(0)
            print(full_msg)

    def update_dashboard(self, current_symbol: str = "MULTI"):
        """Pushes current state to the FastAPI dashboard via callback or POST."""
        try:
            # Trigger the callback (injected by api.py for websocket efficiency)
            self.on_update(current_symbol)
            
            # Fallback for cloud/distributed setups if needed
            # requests.post(f"{self.api_url}/update", json=self.get_state(), timeout=0.1)
        except Exception:
            pass

    def get_state(self):
        """Returns the current engine state for dashboarding."""
        with self.lock:
            return {
                "regime": get_regime(self.tsd_count),
                "tsd_count": self.tsd_count,
                "risk_consumed": self.risk_manager.daily_pnl,
                "max_drawdown": config.MAX_SESSION_DRAWDOWN_PCT,
                "kill_switch": self.kill_switch,
                "pnl": round(self.session_pnl, 2),
                "current_symbol": "MULTI",
                "watchlist": self.watchlist,
                "positions": self.broker.get_positions(),
                "planned_trades": self.planned_trades,
                "logs": self.logs
            }

    def run_tick(self, symbol: str, pre_fetched_data=None):
        """Processes a single symbol tick using pre-fetched or live data."""
        if self.kill_switch:
            return

        try:
            market_data = pre_fetched_data
            if not market_data:
                if self.data_feed.authenticate():
                    market_data = self.data_feed.get_market_data(symbol, "1minute")
                if not market_data:
                    market_data = self.broker.get_market_data(symbol, "1minute")
            
            if not market_data or 'close' not in market_data:
                return

            current_price = market_data['close']

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

            if current_price <= support:
                self.log(f"TOUCH: {symbol} at Support \u20b9{support}")
            elif current_price >= resistance:
                self.log(f"TOUCH: {symbol} at Resistance \u20b9{resistance}")

            prior_data = market_data.get('prior', market_data)
            signal = self.strategy.generate_signal(
                market_data, prior_data, resistance, support, 
                regime, base_range, trend_shift
            )
            
            if signal:
                quantity = 100
                costs = self.tax_calculator.calculate_costs(signal['entry'], signal['target'], quantity)
                ai_confirmed = self.ai_analyzer.confirm_trend(symbol, market_data)
                
                if ai_confirmed and costs['net_profit_pct'] > 0.05:
                    self.broker.place_order(symbol, signal['side'], "MARKET", quantity)
                    self.log(f"ORDER: {symbol} {signal['side']} at \u20b9{signal['entry']}")
                else:
                    if not ai_confirmed:
                        self.log(f"AI FILTER: {symbol} rejected by Trend Analysis.")
                    elif costs['net_profit_pct'] <= 0.05:
                        self.log(f"COST FILTER: {symbol} Profit low ({costs['net_profit_pct']:.2f}%).")

        except Exception:
            pass

    def start(self):
        """Main Loop: Screens stocks and runs the engine."""
        universe = [
            "ABB","ACC","APLAPOLLO","AUBANK","ADANIENSOL","ADANIENT","ADANIGREEN",
            "ADANIPORTS","ADANIPOWER","ATGL","ABCAPITAL","ALKEM","AMBUJACEM","APOLLOHOSP",
            "ASHOKLEY","ASIANPAINT","ASTRAL","AUROPHARMA","DMART","AXISBANK","BSE",
            "BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BAJAJHLDNG","BAJAJHFL","BANKBARODA",
            "BANKINDIA","BDL","BEL","BHARATFORG","BHEL","BPCL","BHARTIARTL","BHARTIHEXA",
            "BIOCON","BLUESTARCO","BOSCHLTD","BRITANNIA","CGPOWER","CANBK","CHOLAFIN",
            "CIPLA","COALINDIA","COCHINSHIP","COFORGE","COLPAL","CONCOR","COROMANDEL",
            "CUMMINSIND","DLF","DABUR","DIVISLAB","DIXON","DRREDDY","DUMMYHDLVR",
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
        screened = self.screener.screen(universe)
        self.watchlist = [s['symbol'] for s in screened][:250]
        self.log(f"Watchlist: {self.watchlist[:5]}... (+{len(self.watchlist)-5} more)")

        with ThreadPoolExecutor(max_workers=50) as executor:
            while True:
                try:
                    now = time.time()
                    if not self.risk_manager.check_constraints():
                        self.log("Risk limit reached. Halting.")
                        break
                        
                    # Batch fetch
                    all_data = {}
                    if hasattr(self.data_feed, "get_market_data_batch"):
                        for i in range(0, len(self.watchlist), 50):
                            chunk = self.watchlist[i:i+50]
                            all_data.update(self.data_feed.get_market_data_batch(chunk))
                    
                    # Parallel process
                    futures = [executor.submit(self.run_tick, s, all_data.get(s)) for s in self.watchlist]
                    for f in futures:
                        try: f.result(timeout=1)
                        except: pass
                    
                    self.update_dashboard()
                    time.sleep(max(0.1, 1.0 - (time.time() - now)))
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.log(f"ENGINE ERROR: {e}")

if __name__ == "__main__":
    engine = TradingEngine()
    engine.start()
