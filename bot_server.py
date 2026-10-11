import asyncio
import os
import traceback
from threading import Thread

import requests
from flask import Flask, request
from aiogram.types import Update

import bot as bot_module
from database import init_db

app = Flask(__name__)

# Лучше задать WEBHOOK_SECRET в Environment на Render.
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "my-secret-token-123")

bot_loop = asyncio.new_event_loop()


def run_bot_loop():
    asyncio.set_event_loop(bot_loop)
    bot_loop.run_forever()


Thread(target=run_bot_loop, daemon=True).start()

# Создаём таблицу при старте сервиса.
init_db()


@app.route("/")
def health():
    return "Roulette bot is running!"


@app.route("/health")
def health_check():
    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return "Unauthorized", 401

    try:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return "Invalid JSON", 400

        update = Update.model_validate(payload)
        future = asyncio.run_coroutine_threadsafe(
            bot_module.dp.feed_update(bot_module.bot, update),
            bot_loop,
        )
        future.result(timeout=30)
        return "OK", 200
    except Exception:
        traceback.print_exc()
        return "Error", 500


def set_webhook():
    external_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    if not external_url:
        print("RENDER_EXTERNAL_URL не задан; webhook не установлен.")
        return
    if not bot_module.BOT_TOKEN:
        print("BOT_TOKEN не задан; webhook не установлен.")
        return

    webhook_url = f"{external_url}/webhook"
    api_url = f"https://api.telegram.org/bot{bot_module.BOT_TOKEN}/setWebhook"
    try:
        response = requests.post(
            api_url,
            json={"url": webhook_url, "secret_token": WEBHOOK_SECRET},
            timeout=15,
        )
        print(f"setWebhook: HTTP {response.status_code} {response.text}")
        print(f"Webhook URL: {webhook_url}")
    except requests.RequestException:
        traceback.print_exc()


if __name__ == "__main__":
    Thread(target=set_webhook, daemon=True).start()
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)
