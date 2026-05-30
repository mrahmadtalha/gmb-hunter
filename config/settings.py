# ============================================================
#  GMB HUNTER — Configuration Settings
#  Edit this file to customize your scraping targets
# ============================================================

# --- SCRAPING TARGET ---
DEFAULT_BUSINESS_TYPE = "restaurants"   # e.g. dentists, plumbers, gyms
DEFAULT_CITY          = "New York"      # Target city
RECORDS_PER_DAY       = 100             # How many businesses to collect daily

# --- FREE AI API KEYS (get free keys from each site) ---
# Groq    → https://console.groq.com         (fastest, most generous free tier)
# Gemini  → https://aistudio.google.com      (Google AI, free tier)
# Mistral → https://console.mistral.ai       (European AI, free tier)
# Cohere  → https://dashboard.cohere.com     (free tier)

AI_APIS = [
    {
        "name":    "Groq",
        "api_key": "YOUR_GROQ_API_KEY_HERE",
        "model":   "llama3-8b-8192",
        "base_url":"https://api.groq.com/openai/v1",
        "daily_limit": 14400,   # requests per day (free tier)
        "active":  True
    },
    {
        "name":    "Gemini",
        "api_key": "YOUR_GEMINI_API_KEY_HERE",
        "model":   "gemini-1.5-flash",
        "base_url":"https://generativelanguage.googleapis.com/v1beta",
        "daily_limit": 1500,
        "active":  True
    },
    {
        "name":    "Mistral",
        "api_key": "YOUR_MISTRAL_API_KEY_HERE",
        "model":   "mistral-small-latest",
        "base_url":"https://api.mistral.ai/v1",
        "daily_limit": 1000,
        "active":  True
    },
    {
        "name":    "Cohere",
        "api_key": "YOUR_COHERE_API_KEY_HERE",
        "model":   "command-r",
        "base_url":"https://api.cohere.ai/v1",
        "daily_limit": 1000,
        "active":  True
    },
]

# --- SCRAPING SOURCES (in priority order) ---
SCRAPING_SOURCES = [
    "google_maps",   # Primary source
    "yellow_pages",  # Backup 1
    "yelp",          # Backup 2
]

# --- ANTI-BLOCK SETTINGS ---
MIN_DELAY_SECONDS = 2    # Minimum wait between requests
MAX_DELAY_SECONDS = 5    # Maximum wait between requests
MAX_RETRIES       = 3    # Retry failed requests this many times

# --- OUTPUT SETTINGS ---
OUTPUT_DIR  = "output"
LOG_DIR     = "logs"
DB_NAME     = "database/gmb_hunter.db"

# --- DATA FIELDS TO COLLECT ---
BUSINESS_FIELDS = [
    "business_name",
    "phone_number",
    "email",
    "website",
    "rating",
    "review_count",
    "address",
    "city",
    "category",
    "source",
    "scraped_date",
]