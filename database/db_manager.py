"""
DATABASE AGENT
Handles all database operations:
- Create tables
- Save business records
- Check for duplicates
- Generate daily stats
"""

import sqlite3
import hashlib
import os
import sys
from datetime import datetime, date

# Fix import path on Windows
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_NAME, BUSINESS_FIELDS


class DatabaseManager:

    def __init__(self):
        os.makedirs("database", exist_ok=True)
        self.db_path = DB_NAME
        self.conn = None
        self.setup_database()

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def setup_database(self):
        """Create all tables if they don't exist"""
        conn = self.connect()
        cursor = conn.cursor()

        # Main businesses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint     TEXT UNIQUE NOT NULL,
                business_name   TEXT,
                phone_number    TEXT,
                email           TEXT,
                website         TEXT,
                rating          REAL,
                review_count    INTEGER,
                address         TEXT,
                city            TEXT,
                category        TEXT,
                source          TEXT,
                scraped_date    TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Daily scraping log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                log_date        TEXT NOT NULL,
                total_scraped   INTEGER DEFAULT 0,
                total_skipped   INTEGER DEFAULT 0,
                total_saved     INTEGER DEFAULT 0,
                ai_api_used     TEXT,
                source_used     TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # AI API usage tracker
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                api_name    TEXT NOT NULL,
                usage_date  TEXT NOT NULL,
                call_count  INTEGER DEFAULT 0,
                UNIQUE(api_name, usage_date)
            )
        """)

        conn.commit()
        conn.close()
        print("✅ Database ready:", self.db_path)

    def generate_fingerprint(self, business_data: dict) -> str:
        """
        Create a unique ID for each business.
        Uses name + phone or name + address to detect duplicates.
        """
        name  = str(business_data.get("business_name", "")).lower().strip()
        phone = str(business_data.get("phone_number",  "")).strip()
        addr  = str(business_data.get("address",       "")).lower().strip()

        unique_string = f"{name}|{phone}|{addr}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def is_duplicate(self, business_data: dict) -> bool:
        """Check if this business was already scraped before"""
        fingerprint = self.generate_fingerprint(business_data)
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM businesses WHERE fingerprint = ?",
            (fingerprint,)
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def save_business(self, business_data: dict) -> bool:
        """Save a new business record. Returns True if saved, False if duplicate."""
        if self.is_duplicate(business_data):
            return False

        fingerprint = self.generate_fingerprint(business_data)
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO businesses
                    (fingerprint, business_name, phone_number, email, website,
                     rating, review_count, address, city, category, source, scraped_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fingerprint,
                business_data.get("business_name"),
                business_data.get("phone_number"),
                business_data.get("email"),
                business_data.get("website"),
                business_data.get("rating"),
                business_data.get("review_count"),
                business_data.get("address"),
                business_data.get("city"),
                business_data.get("category"),
                business_data.get("source"),
                business_data.get("scraped_date", str(date.today())),
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_today_records(self) -> list:
        """Get all records scraped today"""
        today = str(date.today())
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM businesses WHERE scraped_date = ?",
            (today,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def get_total_count(self) -> int:
        """Get total number of businesses in database"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM businesses")
        result = cursor.fetchone()
        conn.close()
        return result["count"]

    def update_daily_log(self, scraped=0, skipped=0, saved=0, api="", source=""):
        """Update today's scraping stats"""
        today = str(date.today())
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM daily_log WHERE log_date = ?", (today,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE daily_log
                SET total_scraped = total_scraped + ?,
                    total_skipped = total_skipped + ?,
                    total_saved   = total_saved   + ?
                WHERE log_date = ?
            """, (scraped, skipped, saved, today))
        else:
            cursor.execute("""
                INSERT INTO daily_log (log_date, total_scraped, total_skipped, total_saved, ai_api_used, source_used)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (today, scraped, skipped, saved, api, source))

        conn.commit()
        conn.close()

    def track_api_usage(self, api_name: str) -> int:
        """Track how many times an API was called today. Returns today's count."""
        today = str(date.today())
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO api_usage (api_name, usage_date, call_count)
            VALUES (?, ?, 1)
            ON CONFLICT(api_name, usage_date) DO UPDATE SET
                call_count = call_count + 1
        """, (api_name, today))

        conn.commit()
        cursor.execute(
            "SELECT call_count FROM api_usage WHERE api_name=? AND usage_date=?",
            (api_name, today)
        )
        result = cursor.fetchone()
        conn.close()
        return result["call_count"] if result else 0

    def get_api_usage_today(self, api_name: str) -> int:
        """Get today's usage count for a specific API"""
        today = str(date.today())
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT call_count FROM api_usage WHERE api_name=? AND usage_date=?",
            (api_name, today)
        )
        result = cursor.fetchone()
        conn.close()
        return result["call_count"] if result else 0


if __name__ == "__main__":
    db = DatabaseManager()
    print(f"Total businesses in DB: {db.get_total_count()}")