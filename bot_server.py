import asyncio
import os
from threading import Thread

from flask import Flask
import bot as bot_module  # Импортируем наш файл bot.py

app = Flask(__name__)

@app.route('/')
def health():
    return "Bot is running!"

@app.route('/health')
def health_check():
    return "OK"

def run_bot():
    # Запускаем polling в отдельном потоке
    asyncio.run(bot_module.main())

if __name__ == "__main__":
    # Запускаем бота в фоновом режиме
    bot_thread = Thread(target=run_bot)
    bot_thread.start()

    # Запускаем Flask-сервер, который слушает порт Render
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
