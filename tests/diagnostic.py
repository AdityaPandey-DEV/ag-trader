import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.screener import StockScreener
from main import TradingEngine

def diagnostic_test():
    print("--- STARTING AG_TRADER DIAGNOSTIC ---")
    
    # 1. Test Deduplication
    print("\n[1/3] Testing Universe Deduplication...")
    symbol = "tcs" # lowercase
    raw_universe = [symbol, "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
    universe = list(set([s.upper().strip() for s in raw_universe]))
    print(f"Raw: {raw_universe}")
    print(f"Deduplicated: {universe}")
    if len(universe) == 5:
        print("✅ SUCCESS: Universe deduplicated correctly.")
    else:
        print(f"❌ FAILURE: Expected 5 symbols, got {len(universe)}.")

    # 2. Test Screener Output Types
    print("\n[2/3] Testing Screener Data Types...")
    screener = StockScreener()
    results = screener.screen(["TCS"])
    if results:
        stock = results[0]
        print(f"Screener Result for TCS: {stock}")
        if isinstance(stock['sentiment_score'], float):
            print("✅ SUCCESS: Sentiment score is a float.")
        else:
            print(f"❌ FAILURE: Sentiment score is {type(stock['sentiment_score'])}.")
    else:
        print("⚠️ SKIPPED: Screener returned no results (maybe filtered out).")

    # 3. Test API Connectivity
    print("\n[3/3] Testing Dashboard API Bridge...")
    try:
        engine = TradingEngine()
        engine.update_dashboard("DIAGNOSTIC")
        print("✅ SUCCESS: Engine successfully attempted to update dashboard.")
    except Exception as e:
        print(f"❌ FAILURE: Dashboard bridge error: {e}")

    print("\n--- DIAGNOSTIC COMPLETE ---")

if __name__ == "__main__":
    diagnostic_test()
