"""
LOGGER UTILITY
Clean, colored console output + saves to log files
"""

import os
import sys
import logging
from datetime import datetime, date

# Fix import path on Windows
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import LOG_DIR


os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, f"gmb_hunter_{date.today()}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("GMBHunter")


def log_info(msg):    logger.info(f"ℹ️  {msg}")
def log_success(msg): logger.info(f"✅ {msg}")
def log_warning(msg): logger.warning(f"⚠️  {msg}")
def log_error(msg):   logger.error(f"❌ {msg}")
def log_skip(msg):    logger.info(f"⏭️  SKIP: {msg}")
def log_save(msg):    logger.info(f"💾 SAVED: {msg}")
def log_api(msg):     logger.info(f"🤖 AI: {msg}")
def log_scrape(msg):  logger.info(f"🔍 SCRAPE: {msg}")


def print_banner():
    print("""
╔══════════════════════════════════════════════════╗
║         GMB HUNTER — AI Agent System             ║
║         Phase 1: Foundation Ready ✅              ║
╚══════════════════════════════════════════════════╝
    """)


def print_progress(current, total, business_name=""):
    bar_len   = 30
    filled    = int(bar_len * current / total) if total > 0 else 0
    bar       = "█" * filled + "░" * (bar_len - filled)
    pct       = int(100 * current / total) if total > 0 else 0
    name_str  = f" — {business_name[:30]}" if business_name else ""
    print(f"\r[{bar}] {pct}% ({current}/{total}){name_str}", end="", flush=True)
    if current >= total:
        print()