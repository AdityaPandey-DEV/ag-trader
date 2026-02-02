from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class BaseBroker(ABC):
    @abstractmethod
    def authenticate(self):
        """Handle API authentication."""
        pass

    @abstractmethod
    def get_market_data(self, symbol: str, interval: str) -> Dict:
        """Fetch OHLCV data."""
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: str, order_type: str, quantity: int, price: Optional[float] = None) -> str:
        """Place a market or limit order."""
        pass

    @abstractmethod
    def place_oco_order(self, symbol: str, side: str, quantity: int, entry_price: float, target: float, stop_loss: float) -> str:
        """Place a bracket/OCO order (Entry + SL + Target)."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str):
        """Cancel an open order."""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> str:
        """Check order state."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict]:
        """Fetch current open positions."""
        pass
