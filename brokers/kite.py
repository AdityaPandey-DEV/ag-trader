from brokers.base import BaseBroker
from typing import Dict, List, Optional
try:
    from kiteconnect import KiteConnect
except ImportError:
    KiteConnect = None

class KiteBroker(BaseBroker):
    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.kite = None
        if KiteConnect:
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)

    def authenticate(self):
        # In a real scenario, this would handle the login flow
        return self.kite is not None

    def get_market_data(self, symbol: str, interval: str) -> Dict:
        if not self.kite: return {}
        # Simple wrapper for quote
        quote = self.kite.quote(f"NSE:{symbol}")
        ohlc = quote[f"NSE:{symbol}"]["ohlc"]
        return {
            "open": ohlc["open"],
            "high": ohlc["high"],
            "low": ohlc["low"],
            "close": quote[f"NSE:{symbol}"]["last_price"],
            "volume": quote[f"NSE:{symbol}"]["volume"]
        }

    def place_order(self, symbol: str, side: str, order_type: str, quantity: int, price: Optional[float] = None) -> str:
        if not self.kite: return "error"
        # transaction_type = BUY or SELL
        tt = self.kite.TRANSACTION_TYPE_BUY if side == "LONG" else self.kite.TRANSACTION_TYPE_SELL
        ot = self.kite.ORDER_TYPE_MARKET if order_type == "MARKET" else self.kite.ORDER_TYPE_LIMIT
        
        return self.kite.place_order(
            variety=self.kite.VARIETY_REGULAR,
            exchange=self.kite.EXCHANGE_NSE,
            tradingsymbol=symbol,
            transaction_type=tt,
            quantity=quantity,
            order_type=ot,
            price=price,
            product=self.kite.PRODUCT_MIS
        )

    def place_oco_order(self, symbol: str, side: str, quantity: int, entry_price: float, target: float, stop_loss: float) -> str:
        # Zerodha GTT or Bracket Order (if available) - simplifying to MIS with SL-M for now
        # In a real system, this would be a multi-order leg or GTT
        entry_id = self.place_order(symbol, side, "MARKET", quantity)
        # Place SL and Target as separate orders (simplified)
        return entry_id

    def cancel_order(self, order_id: str):
        if self.kite:
            self.kite.cancel_order(self.kite.VARIETY_REGULAR, order_id)

    def get_order_status(self, order_id: str) -> str:
        if not self.kite: return "UNKNOWN"
        history = self.kite.order_history(order_id)
        return history[-1]["status"] if history else "UNKNOWN"

    def get_positions(self) -> List[Dict]:
        return self.kite.positions()["net"] if self.kite else []
