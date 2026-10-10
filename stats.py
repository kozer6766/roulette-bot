from collections import Counter
from database import get_all_spins


def get_stats():
    spins = get_all_spins()
    if not spins:
        return None

    numbers = [s[0] for s in spins]
    colors = [s[1] for s in spins]

    total = len(numbers)
    number_counter = Counter(numbers)
    color_counter = Counter(colors)

    top_numbers = number_counter.most_common(5)

    color_pct = {
        c: round(color_counter.get(c, 0) / total * 100, 1)
        for c in ("red", "black", "green")
    }

    low = sum(1 for n in numbers if 1 <= n <= 18)
    high = sum(1 for n in numbers if 19 <= n <= 36)
    zero = sum(1 for n in numbers if n == 0)

    range_pct = {
        "low": round(low / total * 100, 1),
        "high": round(high / total * 100, 1),
        "zero": round(zero / total * 100, 1),
    }

    even = sum(1 for n in numbers if n != 0 and n % 2 == 0)
    odd = sum(1 for n in numbers if n != 0 and n % 2 == 1)

    parity_pct = {
        "even": round(even / total * 100, 1),
        "odd": round(odd / total * 100, 1),
    }

    d1 = sum(1 for n in numbers if 1 <= n <= 12)
    d2 = sum(1 for n in numbers if 13 <= n <= 24)
    d3 = sum(1 for n in numbers if 25 <= n <= 36)

    dozen_pct = {
        "d1": round(d1 / total * 100, 1),
        "d2": round(d2 / total * 100, 1),
        "d3": round(d3 / total * 100, 1),
    }

    last = spins[:10]

    return {
        "total": total,
        "top_numbers": top_numbers,
        "color_pct": color_pct,
        "range_pct": range_pct,
        "parity_pct": parity_pct,
        "dozen_pct": dozen_pct,
        "last": last,
    }


def format_stats(stats):
    if not stats:
        return "Пока нет данных. Добавь первое число командой /add <число>."

    text = f"📊 *Статистика по {stats['total']} спинам*\n\n"

    text += "🎨 *Цвета:*\n"
    text += f"🔴 Красный: {stats['color_pct']['red']}%\n"
    text += f"⚫ Чёрный: {stats['color_pct']['black']}%\n"
    text += f"🟢 Зеро: {stats['color_pct']['green']}%\n\n"

    text += "📉 *Диапазоны:*\n"
    text += f"🔹 1–18: {stats['range_pct']['low']}%\n"
    text += f"🔸 19–36: {stats['range_pct']['high']}%\n"
    text += f"⚪ Зеро: {stats['range_pct']['zero']}%\n\n"

    text += "⚖️ *Чёт / Нечет:*\n"
    text += f"➗ Чётные: {stats['parity_pct']['even']}%\n"
    text += f"➖ Нечетные: {stats['parity_pct']['odd']}%\n\n"

    text += "🎯 *Дюжины:*\n"
    text += f"1️⃣ 1–12: {stats['dozen_pct']['d1']}%\n"
    text += f"2️⃣ 13–24: {stats['dozen_pct']['d2']}%\n"
    text += f"3️⃣ 25–36: {stats['dozen_pct']['d3']}%\n\n"

    text += "🔥 *Топ-5 чисел:*\n"
    for num, count in stats["top_numbers"]:
        text += f"{num} — {count} раз\n"

    text += "\n🕒 *Последние 10 спинов:*\n"
    emoji = {"red": "🔴", "black": "⚫", "green": "🟢"}
    line = " ".join(f"{emoji[c]}{n}" for n, c, _ in stats["last"])
    text += line

    return text


def get_prediction(limit=20):
    spins = get_all_spins()
    if len(spins) < 5:
        return None

    recent = spins[:limit]
    numbers = [s[0] for s in recent]
    colors = [s[1] for s in recent]

    counter = Counter(numbers)
    color_counter = Counter(colors)

    top_numbers = [num for num, _ in counter.most_common(5)]

    total = len(recent)
    top_color = max(
        ("red", "black", "green"),
        key=lambda c: color_counter.get(c, 0)
    )
    color_pct = round(color_counter.get(top_color, 0) / total * 100)

    emoji = {"red": "🔴", "black": "⚫", "green": "🟢"}[top_color]

    low = sum(1 for n in numbers if 1 <= n <= 18)
    high = sum(1 for n in numbers if 19 <= n <= 36)
    if low > high:
        top_range = "1–18"
    elif high > low:
        top_range = "19–36"
    else:
        top_range = "поровну"

    even = sum(1 for n in numbers if n != 0 and n % 2 == 0)
    odd = sum(1 for n in numbers if n != 0 and n % 2 == 1)
    if even > odd:
        top_parity = "Чётные"
    elif odd > even:
        top_parity = "Нечетные"
    else:
        top_parity = "поровну"

    return {
        "top_numbers": top_numbers,
        "top_color": top_color,
        "top_color_emoji": emoji,
        "color_pct": color_pct,
        "top_range": top_range,
        "top_parity": top_parity,
        "total": total,
    }


def format_prediction(pred):
    if not pred:
        return "Мало данных для прогноза. Добавь хотя бы 5 чисел."

    text = f"🔮 *Прогноз на основе последних {pred['total']} спинов*\n\n"

    text += "🎨 *Наиболее вероятный цвет:*\n"
    text += f"{pred['top_color_emoji']} {pred['top_color']} — {pred['color_pct']}%\n\n"

    text += "📉 *Наиболее частый диапазон:*\n"
    text += f"{pred['top_range']}\n\n"

    text += "⚖️ *Перевес:*\n"
    text += f"{pred['top_parity']}\n\n"

    text += "🔥 *Возможные числа:*\n"
    nums = " ".join(f"{n}" for n in pred["top_numbers"])
    text += nums + "\n\n"

    text += "_Это не предсказание, а статистика частот._"

    return text