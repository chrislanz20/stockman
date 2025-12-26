"""
Stockman - Memory & Context Management
Persistent storage using Supabase PostgreSQL
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# Get database URL from environment
DATABASE_URL = os.environ.get('POSTGRES_URL') or os.environ.get('DATABASE_URL')

class MemoryManager:
    def __init__(self):
        self._init_database()

    def _get_connection(self):
        """Get database connection"""
        if not DATABASE_URL:
            raise Exception("POSTGRES_URL environment variable not set")
        conn = psycopg2.connect(DATABASE_URL)
        return conn

    def _init_database(self):
        """Initialize database tables"""
        if not DATABASE_URL:
            print("Warning: POSTGRES_URL not set, database operations will fail")
            return

        conn = self._get_connection()
        cursor = conn.cursor()

        # User profile
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY DEFAULT 1,
                name TEXT DEFAULT 'Friend',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                preferences TEXT DEFAULT '{}'
            )
        """)

        # Conversation history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Portfolio holdings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id SERIAL PRIMARY KEY,
                ticker TEXT UNIQUE NOT NULL,
                shares REAL DEFAULT 0,
                avg_price REAL DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT DEFAULT ''
            )
        """)

        # Watchlist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id SERIAL PRIMARY KEY,
                ticker TEXT UNIQUE NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT DEFAULT ''
            )
        """)

        # Conversation summaries (for long-term memory)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id SERIAL PRIMARY KEY,
                week_of DATE NOT NULL,
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Trade history (what they bought/sold)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id SERIAL PRIMARY KEY,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                shares REAL,
                price REAL,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Initialize profile if not exists
        cursor.execute("""
            INSERT INTO profile (id, name)
            VALUES (1, 'Friend')
            ON CONFLICT (id) DO NOTHING
        """)

        conn.commit()
        cursor.close()
        conn.close()

    # ============== Profile ==============

    def get_profile(self) -> Dict:
        """Get user profile"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM profile WHERE id = 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            return {
                "name": row["name"],
                "created_at": str(row["created_at"]) if row["created_at"] else None,
                "preferences": json.loads(row["preferences"] or "{}")
            }
        return {"name": "Friend", "preferences": {}}

    def update_profile(self, name: str = None):
        """Update user profile"""
        conn = self._get_connection()
        cursor = conn.cursor()
        if name:
            cursor.execute("UPDATE profile SET name = %s WHERE id = 1", (name,))
        conn.commit()
        cursor.close()
        conn.close()

    def update_preferences(self, preferences: Dict):
        """Update user preferences"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Merge with existing preferences
        current = self.get_profile().get("preferences", {})
        current.update(preferences)

        cursor.execute(
            "UPDATE profile SET preferences = %s WHERE id = 1",
            (json.dumps(current),)
        )
        conn.commit()
        cursor.close()
        conn.close()

    # ============== Messages ==============

    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (role, content) VALUES (%s, %s)",
            (role, content)
        )
        conn.commit()
        cursor.close()
        conn.close()

    def get_recent_messages(self, limit: int = 30) -> List[Dict]:
        """Get recent conversation messages"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT role, content, timestamp FROM messages ORDER BY timestamp DESC LIMIT %s",
            (limit,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Return in chronological order
        messages = [{"role": r["role"], "content": r["content"], "timestamp": str(r["timestamp"])} for r in rows]
        return list(reversed(messages))

    def get_message_count(self) -> int:
        """Get total message count"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count

    # ============== Portfolio ==============

    def get_portfolio(self) -> List[Dict]:
        """Get current portfolio"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM portfolio ORDER BY ticker")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return [{
            "ticker": r["ticker"],
            "shares": r["shares"],
            "avg_price": r["avg_price"],
            "added_at": str(r["added_at"]) if r["added_at"] else None,
            "notes": r["notes"]
        } for r in rows]

    def add_to_portfolio(self, ticker: str, shares: float = 0, price: float = 0):
        """Add or update portfolio position"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO portfolio (ticker, shares, avg_price)
               VALUES (%s, %s, %s)
               ON CONFLICT(ticker) DO UPDATE SET
               shares = portfolio.shares + EXCLUDED.shares,
               avg_price = EXCLUDED.avg_price""",
            (ticker, shares or 0, price or 0)
        )

        conn.commit()
        cursor.close()
        conn.close()

    def remove_from_portfolio(self, ticker: str):
        """Remove stock from portfolio"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM portfolio WHERE ticker = %s", (ticker,))
        conn.commit()
        cursor.close()
        conn.close()

    # ============== Watchlist ==============

    def get_watchlist(self) -> List[Dict]:
        """Get current watchlist"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM watchlist ORDER BY ticker")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return [{
            "ticker": r["ticker"],
            "added_at": str(r["added_at"]) if r["added_at"] else None,
            "notes": r["notes"]
        } for r in rows]

    def add_to_watchlist(self, ticker: str, notes: str = ""):
        """Add stock to watchlist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO watchlist (ticker, notes) VALUES (%s, %s)
               ON CONFLICT (ticker) DO NOTHING""",
            (ticker, notes)
        )
        conn.commit()
        cursor.close()
        conn.close()

    def remove_from_watchlist(self, ticker: str):
        """Remove stock from watchlist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE ticker = %s", (ticker,))
        conn.commit()
        cursor.close()
        conn.close()

    # ============== Trade History ==============

    def log_trade(self, ticker: str, action: str, shares: float = None,
                  price: float = None, reason: str = None):
        """Log a trade action"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO trade_history (ticker, action, shares, price, reason)
               VALUES (%s, %s, %s, %s, %s)""",
            (ticker, action, shares, price, reason)
        )
        conn.commit()
        cursor.close()
        conn.close()

    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT * FROM trade_history ORDER BY timestamp DESC LIMIT %s",
            (limit,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return [{
            "ticker": r["ticker"],
            "action": r["action"],
            "shares": r["shares"],
            "price": r["price"],
            "reason": r["reason"],
            "timestamp": str(r["timestamp"]) if r["timestamp"] else None
        } for r in rows]

    # ============== Summaries ==============

    def add_weekly_summary(self, summary: str):
        """Add weekly conversation summary"""
        conn = self._get_connection()
        cursor = conn.cursor()
        week_of = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "INSERT INTO summaries (week_of, summary) VALUES (%s, %s)",
            (week_of, summary)
        )
        conn.commit()
        cursor.close()
        conn.close()

    def get_summaries(self, limit: int = 10) -> List[Dict]:
        """Get recent summaries"""
        conn = self._get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT * FROM summaries ORDER BY week_of DESC LIMIT %s",
            (limit,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return [{
            "week_of": str(r["week_of"]) if r["week_of"] else None,
            "summary": r["summary"]
        } for r in rows]

    # ============== Full Context ==============

    def get_full_context(self) -> Dict:
        """Get full context for AI prompt"""
        return {
            "profile": self.get_profile(),
            "recent_messages": self.get_recent_messages(30),
            "portfolio": self.get_portfolio(),
            "watchlist": self.get_watchlist(),
            "preferences": self.get_profile().get("preferences", {}),
            "summaries": self.get_summaries(5),
            "trade_history": self.get_trade_history(20)
        }
