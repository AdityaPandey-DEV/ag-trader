from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Market Metrics
    BASE_RANGE_PERIOD: int = 20
    TREND_SHIFT_PERIOD: int = 20
    TREND_SHIFT_THRESHOLD_MULT: float = 0.7
    
    # Regime Thresholds
    REGIME_NEUTRAL_MAX_TSD: int = 1
    REGIME_TRANSITIONAL_MAX_TSD: int = 3
    
    # Risk Management
    MAX_TRADES_PER_SESSION: int = 3
    MAX_SESSION_DRAWDOWN_PCT: float = 1.5
    MAX_CONSECUTIVE_LOSSES: int = 2
    PER_TRADE_RISK_PCT: float = 0.5
    
    # Strategy
    TARGET_VOL_MULT: float = 1.0
    TARGET_TREND_MULT: float = 0.4
    
    # Broker Config
    DEFAULT_BROKER: str = "ZERODHA"  # Options: ZERODHA, DHAN, MOCK
    
    # Credentials (optional for mock, required for live)
    GEMINI_API_KEY: Optional[str] = None
    KITE_API_KEY: Optional[str] = None
    KITE_ACCESS_TOKEN: Optional[str] = None
    DHAN_CLIENT_ID: Optional[str] = None
    DHAN_ACCESS_TOKEN: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"

config = Settings()
