"""
Stockman - Finnhub Data Source
News, sentiment, and analyst ratings
"""

import httpx
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class FinnhubSource:
    """Finnhub data source for news and sentiment"""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_quote(self, ticker: str) -> Dict:
        """Get current quote from Finnhub"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/quote",
                    params={"symbol": ticker, "token": self.api_key},
                    timeout=10.0
                )
                data = response.json()

                return {
                    "ticker": ticker,
                    "current": data.get("c", 0),
                    "change": data.get("d", 0),
                    "change_pct": data.get("dp", 0),
                    "high": data.get("h", 0),
                    "low": data.get("l", 0),
                    "open": data.get("o", 0),
                    "previous_close": data.get("pc", 0)
                }
        except Exception as e:
            return {"error": str(e), "ticker": ticker}

    async def get_news(self, ticker: str, days: int = 7) -> List[Dict]:
        """Get recent news for a ticker"""
        try:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            to_date = datetime.now().strftime("%Y-%m-%d")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/company-news",
                    params={
                        "symbol": ticker,
                        "from": from_date,
                        "to": to_date,
                        "token": self.api_key
                    },
                    timeout=10.0
                )
                news = response.json()

                if not isinstance(news, list):
                    return []

                return [{
                    "headline": item.get("headline", ""),
                    "summary": item.get("summary", "")[:200],
                    "source": item.get("source", ""),
                    "url": item.get("url", ""),
                    "datetime": datetime.fromtimestamp(
                        item.get("datetime", 0)
                    ).isoformat() if item.get("datetime") else None
                } for item in news[:10]]  # Top 10 articles

        except Exception as e:
            return []

    async def get_sentiment(self, ticker: str) -> Dict:
        """Get social sentiment for a ticker"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/stock/social-sentiment",
                    params={"symbol": ticker, "token": self.api_key},
                    timeout=10.0
                )
                data = response.json()

                # Aggregate sentiment
                reddit = data.get("reddit", [])
                twitter = data.get("twitter", [])

                total_mentions = 0
                positive = 0
                negative = 0

                for item in reddit + twitter:
                    total_mentions += item.get("mention", 0)
                    positive += item.get("positiveScore", 0)
                    negative += item.get("negativeScore", 0)

                sentiment_score = 0.5  # Neutral default
                if positive + negative > 0:
                    sentiment_score = positive / (positive + negative)

                return {
                    "ticker": ticker,
                    "sentiment_score": round(sentiment_score, 2),
                    "total_mentions": total_mentions,
                    "positive": positive,
                    "negative": negative
                }

        except Exception as e:
            return {"ticker": ticker, "sentiment_score": 0.5, "error": str(e)}

    async def get_analyst_ratings(self, ticker: str) -> Dict:
        """Get analyst recommendations"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/stock/recommendation",
                    params={"symbol": ticker, "token": self.api_key},
                    timeout=10.0
                )
                data = response.json()

                if not data:
                    return {"ticker": ticker, "analyst_rating": None}

                # Get most recent recommendation
                latest = data[0] if isinstance(data, list) and data else {}

                buy = latest.get("buy", 0) + latest.get("strongBuy", 0)
                hold = latest.get("hold", 0)
                sell = latest.get("sell", 0) + latest.get("strongSell", 0)
                total = buy + hold + sell

                rating = "Hold"
                if total > 0:
                    if buy / total > 0.6:
                        rating = "Strong Buy"
                    elif buy / total > 0.4:
                        rating = "Buy"
                    elif sell / total > 0.4:
                        rating = "Sell"

                return {
                    "ticker": ticker,
                    "analyst_rating": rating,
                    "buy_count": buy,
                    "hold_count": hold,
                    "sell_count": sell,
                    "period": latest.get("period")
                }

        except Exception as e:
            return {"ticker": ticker, "analyst_rating": None, "error": str(e)}

    async def get_price_target(self, ticker: str) -> Dict:
        """Get analyst price targets"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/stock/price-target",
                    params={"symbol": ticker, "token": self.api_key},
                    timeout=10.0
                )
                data = response.json()

                return {
                    "ticker": ticker,
                    "target_high": data.get("targetHigh"),
                    "target_low": data.get("targetLow"),
                    "target_mean": data.get("targetMean"),
                    "target_median": data.get("targetMedian")
                }

        except Exception as e:
            return {"ticker": ticker, "error": str(e)}
