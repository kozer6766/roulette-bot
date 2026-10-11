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

from database import (
    init_db,
    add_spin,
    get_last_spins,
    clear_spins,
    save_prediction,
    get_prediction_stats,
)
from stats import (
    get_stats,
    format_stats,
    get_prediction,
    format_prediction,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Не задана переменная окружения BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

COLORS = {
    "red": "🔴",
    "black": "⚫",
    "green": "🟢",
}


# =========================
# КЛАВИАТУРЫ
# =========================

def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data="stats",
            ),
            InlineKeyboardButton(
                text="🔮 Анализ частот",
                callback_data="predict",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎲 Последние спины",
                callback_data="last",
            ),
            InlineKeyboardButton(
                text="➕ Как добавить",
                callback_data="help_add",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📈 Статистика прогнозов",
                callback_data="tracking",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Очистить историю",
                callback_data="clear",
            ),
        ],
    ])


def navigation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back",
            ),
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="home",
            ),
        ]
    ])


def prediction_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💾 Сохранить прогноз",
                callback_data="save_prediction",
            ),
        ],
        [
            InlineKeyboardButton(
                text="📈 Статистика прогнозов",
                callback_data="tracking",
            ),
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="back",
            ),
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="home",
            ),
        ],
    ])


def clear_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Да, очистить",
                callback_data="clear_confirm",
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="home",
            ),
        ]
    ])


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

def home_text() -> str:
    return (
        "🎰 <b>ROULETTE CLUB</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📈 Статистика и история рулетки\n\n"
        "Отправь выпавшие числа через пробел, например:\n"
        "<code>7 18 15 5 35</code>\n\n"
        "Или используй команду: <code>/add 17</code>\n\n"
        "Выбери действие в меню ниже.\n\n"
        "⚠️ Частоты и прогнозы основаны на прошлых результатах "
        "и не гарантируют будущие."
    )


async def show_home(target, edit: bool = False):
    if edit:
        try:
            await target.edit_text(
                home_text(),
                parse_mode="HTML",
                reply_markup=main_keyboard(),
            )
            return
        except Exception:
            pass

await target.answer(
        home_text(),
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@dp.message(Command("start", "menu"))
async def cmd_start(message: Message):
    await show_home(message)


# =========================
# ДОБАВЛЕНИЕ РЕЗУЛЬТАТОВ
# =========================

@dp.message(Command("add"))
async def cmd_add(message: Message):
    args = (message.text or "").split()

    if len(args) != 2 or not args[1].isdigit():
        await message.answer(
            "⚠️ Используй команду так: <code>/add 17</code>",
            parse_mode="HTML",
        )
        return

    number = int(args[1])

    if not 0 <= number <= 36:
        await message.answer(
            "⚠️ Число должно быть от 0 до 36."
        )
        return

    user_id = message.from_user.id if message.from_user else None
    color = add_spin(number, user_id)

    await message.answer(
        f"✅ Результат записан: {COLORS[color]} {number}\n"
        "Сохранённые прогнозы проверены по новому результату.",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@dp.message(F.text.regexp(r"^\s*\d{1,2}(\s*[,;\s]\s*\d{1,2})*\s*$"))
async def quick_add(message: Message):
    nums = re.findall(r"\d{1,2}", message.text or "")
    added = []
    skipped = []

    user_id = message.from_user.id if message.from_user else None

    for num_str in nums:
        number = int(num_str)

        if 0 <= number <= 36:
            color = add_spin(number, user_id)
            added.append(f"{COLORS[color]} {number}")
        else:
            skipped.append(num_str)

    if added:
        await message.answer(
            f"🎲 Записано результатов: {len(added)}\n"
            + " · ".join(added),
            parse_mode="HTML",
            reply_markup=main_keyboard(),
        )

    if skipped:
        await message.answer(
            "⚠️ Пропущены числа вне диапазона 0–36: "
            + ", ".join(skipped)
        )


# =========================
# ПОСЛЕДНИЕ СПИНЫ
# =========================

async def send_last(target):
    spins = get_last_spins(10)

    if not spins:
        text = (
            "🎲 История пока пуста.\n"
            "Добавь результат числом от 0 до 36."
        )
    else:
        line = " · ".join(
            f"{COLORS[color]} {number}"
            for number, color in spins
        )
        text = (
            f"🎲 <b>ПОСЛЕДНИЕ {len(spins)} СПИНОВ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"{line}"
        )

    await target.answer(
        text,
        parse_mode="HTML",
        reply_markup=navigation_keyboard(),
    )


@dp.message(Command("last"))
async def cmd_last(message: Message):
    await send_last(message)


@dp.callback_query(F.data == "last")
async def cb_last(callback: CallbackQuery):
    await callback.answer()
    spins = get_last_spins(10)

    if not spins:
        text = (
            "🎲 История пока пуста.\n"
            "Добавь результат числом от 0 до 36."
        )
    else:
        line = " · ".join(
            f"{COLORS[color]} {number}"
            for number, color in spins
        )
        text = (
            f"🎲 <b>ПОСЛЕДНИЕ {len(spins)} СПИНОВ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"{line}"
        )

    if callback.message:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=navigation_keyboard(),
        )


# =========================
# ОБЩАЯ СТАТИСТИКА
# =========================

@dp.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
    await callback.answer()

    text = format_stats(get_stats())

    if callback.message:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=navigation_keyboard(),
        )


# =========================
# АНАЛИЗ И СОХРАНЕНИЕ ПРОГНОЗА
# =========================

@dp.message(Command("predict"))
async def cmd_predict(message: Message):
    prediction = get_prediction()

await message.answer(
        format_prediction(prediction),
        parse_mode="HTML",
        reply_markup=(
            prediction_keyboard()
            if prediction and prediction.get("candidates")
            else navigation_keyboard()
        ),
    )


@dp.callback_query(F.data == "predict")
async def cb_predict(callback: CallbackQuery):
    await callback.answer()

    prediction = get_prediction()

    if callback.message:
        await callback.message.edit_text(
            format_prediction(prediction),
            parse_mode="HTML",
            reply_markup=(
                prediction_keyboard()
                if prediction and prediction.get("candidates")
                else navigation_keyboard()
            ),
        )


@dp.callback_query(F.data == "save_prediction")
async def cb_save_prediction(callback: CallbackQuery):
    await callback.answer()

    if not callback.from_user:
        return

    prediction = get_prediction()

    if not prediction or not prediction.get("candidates"):
        if callback.message:
            await callback.message.answer(
                "⚠️ Пока нет готового прогноза для сохранения. "
                "Добавь результаты и попробуй снова."
            )
        return

    # В stats.py кандидаты представлены словарями с ключом number.
    candidates = [
        item["number"]
        for item in prediction["candidates"]
        if isinstance(item, dict) and "number" in item
    ]

    if not candidates:
        if callback.message:
            await callback.message.answer(
                "⚠️ Не удалось получить числа прогноза. "
                "Проверь формат данных в stats.py."
            )
        return

    method = str(prediction.get("best_method", "unknown"))

    save_prediction(
        callback.from_user.id,
        candidates,
        method,
    )

    if callback.message:
        numbers_text = ", ".join(map(str, candidates))
        await callback.message.answer(
            "💾 <b>Прогноз сохранён!</b>\n\n"
            f"Кандидаты: <code>{numbers_text}</code>\n\n"
            "Следующий добавленный результат будет использован "
            "для проверки этого прогноза.\n"
            "Посмотреть попадания можно в разделе "
            "«📈 Статистика прогнозов».",
            parse_mode="HTML",
            reply_markup=navigation_keyboard(),
        )


# =========================
# СТАТИСТИКА ПОПАДАНИЙ
# =========================

def format_tracking_stats(user_id: int) -> str:
    data = get_prediction_stats(user_id)

    total = data.get("total", 0)
    evaluated = data.get("evaluated", 0)
    hits = data.get("hits", 0)
    misses = data.get("misses", 0)
    pending = data.get("pending", 0)
    hit_rate = data.get("hit_rate", 0)

    if evaluated:
        rate_text = f"{hit_rate:.1f}%"
    else:
        rate_text = "пока нет проверенных прогнозов"

    return (
        "📈 <b>СТАТИСТИКА ПРОГНОЗОВ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💾 Всего сохранено: <b>{total}</b>\n"
        f"✅ Попадания: <b>{hits}</b>\n"
        f"❌ Промахи: <b>{misses}</b>\n"
        f"⏳ Ожидают проверки: <b>{pending}</b>\n"
        f"🔎 Проверено: <b>{evaluated}</b>\n"
        f"🎯 Процент попаданий: <b>{rate_text}</b>\n\n"
        "Попадание означает, что следующий записанный результат "
        "входил в сохранённый список кандидатов.\n\n"
        "⚠️ Прошлые результаты не гарантируют будущие."
    )


@dp.message(Command("tracking"))
async def cmd_tracking(message: Message):
    if not message.from_user:
        return

    await message.answer(
        format_tracking_stats(message.from_user.id),
        parse_mode="HTML",
        reply_markup=navigation_keyboard(),
    )


@dp.callback_query(F.data == "tracking")
async def cb_tracking(callback: CallbackQuery):
    await callback.answer()

    if callback.message and callback.from_user:
        await callback.message.edit_text(
            format_tracking_stats(callback.from_user.id),
            parse_mode="HTML",
            reply_markup=navigation_keyboard(),
        )

# =========================
# ПОМОЩЬ
# =========================

@dp.callback_query(F.data == "help_add")
async def cb_help_add(callback: CallbackQuery):
    await callback.answer()

    text = (
        "➕ <b>КАК ДОБАВИТЬ РЕЗУЛЬТАТЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Одно число:\n"
        "<code>/add 17</code>\n\n"
        "Несколько чисел через пробел:\n"
        "<code>7 18 15 5 35</code>\n\n"
        "Допустимые значения: от 0 до 36.\n\n"
        "Чтобы сохранить прогноз, открой «🔮 Анализ частот» "
        "и нажми «💾 Сохранить прогноз».\n"
        "Команда статистики прогнозов: <code>/tracking</code>."
    )

    if callback.message:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=navigation_keyboard(),
        )


# =========================
# ОЧИСТКА ИСТОРИИ
# =========================

@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    await message.answer(
        "🗑️ Очистить всю историю спинов?\n"
        "Это действие нельзя отменить.",
        parse_mode="HTML",
        reply_markup=clear_confirmation_keyboard(),
    )


@dp.callback_query(F.data == "clear")
async def cb_clear(callback: CallbackQuery):
    await callback.answer()

    if callback.message:
        await callback.message.edit_text(
            "🗑️ Очистить всю историю спинов?\n"
            "Это действие нельзя отменить.",
            parse_mode="HTML",
            reply_markup=clear_confirmation_keyboard(),
        )


@dp.callback_query(F.data == "clear_confirm")
async def cb_clear_confirm(callback: CallbackQuery):
    clear_spins()
    await callback.answer("История очищена")

    if callback.message:
        await callback.message.edit_text(
            "🗑️ История очищена.\n"
            "Можно начинать новую запись результатов.",
            parse_mode="HTML",
            reply_markup=navigation_keyboard(),
        )


# =========================
# ВОЗВРАТ В МЕНЮ
# =========================

@dp.callback_query(F.data.in_({"home", "back"}))
async def cb_home(callback: CallbackQuery):
    await callback.answer()

    if callback.message:
        await show_home(callback.message, edit=True)


# =========================
# ЗАПУСК
# =========================

async def main():
    init_db()
    print("Бот готов к работе через webhook.")
