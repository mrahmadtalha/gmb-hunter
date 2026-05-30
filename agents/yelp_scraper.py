"""
YELP SCRAPER
Scrapes business data from yelp.com
Fields: name, phone, address, website, rating, review count
Used as backup when YellowPages is blocked.
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


class YelpScraper:

    BASE_URL = "https://www.yelp.com/search"

    def __init__(self):
        self.session = requests.Session()
        self.source  = "yelp"

    def _delay(self):
        wait = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
        time.sleep(wait)

    def _fetch_page(self, url: str, retries: int = 0) -> BeautifulSoup | None:
        try:
            self.session.headers.update(get_headers())
            response = self.session.get(url, timeout=15)

            if response.status_code == 200:
                return BeautifulSoup(response.text, "lxml")
            elif response.status_code == 429:
                log_warning("Rate limited by Yelp. Waiting 60s...")
                time.sleep(60)
                if retries < MAX_RETRIES:
                    return self._fetch_page(url, retries + 1)
            else:
                log_warning(f"Yelp returned status {response.status_code}")

        except requests.exceptions.Timeout:
            log_warning(f"Timeout: {url}")
            if retries < MAX_RETRIES:
                self._delay()
                return self._fetch_page(url, retries + 1)
        except Exception as e:
            log_error(f"Fetch error: {e}")

        return None

    def _parse_business(self, card) -> dict | None:
        try:
            business = {}

            # Business name
            name_el = card.select_one("a[class*='businessName']")
            if not name_el:
                name_el = card.select_one("h3 a")
            if not name_el:
                name_el = card.select_one("[class*='businessName']")
            business["business_name"] = name_el.get_text(strip=True) if name_el else ""

            if not business["business_name"]:
                return None

            # Rating
            rating_el = card.select_one("[aria-label*='star rating']")
            if not rating_el:
                rating_el = card.select_one("[class*='rating']")
            try:
                label = rating_el.get("aria-label", "0") if rating_el else "0"
                business["rating"] = float(label.split(" ")[0]) if label else 0.0
            except:
                business["rating"] = 0.0

            # Review count
            review_el = card.select_one("[class*='reviewCount']")
            if not review_el:
                review_el = card.select_one("span[class*='review']")
            try:
                raw = review_el.get_text(strip=True) if review_el else "0"
                business["review_count"] = int("".join(filter(str.isdigit, raw)) or 0)
            except:
                business["review_count"] = 0

            # Address
            addr_el = card.select_one("address")
            if not addr_el:
                addr_el = card.select_one("[class*='secondaryAttributes']")
            business["address"] = addr_el.get_text(strip=True) if addr_el else ""

            # Phone — Yelp hides phone on listing page, detail page needed
            business["phone_number"] = ""

            # Website — not shown on listing
            business["website"] = ""

            # Category
            cat_el = card.select_one("[class*='priceCategory'] a")
            if not cat_el:
                cat_el = card.select_one("[class*='category']")
            business["category"] = cat_el.get_text(strip=True) if cat_el else ""

            business["email"]        = ""
            business["source"]       = self.source
            business["scraped_date"] = str(date.today())

            return business

        except Exception as e:
            log_error(f"Parse error: {e}")
            return None

    def scrape(self, business_type: str, city: str, max_results: int = 100) -> list:
        results      = []
        page         = 0
        search_query = business_type.replace(" ", "%20")
        city_query   = city.replace(" ", "%20")

        log_scrape(f"Yelp → '{business_type}' in '{city}' (target: {max_results})")

        while len(results) < max_results:
            url = f"{self.BASE_URL}?find_desc={search_query}&find_loc={city_query}&start={page * 10}"
            log_scrape(f"Page {page + 1}: {url}")

            soup = self._fetch_page(url)
            if not soup:
                log_warning("Could not fetch Yelp page. Stopping.")
                break

            cards = soup.select("[class*='container__09f24']")
            if not cards:
                cards = soup.select("li[class*='regular-search-result']")
            if not cards:
                log_warning(f"No Yelp results found on page {page + 1}")
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
                    log_success(f"Found: {business['business_name']} | ⭐ {business['rating']}")

            log_scrape(f"Page {page + 1}: extracted {page_count}. Total: {len(results)}")

            if page_count == 0:
                break

            page += 1
            self._delay()

        log_success(f"Yelp scraping done. Total: {len(results)}")
        return results


if __name__ == "__main__":
    scraper = YelpScraper()
    results = scraper.scrape("plumbers", "Houston", max_results=5)
    for r in results:
        print(r)