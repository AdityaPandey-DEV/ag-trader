import random
import uuid
import datetime
import time
from typing import Dict, List, Optional
from brokers.base import BaseBroker

class MockBroker(BaseBroker):
    def __init__(self):
        self.orders = {}
        self.positions = []
        self.balance = 100000.0
        self.cache = {} 

    def authenticate(self):
        return True

    def get_market_data(self, symbol: str, interval: str) -> Optional[Dict]:
        """MockBroker should NOT be used for Data (Execution Only)."""
        print(f"[MOCK] WARN: get_market_data called! This should not happen in Universal Data Feed mode.")
        return None
            
    def get_market_data_batch(self, symbols: List[str]) -> Dict[str, Dict]:
        """MockBroker should NOT be used for Data (Execution Only)."""
        return {}

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
