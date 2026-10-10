import asyncio
import os
from threading import Thread

from flask import Flask, request
from aiogram.types import Update
import bot as bot_module

app = Flask(__name__)

# Важно: секретная строка, чтобы Telegram мог подтвердить, что это его запрос
WEBHOOK_SECRET = "my-secret-token-123"

@app.route('/')
def health():
    return "Bot is running!"

@app.route('/health')
def health_check():
    return "OK"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return "Unauthorized", 401
    
    # Передаем сообщение в aiogram для обработки
    update = Update.model_validate(request.json, context={"bot": bot_module.bot})
    asyncio.run(bot_module.dp.feed_update(bot_module.bot, update))
    return "OK", 200

def set_webhook():
    # Ждем, пока Flask поднимется, и ставим вебхук
    import time
    time.sleep(3)
    import requests
    # Render автоматически подставляет внешний URL в переменную RENDER_EXTERNAL_URL
    webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook"
    url = f"https://api.telegram.org/bot{bot_module.BOT_TOKEN}/setWebhook"
    data = {"url": webhook_url, "secret_token": WEBHOOK_SECRET}
    requests.post(url, json=data)
    print(f"Webhook установлен на: {webhook_url}")

if __name__ == "__main__":
    # Запускаем установку вебхука в фоне
    Thread(target=set_webhook).start()
    
    # Запускаем Flask-сервер
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
