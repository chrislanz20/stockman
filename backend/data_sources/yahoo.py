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

        current_price = 0
        previous_close = 0
        volume = 0
        name = ticker

        # Method 1: Try history first (most reliable for getting price)
        try:
            hist = stock.history(period="5d")
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
                if len(hist) > 1:
                    previous_close = float(hist['Close'].iloc[-2])
                else:
                    previous_close = current_price
                volume = int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0
        except Exception:
            pass

        # Method 2: Try fast_info (faster than info)
        try:
            fast = stock.fast_info
            if current_price == 0:
                current_price = getattr(fast, 'last_price', 0) or 0
            if previous_close == 0:
                previous_close = getattr(fast, 'previous_close', 0) or current_price
            if volume == 0:
                volume = getattr(fast, 'last_volume', 0) or 0
        except Exception:
            pass

        # Method 3: Try info dict (slowest but has most data)
        info = {}
        try:
            info = stock.info or {}
            if current_price == 0:
                current_price = (
                    info.get("currentPrice") or
                    info.get("regularMarketPrice") or
                    info.get("regularMarketPreviousClose") or
                    info.get("previousClose") or
                    0
                )
            if previous_close == 0:
                previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or current_price
            name = info.get("shortName", ticker)
        except Exception:
            pass

        # Ensure we have a previous_close for change calculation
        if previous_close == 0:
            previous_close = current_price

        change = current_price - previous_close if current_price and previous_close else 0
        change_pct = (change / previous_close * 100) if previous_close else 0

        return {
            "ticker": ticker,
            "name": name,
            "price": round(current_price, 2) if current_price else 0,
            "previous_close": round(previous_close, 2) if previous_close else 0,
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "volume": volume,
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
            "description": info.get("longBusinessSummary", "")[:500] if info.get("longBusinessSummary") else ""
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
