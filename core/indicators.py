import pandas as pd
import numpy as np

def calculate_base_range(high: pd.Series, low: pd.Series, period: int = 20) -> pd.Series:
    """
    R = SMA(High - Low, 20 periods)
    """
    return (high - low).rolling(window=period).mean()

def calculate_trend_shift_ema(close: pd.Series, period: int = 200) -> pd.Series:
    """
    T = slope of EMA(200)
    """
    ema = close.ewm(span=period, adjust=False).mean()
    return ema.diff()

def calculate_trend_shift_linreg(close: pd.Series, period: int = 20) -> pd.Series:
    """
    T = Linear regression slope of closing prices (20 periods)
    """
    def get_slope(y):
        x = np.arange(len(y))
        slope, _ = np.polyfit(x, y, 1)
        return slope
    
    return close.rolling(window=period).apply(get_slope, raw=True)

def update_tsd_count(current_tsd_count: int, trend_shift: float, base_range: float, threshold_mult: float = 0.7) -> int:
    """
    A trading day qualifies as a Trend Shift Day if: |T_day| > 0.7 * R_day
    Decay logic: If condition fails -> TSD_Count = max(0, TSD_Count - 1)
    """
    if abs(trend_shift) > threshold_mult * base_range:
        return current_tsd_count + 1
    else:
        return max(0, current_tsd_count - 1)

def get_regime(tsd_count: int) -> str:
    """
    Regime A: TSD_Count <= 1 (Range / Neutral)
    Regime B: TSD_Count in {2, 3} (Transitional / Emerging)
    Regime C: TSD_Count >= 4 (Established Trend)
    """
    if tsd_count <= 1:
        return "REGIME_A"
    elif 2 <= tsd_count <= 3:
        return "REGIME_B"
    else:
        return "REGIME_C"
