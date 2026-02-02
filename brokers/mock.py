from brokers.base import BaseBroker
from typing import Dict, List, Optional
import uuid
try:
    import yfinance as yf
except ImportError:
    yf = None

class MockBroker(BaseBroker):
    def __init__(self):
        self.orders = {}
        self.positions = []
        self.balance = 100000.0

    def authenticate(self):
        return True

    def get_market_data(self, symbol: str, interval: str) -> Optional[Dict]:
        """Fetch real data using yfinance (free)."""
        try:
            if not yf:
                return None
                
            # Standardize for NSE if not specified
            ticker_symbol = symbol if "." in symbol else f"{symbol}.NS"
            ticker = yf.Ticker(ticker_symbol)
            
            # Mapping interval (yfinance: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d...)
            yf_interval = "5m" if "5" in interval else "1m"
            
            data = ticker.history(period="1d", interval=yf_interval)
            if data.empty:
                return None
                
            last_row = data.iloc[-1]
            return {
                "open": last_row['Open'],
                "high": last_row['High'],
                "low": last_row['Low'],
                "close": last_row['Close'],
                "volume": last_row['Volume']
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
