import os
import re
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database import init_db, add_spin, get_last_spins, clear_spins
from stats import get_stats, format_stats, get_prediction, format_prediction

# 👇 ВСТАВЬ СВОЙ ТОКЕН СЮДА (между кавычками)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="🔮 Прогноз", callback_data="predict"),
        ],
        [
            InlineKeyboardButton(text="🕒 Последние 10", callback_data="last"),
            InlineKeyboardButton(text="🗑️ Очистить", callback_data="clear"),
        ],
    ])


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🎰 *Бот-статистик рулетки*\n\n"
        "Отправь числа через пробел — они добавятся в базу.\n"
        "Например: 7 18 15 5 35\n\n"
        "Или пользуйся кнопками ниже:",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )


@dp.message(Command("add"))
async def cmd_add(message: Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("⚠️ Используй так: /add 17", parse_mode="Markdown")
        return

    number = int(args[1])
    if not 0 <= number <= 36:
        await message.answer("⚠️ Число должно быть от 0 до 36.")
        return

    color = add_spin(number, message.from_user.id)
    emoji = {"red": "🔴", "black": "⚫", "green": "🟢"}[color]
    await message.answer(f"✅ Добавлено: {emoji} {number}", parse_mode="Markdown")


def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="🔮 Прогноз", callback_data="predict"),
        ],
        [
            InlineKeyboardButton(text="🕒 Последние 10", callback_data="last"),
            InlineKeyboardButton(text="🗑️ Очистить", callback_data="clear"),
        ],
    ])


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🎰 *Бот-статистик рулетки*\n\n"
        "Отправь числа через пробел — они добавятся в базу.\n"
        "Например: 7 18 15 5 35\n\n"
        "Или пользуйся кнопками ниже:",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )


@dp.message(Command("last"))
async def cmd_last(message: Message):
    spins = get_last_spins(10)
    if not spins:
        await message.answer("Пока нет данных.")
        return

    emoji = {"red": "🔴", "black": "⚫", "green": "🟢"}
    line = " ".join(f"{emoji[c]}{n}" for n, c in spins)
    await message.answer(f"🕒 *Последние 10:*\n{line}", parse_mode="Markdown")


@dp.message(Command("predict"))
async def cmd_predict(message: Message):
    pred = get_prediction()
    await message.answer(format_prediction(pred), parse_mode="Markdown")


@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    clear_spins()
    await message.answer("🗑️ База очищена.")


import re


@dp.message(F.text.regexp(r"^\s*\d{1,2}(\s*[,;\s]\s*\d{1,2})*\s*$"))
async def quick_add(message: Message):
    # Находим все числа в сообщении
    nums = re.findall(r"\d{1,2}", message.text)

    added = []
    skipped = []

    for num_str in nums:
        number = int(num_str)
        if 0 <= number <= 36:
            color = add_spin(number, message.from_user.id)
            emoji = {"red": "🔴", "black": "⚫", "green": "🟢"}[color]
            added.append(f"{emoji} {number}")
        else:
            skipped.append(num_str)

    if added:
        await message.answer(
            f"✅ Добавлено ({len(added)}):\n" + "\n".join(added),
            parse_mode="Markdown"
        )
    if skipped:
        await message.answer(
            f"⚠️ Пропущено (вне диапазона 0–36): {', '.join(skipped)}"
        )

@dp.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
    stats = get_stats()
    await callback.message.answer(format_stats(stats), parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "predict")
async def cb_predict(callback: CallbackQuery):
    pred = get_prediction()
    await callback.message.answer(format_prediction(pred), parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "last")
async def cb_last(callback: CallbackQuery):
    spins = get_last_spins(10)
    if not spins:
        await callback.message.answer("Пока нет данных.")
        await callback.answer()
        return

    emoji = {"red": "🔴", "black": "⚫", "green": "🟢"}
    line = " ".join(f"{emoji[c]}{n}" for n, c in spins)
    await callback.message.answer(f"🕒 *Последние 10:*\n{line}", parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "clear")
async def cb_clear(callback: CallbackQuery):
    clear_spins()
    await callback.message.answer("🗑️ База очищена.")
    await callback.answer()


async def main():
    init_db()
    print("Бот запущен...")
    # Polling убираем, теперь бота будет запускать bot_server.py через webhook
