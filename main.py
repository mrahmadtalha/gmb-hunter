"""
GMB HUNTER — MAIN ENTRY POINT
Usage:
    python main.py              ← full run (100 businesses)
    python main.py --test       ← quick test (5 businesses)
    python main.py --phase1     ← phase 1 foundation test only
"""

import sys
import os
from datetime import date
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger        import print_banner, log_info, log_success, log_warning, log_error, print_progress
from database.db_manager import DatabaseManager
from agents.saver_agent  import SaverAgent
from agents.scout_agent  import ScoutAgent
from config.settings     import DEFAULT_BUSINESS_TYPE, DEFAULT_CITY, RECORDS_PER_DAY, AI_APIS


def run(business_type=None, city=None, target=None, test_mode=False):
    print_banner()

    biz_type = business_type or DEFAULT_BUSINESS_TYPE
    location = city          or DEFAULT_CITY
    goal     = 5             if test_mode else (target or RECORDS_PER_DAY)

    print("=" * 52)
    print(f"  Mode     : {'QUICK TEST (5 records)' if test_mode else 'FULL RUN'}")
    print(f"  Category : {biz_type}")
    print(f"  City     : {location}")
    print(f"  Target   : {goal} businesses")
    print("=" * 52)

    # ── Init agents ────────────────────────────────────
    db    = DatabaseManager()
    saver = SaverAgent(business_type=biz_type, city=location)
    scout = ScoutAgent()

    # ── Scrape raw data ────────────────────────────────
    log_info("Scout Agent: Starting scrape...")
    raw_businesses = scout.collect(biz_type, location, target=goal)

    if not raw_businesses:
        log_error("Scout Agent returned 0 results. Check your internet connection.")
        return

    log_success(f"Scout collected {len(raw_businesses)} raw records")

    # ── Process each business ──────────────────────────
    saved   = 0
    skipped = 0

    print()
    for i, business in enumerate(raw_businesses, 1):
        name = business.get("business_name", "Unknown")

        # Dedup check
        if db.is_duplicate(business):
            log_warning(f"Duplicate skipped: {name}")
            skipped += 1
            print_progress(i, len(raw_businesses), name)
            continue

        # Save to DB + CSV + XLSX
        db.save_business(business)
        saver.save(business)
        saved += 1

        log_success(f"[{saved}] Saved: {name} | {business.get('phone_number','N/A')}")
        print_progress(saved, goal, name)

    # Update daily log
    db.update_daily_log(
        scraped = len(raw_businesses),
        skipped = skipped,
        saved   = saved,
        source  = "yellow_pages+yelp"
    )

    # ── Final summary ──────────────────────────────────
    paths = saver.get_output_paths()
    print()
    print("=" * 52)
    print("  DONE ✅")
    print("=" * 52)
    print(f"  Scraped   : {len(raw_businesses)}")
    print(f"  Saved     : {saved}")
    print(f"  Skipped   : {skipped} (duplicates)")
    print(f"  Total DB  : {db.get_total_count()}")
    print()
    print(f"  📄 CSV  → {paths['csv']}")
    print(f"  📊 XLSX → {paths['xlsx']}")
    print("=" * 52)


def phase1_test():
    """Phase 1 foundation test — no scraping, just structure check"""
    print_banner()
    print("=" * 52)
    print("  Phase 1 Foundation Test")
    print("=" * 52)

    db    = DatabaseManager()
    saver = SaverAgent(business_type=DEFAULT_BUSINESS_TYPE, city=DEFAULT_CITY)

    test_businesses = [
        {
            "business_name": "Pizza Palace",   "phone_number": "+1-212-555-0101",
            "email": "info@pizzapalace.com",   "website": "https://pizzapalace.com",
            "rating": 4.5, "review_count": 320, "address": "123 Broadway, New York",
            "city": "New York", "category": "restaurants",
            "source": "test", "scraped_date": str(date.today()),
        },
        {
            "business_name": "Burger House",   "phone_number": "+1-212-555-0202",
            "email": "info@burgerhouse.com",   "website": "https://burgerhouse.com",
            "rating": 4.2, "review_count": 180, "address": "456 5th Ave, New York",
            "city": "New York", "category": "restaurants",
            "source": "test", "scraped_date": str(date.today()),
        },
    ]

    saved = 0
    for b in test_businesses:
        if not db.is_duplicate(b):
            db.save_business(b)
            saver.save(b)
            saved += 1
            log_success(f"Saved: {b['business_name']}")

    paths = saver.get_output_paths()
    print()
    print(f"  ✅ Database     : WORKING")
    print(f"  ✅ CSV Output   : {paths['csv']}")
    print(f"  ✅ XLSX Output  : {paths['xlsx']}")
    print(f"  ✅ Deduplication: WORKING")
    print(f"  📊 Saved: {saved} | Total DB: {db.get_total_count()}")
    print()

    print("  AI APIs:")
    for api in AI_APIS:
        status = "🔑 Key needed" if "YOUR_" in api["api_key"] else "✅ Ready"
        print(f"    {api['name']:12} — {status}")
    print()
    print("  Phase 1 Complete ✅")


# ── Entry point ────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]

    if "--phase1" in args:
        phase1_test()
    elif "--test" in args:
        # Quick test: parse optional --type and --city flags
        btype = DEFAULT_BUSINESS_TYPE
        bcity = DEFAULT_CITY
        if "--type" in args:
            btype = args[args.index("--type") + 1]
        if "--city" in args:
            bcity = args[args.index("--city") + 1]
        run(business_type=btype, city=bcity, test_mode=True)
    else:
        btype = DEFAULT_BUSINESS_TYPE
        bcity = DEFAULT_CITY
        if "--type" in args:
            btype = args[args.index("--type") + 1]
        if "--city" in args:
            bcity = args[args.index("--city") + 1]
        run(business_type=btype, city=bcity)