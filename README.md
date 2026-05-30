# GMB Hunter — AI Agent Scraping System

Automatically scrapes 100+ Google My Business records daily.
Saves to CSV and XLSX. Prevents duplicates. Free to run.

---

## Project Structure

```
gmb_hunter/
├── main.py                          ← Run this
├── requirements.txt                 ← Python packages
├── config/
│   └── settings.py                  ← YOUR SETTINGS HERE
├── agents/
│   ├── scout_agent.py               ← Agent 1: Coordinates scrapers
│   ├── googlemaps_scraper.py        ← Scraper: Google Maps
│   ├── yellowpages_scraper.py       ← Scraper: Yellow Pages
│   ├── yelp_scraper.py              ← Scraper: Yelp
│   └── saver_agent.py               ← Agent 4: Saves CSV + XLSX
├── database/
│   └── db_manager.py                ← Agent 3: Deduplication + SQLite
├── utils/
│   ├── logger.py                    ← Logging
│   └── user_agents.py               ← Anti-block browser headers
├── output/                          ← Your daily files appear here
└── logs/                            ← Daily log files
```

---

## Setup (One Time Only)

### Step 1 — Install Python packages
```bash
pip install -r requirements.txt
```

### Step 2 — Configure your target
Open `config/settings.py` and set:
```python
DEFAULT_BUSINESS_TYPE = "dentists"     # what to search
DEFAULT_CITY          = "Chicago"      # which city
RECORDS_PER_DAY       = 100            # how many per day
```

---

## How to Run

### Quick test (5 businesses — verify it works)
```bash
python main.py --test
```

### Full run (100 businesses — default city/type)
```bash
python main.py
```

### Custom city and type
```bash
python main.py --type dentists --city "Los Angeles"
python main.py --type plumbers --city Houston
python main.py --type gyms     --city "New York"
```

### Test Phase 1 foundation only
```bash
python main.py --phase1
```

---

## Output Files

Every run creates two files in the `output/` folder:

```
output/
├── dentists_chicago_2026-05-29.csv    ← Universal format
└── dentists_chicago_2026-05-29.xlsx   ← Excel with formatting
```

Each file contains:
| Column | Example |
|---|---|
| Business Name | Dr. Smith Dental |
| Phone Number | +1-312-555-0101 |
| Email | info@drsmith.com |
| Website | https://drsmith.com |
| Rating | 4.7 |
| Review Count | 214 |
| Address | 123 Main St, Chicago, IL |
| City | Chicago |
| Category | dentists |
| Source | google_maps |
| Scraped Date | 2026-05-29 |

---

## How Deduplication Works

Every business gets a unique fingerprint based on:
`name + phone + address`

Before saving, the system checks the database.
If already exists → **skip**.
If new → **save**.

This means you can run the script daily and it will
**never save the same business twice** across any day.

---

## Scraping Sources (Auto Fallback)

```
Google Maps  →  (blocked?)  →  Yellow Pages  →  (blocked?)  →  Yelp
```

The system automatically switches sources if one gets blocked.
No manual intervention needed.

---

## Daily Usage for Client Work

Run every morning:
```bash
python main.py --type "restaurants" --city "Chicago"
```

Send the client the XLSX file from the `output/` folder.

---

## Troubleshooting

**"No results found"**
- Google/YellowPages may be temporarily blocking requests
- Wait 10-15 minutes and try again
- Try a different city first to test

**"ModuleNotFoundError"**
- Run: `pip install -r requirements.txt`
- Make sure you're running from the `gmb_hunter/` folder

**Slow scraping**
- Normal — delays are intentional to avoid IP bans
- 100 records takes approx 10-20 minutes

---

## Coming Next

- Phase 3: AI Brain Agent (auto-extracts emails, cleans data)
- Phase 4: Full deduplication across all past runs  
- Phase 5: Auto-scheduler (runs daily at set time)