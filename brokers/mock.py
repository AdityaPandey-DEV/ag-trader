import random
import uuid
import datetime
import time
from typing import Dict, List, Optional
from brokers.base import BaseBroker

try:
    import yfinance as yf
except ImportError:
    yf = None

class MockBroker(BaseBroker):
    def __init__(self):
        self.orders = {}
        self.positions = []
        self.balance = 100000.0
        self.cache = {}
        self.cache_expiry = {}

    def authenticate(self):
        return True

    def get_market_data(self, symbol: str, interval: str) -> Optional[Dict]:
        """Fetch data from Yahoo Finance (Free Fallback)."""
        try:
            if not yf: return None
            ticker_symbol = symbol if "." in symbol else f"{symbol}.NS"
            
            now = time.time()
            # Cache duration: 60s
            if ticker_symbol in self.cache and now < self.cache_expiry.get(ticker_symbol, 0):
                return self.cache[ticker_symbol]

            ticker = yf.Ticker(ticker_symbol)
            data = ticker.history(period="1d", interval="1m")
            if data.empty: return None
            
            row = data.iloc[-1]
            # Simple structure
            market_data = {
                "open": row['Open'],
                "high": row['High'],
                "low": row['Low'],
                "close": row['Close'],
                "volume": row['Volume']
            }
            
            self.cache[ticker_symbol] = market_data
            self.cache_expiry[ticker_symbol] = now + 60
            return market_data
        except Exception as e:
            # print(f"[MOCK] Data Error: {e}")
            return None

    def get_market_data_batch(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch multiple symbols from YFinance threaded."""
        results = {}
        from concurrent.futures import ThreadPoolExecutor
        
        def fetch(s):
            d = self.get_market_data(s, "1minute")
            return s, d
            
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch, s) for s in symbols]
            for f in futures:
                try:
                    s, d = f.result(timeout=2)
                    if d: results[s] = d
                except: pass
        return results

    def place_order(self, symbol: str, side: str, order_type: str, quantity: int, price: Optional[float] = None) -> str:
        order_id = str(uuid.uuid4())
        self.orders[order_id] = {"status": "COMPLETE", "symbol": symbol, "side": side}
        return order_id

    def place_oco_order(self, symbol: str, side: str, quantity: int, entry_price: float, target: float, stop_loss: float) -> str:
        order_id = str(uuid.uuid4())
        self.orders[order_id] = {
            "status": "OPEN", 
            "symbol": symbol, 
            "side": side, 
            "entry": entry_price, 
            "target": target, 
            "sl": stop_loss
        }
        return order_id

    def cancel_order(self, order_id: str):
        if order_id in self.orders:
            self.orders[order_id]["status"] = "CANCELLED"

    def get_order_status(self, order_id: str) -> str:
        return self.orders.get(order_id, {}).get("status", "NOT_FOUND")

    def get_positions(self) -> List[Dict]:
        return self.positions

    def get_balance(self) -> float:
        return self.balance
