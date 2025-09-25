from fastapi import FastAPI
from bs4 import BeautifulSoup
import requests
import datetime
import time

app = FastAPI()

# Myanmar timezone
TIMEZONE = datetime.timezone(datetime.timedelta(hours=6, minutes=30))

# Session data storage
current_am = {}
current_pm = {}
history = []

# Function to fetch live data
def get_live():
    url = "https://www.set.or.th/en/market/product/stock/overview"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    try:
        table = soup.find_all("table")[1]  
        set_index = table.find_all("div")[4]  
        value_index = table.find_all("div")[6]  

        live_set = set_index.get_text(strip=True)  
        live_value = value_index.get_text(strip=True)  

        clean_set = live_set.replace(",", "")  
        formatted="{:.2f}".format(float(clean_set))  
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
        # Fetch fail fallback
        return {
            "date": "--",
            "time": "--",
            "set": "--",
            "value": "--",
            "twod": "--"
        }

# Background scheduler simulation (simple loop, can replace with APScheduler)
import threading

def live_scheduler():
    global current_am, current_pm, history
    while True:
        now_time = datetime.datetime.now(TIMEZONE).strftime("%H:%M:%S")
        
        # 08:50 reset placeholder
        if "08:50:00" <= now_time < "09:00:00":
            placeholder = {"date":"--","time":"--","set":"--","value":"--","twod":"--"}
            current_am = placeholder
            current_pm = placeholder
        
        # AM session running 09:00 → 12:01
        elif "09:00:00" <= now_time <= "12:01:00":
            live = get_live()
            current_am = live
            current_pm = {"date":"--","time":"--","set":"--","value":"--","twod":"--"}
        
        # PM session running 13:00 → 16:30
        elif "13:00:00" <= now_time <= "16:30:00":
            live = get_live()
            current_pm = live
        
        # AM finished at 12:01
        if now_time == "12:01:00":
            history.append({"session":"AM", **current_am})
        
        # PM finished at 16:30
        if now_time == "16:30:00":
            history.append({"session":"PM", **current_pm})
        
        time.sleep(4)  # 4 seconds interval

# Start background thread
threading.Thread(target=live_scheduler, daemon=True).start()

# Status endpoint
@app.get("/")
def root():
    return {"message": "FastAPI Live Scheduler Running", "time": datetime.datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")}

# Data endpoint
@app.get("/data")
def data():
    now_time = datetime.datetime.now(TIMEZONE).strftime("%H:%M:%S")
    
    # 08:50 → 09:00 reset placeholder
    if "08:50:00" <= now_time < "09:00:00":
        placeholder = {"date":"--","time":"--","set":"--","value":"--","twod":"--"}
        return {"AM": placeholder, "PM": placeholder, "history": history}
    
    # AM session
    elif "09:00:00" <= now_time <= "12:01:00":
        pm_placeholder = {"date":"--","time":"--","set":"--","value":"--","twod":"--"}
        return {"AM": current_am, "PM": pm_placeholder, "history": history}
    
    # PM session
    elif "13:00:00" <= now_time <= "16:30:00":
        return {"AM": current_am, "PM": current_pm, "history": history}
    
    # Other time
    else:
        return {"AM": current_am, "PM": current_pm, "history": history}