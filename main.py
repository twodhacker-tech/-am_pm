import json
import os
import time as t
from datetime import datetime, time
from threading import Thread
from fastapi import FastAPI
import requests
from bs4 import BeautifulSoup
import pytz

app = FastAPI()
TIMEZONE = pytz.timezone("Asia/Yangon")
DATA_FILE = "ResultsHistory.json"

# -------------------------
# Placeholders
# -------------------------
PLACEHOLDER = {"date": "--", "time": "--", "set": "--", "value": "--", "twod": "--"}
current_am = PLACEHOLDER.copy()
current_pm = PLACEHOLDER.copy()
history = []

last_am_saved_date = None
last_pm_saved_date = None
last_reset_date = None

# -------------------------
# Helpers
# -------------------------
def time_from_hms(hms: str) -> time:
    h, m, s = map(int, hms.split(":"))
    return time(h, m, s)

def in_range(start_hms: str, end_hms: str, now_time: time) -> bool:
    start = time_from_hms(start_hms)
    end = time_from_hms(end_hms)
    return start <= now_time < end

def load_history():
    global history, last_am_saved_date, last_pm_saved_date
    if not os.path.exists(DATA_FILE):
        history.clear()
        return
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            history[:] = data.get("history", [])
            # last saved
            for rec in reversed(history):
                if rec.get("session") == "AM" and rec.get("date"):
                    last_am_saved_date = rec.get("date")
                    break
            for rec in reversed(history):
                if rec.get("session") == "PM" and rec.get("date"):
                    last_pm_saved_date = rec.get("date")
                    break
    except:
        history.clear()

def save_history():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump({"history": history}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error saving history:", e)

# -------------------------
# Fetch Live
# -------------------------
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
        now_dt = datetime.now(TIMEZONE)
        return {"date": now_dt.strftime("%Y-%m-%d"),
                "time": now_dt.strftime("%H:%M:%S"),
                "set": live_set,
                "value": live_value,
                "twod": twod_live}
    except:
        now_dt = datetime.now(TIMEZONE)
        return {"date": "--", "time": now_dt.strftime("%H:%M:%S"),
                "set": "--", "value": "--", "twod": "--"}

# -------------------------
# Background Runner
# -------------------------
def runner():
    global current_am, current_pm, history
    global last_am_saved_date, last_pm_saved_date, last_reset_date

    load_history()
    while True:
        now_dt = datetime.now(TIMEZONE)
        now_time = now_dt.time()
        today_str = now_dt.date().isoformat()

        # 08:50 reset placeholders once/day
        if in_range("08:50:00", "09:00:00", now_time):
            if last_reset_date != today_str:
                current_am = PLACEHOLDER.copy()
                current_pm = PLACEHOLDER.copy()
                last_reset_date = today_str
                print(f"[{now_dt.strftime('%H:%M:%S')}] Reset placeholders")

        # AM run 09:00-12:01
        if in_range("09:00:00", "12:01:00", now_time):
            current_am = get_live()
            current_pm = PLACEHOLDER.copy()

        # Save AM after 12:01 once
        if now_time >= time_from_hms("12:01:00") and last_am_saved_date != today_str:
            if current_am.get("date") != "--":
                history.append({"session": "AM", **current_am})
                save_history()
                last_am_saved_date = today_str
                print(f"[{now_dt.strftime('%H:%M:%S')}] AM saved")

        # PM run 13:00-16:30
        if in_range("13:00:00", "16:30:01", now_time):
            current_pm = get_live()

        # Save PM after 16:30 once
        if now_time >= time_from_hms("16:30:00") and last_pm_saved_date != today_str:
            if current_pm.get("date") != "--":
                history.append({"session": "PM", **current_pm})
                save_history()
                last_pm_saved_date = today_str
                print(f"[{now_dt.strftime('%H:%M:%S')}] PM saved")

        t.sleep(1)

Thread(target=runner, daemon=True).start()

# -------------------------
# FastAPI Endpoints
# -------------------------
@app.get("/")
def root():
    return {"message": "FastAPI Live Scheduler Running",
            "time": datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")}

@app.get("/data")
def get_data():
    now_time = datetime.now(TIMEZONE).time()

    # Before 08:50 -> show last saved
    data = {"AM": current_am, "PM": current_pm, "history": history}
    if in_range("08:50:00", "09:00:00", now_time):
        data["AM"] = PLACEHOLDER.copy()
        data["PM"] = PLACEHOLDER.copy()
    return data