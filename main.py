"""
GMB HUNTER — MAIN ENTRY POINT
Usage:
    python main.py                                    <- full run (100 businesses)
    python main.py --test                             <- quick test (5 businesses)
    python main.py --test --type dentists --city Lahore
    python main.py --type restaurants --city "Dera Ghazi Khan"
    python main.py --phase1                           <- foundation test only
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logger        import print_banner, log_info, log_success, log_warning, log_error, print_progress
from database.db_manager import DatabaseManager
from agents.saver_agent  import SaverAgent
from agents.scout_agent  import ScoutAgent
from agents.detail_agent import DetailAgent
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

    db     = DatabaseManager()
    saver  = SaverAgent(business_type=biz_type, city=location)
    scout  = ScoutAgent()
    detail = DetailAgent()

    # ── Step 1: Scrape basic data ──────────────────────
    log_info("Step 1/3 — Scout Agent: scraping business listings...")
    raw_businesses = scout.collect(biz_type, location, target=goal)

    if not raw_businesses:
        log_error("Scout Agent returned 0 results. Check internet connection.")
        return

    log_success(f"Scout collected {len(raw_businesses)} raw records")

    # ── Step 2: Enrich with phone, reviews, email ──────
    log_info("Step 2/3 — Detail Agent: extracting phone, reviews, email...")
    enriched_businesses = detail.enrich_all(raw_businesses)
    log_success(f"Detail Agent enriched {len(enriched_businesses)} records")

    # ── Step 3: Dedup check + save ─────────────────────
    log_info("Step 3/3 — Saving to database, CSV and XLSX...")
    saved   = 0
    skipped = 0

    print()
    for i, business in enumerate(enriched_businesses, 1):
        name = business.get("business_name", "Unknown")

        if db.is_duplicate(business):
            log_warning(f"Duplicate skipped: {name}")
            skipped += 1
            continue

        db.save_business(business)
        saver.save(business)
        saved += 1
        print_progress(saved, goal, name)

    db.update_daily_log(
        scraped = len(raw_businesses),
        skipped = skipped,
        saved   = saved,
        source  = "google_maps"
    )

    paths = saver.get_output_paths()
    print()
    print("=" * 52)
    print("  DONE ✅")
    print("=" * 52)
    print(f"  Scraped   : {len(raw_businesses)}")
    print(f"  Enriched  : {len(enriched_businesses)}")
    print(f"  Saved     : {saved}")
    print(f"  Skipped   : {skipped} (duplicates)")
    print(f"  Total DB  : {db.get_total_count()}")
    print()
    print(f"  📄 CSV  → {paths['csv']}")
    print(f"  📊 XLSX → {paths['xlsx']}")
    print("=" * 52)


def phase1_test():
    print_banner()
    print("=" * 52)
    print("  Phase 1 Foundation Test")
    print("=" * 52)
    db    = DatabaseManager()
    saver = SaverAgent(business_type=DEFAULT_BUSINESS_TYPE, city=DEFAULT_CITY)
    test_businesses = [
        {
            "business_name": "Test Restaurant",  "phone_number": "+92-64-123-4567",
            "email": "info@test.com",            "website": "https://test.com",
            "rating": 4.5, "review_count": 320,  "address": "Main Bazar, Test City",
            "city": DEFAULT_CITY, "category": DEFAULT_BUSINESS_TYPE,
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
    print(f"  ✅ Database     : WORKING")
    print(f"  ✅ CSV Output   : {paths['csv']}")
    print(f"  ✅ XLSX Output  : {paths['xlsx']}")
    print(f"  📊 Saved: {saved} | Total DB: {db.get_total_count()}")
    print()
    print("  AI APIs Configured:")
    for api in AI_APIS:
        status = "🔑 Key needed" if "YOUR_" in api["api_key"] else "✅ Ready"
        print(f"    {api['name']:12} — {status}")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--phase1" in args:
        phase1_test()
    else:
        btype = DEFAULT_BUSINESS_TYPE
        bcity = DEFAULT_CITY
        if "--type" in args:
            idx   = args.index("--type")
            btype = args[idx + 1]
        if "--city" in args:
            idx   = args.index("--city")
            bcity = args[idx + 1]
        run(
            business_type = btype,
            city          = bcity,
            test_mode     = "--test" in args
        )