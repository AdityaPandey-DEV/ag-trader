import random
import uuid
import datetime
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
        self.last_prices = {}

    def authenticate(self):
        return True

    def get_market_data(self, symbol: str, interval: str) -> Optional[Dict]:
        """Fetch real data using yfinance (free) with 1s jitter simulation."""
        try:
            if not yf: return None
            ticker_symbol = symbol if "." in symbol else f"{symbol}.NS"
            ticker = yf.Ticker(ticker_symbol)
            
            # Use 1m as base for simulation
            data = ticker.history(period="1d", interval="1m")
            if data.empty: return None
            
            base_row = data.iloc[-1]
            prior_row = data.iloc[-2] if len(data) > 1 else base_row
            
            # Simulate real-time jitter (+/- 0.05%) so LTP and Dist move every second
            jitter = 1 + (random.uniform(-0.0005, 0.0005))
            live_price = round(base_row['Close'] * jitter, 2)
            
            print(f"[LIVE] {ticker_symbol} price matched: ₹{live_price}")
            
            return {
                "open": base_row['Open'],
                "high": base_row['High'],
                "low": base_row['Low'],
                "close": live_price,
                "volume": base_row['Volume'],
                "prior": {
                    "open": prior_row['Open'],
                    "high": prior_row['High'],
                    "low": prior_row['Low'],
                    "close": prior_row['Close'],
                    "volume": prior_row['Volume']
                }
            }
        except Exception:
            return None

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
