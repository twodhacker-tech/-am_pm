# main.py
from fastapi import FastAPI
from bs4 import BeautifulSoup
import requests
import datetime
import time
import threading
import json
import os
import pytz

app = FastAPI()

# ------------------------
# Config / Timezone
# ------------------------
TIMEZONE = pytz.timezone("Asia/Yangon")

DATA_FILE = "ResultsHistory.json"

# Placeholder used for "--"
PLACEHOLDER = {
    "date": "--",
    "time": "--",
    "set": "--",
    "value": "--",
    "twod": "--"
}

# runtime state
current_am = PLACEHOLDER.copy()
current_pm = PLACEHOLDER.copy()
history = []

# flags to avoid duplicate daily saves/resets
last_am_saved_date = None
last_pm_saved_date = None
last_reset_date = None

# ------------------------
# Helpers
# ------------------------
def time_from_hms(hms: str) -> datetime.time:
    h, m, s = map(int, hms.split(":"))
    return datetime.time(h, m, s)

def in_range(start_hms: str, end_hms: str, now_time: datetime.time) -> bool:
    """Return True if now_time is in [start, end)."""
    start = time_from_hms(start_hms)
    end = time_from_hms(end_hms)
    return start <= now_time < end

def load_history():
    global history, last_am_saved_date, last_pm_saved_date
    if not os.path.exists(DATA_FILE):
        history = []
        return
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            history = data.get("history", [])
            if history:
                for rec in reversed(history):
                    if rec.get("session") == "AM" and rec.get("date"):
                        last_am_saved_date = rec.get("date")
                        break
                for rec in reversed(history):
                    if rec.get("session") == "PM" and rec.get("date"):
                        last_pm_saved_date = rec.get("date")
                        break
    except Exception:
        history = []

def save_history():
    global history
    try:
        with open(DATA_FILE, "w") as f:
            json.dump({"history": history}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error saving history:", e)

# ------------------------
# Live fetch function
# ------------------------
def get_live():
    try:
        url = "https://www.set.or.th/en/market/product/stock/overview"
        response = requests.get(url, timeout=8)
        soup = BeautifulSoup(response.text, "html.parser")

        table = soup.find_all("table")[1]
        set_index = table.find_all("div")[4]
        value_index = table.find_all("div")[6]

        live_set = set_index.get_text(strip=True)
        live_value = value_index.get_text(strip=True)

        clean_set = live_set.replace(",", "")
        formatted = "{:.2f}".format(float(clean_set))
        top = formatted[-1]

        clean_value = live_value.replace(",", "")
        if clean_value in ["", "-"]:
            clean_value = "0.00"
        last = str(int(float(clean_value)))[-1]

        twod_live = f"{top}{last}"

        now_dt = datetime.datetime.now(TIMEZONE)
        return {
            "date": now_dt.strftime("%Y-%m-%d"),
            "time": now_dt.strftime("%H:%M:%S"),
            "set": live_set,
            "value": live_value,
            "twod": twod_live
        }
    except Exception:
        now_dt = datetime.datetime.now(TIMEZONE)
        return {
            "date": "--",
            "time": now_dt.strftime("%H:%M:%S"),
            "set": "--",
            "value": "--",
            "twod": "--"
        }

# ------------------------
# Background runner
# ------------------------
def live_runner():
    global current_am, current_pm, history
    global last_am_saved_date, last_pm_saved_date, last_reset_date

    load_history()

    while True:
        now_dt = datetime.datetime.now(TIMEZONE)
        now_time = now_dt.time()
        today_str = now_dt.date().isoformat()

        # Reset placeholders once per day at 08:50 - 09:00
        if in_range("08:50:00", "09:00:00", now_time):
            if last_reset_date != today_str:
                current_am = PLACEHOLDER.copy()
                current_pm = PLACEHOLDER.copy()
                last_reset_date = today_str
                print(f"[{now_dt.strftime('%H:%M:%S')}] Reset placeholders at 08:50 for {today_str}")

        # AM running: 09:00 - 12:01
        if in_range("09:00:00", "12:01:00", now_time):
            live = get_live()
            current_am = live
            current_pm = PLACEHOLDER.copy()

        # Save AM history at 12:01 if not saved yet
        if now_time >= time_from_hms("12:01:00"):
            if last_am_saved_date != today_str:
                if current_am.get("date") and current_am.get("date") != "--":
                    history.append({"session": "AM", **current_am})
                    save_history()
                    last_am_saved_date = today_str
                    print(f"[{now_dt.strftime('%H:%M:%S')}] AM saved to history")

        # PM running: 13:00 - 16:30
        if in_range("13:00:00", "16:30:01", now_time):
            live = get_live()
            current_pm = live

        # Save PM history at 16:30 if not saved yet
        if now_time >= time_from_hms("16:30:00"):
            if last_pm_saved_date != today_str:
                if current_pm.get("date") and current_pm.get("date") != "--":
                    history.append({"session": "PM", **current_pm})
                    save_history()
                    last_pm_saved_date = today_str
                    print(f"[{now_dt.strftime('%H:%M:%S')}] PM saved to history")

        time.sleep(1)

thread = threading.Thread(target=live_runner, daemon=True)
thread.start()

# ------------------------
# FastAPI endpoints
# ------------------------
@app.get("/")
def root():
    now = datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    return {"message": "FastAPI Live Scheduler Running", "time": now}

@app.get("/data")
def get_data():
    now_dt = datetime.datetime.now(TIMEZONE)
    now_time = now_dt.time()

    if now_time < time_from_hms("08:00:00"):
        return {"AM": {}, "PM": {}, "history": history}

    if in_range("08:50:00", "09:00:00", now_time):
        return {"AM": PLACEHOLDER.copy(), "PM": PLACEHOLDER.copy(), "history": history}

    if in_range("09:00:00", "12:01:00", now_time):
        return {"AM": current_am, "PM": PLACEHOLDER.copy(), "history": history}

    if in_range("12:01:00", "13:00:00", now_time):
        return {"AM": current_am, "PM": PLACEHOLDER.copy(), "history": history}

    if in_range("13:00:00", "16:30:01", now_time):
        return {"AM": current_am, "PM": current_pm, "history": history}

    if now_time >= time_from_hms("16:30:00"):
        return {"AM": current_am, "PM": current_pm, "history": history}

    return {"AM": {}, "PM": {}, "history": history}