from dhanhq import dhanhq
from brokers.base import BaseBroker
from typing import Dict, List, Optional

class DhanBroker(BaseBroker):
    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.dhan = None
        
        if client_id and "your_" not in client_id:
            try:
                self.dhan = dhanhq(client_id, access_token)
            except Exception as e:
                print(f"[DHAN] Initialization Error: {e}")

    def authenticate(self):
        return self.dhan is not None

    def get_market_data(self, symbol: str, interval: str) -> Optional[Dict]:
        """Fetch real-time data for a single symbol from Dhan."""
        batch = self.get_market_data_batch([symbol])
        return batch.get(symbol)

    def get_market_data_batch(self, symbols: List[str]) -> Dict[str, Dict]:
        """Fetch real-time data for multiple symbols in one go."""
        if not self.dhan:
            return {}
            
        try:
            # Map symbols to Dhan format (SYMBOL-EQ)
            mapping = {f"{s.split('.')[0] if '.' in s else s}-EQ": s for s in symbols}
            dhan_securities = {ds: 'NSE_EQ' for ds in mapping.keys()}
            
            # Use batch quote_data call
            response = self.dhan.quote_data(securities=dhan_securities)
            
            results = {}
            if response and response.get('status') == 'success':
                data_map = response.get('data', {})
                for ds, target_symbol in mapping.items():
                    data = data_map.get(ds, {})
                    if data:
                        results[target_symbol] = {
                            "open": data.get('open', 0),
                            "high": data.get('high', 0),
                            "low": data.get('low', 0),
                            "close": data.get('last_price', data.get('lp', 0)),
                            "volume": data.get('volume', 0)
                        }
            return results
        except Exception as e:
            print(f"[DHAN] Batch Data Fetch Error: {e}")
            return {}

    def place_order(self, symbol: str, side: str, order_type: str, quantity: int, price: Optional[float] = None) -> str:
        """Paper Trading Placeholder."""
        return "PAPER_ORDER"

    def place_oco_order(self, symbol: str, side: str, quantity: int, entry_price: float, target: float, stop_loss: float) -> str:
        """Paper Trading Placeholder."""
        return "PAPER_ORDER"

    def cancel_order(self, order_id: str):
        """Paper Trading Placeholder."""
        pass

    def get_order_status(self, order_id: str) -> str:
        """Paper Trading Placeholder."""
        return "COMPLETE"

    def get_positions(self) -> List[Dict]:
        """Paper Trading Placeholder."""
        return []
