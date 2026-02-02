import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from main import TradingEngine
from config.settings import config
import pandas as pd

def run_complex_test():
    print("=== STARTING COMPLEX INTEGRATION TEST ===")
    
    # 1. Initialize Engine
    try:
        engine = TradingEngine()
        print("[SUCCESS] Engine initialized.")
    except Exception as e:
        print(f"[FAILURE] Engine initialization failed: {e}")
        return

    # 2. Run Pre-market Screening
    universe = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "ZOMATO"]
    try:
        engine.run_pre_market(universe)
        if not engine.watchlist:
            print("[WARNING] Watchlist is empty. Check fundamental scores.")
        else:
            print(f"[SUCCESS] Screening complete. Top stock: {engine.watchlist[0]['symbol']}")
    except Exception as e:
        print(f"[FAILURE] Screening failed: {e}")
        return

    # 3. Simulate a Trade Tick
    if engine.watchlist:
        symbol = engine.watchlist[0]['symbol']
        print(f"--- Simulating tick for {symbol} ---")
        
        # Inject custom mock data to force a signal
        # resistance = 20100, current = 20100 (triggers short)
        # We need to make sure the target is far enough for tax calculator to pass
        engine.broker.get_market_data = lambda s, i: {
            "open": 20080, "high": 20120, "low": 20070, "close": 20100, "volume": 5000
        }
        
        # Override generate_signal to ensure a SHORT signal
        engine.strategy.generate_signal = lambda *args: {
            "side": "SHORT", "entry": 20100, "target": 20050, "stop_loss": 20130, "reason": "Test"
        }
        
        try:
            engine.run_tick(symbol)
            print("[SUCCESS] Tick simulation complete.")
        except Exception as e:
            print(f"[FAILURE] Tick simulation failed: {e}")
            return

    # 4. Check Risk Manager State
    print(f"Risk Consumed: {engine.risk_manager.current_drawdown}%")
    print(f"Session Trades: {len(engine.risk_manager.session_trades)}")
    
    print("=== INTEGRATION TEST COMPLETE ===")

if __name__ == "__main__":
    run_complex_test()
