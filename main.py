from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import pytz
import time
import os
import json
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

last_am = None
last_pm = None

# ------------------------
# Utility functions
# ------------------------
def get_live():
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


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"live": {}, "AM": {}, "PM": {}, "history": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ------------------------
# Scheduler Jobs
# ------------------------
def job_live():
    global last_am, last_pm
    now = datetime.datetime.now(TIMEZONE)
    current_time = now.strftime("%H:%M:%S")

    live = get_live()
    data = load_data()
    data["live"] = live
    save_data(data)

    # AM Section
    if "09:00:00" <= current_time <= "12:01:00":
        last_am = live
        print(f"[AM RUN] {live['time']} -> {live['twod']}")

    # PM Section
    elif "12:30:00" <= current_time <= "16:30:00":
        last_pm = live
        print(f"[PM RUN] {live['time']} -> {live['twod']}")

    else:
        print(f"[WAIT] {current_time}")


def close_am():
    global last_am
    if last_am:
        data = load_data()
        data["AM"] = last_am
        data["history"].append({"session": "AM", **last_am})
        save_data(data)
        print(f"[AM CLOSED] saved at 12:01 -> {last_am}")
        last_am = None


def close_pm():
    global last_pm
    if last_pm:
        data = load_data()
        data["PM"] = last_pm
        data["history"].append({"session": "PM", **last_pm})
        save_data(data)
        print(f"[PM CLOSED] saved at 16:30 -> {last_pm}")
        last_pm = None

# ------------------------
# FastAPI Startup Event
# ------------------------
scheduler = BackgroundScheduler(timezone=TIMEZONE)

@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(job_live, "interval", seconds=4)  # run every 4 sec
    scheduler.add_job(close_am, "cron", hour=12, minute=1, second=0)
    scheduler.add_job(close_pm, "cron", hour=16, minute=30, second=0)
    scheduler.start()
    print("Scheduler started...")

# ------------------------
# API Endpoints
# ------------------------
@app.get("/")
def home():
    return {"message": "FastAPI Scheduler Running", "time": time.strftime("%Y-%m-%d %H:%M:%S")}

@app.get("/data")
def get_data():
    return load_data()