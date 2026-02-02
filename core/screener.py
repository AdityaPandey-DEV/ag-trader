from utils.fundamental_analyzer import FundamentalAnalyzer
from utils.news_aggregator import NewsSentimentAnalyzer
from typing import List, Dict

class StockScreener:
    """
    Rules-based multi-factor stock screener.
    Combines Technical, Fundamental, and News filters.
    """
    def __init__(self, api_key: str = None):
        self.fundamentals = FundamentalAnalyzer()
        self.news = NewsSentimentAnalyzer(api_key=api_key)

    def screen(self, universe: List[str]) -> List[Dict]:
        """
        Screens a list of symbols and returns a sorted watchlist.
        """
        watchlist = []
        
        for symbol in universe:
            # 1. Fundamental Check
            fundamental_score = self.fundamentals.get_fundamental_score(symbol)
            if fundamental_score < 40: # Quality threshold
                continue
                
            # 2. News/Sentiment Check
            sentiment_score = self.news.get_sentiment_score(symbol)
            if sentiment_score < -0.2: # High negativity threshold
                continue
                
            # 3. Final Multi-factor Score
            # Weighting: 60% Fundamentals, 40% News Sentiment
            final_score = (fundamental_score * 0.6) + ((sentiment_score + 1) * 50 * 0.4)
            
            watchlist.append({
                "symbol": symbol,
                "score": float(round(final_score, 2)),
                "fundamental_score": float(fundamental_score),
                "sentiment_score": float(sentiment_score)
            })
            
        # Sort by score descending
        watchlist.sort(key=lambda x: x['score'], reverse=True)
        return watchlist

if __name__ == "__main__":
    screener = StockScreener()
    universe = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "ZOMATO"]
    top_stocks = screener.screen(universe)
    print("Watchlist for today:")
    for stock in top_stocks:
        print(f"{stock['symbol']}: Score {stock['score']} (Fund: {stock['fundamental_score']}, News: {stock['sentiment_score']})")
