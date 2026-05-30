"""
Debug: check what website/email data Google Maps detail page actually has
"""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
options.add_argument("--lang=en-US")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36")

service = Service(ChromeDriverManager().install())
driver  = webdriver.Chrome(service=service, options=options)

# Search for Hummings restaurant
driver.get("https://www.google.com/maps/search/Hummings+restaurant+London")
time.sleep(4)

# Click first result
try:
    first = driver.find_element(By.CSS_SELECTOR, "div.Nv2PK")
    first.click()
    time.sleep(4)
except:
    print("Could not click first result")

print("=== PAGE URL ===")
print(driver.current_url)

print("\n=== ALL LINKS ON PAGE ===")
links = driver.find_elements(By.CSS_SELECTOR, "a[href]")
for link in links[:30]:
    href  = link.get_attribute("href") or ""
    label = link.get_attribute("aria-label") or link.text or ""
    if href and "google" not in href and href.startswith("http"):
        print(f"  HREF: {href[:80]}  |  LABEL: {label[:40]}")

print("\n=== BUTTONS WITH ARIA-LABELS ===")
buttons = driver.find_elements(By.CSS_SELECTOR, "button[aria-label], a[aria-label]")
for btn in buttons:
    label = btn.get_attribute("aria-label") or ""
    if any(w in label.lower() for w in ["web", "site", "visit", "http"]):
        print(f"  LABEL: {label[:80]}")

print("\n=== EMAIL PATTERNS IN PAGE SOURCE ===")
source = driver.page_source
emails = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', source)
emails = [e for e in emails if not any(x in e for x in ["google","schema","w3.org","sentry"])]
print(f"  Found emails: {emails[:10]}")

driver.quit()