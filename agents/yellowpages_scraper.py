"""
YELLOW PAGES SCRAPER
Scrapes business data from yellowpages.com
Fields: name, phone, address, website, category
Most reliable free source — no login required.
"""

import os
import sys
import time
import random
import requests
from bs4 import BeautifulSoup
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.user_agents import get_headers
from utils.logger import log_scrape, log_success, log_warning, log_error
from config.settings import MIN_DELAY_SECONDS, MAX_DELAY_SECONDS, MAX_RETRIES


class YellowPagesScraper:

    BASE_URL = "https://www.yellowpages.com/search"

    def __init__(self):
        self.session = requests.Session()
        self.source  = "yellow_pages"

    def _delay(self):
        """Random delay between requests to avoid blocks"""
        wait = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
        time.sleep(wait)

    def _fetch_page(self, url: str, retries: int = 0) -> BeautifulSoup | None:
        """Fetch a page with retry logic"""
        try:
            self.session.headers.update(get_headers())
            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                return BeautifulSoup(response.text, "lxml")
            elif response.status_code == 429:
                log_warning(f"Rate limited by YellowPages. Waiting 30s...")
                time.sleep(30)
                if retries < MAX_RETRIES:
                    return self._fetch_page(url, retries + 1)
            else:
                log_warning(f"YellowPages returned status {response.status_code}")

        except requests.exceptions.Timeout:
            log_warning(f"Timeout fetching: {url}")
            if retries < MAX_RETRIES:
                self._delay()
                return self._fetch_page(url, retries + 1)
        except Exception as e:
            log_error(f"Fetch error: {e}")

        return None

    def _parse_business(self, card) -> dict | None:
        """Extract business details from a single result card"""
        try:
            business = {}

            # Business name
            name_el = card.select_one("a.business-name span")
            if not name_el:
                name_el = card.select_one(".business-name")
            business["business_name"] = name_el.get_text(strip=True) if name_el else ""

            # Skip if no name found
            if not business["business_name"]:
                return None

            # Phone number
            phone_el = card.select_one(".phones.phone.primary")
            if not phone_el:
                phone_el = card.select_one("[class*='phone']")
            business["phone_number"] = phone_el.get_text(strip=True) if phone_el else ""

            # Address
            street_el  = card.select_one(".street-address")
            locality_el = card.select_one(".locality")
            street   = street_el.get_text(strip=True)   if street_el   else ""
            locality = locality_el.get_text(strip=True) if locality_el else ""
            business["address"] = f"{street} {locality}".strip()

            # Website
            web_el = card.select_one("a.track-visit-website")
            if not web_el:
                web_el = card.select_one("[class*='website']")
            business["website"] = web_el.get("href", "") if web_el else ""

            # Category
            cat_el = card.select_one(".categories a")
            business["category"] = cat_el.get_text(strip=True) if cat_el else ""

            # Rating
            rating_el = card.select_one(".rating .count")
            if not rating_el:
                rating_el = card.select_one("[class*='rating']")
            try:
                raw_rating = rating_el.get_text(strip=True) if rating_el else "0"
                business["rating"] = float(raw_rating.replace("(","").replace(")","").strip() or 0)
            except:
                business["rating"] = 0.0

            # Review count
            review_el = card.select_one(".count")
            try:
                raw_count = review_el.get_text(strip=True) if review_el else "0"
                cleaned   = raw_count.replace("(","").replace(")","").strip()
                business["review_count"] = int(cleaned) if cleaned.isdigit() else 0
            except:
                business["review_count"] = 0

            # Email — YP doesn't show emails directly, leave empty for AI agent to find
            business["email"]        = ""
            business["source"]       = self.source
            business["scraped_date"] = str(date.today())

            return business

        except Exception as e:
            log_error(f"Parse error: {e}")
            return None

    def scrape(self, business_type: str, city: str, max_results: int = 100) -> list:
        """
        Main scrape method.
        Returns list of business dicts.
        """
        results      = []
        page         = 1
        search_query = business_type.replace(" ", "+")
        city_query   = city.replace(" ", "+")

        log_scrape(f"YellowPages → '{business_type}' in '{city}' (target: {max_results})")

        while len(results) < max_results:
            url = f"{self.BASE_URL}?search_terms={search_query}&geo_location_terms={city_query}&page={page}"
            log_scrape(f"Page {page}: {url}")

            soup = self._fetch_page(url)
            if not soup:
                log_warning("Could not fetch page. Stopping.")
                break

            # Find all business cards
            cards = soup.select(".result .info")
            if not cards:
                cards = soup.select("[class*='result']")

            if not cards:
                log_warning(f"No results found on page {page}. Stopping.")
                break

            page_count = 0
            for card in cards:
                if len(results) >= max_results:
                    break

                business = self._parse_business(card)
                if business and business.get("business_name"):
                    business["city"] = city
                    results.append(business)
                    page_count += 1
                    log_success(f"Found: {business['business_name']} | {business['phone_number']}")

            log_scrape(f"Page {page}: extracted {page_count} businesses. Total so far: {len(results)}")

            # Check if there's a next page
            next_btn = soup.select_one("a.next")
            if not next_btn:
                log_scrape("No more pages available.")
                break

            page += 1
            self._delay()

        log_success(f"YellowPages scraping done. Total collected: {len(results)}")
        return results


if __name__ == "__main__":
    scraper  = YellowPagesScraper()
    results  = scraper.scrape("dentists", "Chicago", max_results=5)
    for r in results:
        print(r)