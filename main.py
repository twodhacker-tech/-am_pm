from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, date
import pytz
import requests
import sqlite3
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLite DB
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

# Myanmar timezone
tz = pytz.timezone("Asia/Yangon")

# Target API
TARGET_API = "https://api.thaistock2d.com/live"

# Scheduler fetch
def fetch_snapshot(period):
    try:
        response = requests.get(TARGET_API, timeout=5)
        result = response.json()
        live = result.get("live", {})
        set_value = live.get("set", "--")
        value = live.get("value", "--")
        twod = live.get("twod", "--")
        time_str = live.get("time", "--")
        date_str = live.get("date", datetime.now(tz).strftime("%Y-%m-%d"))
    except Exception as e:
        print(f"Error fetching snapshot: {e}")
        set_value = value = twod = "--"
        now = datetime.now(tz)
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

    # Insert into DB
    cursor.execute("""
        INSERT INTO records (record_date, record_time, set_value, value, twod, period)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (date_str, time_str, set_value, value, twod, period))
    conn.commit()
    print(f"Recorded {period} snapshot at {time_str} on {date_str}")

# Scheduler
scheduler = BackgroundScheduler(timezone=tz)
scheduler.add_job(lambda: fetch_snapshot("AM"), 'cron', hour=12, minute=1)
scheduler.add_job(lambda: fetch_snapshot("PM"), 'cron', hour=16, minute=30)
scheduler.start()

# ----------------
# Routes
# ----------------
@app.get("/")
def home():
    result = {
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

    # Initialize AM/PM with placeholder
    result = {
        "AM": {"date": "--", "time": "--", "set": "--", "value": "--", "twod": "--"},
        "PM": {"date": "--", "time": "--", "set": "--", "value": "--", "twod": "--"}
    }

    for r in rows:
        period = r[0]
        result[period] = {
            "date": r[1],
            "time": r[2],
            "set": r[3],
            "value": r[4],
            "twod": r[5]
        }

    return result
