import os
import json
import requests

class AITrendAnalyzer:
    """
    Uses AI (e.g., Gemini) to confirm trend based on numerical data.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        # Using v1 endpoint which is more stable for general models
        self.api_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={self.api_key}"

    def confirm_trend(self, data_summary: str) -> bool:
        """
        Queries AI to confirm if the current conditions favor the trade.
        """
        if not self.api_key:
            print("AI API Key not found. Skipping AI confirmation (returning True).")
            return True

        prompt = f"""
        Act as a professional quant trader. Analyze the following stock data and confirm if a Mean Reversion Counter-Trend trade is advisable.
        Data: {data_summary}
        Return ONLY a JSON with 'confirmed' (bool) and 'reason' (string).
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
                print(f"AI Error: {result.get('error', {}).get('message', 'Unknown error')}")
                return True # Fallback

            # Extracting text response (simplified)
            text = result['candidates'][0]['content']['parts'][0]['text']
            # Parse JSON from markdown block if needed
            clean_text = text.replace('```json', '').replace('```', '').strip()
            analysis = json.loads(clean_text)
            print(f"AI Analysis: {analysis['reason']}")
            return analysis.get('confirmed', False)
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return True # Fallback to technicals only
