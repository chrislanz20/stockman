"""
Stockman - Yahoo Finance Data Source
Free, reliable source for price and fundamental data
"""

import yfinance as yf
from typing import Dict, Optional
import asyncio


class YahooFinanceSource:
    """Yahoo Finance data source"""

    async def get_quote(self, ticker: str) -> Dict:
        """Get current quote and basic info for a ticker"""
        try:
            # Run in executor since yfinance is synchronous
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._fetch_quote, ticker)
            return data
        except Exception as e:
            return {"error": str(e), "ticker": ticker}

    def _fetch_quote(self, ticker: str) -> Dict:
        """Synchronous fetch for Yahoo Finance"""
        stock = yf.Ticker(ticker)
        info = stock.info

        # Get current price data with multiple fallbacks
        current_price = (
            info.get("currentPrice") or
            info.get("regularMarketPrice") or
            info.get("regularMarketPreviousClose") or
            info.get("previousClose") or
            0
        )

        # If still no price, try history
        if current_price == 0:
            try:
                hist = stock.history(period="5d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
            except:
                pass

        previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or current_price

        change = current_price - previous_close if current_price and previous_close else 0
        change_pct = (change / previous_close * 100) if previous_close else 0

        return {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "price": current_price,
            "previous_close": previous_close,
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": info.get("volume", 0),
            "avg_volume": info.get("averageVolume", 0),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "high_52w": info.get("fiftyTwoWeekHigh"),
            "low_52w": info.get("fiftyTwoWeekLow"),
            "high_today": info.get("dayHigh"),
            "low_today": info.get("dayLow"),
            "open": info.get("open"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "description": info.get("longBusinessSummary", "")[:500]  # First 500 chars
        }

    async def get_history(self, ticker: str, period: str = "1mo") -> Dict:
        """Get historical price data"""
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, self._fetch_history, ticker, period
            )
            return data
        except Exception as e:
            return {"error": str(e), "ticker": ticker}

    def _fetch_history(self, ticker: str, period: str) -> Dict:
        """Synchronous fetch for historical data"""
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        if hist.empty:
            return {"ticker": ticker, "history": []}

        # Convert to list of dicts
        history = []
        for date, row in hist.iterrows():
            history.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"])
            })

        return {
            "ticker": ticker,
            "period": period,
            "history": history
        }

    async def get_financials(self, ticker: str) -> Dict:
        """Get financial statements"""
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._fetch_financials, ticker)
            return data
        except Exception as e:
            return {"error": str(e), "ticker": ticker}

    def _fetch_financials(self, ticker: str) -> Dict:
        """Synchronous fetch for financials"""
        stock = yf.Ticker(ticker)

        # Get income statement
        income = stock.income_stmt
        balance = stock.balance_sheet
        cash = stock.cashflow

        return {
            "ticker": ticker,
            "has_financials": not income.empty,
            "revenue": income.loc["Total Revenue"].iloc[0] if "Total Revenue" in income.index else None,
            "net_income": income.loc["Net Income"].iloc[0] if "Net Income" in income.index else None,
            "total_assets": balance.loc["Total Assets"].iloc[0] if "Total Assets" in balance.index else None,
            "total_debt": balance.loc["Total Debt"].iloc[0] if "Total Debt" in balance.index else None,
        }
