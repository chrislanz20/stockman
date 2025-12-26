"""
Stockman - Morning Briefing Generator
Generates personalized daily briefings with life wisdom quotes
"""

import os
import json
import random
from datetime import datetime
from anthropic import Anthropic

# Life wisdom quotes - not stock related, about perspective and positivity
LIFE_QUOTES = [
    {"quote": "The happiness of your life depends upon the quality of your thoughts.", "author": "Marcus Aurelius"},
    {"quote": "What lies behind us and what lies before us are tiny matters compared to what lies within us.", "author": "Ralph Waldo Emerson"},
    {"quote": "The obstacle is the way.", "author": "Marcus Aurelius"},
    {"quote": "We suffer more often in imagination than in reality.", "author": "Seneca"},
    {"quote": "The best time to plant a tree was 20 years ago. The second best time is now.", "author": "Chinese Proverb"},
    {"quote": "It is not the man who has too little, but the man who craves more, that is poor.", "author": "Seneca"},
    {"quote": "You have power over your mind - not outside events. Realize this, and you will find strength.", "author": "Marcus Aurelius"},
    {"quote": "He who has a why to live can bear almost any how.", "author": "Friedrich Nietzsche"},
    {"quote": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"quote": "In the middle of difficulty lies opportunity.", "author": "Albert Einstein"},
    {"quote": "The wound is the place where the Light enters you.", "author": "Rumi"},
    {"quote": "Everything you've ever wanted is on the other side of fear.", "author": "George Addair"},
    {"quote": "The purpose of life is not to be happy. It is to be useful, to be honorable, to be compassionate.", "author": "Ralph Waldo Emerson"},
    {"quote": "What you get by achieving your goals is not as important as what you become by achieving your goals.", "author": "Zig Ziglar"},
    {"quote": "Waste no more time arguing about what a good man should be. Be one.", "author": "Marcus Aurelius"},
    {"quote": "The only impossible journey is the one you never begin.", "author": "Tony Robbins"},
    {"quote": "Your time is limited, don't waste it living someone else's life.", "author": "Steve Jobs"},
    {"quote": "Life is 10% what happens to you and 90% how you react to it.", "author": "Charles R. Swindoll"},
    {"quote": "The greatest glory in living lies not in never falling, but in rising every time we fall.", "author": "Nelson Mandela"},
    {"quote": "Very little is needed to make a happy life; it is all within yourself, in your way of thinking.", "author": "Marcus Aurelius"},
    {"quote": "The mind is everything. What you think you become.", "author": "Buddha"},
    {"quote": "Gratitude turns what we have into enough.", "author": "Anonymous"},
    {"quote": "Be yourself; everyone else is already taken.", "author": "Oscar Wilde"},
    {"quote": "The only limit to our realization of tomorrow is our doubts of today.", "author": "Franklin D. Roosevelt"},
    {"quote": "You must be the change you wish to see in the world.", "author": "Mahatma Gandhi"},
    {"quote": "It does not matter how slowly you go as long as you do not stop.", "author": "Confucius"},
    {"quote": "The secret of getting ahead is getting started.", "author": "Mark Twain"},
    {"quote": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt"},
    {"quote": "Everything has beauty, but not everyone sees it.", "author": "Confucius"},
    {"quote": "The journey of a thousand miles begins with one step.", "author": "Lao Tzu"},
]


class BriefingGenerator:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def get_daily_quote(self) -> dict:
        """Get a random life wisdom quote"""
        # Use date as seed for consistent daily quote
        today = datetime.now().strftime("%Y-%m-%d")
        random.seed(hash(today))
        quote = random.choice(LIFE_QUOTES)
        random.seed()  # Reset seed
        return quote

    async def generate_briefing(self, memory, data_aggregator) -> dict:
        """Generate the full morning briefing"""

        # Get quote of the day
        quote = self.get_daily_quote()

        # Get user context
        profile = memory.get_profile()
        portfolio = memory.get_portfolio()
        watchlist = memory.get_watchlist()

        # Get all tickers
        tickers = list(set(
            [s['ticker'] for s in portfolio] +
            [s['ticker'] for s in watchlist]
        ))

        # Get market data
        market_data = {}
        portfolio_summary = {"total_value": 0, "total_change": 0, "total_change_pct": 0}

        if tickers:
            market_data = await data_aggregator.get_stock_data(tickers)

            # Calculate portfolio performance
            total_value = 0
            total_cost = 0

            for holding in portfolio:
                ticker = holding['ticker']
                if ticker in market_data:
                    current_price = market_data[ticker].get('price', 0)
                    shares = holding['shares'] or 0
                    avg_price = holding['avg_price'] or current_price

                    current_value = current_price * shares
                    cost_basis = avg_price * shares

                    total_value += current_value
                    total_cost += cost_basis

            if total_cost > 0:
                portfolio_summary = {
                    "total_value": round(total_value, 2),
                    "total_change": round(total_value - total_cost, 2),
                    "total_change_pct": round(((total_value - total_cost) / total_cost) * 100, 2)
                }

        # Generate AI summary
        briefing_text = await self._generate_ai_summary(
            profile, portfolio, watchlist, market_data, portfolio_summary
        )

        return {
            "quote": quote,
            "portfolio_summary": portfolio_summary,
            "market_data": market_data,
            "briefing_text": briefing_text,
            "generated_at": datetime.now().isoformat(),
            "greeting": self._get_greeting(profile.get("name", "Friend"))
        }

    def _get_greeting(self, name: str) -> str:
        """Get time-appropriate greeting"""
        hour = datetime.now().hour
        if hour < 12:
            return f"Good morning, {name}!"
        elif hour < 17:
            return f"Good afternoon, {name}!"
        else:
            return f"Good evening, {name}!"

    async def _generate_ai_summary(self, profile, portfolio, watchlist,
                                    market_data, portfolio_summary) -> str:
        """Generate AI-powered briefing summary"""

        if not portfolio and not watchlist:
            return "Add some stocks to your portfolio or watchlist to get personalized briefings!"

        prompt = f"""Generate a brief, friendly morning stock briefing. Keep it concise (3-4 sentences max).

Portfolio Summary:
- Total Value: ${portfolio_summary.get('total_value', 0):,.2f}
- Change: ${portfolio_summary.get('total_change', 0):,.2f} ({portfolio_summary.get('total_change_pct', 0)}%)

Portfolio Holdings:
{json.dumps(portfolio, indent=2)}

Watchlist:
{json.dumps(watchlist, indent=2)}

Current Market Data:
{json.dumps(market_data, indent=2)}

Write a natural, conversational summary highlighting:
1. Overall portfolio performance (if they have holdings)
2. Any notable movers (up or down more than 3%)
3. One brief insight or thing to watch

Keep it warm and encouraging. No stock advice, just observations."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text
