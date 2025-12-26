"""
Stockman - Memory & Context Management
Persistent storage for conversations, portfolio, and user preferences
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

# Use /tmp on Vercel (serverless), local data folder otherwise
# Check multiple Vercel indicators to be safe
IS_SERVERLESS = (
    os.environ.get('VERCEL') or
    os.environ.get('VERCEL_ENV') or
    os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or
    not os.path.exists(os.path.join(os.path.dirname(__file__), "../data"))
)

if IS_SERVERLESS:
    DATABASE_PATH = '/tmp/stockman.db'
else:
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), "../data/stockman.db")

class MemoryManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self._init_database()

    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self):
        """Initialize database tables"""
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Portfolio holdings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT UNIQUE NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT DEFAULT ''
            )
        """)

        # Conversation summaries (for long-term memory)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_of DATE NOT NULL,
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Trade history (what they bought/sold)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                shares REAL,
                price REAL,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Initialize profile if not exists
        cursor.execute("INSERT OR IGNORE INTO profile (id) VALUES (1)")

        conn.commit()
        conn.close()

    # ============== Profile ==============

    def get_profile(self) -> Dict:
        """Get user profile"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profile WHERE id = 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "name": row["name"],
                "created_at": row["created_at"],
                "preferences": json.loads(row["preferences"] or "{}")
            }
        return {"name": "Friend", "preferences": {}}

    def update_profile(self, name: str = None):
        """Update user profile"""
        conn = self._get_connection()
        cursor = conn.cursor()
        if name:
            cursor.execute("UPDATE profile SET name = ? WHERE id = 1", (name,))
        conn.commit()
        conn.close()

    def update_preferences(self, preferences: Dict):
        """Update user preferences"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Merge with existing preferences
        current = self.get_profile().get("preferences", {})
        current.update(preferences)

        cursor.execute(
            "UPDATE profile SET preferences = ? WHERE id = 1",
            (json.dumps(current),)
        )
        conn.commit()
        conn.close()

    # ============== Messages ==============

    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            (role, content)
        )
        conn.commit()
        conn.close()

    def get_recent_messages(self, limit: int = 30) -> List[Dict]:
        """Get recent conversation messages"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, timestamp FROM messages ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()

        # Return in chronological order
        messages = [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]} for r in rows]
        return list(reversed(messages))

    def get_message_count(self) -> int:
        """Get total message count"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # ============== Portfolio ==============

    def get_portfolio(self) -> List[Dict]:
        """Get current portfolio"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM portfolio ORDER BY ticker")
        rows = cursor.fetchall()
        conn.close()

        return [{
            "ticker": r["ticker"],
            "shares": r["shares"],
            "avg_price": r["avg_price"],
            "added_at": r["added_at"],
            "notes": r["notes"]
        } for r in rows]

    def add_to_portfolio(self, ticker: str, shares: float = 0, price: float = 0):
        """Add or update portfolio position"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO portfolio (ticker, shares, avg_price)
               VALUES (?, ?, ?)
               ON CONFLICT(ticker) DO UPDATE SET
               shares = shares + excluded.shares,
               avg_price = excluded.avg_price""",
            (ticker, shares or 0, price or 0)
        )

        conn.commit()
        conn.close()

    def remove_from_portfolio(self, ticker: str):
        """Remove stock from portfolio"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM portfolio WHERE ticker = ?", (ticker,))
        conn.commit()
        conn.close()

    # ============== Watchlist ==============

    def get_watchlist(self) -> List[Dict]:
        """Get current watchlist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM watchlist ORDER BY ticker")
        rows = cursor.fetchall()
        conn.close()

        return [{
            "ticker": r["ticker"],
            "added_at": r["added_at"],
            "notes": r["notes"]
        } for r in rows]

    def add_to_watchlist(self, ticker: str, notes: str = ""):
        """Add stock to watchlist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO watchlist (ticker, notes) VALUES (?, ?)",
            (ticker, notes)
        )
        conn.commit()
        conn.close()

    def remove_from_watchlist(self, ticker: str):
        """Remove stock from watchlist"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
        conn.commit()
        conn.close()

    # ============== Trade History ==============

    def log_trade(self, ticker: str, action: str, shares: float = None,
                  price: float = None, reason: str = None):
        """Log a trade action"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO trade_history (ticker, action, shares, price, reason)
               VALUES (?, ?, ?, ?, ?)""",
            (ticker, action, shares, price, reason)
        )
        conn.commit()
        conn.close()

    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Get trade history"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM trade_history ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [{
            "ticker": r["ticker"],
            "action": r["action"],
            "shares": r["shares"],
            "price": r["price"],
            "reason": r["reason"],
            "timestamp": r["timestamp"]
        } for r in rows]

    # ============== Summaries ==============

    def add_weekly_summary(self, summary: str):
        """Add weekly conversation summary"""
        conn = self._get_connection()
        cursor = conn.cursor()
        week_of = datetime.now().strftime("%Y-%m-%d")
        cursor.execute(
            "INSERT INTO summaries (week_of, summary) VALUES (?, ?)",
            (week_of, summary)
        )
        conn.commit()
        conn.close()

    def get_summaries(self, limit: int = 10) -> List[Dict]:
        """Get recent summaries"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM summaries ORDER BY week_of DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [{
            "week_of": r["week_of"],
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
