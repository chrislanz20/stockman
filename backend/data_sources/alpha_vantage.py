"""
Stockman - Alpha Vantage Data Source
Technical indicators and additional market data
"""

import httpx
from typing import Dict, Optional


class AlphaVantageSource:
    """Alpha Vantage data source for technical indicators"""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_quote(self, ticker: str) -> Dict:
        """Get global quote"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": ticker,
                        "apikey": self.api_key
                    },
                    timeout=10.0
                )
                data = response.json()
                quote = data.get("Global Quote", {})

                return {
                    "ticker": ticker,
                    "price": float(quote.get("05. price", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_pct": quote.get("10. change percent", "0%").replace("%", ""),
                    "volume": int(quote.get("06. volume", 0)),
                    "previous_close": float(quote.get("08. previous close", 0))
                }

        except Exception as e:
            return {"ticker": ticker, "error": str(e)}

    async def get_technicals(self, ticker: str) -> Dict:
        """Get technical indicators (RSI, SMA, etc.)"""
        try:
            # Get RSI
            rsi_data = await self._get_rsi(ticker)

            # Get SMA (20-day and 50-day)
            sma_20 = await self._get_sma(ticker, 20)
            sma_50 = await self._get_sma(ticker, 50)

            return {
                "ticker": ticker,
                "rsi": rsi_data.get("rsi"),
                "sma_20": sma_20.get("sma"),
                "sma_50": sma_50.get("sma"),
                "rsi_signal": self._interpret_rsi(rsi_data.get("rsi")),
                "trend": self._interpret_trend(sma_20.get("sma"), sma_50.get("sma"))
            }

        except Exception as e:
            return {"ticker": ticker, "error": str(e), "rsi": 50}

    async def _get_rsi(self, ticker: str, period: int = 14) -> Dict:
        """Get RSI indicator"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "function": "RSI",
                        "symbol": ticker,
                        "interval": "daily",
                        "time_period": period,
                        "series_type": "close",
                        "apikey": self.api_key
                    },
                    timeout=10.0
                )
                data = response.json()

                # Get most recent RSI value
                technical_data = data.get("Technical Analysis: RSI", {})
                if technical_data:
                    latest_date = list(technical_data.keys())[0]
                    rsi_value = float(technical_data[latest_date].get("RSI", 50))
                    return {"rsi": round(rsi_value, 2)}

                return {"rsi": 50}  # Default neutral

        except Exception as e:
            return {"rsi": 50, "error": str(e)}

    async def _get_sma(self, ticker: str, period: int) -> Dict:
        """Get Simple Moving Average"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "function": "SMA",
                        "symbol": ticker,
                        "interval": "daily",
                        "time_period": period,
                        "series_type": "close",
                        "apikey": self.api_key
                    },
                    timeout=10.0
                )
                data = response.json()

                technical_data = data.get(f"Technical Analysis: SMA", {})
                if technical_data:
                    latest_date = list(technical_data.keys())[0]
                    sma_value = float(technical_data[latest_date].get("SMA", 0))
                    return {"sma": round(sma_value, 2)}

                return {"sma": None}

        except Exception as e:
            return {"sma": None, "error": str(e)}

    def _interpret_rsi(self, rsi: Optional[float]) -> str:
        """Interpret RSI value"""
        if rsi is None:
            return "Unknown"
        if rsi >= 70:
            return "Overbought"
        elif rsi <= 30:
            return "Oversold"
        elif rsi >= 60:
            return "Bullish"
        elif rsi <= 40:
            return "Bearish"
        return "Neutral"

    def _interpret_trend(self, sma_20: Optional[float], sma_50: Optional[float]) -> str:
        """Interpret trend based on moving averages"""
        if sma_20 is None or sma_50 is None:
            return "Unknown"
        if sma_20 > sma_50:
            return "Uptrend"
        elif sma_20 < sma_50:
            return "Downtrend"
        return "Sideways"

    async def get_overview(self, ticker: str) -> Dict:
        """Get company overview/fundamentals"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "function": "OVERVIEW",
                        "symbol": ticker,
                        "apikey": self.api_key
                    },
                    timeout=10.0
                )
                data = response.json()

                return {
                    "ticker": ticker,
                    "name": data.get("Name"),
                    "description": data.get("Description", "")[:500],
                    "sector": data.get("Sector"),
                    "industry": data.get("Industry"),
                    "market_cap": data.get("MarketCapitalization"),
                    "pe_ratio": data.get("PERatio"),
                    "peg_ratio": data.get("PEGRatio"),
                    "book_value": data.get("BookValue"),
                    "dividend_yield": data.get("DividendYield"),
                    "eps": data.get("EPS"),
                    "revenue_ttm": data.get("RevenueTTM"),
                    "profit_margin": data.get("ProfitMargin"),
                    "52_week_high": data.get("52WeekHigh"),
                    "52_week_low": data.get("52WeekLow"),
                    "analyst_target": data.get("AnalystTargetPrice")
                }

        except Exception as e:
            return {"ticker": ticker, "error": str(e)}
