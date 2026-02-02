import os
import requests
import json

class NewsSentimentAnalyzer:
    """
    Aggregates news and uses AI (Gemini) for sentiment analysis.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        # Using v1 endpoint
        self.api_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={self.api_key}"

    def get_latest_news(self, symbol: str) -> str:
        """
        Simulates fetching latest news for a symbol.
        In a real app, use NewsAPI, Google News RSS, or similar.
        """
        # Mock news snippets
        mock_news = {
            "TCS": "TCS reports 15% growth in quarterly profit, beats street expectations.",
            "INFY": "Infosys expands partnership with Google Cloud for AI solutions.",
            "RELIANCE": "Reliance Retail continues aggressive expansion with new store openings.",
            "HDFCBANK": "HDFC Bank faces regulatory pressure on credit card growth."
        }
        return mock_news.get(symbol, f"Minor developments reported for {symbol} lately.")

    def get_sentiment_score(self, symbol: str) -> float:
        """
        Returns a sentiment score from -1 (Extremely Negative) to 1 (Extremely Positive).
        """
        if not self.api_key:
            return 0.5 # Neutral fallback

        news_text = self.get_latest_news(symbol)
        prompt = f"""
        Analyze the following news excerpt for {symbol} and provide a sentiment score between -1 and 1.
        News: {news_text}
        Return ONLY a JSON with 'sentiment_score' (float) and 'analysis' (short string).
        """

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=10)
            result = response.json()
            if 'candidates' not in result:
                return 0.5 # Neutral fallback on error

            text = result['candidates'][0]['content']['parts'][0]['text']
            clean_text = text.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_text)
            return data.get('sentiment_score', 0)
        except Exception as e:
            print(f"Sentiment analysis failed for {symbol}: {e}")
            return 0.0 # Neutral
