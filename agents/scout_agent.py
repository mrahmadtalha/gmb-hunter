"""
SCOUT AGENT (Agent 1)
The main scraper coordinator.

Controls:
- Which source to use (YellowPages → Yelp → fallback)
- Switches source if one gets blocked
- Collects raw business data
- Passes clean list to next agents
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.googlemaps_scraper  import GoogleMapsScraper
from agents.yellowpages_scraper import YellowPagesScraper
from agents.yelp_scraper        import YelpScraper
from utils.logger import log_info, log_success, log_warning, log_error, log_scrape
from config.settings import RECORDS_PER_DAY, SCRAPING_SOURCES


class ScoutAgent:
    """
    Coordinates all scrapers.
    Priority: Google Maps → YellowPages → Yelp
    If one source fails or gets blocked → auto switches to next.
    Collects until target number is reached.
    """

    def __init__(self):
        self.scrapers = {
            "google_maps":  GoogleMapsScraper(),
            "yellow_pages": YellowPagesScraper(),
            "yelp":         YelpScraper(),
        }
        self.source_priority = ["google_maps", "yellow_pages", "yelp"]
        self.current_source  = "google_maps"

    def _switch_source(self, failed_source: str) -> str | None:
        """Switch to next available source"""
        try:
            idx = self.source_priority.index(failed_source)
            if idx + 1 < len(self.source_priority):
                next_source = self.source_priority[idx + 1]
                log_warning(f"Switching from {failed_source} → {next_source}")
                return next_source
        except ValueError:
            pass
        log_error("All scraping sources exhausted!")
        return None

    def collect(self, business_type: str, city: str, target: int = None) -> list:
        """
        Main collection method.
        Tries each source until target number of businesses is reached.

        Returns: list of raw business dicts
        """
        if target is None:
            target = RECORDS_PER_DAY

        all_results    = []
        source         = self.current_source
        attempts       = 0
        max_attempts   = len(self.source_priority)

        log_info(f"Scout Agent starting → '{business_type}' in '{city}' | Target: {target}")

        while len(all_results) < target and attempts < max_attempts:
            scraper = self.scrapers.get(source)
            if not scraper:
                log_error(f"No scraper found for source: {source}")
                source = self._switch_source(source)
                if not source:
                    break
                attempts += 1
                continue

            try:
                needed  = target - len(all_results)
                log_scrape(f"Using {source.upper()} — need {needed} more records")

                results = scraper.scrape(
                    business_type = business_type,
                    city          = city,
                    max_results   = needed
                )

                if results:
                    all_results.extend(results)
                    log_success(f"{source}: collected {len(results)} — total now: {len(all_results)}")

                    if len(all_results) >= target:
                        break
                    else:
                        # Got some but not enough — try next source for remainder
                        log_warning(f"{source} only returned {len(results)}, need more. Trying next source...")
                        next_source = self._switch_source(source)
                        if next_source:
                            source = next_source
                        else:
                            break
                else:
                    log_warning(f"{source} returned 0 results. Switching source...")
                    next_source = self._switch_source(source)
                    if next_source:
                        source = next_source
                    else:
                        break

            except Exception as e:
                log_error(f"Scout error on {source}: {e}")
                next_source = self._switch_source(source)
                if next_source:
                    source = next_source
                else:
                    break

            attempts += 1

        log_success(f"Scout Agent done. Total raw records: {len(all_results)}")
        return all_results[:target]

    def quick_test(self, business_type: str, city: str, limit: int = 5) -> list:
        """
        Quick test — scrape just 5 businesses to verify everything works.
        Use this before running full 100-record scrape.
        """
        log_info(f"Quick test: {limit} businesses only")
        return self.collect(business_type, city, target=limit)


if __name__ == "__main__":
    agent   = ScoutAgent()
    results = agent.quick_test("restaurants", "Chicago", limit=3)
    print(f"\n--- RESULTS ({len(results)}) ---")
    for r in results:
        print(f"  {r.get('business_name')} | {r.get('phone_number')} | {r.get('address')}")