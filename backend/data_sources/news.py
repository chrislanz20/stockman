"""
Stockman - News Aggregator
Pulls news from multiple free sources
"""

import feedparser
import httpx
from typing import List, Dict
from datetime import datetime
import asyncio


class NewsSource:
    """Aggregates news from multiple free sources"""

    async def get_news(self, ticker: str, limit: int = 10) -> List[Dict]:
        """Get news for a ticker from multiple sources"""
        try:
            # Gather from multiple sources in parallel
            google_news, yahoo_news = await asyncio.gather(
                self._get_google_news(ticker),
                self._get_yahoo_rss(ticker),
                return_exceptions=True
            )

            all_news = []

            if isinstance(google_news, list):
                all_news.extend(google_news)
            if isinstance(yahoo_news, list):
                all_news.extend(yahoo_news)

            # Sort by date and limit
            all_news.sort(key=lambda x: x.get("datetime", ""), reverse=True)
            return all_news[:limit]

        except Exception as e:
            return []

    async def _get_google_news(self, ticker: str) -> List[Dict]:
        """Get news from Google News RSS"""
        try:
            # Run feedparser in executor (it's synchronous)
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(
                None,
                feedparser.parse,
                f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
            )

            news = []
            for entry in feed.entries[:10]:
                news.append({
                    "headline": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:200] if entry.get("summary") else "",
                    "source": "Google News",
                    "url": entry.get("link", ""),
                    "datetime": entry.get("published", "")
                })

            return news

        except Exception as e:
            return []

    async def _get_yahoo_rss(self, ticker: str) -> List[Dict]:
        """Get news from Yahoo Finance RSS"""
        try:
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(
                None,
                feedparser.parse,
                f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
            )

            news = []
            for entry in feed.entries[:10]:
                news.append({
                    "headline": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:200] if entry.get("summary") else "",
                    "source": "Yahoo Finance",
                    "url": entry.get("link", ""),
                    "datetime": entry.get("published", "")
                })

            return news

        except Exception as e:
            return []

    async def get_market_news(self, limit: int = 10) -> List[Dict]:
        """Get general market news"""
        try:
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(
                None,
                feedparser.parse,
                "https://news.google.com/rss/search?q=stock+market&hl=en-US&gl=US&ceid=US:en"
            )

            news = []
            for entry in feed.entries[:limit]:
                news.append({
                    "headline": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:200] if entry.get("summary") else "",
                    "source": "Google News",
                    "url": entry.get("link", ""),
                    "datetime": entry.get("published", "")
                })

            return news

        except Exception as e:
            return []
