from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import requests
import sqlite3
from fastapi.middleware.cors import CORSMiddleware

# FastAPI app
app = FastAPI()

# Enable CORS (Android/Web client)
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
        response = requests.get(TARGET_API)
        result = response.json()
        live = result.get("live", {})
        
        # Extract fields
        set_value = live.get("set", "--")
        value = live.get("value", "--")
        twod = live.get("twod", "--")
        time_str = live.get("time", "--")
        date_str = live.get("date", datetime.now(myanmar_tz).strftime("%Y-%m-%d"))
        
        now = datetime.now(myanmar_tz)
        record_date = date_str
        record_time = time_str if time_str != "--" else now.time().strftime("%H:%M:%S")
        
        # Insert into DB
        cursor.execute("""
            INSERT INTO records (record_date, record_time, set_value, value, twod)
            VALUES (?, ?, ?, ?, ?)
        """, (record_date, record_time, set_value, value, twod))
        conn.commit()
        
        print(f"Recorded 2D data at {record_time} on {record_date}")
        
    except Exception as e:
        print(f"Error fetching snapshot: {e}")

# Scheduler setup
scheduler = BackgroundScheduler(timezone=myanmar_tz)
scheduler.add_job(fetch_snapshot, 'cron', hour=12, minute=1)
scheduler.add_job(fetch_snapshot, 'cron', hour=16, minute=30)
scheduler.start()

# API endpoint: Get all records
@app.get("/records")
def get_records():
    cursor.execute("SELECT record_date, record_time, set_value, value, twod FROM records ORDER BY id")
    rows = cursor.fetchall()
    return [
        {
            "date": r[0],
            "time": r[1],
            "set": r[2],
            "value": r[3],
            "twod": r[4]
        } for r in rows
    ]

# API endpoint: Get latest record
@app.get("/latest")
def latest_record():
    cursor.execute("SELECT record_date, record_time, set_value, value, twod FROM records ORDER BY id DESC LIMIT 1")
    r = cursor.fetchone()
    if r:
        return {
            "date": r[0],
            "time": r[1],
            "set": r[2],
            "value": r[3],
            "twod": r[4]
        }
    return {"message": "No records yet"}
