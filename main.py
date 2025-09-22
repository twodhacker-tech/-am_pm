from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import sqlite3
from fastapi.middleware.cors import CORSMiddleware
import time

# -----------------------
# FastAPI app & CORS
# -----------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# SQLite DB
# -----------------------
conn = sqlite3.connect("stock2d.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_date TEXT,
    record_time TEXT,
    set_value TEXT,
    value TEXT,
    twod TEXT,
    period TEXT
)
""")
conn.commit()

# -----------------------
# Timezone
# -----------------------
tz = pytz.timezone("Asia/Yangon")

# -----------------------
# Function to scrape SET website
# -----------------------
def scrape_set_live():
    url = "https://www.set.or.th/en/market/product/stock/overview"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return {"date": "--", "time": "--", "set": "--", "value": "--", "twod": "--", "error": f"request_error: {e}"}
    
    soup = BeautifulSoup(resp.text, "html.parser")
    try:
        tables = soup.find_all("table")
        table = tables[1]
        divs = table.find_all("div")
        live_set = divs[4].get_text(strip=True)
        live_value = divs[6].get_text(strip=True)

        clean_set = live_set.replace(",", "")
        formatted = "{:.2f}".format(float(clean_set))
        top = formatted[-1]

        clean_value = live_value.replace(",", "") or "0.00"
        last = str(int(float(clean_value)))[-1]

        twod_live = f"{top}{last}"
        now = datetime.now(tz)
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "set": live_set,
            "value": live_value,
            "twod": twod_live
        }
    except Exception as e:
        return {"date": "--", "time": "--", "set": "--", "value": "--", "twod": "--", "error": f"parse_error: {e}"}

# -----------------------
# Fetch & record snapshot
# -----------------------
def fetch_snapshot(period):
    data = scrape_set_live()
    set_value = data.get("set", "--")
    value = data.get("value", "--")
    twod = data.get("twod", "--")

    now = datetime.now(tz)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    cursor.execute("""
        INSERT INTO records (record_date, record_time, set_value, value, twod, period)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (date_str, time_str, set_value, value, twod, period))
    conn.commit()
    print(f"Recorded {period} snapshot: twod={twod}, set={set_value}, value={value}")

# -----------------------
# Scheduler
# -----------------------
scheduler = BackgroundScheduler(timezone=tz)
scheduler.add_job(lambda: fetch_snapshot("AM"), 'cron', hour=12, minute=1)
scheduler.add_job(lambda: fetch_snapshot("PM"), 'cron', hour=16, minute=30)
scheduler.start()

# -----------------------
# Routes
# -----------------------
@app.get("/")
def home():
    live_data = scrape_set_live()
    result = {
        "live": live_data,
        "AM": {"date": "--", "time": "--", "set": "--", "value": "--", "twod": "--"},
        "PM": {"date": "--", "time": "--", "set": "--", "value": "--", "twod": "--"}
    }
    return result

@app.get("/latest")
def latest_day_snapshot():
    today = datetime.now(tz).strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT period, record_date, record_time, set_value, value, twod
        FROM records
        WHERE record_date = ?
    """, (today,))
    rows = cursor.fetchall()

    # Initialize only AM/PM placeholders
    result = {
        "AM": {"date": "--", "time": "--", "set": "--", "value": "--", "twod": "--"},
        "PM": {"date": "--", "time": "--", "set": "--", "value": "--", "twod": "--"}
    }

    # Update AM/PM if records exist
    for r in rows:
        period = r[0]
        result[period] = {
            "date": r[1],
            "time": r[2],
            "set": r[3],
            "value": r[4],
            "twod": r[5]
        }

    # Add live scrape data at the end (no initial placeholder needed)
    result["live"] = scrape_set_live()

    return result
