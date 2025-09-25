from fastapi import FastAPI
import datetime
import pytz
import threading
import time
import json
import os
import requests
from bs4 import BeautifulSoup

# ------------------------
# FastAPI app
# ------------------------
app = FastAPI()

# ------------------------
# Global Variables
# ------------------------
TIMEZONE = pytz.timezone("Asia/Yangon")
DATA_FILE = "ResultsHistory.json"

current_am = {}
current_pm = {}
history = []

# ------------------------
# Utility Functions
# ------------------------
def get_live():
    try:
        url = "https://www.set.or.th/en/market/product/stock/overview"
        response = requests.get(url)
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

        return {
            "date": datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d"),
            "time": datetime.datetime.now(TIMEZONE).strftime("%H:%M:%S"),
            "set": live_set,
            "value": live_value,
            "twod": twod_live
        }
    except Exception as e:
        return {
            "date": datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d"),
            "time": datetime.datetime.now(TIMEZONE).strftime("%H:%M:%S"),
            "set": "--",
            "value": "--",
            "twod": "--",
            "error": str(e)
        }

def load_history():
    global history
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)
            history = data.get("history", [])
            return history
        except:
            return []

def save_history():
    global history
    data = {"history": history}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ------------------------
# Continuous Live Runner
# ------------------------
def run_live_continuous():
    global current_am, current_pm, history
    while True:
        now = datetime.datetime.now(TIMEZONE)
        current_time = now.strftime("%H:%M:%S")

        # AM session 09:00:00 → 12:01:00
        if "09:00:00" <= current_time <= "12:01:00":
            live = get_live()
            current_am = live
            if current_time == "12:01:00":
                history.append({"session": "AM", **current_am})
                save_history()

        # PM session 13:00:00 → 16:30:00
        elif "13:00:00" <= current_time <= "16:30:00":
            live = get_live()
            current_pm = live
            if current_time == "16:30:00":
                history.append({"session": "PM", **current_pm})
                save_history()

        # CPU-friendly small sleep
        time.sleep(0.1)

# ------------------------
# FastAPI Startup Event
# ------------------------
@app.on_event("startup")
def start_background_task():
    load_history()
    thread = threading.Thread(target=run_live_continuous, daemon=True)
    thread.start()
    print("Continuous Live Runner Started...")

# ------------------------
# API Endpoints
# ------------------------
@app.get("/")
def home():
    return {
        "message": "FastAPI Live Scheduler Running",
        "time": datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
    }

@app.get("/data")
def get_data():
    return {
        "AM": current_am,
        "PM": current_pm,
        "history": history
    }