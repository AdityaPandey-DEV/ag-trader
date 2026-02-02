import pandas as pd
from typing import Optional, Dict

class mean_reversion_strategy:
    def __init__(self, config):
        self.config = config

    def check_rejection_candle(self, open: float, high: float, low: float, close: float, side: str) -> bool:
        """
        Counter-Trend Short: Rejection candle (upper wick > body)
        Counter-Trend Long: Rejection candle (lower wick > body)
        """
        body = abs(close - open)
        if side == "SHORT":
            upper_wick = high - max(open, close)
            return upper_wick > (0.3 * body) # Relaxed from 1.0 * body
        elif side == "LONG":
            lower_wick = min(open, close) - low
            return lower_wick > (0.3 * body) # Relaxed from 1.0 * body
        return False

    def check_volume_filter(self, current_volume: float, prior_volume: float) -> bool:
        """
        Red candle volume >= prior candle volume (for shorts)
        Green candle volume >= prior candle volume (for longs)
        """
        # Relaxed: Only needs 70% of prior volume to confirm
        return current_volume >= (prior_volume * 0.7)

    def generate_signal(self, 
                       price_data: Dict[str, float], 
                       prior_price_data: Dict[str, float],
                       resistance: float, 
                       support: float,
                       regime: str,
                       base_range: float,
                       trend_shift: float) -> Optional[Dict]:
        """
        Generates trade signal if all conditions are met.
        """
        if regime == "REGIME_C":
            return None  # Mean reversion disabled in Established Trend

        current_price = price_data['close']
        
        # Counter-Trend Short
        if current_price >= resistance:
            if self.check_rejection_candle(price_data['open'], price_data['high'], 
                                         price_data['low'], current_price, "SHORT"):
                if self.check_volume_filter(price_data['volume'], prior_price_data['volume']):
                    # Calculate Target & SL
                    # Target = Resistance - (R + 0.4 * |T|)
                    target = resistance - (base_range + self.config.TARGET_TREND_MULT * abs(trend_shift))
                    stop_loss = price_data['high'] + (0.001 * current_price) # Small buffer above high
                    
                    return {
                        "side": "SHORT",
                        "entry": current_price,
                        "target": target,
                        "stop_loss": stop_loss,
                        "reason": "Resistance Rejection"
                    }

        # Counter-Trend Long
        if current_price <= support:
            if self.check_rejection_candle(price_data['open'], price_data['high'], 
                                         price_data['low'], current_price, "LONG"):
                if self.check_volume_filter(price_data['volume'], prior_price_data['volume']):
                    # Target = Support + (R + 0.4 * |T|)
                    target = support + (base_range + self.config.TARGET_TREND_MULT * abs(trend_shift))
                    stop_loss = price_data['low'] - (0.001 * current_price)
                    
                    return {
                        "side": "LONG",
                        "entry": current_price,
                        "target": target,
                        "stop_loss": stop_loss,
                        "reason": "Support Rejection"
                    }

        return None
