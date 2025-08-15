import os
import requests
import schedule
import time
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ROUTES = [
    ("MOW", "LED", "2025-09-10"),
    ("LED", "MOW", "2025-09-15"),
]

CSV_FILE = "price_history.csv"
last_prices = {}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

def send_telegram_photo(photo_path, caption=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": open(photo_path, "rb")}
    data = {"chat_id": CHAT_ID, "caption": caption}
    requests.post(url, files=files, data=data)

def fetch_price(origin, destination, date):
    url = f"https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    params = {
        "origin": origin,
        "destination": destination,
        "departure_at": date,
        "currency": "rub",
        "token": API_TOKEN
    }
    r = requests.get(url, params=params)
    data = r.json()
    if "data" in data and data["data"]:
        return data["data"][0]["price"]
    return None

def update_history(origin, destination, date, price):
    df = pd.DataFrame([{
        "time": datetime.now(),
        "origin": origin,
        "destination": destination,
        "date": date,
        "price": price
    }])
    header = not os.path.exists(CSV_FILE)
    df.to_csv(CSV_FILE, mode='a', index=False, header=header)

def plot_history():
    if not os.path.exists(CSV_FILE):
        return
    df = pd.read_csv(CSV_FILE, parse_dates=["time"])
    for (orig, dest, date), group in df.groupby(["origin", "destination", "date"]):
        plt.figure()
        plt.plot(group["time"], group["price"], marker="o")
        plt.title(f"{orig} → {dest} ({date})")
        plt.xlabel("Время")
        plt.ylabel("Цена, ₽")
        plt.xticks(rotation=45)
        plt.tight_layout()
        path = f"plot_{orig}_{dest}_{date}.png"
        plt.savefig(path)
        send_telegram_photo(path, f"Динамика цен {orig} → {dest} ({date})")

def check_prices():
    global last_prices
    for origin, destination, date in ROUTES:
        price = fetch_price(origin, destination, date)
        if price:
            update_history(origin, destination, date, price)
            route_key = (origin, destination, date)
            if route_key not in last_prices:
                last_prices[route_key] = price
                send_telegram(f"Стартовая цена {origin} → {destination} ({date}): {price}₽")
            elif price < last_prices[route_key]:
                send_telegram(f"Цена упала {origin} → {destination} ({date}): {last_prices[route_key]}₽ → {price}₽")
                last_prices[route_key] = price

send_telegram("Бот запущен! Слежу за ценами...")
schedule.every(20).minutes.do(check_prices)
schedule.every().day.at("21:00").do(plot_history)

while True:
    schedule.run_pending()
    time.sleep(1)
