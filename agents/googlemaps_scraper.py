"""
GOOGLE MAPS SCRAPER — Selenium Version
Supports both city-name search and coordinate-based grid search.
"""

import os
import sys
import time
import random
import re
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import log_scrape, log_success, log_warning, log_error
from config.settings import MIN_DELAY_SECONDS, MAX_DELAY_SECONDS

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


def clean_address(parts: list) -> str:
    SKIP_PATTERNS = [
        re.compile(r'^\d\.\d'),
        re.compile(r'(open|close|AM|PM|\d+:\d+)', re.IGNORECASE),
        re.compile(r'^Rs\s', re.IGNORECASE),
        re.compile(r'^\d+-star', re.IGNORECASE),
        re.compile(r'^free\s', re.IGNORECASE),
        re.compile(
            r'^(restaurant|cafe|bakery|hotel|fast food|pizza|biryani|bar|lounge|'
            r'Pakistani|Pakistani restaurant|fast food restaurant|chinese restaurant|'
            r'afghan restaurant|cuban restaurant|indian restaurant|italian restaurant|'
            r'desi restaurant|bbq restaurant|seafood restaurant|burger|steakhouse|'
            r'food court|sweet shop|sweets|ice cream|juice bar|tea house|dhaba|'
            r'karahi|tikka|kebab house)s?$',
            re.IGNORECASE
        ),
    ]
    candidates = []
    for p in parts:
        p = p.strip().strip('"').strip("'").strip()
        if not p or len(p) < 4:
            continue
        words = p.split()
        if len(words) > 8:
            continue
        if p.startswith('"') or p.startswith('\u201c'):
            continue
        skip = False
        for pattern in SKIP_PATTERNS:
            if pattern.search(p):
                skip = True
                break
        if not skip:
            candidates.append(p)

    if not candidates:
        return ""

    ADDRESS_HINTS = re.compile(
        r'(road|rd\b|street|st\b|block|colony|sector|phase|plaza|near|town|'
        r'chowk|bazar|bazaar|multan|shakir|garden|railway|manka|taunsa|gulberg|'
        r'dha|johar|model|bahria|cantt|mall|mm alam|liberty|boulevard)',
        re.IGNORECASE
    )
    for c in candidates:
        if ADDRESS_HINTS.search(c):
            return c

    candidates.sort(key=len)
    return candidates[0]


class GoogleMapsScraper:

    def __init__(self):
        self.source = "google_maps"
        self.driver = None

    def _start_browser(self):
        if not SELENIUM_AVAILABLE:
            log_error("Selenium not installed.")
            return False
        try:
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--lang=en-US")
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                "acceptLanguage": "en-US,en;q=0.9"
            })
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            return True
        except Exception as e:
            log_error(f"Could not start Chrome: {e}")
            return False

    def _stop_browser(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def _delay(self):
        time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

    def _scroll_results(self, panel, target: int):
        last_count = 0
        for _ in range(30):
            cards = self.driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
            if len(cards) >= target:
                break
            if len(cards) == last_count:
                break
            last_count = len(cards)
            try:
                self.driver.execute_script("arguments[0].scrollTop += 1200", panel)
                time.sleep(2)
            except:
                break

    def _get_review_count(self, card) -> int:
        try:
            for span in card.find_elements(By.CSS_SELECTOR, "span[aria-label]"):
                label = span.get_attribute("aria-label") or ""
                m = re.search(r'([\d,]+)\s+review', label, re.IGNORECASE)
                if m:
                    return int(m.group(1).replace(",", ""))
        except:
            pass
        try:
            for m in re.finditer(r'\(([\d,]+)\)', card.text):
                val = int(m.group(1).replace(",", ""))
                if val > 0:
                    return val
        except:
            pass
        return 0

    def _extract_businesses(self) -> list:
        businesses = []
        seen_names = set()
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
            if not cards:
                cards = self.driver.find_elements(By.CSS_SELECTOR, "[role='article']")

            for card in cards:
                try:
                    biz = {}
                    name = ""
                    for sel in [".qBF1Pd", "div.fontHeadlineSmall", "h3"]:
                        try:
                            name = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                            if name:
                                break
                        except:
                            continue
                    if not name or name in seen_names:
                        continue
                    seen_names.add(name)
                    biz["business_name"] = name

                    rating = 0.0
                    try:
                        rating = float(card.find_element(By.CSS_SELECTOR, "span.MW4etd").text.strip())
                    except:
                        pass
                    biz["rating"] = rating

                    biz["review_count"] = self._get_review_count(card)

                    raw = card.text.replace(name, "")
                    parts = re.split(r'[\n·•]', raw)
                    parts = [p.strip() for p in parts if p.strip()]
                    biz["address"] = clean_address(parts)

                    website = ""
                    try:
                        w = card.find_element(By.CSS_SELECTOR, "a[data-value='Website']")
                        website = w.get_attribute("href") or ""
                    except:
                        pass
                    biz["website"]       = website
                    biz["phone_number"]  = ""
                    biz["email"]         = ""
                    biz["source"]        = self.source
                    biz["scraped_date"]  = str(date.today())
                    businesses.append(biz)

                    log_success(
                        f"  {name[:35]:<35} | "
                        f"⭐{rating} | 💬{biz['review_count']} | "
                        f"📍{biz['address'][:30]}"
                    )
                except:
                    continue
        except Exception as e:
            log_error(f"Extraction error: {e}")
        return businesses

    def _do_scrape(self, url: str, business_type: str, city: str, max_results: int) -> list:
        """Shared scraping logic used by both scrape() and scrape_by_coordinates()"""
        results = []
        try:
            log_scrape(f"Opening: {url}")
            self.driver.get(url)
            time.sleep(4)
            try:
                self.driver.find_element(By.XPATH, "//button[contains(.,'Accept')]").click()
                time.sleep(1)
            except:
                pass
            try:
                panel = self.driver.find_element(By.CSS_SELECTOR, "div[role='feed']")
                self._scroll_results(panel, max_results)
            except:
                time.sleep(3)

            for biz in self._extract_businesses()[:max_results]:
                biz["city"]     = city
                biz["category"] = business_type
                results.append(biz)
        except Exception as e:
            log_error(f"Scrape error: {e}")
        return results

    def scrape(self, business_type: str, city: str, max_results: int = 100) -> list:
        """Scrape by city name"""
        if not SELENIUM_AVAILABLE:
            log_error("Run: pip install selenium webdriver-manager")
            return []
        log_scrape(f"Google Maps → '{business_type}' in '{city}' (target: {max_results})")
        if not self._start_browser():
            return []
        try:
            url = f"https://www.google.com/maps/search/{business_type.replace(' ', '+')}+in+{city.replace(' ', '+')}"
            results = self._do_scrape(url, business_type, city, max_results)
        finally:
            self._stop_browser()
        log_success(f"Google Maps done. Total: {len(results)}")
        return results

    def scrape_by_coordinates(self, business_type: str, lat: float, lng: float,
                               city: str, max_results: int = 25) -> list:
        """Scrape by coordinates — used by grid search"""
        if not SELENIUM_AVAILABLE:
            log_error("Run: pip install selenium webdriver-manager")
            return []
        if not self._start_browser():
            return []
        try:
            url = (
                f"https://www.google.com/maps/search/"
                f"{business_type.replace(' ', '+')}/"
                f"@{lat},{lng},14z"
            )
            log_scrape(f"Grid @{lat:.4f},{lng:.4f}")
            results = self._do_scrape(url, business_type, city, max_results)
        finally:
            self._stop_browser()
        return results


if __name__ == "__main__":
    scraper = GoogleMapsScraper()
    results = scraper.scrape("restaurants", "Lahore", max_results=5)
    for r in results:
        print(f"  {r['business_name']} | ⭐{r['rating']} | 📍{r['address']}")