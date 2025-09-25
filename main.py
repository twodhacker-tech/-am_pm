from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import pytz
import time

TIMEZONE = pytz.timezone("Asia/Yangon")
scheduler = BackgroundScheduler(timezone=TIMEZONE)

last_am = None
last_pm = None


def job_live():
    """4 စက္ကန့် တစ်ကြိမ် run, section အလိုက် သတ်မှတ်ချိန်မှာပဲ update"""
    global last_am, last_pm
    now = datetime.datetime.now(TIMEZONE)
    current_time = now.strftime("%H:%M:%S")

    # Live data ယူ
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
        # အချိန်မကျသေးရင် run မလုပ်ပါ
        print(f"[WAIT] {current_time}")


def close_am():
    """12:01 မှာ AM နောက်ဆုံး data သိမ်း"""
    global last_am
    if last_am:
        data = load_data()
        data["AM"] = last_am
        data["history"].append({"session": "AM", **last_am})
        save_data(data)
        print(f"[AM CLOSED] saved at 12:01 -> {last_am}")
        last_am = None


def close_pm():
    """16:30 မှာ PM နောက်ဆုံး data သိမ်း"""
    global last_pm
    if last_pm:
        data = load_data()
        data["PM"] = last_pm
        data["history"].append({"session": "PM", **last_pm})
        save_data(data)
        print(f"[PM CLOSED] saved at 16:30 -> {last_pm}")
        last_pm = None


def start_scheduler():
    # 4 စက္ကန့် တစ်ကြိမ် run
    scheduler.add_job(job_live, "interval", seconds=4, id="live_job")

    # AM close
    scheduler.add_job(close_am, "cron", hour=12, minute=1, second=0)

    # PM close
    scheduler.add_job(close_pm, "cron", hour=16, minute=30, second=0)

    scheduler.start()
    print("Scheduler started...")


if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()