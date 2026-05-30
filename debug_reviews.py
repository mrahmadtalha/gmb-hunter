"""
Debug script - prints raw card text and aria-labels to see
exactly what Google Maps returns for review counts
"""
import sys
import os
import time
import re

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

driver.get("https://www.google.com/maps/search/restaurants+in+Dera+Ghazi+Khan")
time.sleep(5)

cards = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
print(f"Found {len(cards)} cards\n")

for i, card in enumerate(cards[:3]):
    print(f"{'='*60}")
    print(f"CARD {i+1} FULL TEXT:")
    print(card.text)
    print()
    print(f"CARD {i+1} ARIA-LABELS:")
    spans = card.find_elements(By.CSS_SELECTOR, "span[aria-label]")
    for span in spans:
        print(f"  aria-label: {span.get_attribute('aria-label')}")
    print()

driver.quit()