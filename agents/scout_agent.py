"""
SCOUT AGENT (Agent 1) — Grid Search Version
Uses geographic grid to systematically cover any city worldwide.
Works for ANY business type: restaurants, doctors, schools,
real estate, tech companies, medical, etc.

No hardcoded city names or areas needed.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.googlemaps_scraper  import GoogleMapsScraper
from agents.yellowpages_scraper import YellowPagesScraper
from agents.yelp_scraper        import YelpScraper
from utils.grid_search          import get_grid_for_city
from utils.logger import log_info, log_success, log_warning, log_error, log_scrape
from config.settings import RECORDS_PER_DAY


class ScoutAgent:
    """
    Universal city grid scraper.

    How it works:
    1. Gets city bounding box from OpenStreetMap (free)
    2. Divides city into NxN grid cells
    3. Searches each grid cell on Google Maps using coordinates
    4. Combines + deduplicates all results
    5. Falls back to YellowPages/Yelp if needed

    Works for ANY city + ANY business type worldwide.
    """

    def __init__(self):
        self.gmaps_scraper = GoogleMapsScraper()
        self.scrapers = {
            "yellow_pages": YellowPagesScraper(),
            "yelp":         YelpScraper(),
        }

    def _deduplicate(self, businesses: list) -> list:
        """Remove duplicates by business name fingerprint"""
        seen   = set()
        unique = []
        for biz in businesses:
            name = biz.get("business_name", "").lower().strip()
            # Use first 30 chars of name as key
            key  = name[:30]
            if key and key not in seen:
                seen.add(key)
                unique.append(biz)
        return unique

    def _collect_via_grid(self, business_type: str, city: str, target: int) -> list:
        """
        Main grid search method.
        Divides city into grid, searches each cell.
        """
        log_info(f"Grid Search: '{business_type}' in '{city}' | Target: {target}")

        # Get grid cells for this city
        cells = get_grid_for_city(city, target=target)

        if not cells:
            # Fallback: if grid fails, use simple city name search
            log_warning("Grid generation failed. Falling back to direct city search...")
            return self._collect_direct(business_type, city, target)

        all_results = []
        total_cells = len(cells)

        for i, cell in enumerate(cells, 1):
            if len(all_results) >= target:
                log_success(f"Target reached! Stopping grid search.")
                break

            needed = min(25, target - len(all_results))
            log_scrape(
                f"Cell {cell['cell']} ({i}/{total_cells}) | "
                f"@{cell['lat']},{cell['lng']} | Need {needed} more"
            )

            try:
                results = self.gmaps_scraper.scrape_by_coordinates(
                    business_type = business_type,
                    lat           = cell["lat"],
                    lng           = cell["lng"],
                    city          = city,
                    max_results   = needed,
                )

                if results:
                    before       = len(all_results)
                    all_results.extend(results)
                    all_results  = self._deduplicate(all_results)
                    added        = len(all_results) - before
                    log_success(
                        f"Cell {cell['cell']}: +{added} new | "
                        f"Total unique: {len(all_results)}/{target}"
                    )
                else:
                    log_warning(f"Cell {cell['cell']}: no results")

            except Exception as e:
                log_error(f"Grid cell error: {e}")
                continue

        return all_results

    def _collect_direct(self, business_type: str, city: str, target: int) -> list:
        """
        Fallback: simple direct search by city name.
        Used when grid generation fails.
        """
        log_scrape(f"Direct search: '{business_type}' in '{city}'")
        try:
            results = self.gmaps_scraper.scrape(
                business_type = business_type,
                city          = city,
                max_results   = target,
            )
            return results or []
        except Exception as e:
            log_error(f"Direct search error: {e}")
            return []

    def collect(self, business_type: str, city: str, target: int = None) -> list:
        """
        Main collection method — called by main.py.

        Args:
            business_type: anything — "restaurants", "dentists", "real estate",
                          "schools", "hospitals", "tech companies", etc.
            city: any city worldwide — "Lahore", "Chicago", "Dubai", etc.
            target: how many records to collect (default: from settings)

        Returns: list of business dicts
        """
        if target is None:
            target = RECORDS_PER_DAY

        log_info(f"Scout Agent → '{business_type}' in '{city}' | Target: {target}")

        # ── Step 1: Grid search on Google Maps ────────────
        all_results = self._collect_via_grid(business_type, city, target)
        log_success(f"Grid search complete: {len(all_results)} unique records")

        # ── Step 2: Top up with YellowPages if needed ─────
        if len(all_results) < target:
            needed = target - len(all_results)
            log_warning(f"Need {needed} more records. Trying YellowPages...")
            try:
                yp = self.scrapers["yellow_pages"].scrape(
                    business_type, city, max_results=needed
                )
                if yp:
                    all_results.extend(yp)
                    all_results = self._deduplicate(all_results)
                    log_success(f"YellowPages added. Total: {len(all_results)}")
            except Exception as e:
                log_error(f"YellowPages error: {e}")

        # ── Step 3: Top up with Yelp if still needed ──────
        if len(all_results) < target:
            needed = target - len(all_results)
            log_warning(f"Need {needed} more records. Trying Yelp...")
            try:
                yelp = self.scrapers["yelp"].scrape(
                    business_type, city, max_results=needed
                )
                if yelp:
                    all_results.extend(yelp)
                    all_results = self._deduplicate(all_results)
                    log_success(f"Yelp added. Total: {len(all_results)}")
            except Exception as e:
                log_error(f"Yelp error: {e}")

        final = all_results[:target]
        log_success(f"Scout Agent done. Final records: {len(final)}")
        return final

    def quick_test(self, business_type: str, city: str, limit: int = 5) -> list:
        log_info(f"Quick test: {limit} businesses only")
        return self.collect(business_type, city, target=limit)


if __name__ == "__main__":
    agent   = ScoutAgent()
    results = agent.quick_test("restaurants", "Lahore", limit=5)
    print(f"\n--- RESULTS ({len(results)}) ---")
    for r in results:
        print(f"  {r.get('business_name')} | {r.get('address')}")