from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import requests
import sqlite3
from fastapi.middleware.cors import CORSMiddleware

# FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLite DB setup
conn = sqlite3.connect("stock2d.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_date TEXT,
    record_time TEXT,
    set_value TEXT,
    value TEXT,
    twod TEXT
)
""")
conn.commit()

# Myanmar timezone
myanmar_tz = pytz.timezone("Asia/Yangon")

# Target API
TARGET_API = "https://api.thaistock2d.com/live"

# Function: Fetch & record snapshot
def fetch_snapshot():
    try:
        response = requests.get(TARGET_API, timeout=5)
        result = response.json()
        live = result.get("live", {})
        
        set_value = live.get("set", "--")
        value = live.get("value", "--")
        twod = live.get("twod", "--")
        time_str = live.get("time", "--")
        date_str = live.get("date", datetime.now(myanmar_tz).strftime("%Y-%m-%d"))
        
    except Exception as e:
        # API failed → insert placeholder
        print(f"Error fetching snapshot: {e}")
        set_value = value = twod = "--"
        now = datetime.now(myanmar_tz)
        time_str = now.time().strftime("%H:%M:%S")
        date_str = now.date().isoformat()
    
    # Insert snapshot (real or placeholder)
    cursor.execute("""
        INSERT INTO records (record_date, record_time, set_value, value, twod)
        VALUES (?, ?, ?, ?, ?)
    """, (date_str, time_str, set_value, value, twod))
    conn.commit()
    print(f"Recorded snapshot at {time_str} on {date_str}")

# Scheduler setup
scheduler = BackgroundScheduler(timezone=myanmar_tz)
scheduler.add_job(fetch_snapshot, 'cron', hour=12, minute=1)
scheduler.add_job(fetch_snapshot, 'cron', hour=16, minute=30)
scheduler.start()

# -------------------
# Routes
# -------------------

# Root route → simple message
@app.get("/")
def home():
    return {"message": "Thai 2D Stock Snapshot API is running. Use /records or /latest endpoints."}

# Get all records
@app.get("/records")
def get_records():
    cursor.execute("SELECT record_date, record_time, set_value, value, twod FROM records ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        now = datetime.now(myanmar_tz)
        return [{
            "date": now.date().isoformat(),
            "time": now.time().strftime("%H:%M:%S"),
            "set": "--",
            "value": "--",
            "twod": "--"
        }]
    return [
        {"date": r[0], "time": r[1], "set": r[2], "value": r[3], "twod": r[4]}
        for r in rows
    ]

# Get latest record
@app.get("/latest")
def latest_record():
    cursor.execute("SELECT record_date, record_time, set_value, value, twod FROM records ORDER BY id DESC LIMIT 1")
    r = cursor.fetchone()
    if r:
        return {"date": r[0], "time": r[1], "set": r[2], "value": r[3], "twod": r[4]}
    # DB empty → placeholder
    now = datetime.now(myanmar_tz)
    return {
        "date": now.date().isoformat(),
        "time": now.time().strftime("%H:%M:%S"),
        "set": "--",
        "value": "--",
        "twod": "--"
    }
