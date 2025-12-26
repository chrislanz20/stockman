"""
Stockman - Morning Briefing Generator
Generates personalized daily briefings with life wisdom quotes
"""

import os
import json
import random
from datetime import datetime
from anthropic import Anthropic

# Perspective-shifting wisdom - thoughts that make you pause and think
WISDOM_QUOTES = [
    {"quote": "A year from now, you'll wish you had started today. But here's the thing - today you can actually start.", "author": ""},
    {"quote": "The days are long but the decades are short. Don't postpone joy waiting for the 'right time.'", "author": ""},
    {"quote": "Everyone you meet is fighting a battle you know nothing about. Be kind. Always.", "author": ""},
    {"quote": "You're not stuck. You're just committed to patterns that no longer serve you. And patterns can change.", "author": ""},
    {"quote": "The person you'll be in 5 years is based on the books you read and the people you spend time with today.", "author": ""},
    {"quote": "Worrying is paying interest on a debt you may never owe.", "author": ""},
    {"quote": "Most of what we stress about won't matter in 5 years. Focus on what will.", "author": ""},
    {"quote": "The cost of not following your heart is spending the rest of your life wishing you had.", "author": ""},
    {"quote": "You can't go back and change the beginning, but you can start where you are and change the ending.", "author": ""},
    {"quote": "Every expert was once a beginner. Every master was once a disaster. Keep going.", "author": ""},
    {"quote": "Your children won't remember the size of your house. They'll remember the size of your presence.", "author": ""},
    {"quote": "The things you own end up owning you. Travel light through life.", "author": ""},
    {"quote": "At the end of life, nobody wishes they had worked more. Invest in what actually matters.", "author": ""},
    {"quote": "You're not behind. You're not ahead. You're exactly where you need to be. Just don't stop.", "author": ""},
    {"quote": "The quality of your life is determined by the quality of the questions you ask yourself.", "author": ""},
    {"quote": "Fear kills more dreams than failure ever will. The things you don't try are the only guaranteed failures.", "author": ""},
    {"quote": "Comparison is the thief of joy. Run your own race.", "author": ""},
    {"quote": "Your potential future self is watching you right now through your memories. Make them proud.", "author": ""},
    {"quote": "The present moment is the only moment you have direct access to. Don't waste it.", "author": ""},
    {"quote": "Nothing changes if nothing changes. You have to do something different to get something different.", "author": ""},
    {"quote": "People will forget what you said. They'll forget what you did. But they'll never forget how you made them feel.", "author": ""},
    {"quote": "You can't pour from an empty cup. Take care of yourself first.", "author": ""},
    {"quote": "Growth is uncomfortable. Staying the same is uncomfortable. Choose the discomfort that leads somewhere.", "author": ""},
    {"quote": "The best view comes after the hardest climb. You're closer to the top than you think.", "author": ""},
    {"quote": "Don't let the fear of the time it takes stop you. The time will pass anyway.", "author": ""},
    {"quote": "Your peace is more important than proving a point. Let things go.", "author": ""},
    {"quote": "Sometimes the bravest thing you can do is ask for help.", "author": ""},
    {"quote": "Life becomes easier when you accept the apology you never received.", "author": ""},
    {"quote": "You don't have to attend every argument you're invited to.", "author": ""},
    {"quote": "The energy you bring to a room matters more than what you say when you get there.", "author": ""},
]


class BriefingGenerator:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def get_daily_quote(self) -> dict:
        """Get a random perspective-shifting wisdom quote"""
        # Use date as seed for consistent daily quote
        today = datetime.now().strftime("%Y-%m-%d")
        random.seed(hash(today))
        quote = random.choice(WISDOM_QUOTES)
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
