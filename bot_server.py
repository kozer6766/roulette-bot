import asyncio
import os
from threading import Thread

from flask import Flask, request
from aiogram.types import Update
import bot as bot_module

app = Flask(__name__)

WEBHOOK_SECRET = "my-secret-token-123"

bot_loop = asyncio.new_event_loop()
asyncio.set_event_loop(bot_loop)


def run_bot_loop():
    asyncio.set_event_loop(bot_loop)
    bot_loop.run_forever()


Thread(target=run_bot_loop, daemon=True).start()


@app.route('/')
def health():
    return "Bot is running!"


@app.route('/health')
def health_check():
    return "OK"


@app.route('/webhook', methods=['POST'])
def webhook():
    print("=== WEBHOOK ПОЛУЧЕН ===")
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return "Unauthorized", 401

    try:
        update = Update.model_validate(request.json, context={"bot": bot_module.bot})
        future = asyncio.run_coroutine_threadsafe(
            bot_module.dp.feed_update(bot_module.bot, update),
            bot_loop
        )
        future.result(timeout=30)
        return "OK", 200
    except Exception as e:
        import traceback
        print("=== ОШИБКА ===")
        print(traceback.format_exc())
        print("=== КОНЕЦ ОШИБКИ ===")
        return "Error", 500


def set_webhook():
    import time
    time.sleep(3)
    import requests
    webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook"
    url = f"https://api.telegram.org/bot{bot_module.BOT_TOKEN}/setWebhook"
    data = {"url": webhook_url, "secret_token": WEBHOOK_SECRET}
    requests.post(url, json=data)
    print(f"Webhook установлен на: {webhook_url}")


if __name__ == "__main__":
    Thread(target=set_webhook, daemon=True).start()

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
