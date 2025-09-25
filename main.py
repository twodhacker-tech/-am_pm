from fastapi import FastAPI
import datetime
import pytz
import time
import threading
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

last_am = None
last_pm = None

# ------------------------
# Utility Functions
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
        return {"AM": {}, "PM": {}, "history": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ------------------------
# AM / PM Save Functions
# ------------------------
def save_am_live(live):
    global last_am
    last_am = live
    data = load_data()
    data["AM"] = live
    save_data(data)
    print(f"[AM RUN] {live['time']} -> {live['twod']}")


def close_am():
    global last_am
    if last_am:
        data = load_data()
        data["AM"] = last_am
        data["history"].append({"session": "AM", **last_am})
        save_data(data)
        print(f"[AM CLOSED] {last_am['time']}")
        last_am = None


def save_pm_live(live):
    global last_pm
    last_pm = live
    data = load_data()
    data["PM"] = live
    save_data(data)
    print(f"[PM RUN] {live['time']} -> {live['twod']}")


def close_pm():
    global last_pm
    if last_pm:
        data = load_data()
        data["PM"] = last_pm
        data["history"].append({"session": "PM", **last_pm})
        save_data(data)
        print(f"[PM CLOSED] {last_pm['time']}")
        last_pm = None


# ------------------------
# Continuous Live Runner
# ------------------------
def run_live_continuous():
    while True:
        now = datetime.datetime.now(TIMEZONE)
        current_time = now.strftime("%H:%M:%S")

        # AM session
        if "09:00:00" <= current_time <= "12:01:00":
            live = get_live()
            save_am_live(live)
            if current_time == "12:01:00":
                close_am()

        # PM session
        elif "13:00:00" <= current_time <= "16:30:00":
            live = get_live()
            save_pm_live(live)
            if current_time == "16:30:00":
                close_pm()

        time.sleep(0.1)  # Continuous but CPU-friendly


# ------------------------
# FastAPI Startup Event
# ------------------------
@app.on_event("startup")
def start_background_task():
    thread = threading.Thread(target=run_live_continuous, daemon=True)
    thread.start()
    print("Continuous Live Runner Started...")


# ------------------------
# API Endpoints
# ------------------------
@app.get("/")
def home():
    return {"message": "FastAPI Live Scheduler Running", "time": datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")}


@app.get("/data")
def get_data():
    return load_data()