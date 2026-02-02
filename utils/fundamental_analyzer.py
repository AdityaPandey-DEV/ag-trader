import random

class FundamentalAnalyzer:
    """
    Simulates fetching and scoring fundamental data.
    In a real system, this would use an API like Alpha Vantage, Yahoo Finance, or similar.
    """
    def __init__(self):
        # Mock database of fundamental data for demonstration
        self.mock_data = {
            "RELIANCE": {"pe": 25.5, "debt_to_equity": 0.4, "roe": 12.5},
            "TCS": {"pe": 30.1, "debt_to_equity": 0.1, "roe": 35.0},
            "HDFCBANK": {"pe": 18.5, "debt_to_equity": 0.8, "roe": 15.2},
            "INFY": {"pe": 24.0, "debt_to_equity": 0.05, "roe": 28.0},
            "ICICIBANK": {"pe": 16.0, "debt_to_equity": 0.9, "roe": 14.8},
        }

    def fetch_metrics(self, symbol: str) -> dict:
        # Returning mock data or random values for unknown symbols
        return self.mock_data.get(symbol, {
            "pe": random.uniform(10, 50),
            "debt_to_equity": random.uniform(0, 2),
            "roe": random.uniform(5, 30)
        })

    def get_fundamental_score(self, symbol: str) -> float:
        """
        Calculates a score from 0 to 100 based on fundamental health.
        Lower PE, lower Debt/Equity, and higher ROE are better.
        """
        metrics = self.fetch_metrics(symbol)
        
        # Scoring components (weights can be adjusted)
        pe_score = max(0, 100 - metrics['pe'] * 2) # PE < 50 is better
        de_score = max(0, 100 - metrics['debt_to_equity'] * 50) # D/E < 2 is better
        roe_score = min(100, metrics['roe'] * 3) # ROE > 33 is max
        
        final_score = (pe_score * 0.3) + (de_score * 0.3) + (roe_score * 0.4)
        return round(final_score, 2)

if __name__ == "__main__":
    fa = FundamentalAnalyzer()
    print(f"TCS Score: {fa.get_fundamental_score('TCS')}")
    print(f"RELIANCE Score: {fa.get_fundamental_score('RELIANCE')}")
