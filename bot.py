import os
import re

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from database import init_db, add_spin, get_last_spins, clear_spins
from stats import get_stats, format_stats, get_prediction, format_prediction

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Не задана переменная окружения BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

COLORS = {"red": "🔴", "black": "⚫", "green": "🟢"}


def main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню в стиле казино."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="🔮 Анализ частот", callback_data="predict"),
        ],
        [
            InlineKeyboardButton(text="🎲 Последние спины", callback_data="last"),
            InlineKeyboardButton(text="➕ Как добавить", callback_data="help_add"),
        ],
        [
            InlineKeyboardButton(text="🗑️ Очистить историю", callback_data="clear"),
        ],
    ])


def navigation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="home"),
        ]
    ])


def clear_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, очистить", callback_data="clear_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="home"),
        ]
    ])


def home_text() -> str:
    return (
        "🎰 <b>ROULETTE CLUB</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📈 <b>Статистика и история рулетки</b>\n\n"
        "Отправь выпавшие числа через пробел, например:\n"
        "<code>7 18 15 5 35</code>\n\n"
        "Или выбери действие в меню ниже.\n\n"
        "⚠️ Частоты показывают прошлые результаты и не гарантируют будущие."
    )


async def show_home(target, edit: bool = False):
    """Показывает меню; target может быть Message или CallbackQuery.message."""
    if edit:
        try:
            await target.edit_text(
                home_text(), parse_mode="HTML", reply_markup=main_keyboard()
            )
            return
        except Exception:
            # Например, сообщение уже содержит такой же текст.
            pass
    await target.answer(home_text(), parse_mode="HTML", reply_markup=main_keyboard())


@dp.message(Command("start", "menu"))
async def cmd_start(message: Message):
    await show_home(message)


@dp.message(Command("add"))
async def cmd_add(message: Message):
    args = (message.text or "").split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("⚠️ Используй команду так: <code>/add 17</code>", parse_mode="HTML")
        return

    number = int(args[1])
    if not 0 <= number <= 36:
        await message.answer("⚠️ Число должно быть от 0 до 36.")
        return

    color = add_spin(number, message.from_user.id if message.from_user else None)
    await message.answer(
        f"✅ Результат записан: {COLORS[color]} <b>{number}</b>",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@dp.message(Command("last"))
async def cmd_last(message: Message):
    await send_last(message)


@dp.message(Command("predict"))
async def cmd_predict(message: Message):
    await message.answer(
        format_prediction(get_prediction()),
        parse_mode="HTML",
        reply_markup=navigation_keyboard(),
    )


@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    await message.answer(
        "🗑️ <b>Очистить всю историю спинов?</b>\nЭто действие нельзя отменить.",
        parse_mode="HTML",
        reply_markup=clear_confirmation_keyboard(),
    )


@dp.message(F.text.regexp(r"^\s*\d{1,2}(\s*[,;\s]\s*\d{1,2})*\s*$"))
async def quick_add(message: Message):
    nums = re.findall(r"\d{1,2}", message.text or "")
    added, skipped = [], []

    for num_str in nums:
        number = int(num_str)
        if 0 <= number <= 36:
            color = add_spin(number, message.from_user.id if message.from_user else None)
            added.append(f"{COLORS[color]} {number}")
        else:
            skipped.append(num_str)

    if added:
        await message.answer(
            f"🎲 <b>Записано результатов: {len(added)}</b>\n" + "  ·  ".join(added),
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )
    if skipped:
        await message.answer(
            "⚠️ Пропущены числа вне диапазона 0–36: " + ", ".join(skipped)
        )


async def send_last(target):
    spins = get_last_spins(10)
    if not spins:
        text = "🎲 <b>История пока пуста.</b>\nДобавь результат числом от 0 до 36."
    else:
        line = "  ·  ".join(f"{COLORS[color]} <b>{number}</b>" for number, color in spins)
        text = f"🎲 <b>ПОСЛЕДНИЕ {len(spins)} СПИНОВ</b>\n━━━━━━━━━━━━━━━━━━\n{line}"
    await target.answer(text, parse_mode="HTML", reply_markup=navigation_keyboard())


@dp.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
    await callback.answer()
    text = format_stats(get_stats())
    if callback.message:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=navigation_keyboard()
        )


@dp.callback_query(F.data == "predict")
async def cb_predict(callback: CallbackQuery):
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            format_prediction(get_prediction()),
            parse_mode="HTML",
            reply_markup=navigation_keyboard(),
        )


@dp.callback_query(F.data == "last")
async def cb_last(callback: CallbackQuery):
    await callback.answer()
    spins = get_last_spins(10)
    if not spins:
        text = "🎲 <b>История пока пуста.</b>\nДобавь результат числом от 0 до 36."
    else:
        line = "  ·  ".join(f"{COLORS[color]} <b>{number}</b>" for number, color in spins)
        text = f"🎲 <b>ПОСЛЕДНИЕ {len(spins)} СПИНОВ</b>\n━━━━━━━━━━━━━━━━━━\n{line}"
    if callback.message:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=navigation_keyboard()
        )


@dp.callback_query(F.data == "help_add")
async def cb_help_add(callback: CallbackQuery):
    await callback.answer()
    text = (
        "➕ <b>КАК ДОБАВИТЬ РЕЗУЛЬТАТЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Можно отправить одно число:\n<code>/add 17</code>\n\n"
        "Или несколько чисел через пробел:\n<code>7 18 15 5 35</code>\n\n"
        "Допустимые значения: от 0 до 36."
    )
    if callback.message:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=navigation_keyboard()
        )


@dp.callback_query(F.data == "clear")
async def cb_clear(callback: CallbackQuery):
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            "🗑️ <b>Очистить всю историю спинов?</b>\nЭто действие нельзя отменить.",
            parse_mode="HTML",
            reply_markup=clear_confirmation_keyboard(),
        )


@dp.callback_query(F.data == "clear_confirm")
async def cb_clear_confirm(callback: CallbackQuery):
    clear_spins()
    await callback.answer("История очищена")
    if callback.message:
        await callback.message.edit_text(
            "🗑️ <b>История очищена.</b>\nМожно начинать новую запись результатов.",
            parse_mode="HTML",
            reply_markup=navigation_keyboard(),
        )


@dp.callback_query(F.data.in_({"home", "back"}))
async def cb_home(callback: CallbackQuery):
    await callback.answer()
    if callback.message:
        await show_home(callback.message, edit=True)


async def main():
    init_db()
    print("Бот готов к работе через webhook.")
