"""
Stockman - Data Aggregator
Combines data from multiple sources for comprehensive stock analysis
"""

import os
import asyncio
from typing import List, Dict
from datetime import datetime

# Import individual data sources
from .yahoo import YahooFinanceSource
from .finnhub import FinnhubSource
from .alpha_vantage import AlphaVantageSource
from .news import NewsSource


class DataAggregator:
    """Aggregates data from multiple sources"""

    def __init__(self):
        self.yahoo = YahooFinanceSource()
        self.finnhub = FinnhubSource(api_key=os.getenv("FINNHUB_API_KEY"))
        self.alpha_vantage = AlphaVantageSource(api_key=os.getenv("ALPHA_VANTAGE_API_KEY"))
        self.news = NewsSource()

    async def get_stock_data(self, tickers: List[str]) -> Dict:
        """Get comprehensive data for multiple tickers"""
        results = {}

        for ticker in tickers:
            try:
                # Get data from multiple sources in parallel
                yahoo_data, finnhub_data, news_data = await asyncio.gather(
                    self.yahoo.get_quote(ticker),
                    self.finnhub.get_quote(ticker),
                    self.news.get_news(ticker),
                    return_exceptions=True
                )

                # Combine data (prefer Yahoo for price, Finnhub for sentiment)
                combined = {
                    "ticker": ticker,
                    "timestamp": datetime.now().isoformat()
                }

                # Yahoo data (primary source for price/fundamentals)
                if isinstance(yahoo_data, dict):
                    combined.update({
                        "price": yahoo_data.get("price", 0),
                        "change": yahoo_data.get("change", 0),
                        "change_pct": yahoo_data.get("change_pct", 0),
                        "volume": yahoo_data.get("volume", 0),
                        "avg_volume": yahoo_data.get("avg_volume", 0),
                        "market_cap": yahoo_data.get("market_cap", 0),
                        "pe_ratio": yahoo_data.get("pe_ratio"),
                        "high_52w": yahoo_data.get("high_52w"),
                        "low_52w": yahoo_data.get("low_52w"),
                        "name": yahoo_data.get("name", ticker)
                    })

                # Finnhub data (sentiment, analyst ratings)
                if isinstance(finnhub_data, dict):
                    combined.update({
                        "analyst_rating": finnhub_data.get("analyst_rating"),
                        "target_price": finnhub_data.get("target_price"),
                        "sentiment_score": finnhub_data.get("sentiment_score")
                    })

                # News headlines
                if isinstance(news_data, list):
                    combined["news"] = news_data[:5]  # Top 5 headlines

                results[ticker] = combined

            except Exception as e:
                results[ticker] = {
                    "ticker": ticker,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

        return results

    async def calculate_opportunity_score(self, ticker: str) -> Dict:
        """
        Calculate opportunity score (1-100) based on multiple factors:
        - Momentum: Price vs moving averages, RSI
        - Volume: Current vs average (unusual activity)
        - Sentiment: News and social sentiment
        - Value: P/E ratio, fundamentals
        """

        try:
            # Get all data
            stock_data = await self.get_stock_data([ticker])
            data = stock_data.get(ticker, {})

            # Get technical indicators
            technicals = await self.alpha_vantage.get_technicals(ticker)

            scores = {
                "momentum": 50,
                "volume": 50,
                "sentiment": 50,
                "value": 50
            }

            # === Momentum Score ===
            # Based on price change and RSI
            change_pct = data.get("change_pct", 0)
            rsi = technicals.get("rsi", 50)

            # Positive momentum if price up and RSI not overbought
            if change_pct > 0 and rsi < 70:
                scores["momentum"] = min(50 + (change_pct * 5) + ((70 - rsi) / 2), 100)
            elif change_pct < 0 and rsi > 30:
                scores["momentum"] = max(50 + (change_pct * 5) - ((rsi - 30) / 2), 0)

            # === Volume Score ===
            # High volume = something is happening
            volume = data.get("volume", 0)
            avg_volume = data.get("avg_volume", 1)

            if avg_volume > 0:
                volume_ratio = volume / avg_volume
                if volume_ratio > 2:
                    scores["volume"] = min(70 + (volume_ratio * 5), 100)
                elif volume_ratio > 1:
                    scores["volume"] = 50 + (volume_ratio * 10)
                else:
                    scores["volume"] = volume_ratio * 50

            # === Sentiment Score ===
            sentiment = data.get("sentiment_score")
            if sentiment is not None:
                scores["sentiment"] = max(min(sentiment * 100, 100), 0)

            # News-based sentiment boost
            news = data.get("news", [])
            if news:
                # Simple: more news = more interest
                scores["sentiment"] = min(scores["sentiment"] + len(news) * 2, 100)

            # === Value Score ===
            pe_ratio = data.get("pe_ratio")
            if pe_ratio:
                # Lower P/E is generally better (for value)
                if pe_ratio < 15:
                    scores["value"] = 80
                elif pe_ratio < 25:
                    scores["value"] = 60
                elif pe_ratio < 40:
                    scores["value"] = 40
                else:
                    scores["value"] = 20

            # Calculate overall score (weighted average)
            overall = (
                scores["momentum"] * 0.25 +
                scores["volume"] * 0.25 +
                scores["sentiment"] * 0.25 +
                scores["value"] * 0.25
            )

            return {
                "ticker": ticker,
                "overall_score": round(overall),
                "breakdown": {
                    "momentum": round(scores["momentum"]),
                    "volume": round(scores["volume"]),
                    "sentiment": round(scores["sentiment"]),
                    "value": round(scores["value"])
                },
                "data": {
                    "price": data.get("price"),
                    "change_pct": change_pct,
                    "volume_ratio": round(volume / avg_volume, 2) if avg_volume > 0 else 0,
                    "rsi": rsi,
                    "pe_ratio": pe_ratio
                },
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "ticker": ticker,
                "error": str(e),
                "overall_score": 0
            }

    async def scan_opportunities(self, price_min: float = 4, price_max: float = 10,
                                  limit: int = 10) -> List[Dict]:
        """
        Scan for stock opportunities in a price range
        Returns top opportunities by score
        """
        # This would require a stock screener API
        # For now, return empty - user adds stocks manually
        return []
