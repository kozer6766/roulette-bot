from collections import Counter
from database import get_all_spins

EMOJI = {"red": "🔴", "black": "⚫", "green": "🟢"}
COLOR_RU = {"red": "Красный", "black": "Чёрный", "green": "Зеро"}


def get_stats():
    spins = get_all_spins()
    if not spins:
        return None

    numbers = [s[0] for s in spins]
    colors = [s[1] for s in spins]
    total = len(numbers)
    number_counter = Counter(numbers)
    color_counter = Counter(colors)

    low = sum(1 for n in numbers if 1 <= n <= 18)
    high = sum(1 for n in numbers if 19 <= n <= 36)
    zero = sum(1 for n in numbers if n == 0)
    even = sum(1 for n in numbers if n != 0 and n % 2 == 0)
    odd = sum(1 for n in numbers if n != 0 and n % 2 == 1)
    dozens = [
        sum(1 for n in numbers if 1 <= n <= 12),
        sum(1 for n in numbers if 13 <= n <= 24),
        sum(1 for n in numbers if 25 <= n <= 36),
    ]

    return {
        "total": total,
        "top_numbers": number_counter.most_common(5),
        "color_pct": {c: round(color_counter.get(c, 0) / total * 100, 1)
                      for c in ("red", "black", "green")},
        "range_pct": {
            "low": round(low / total * 100, 1),
            "high": round(high / total * 100, 1),
            "zero": round(zero / total * 100, 1),
        },
        "parity_pct": {
            "even": round(even / total * 100, 1),
            "odd": round(odd / total * 100, 1),
        },
        "dozen_pct": {
            "d1": round(dozens[0] / total * 100, 1),
            "d2": round(dozens[1] / total * 100, 1),
            "d3": round(dozens[2] / total * 100, 1),
        },
        "last": spins[:10],
    }


def format_stats(stats):
    if not stats:
        return (
            "📊 <b>СТАТИСТИКА КАЗИНО</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Пока нет данных.\n\n"
            "Добавь результаты, например: <code>7 18 15 5 35</code>"
        )

    text = (
        f"📊 <b>СТАТИСТИКА РУЛЕТКИ</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎲 Всего спинов: <b>{stats['total']}</b>\n\n"
        f"🎨 <b>Цвета</b>\n"
        f"🔴 Красный — <b>{stats['color_pct']['red']}%</b>\n"
        f"⚫ Чёрный — <b>{stats['color_pct']['black']}%</b>\n"
        f"🟢 Зеро — <b>{stats['color_pct']['green']}%</b>\n\n"
        f"📉 <b>Диапазоны</b>\n"
        f"1–18 — <b>{stats['range_pct']['low']}%</b>\n"
        f"19–36 — <b>{stats['range_pct']['high']}%</b>\n"
        f"Зеро — <b>{stats['range_pct']['zero']}%</b>\n\n"
        f"⚖️ <b>Чётность</b>\n"
        f"Чётные — <b>{stats['parity_pct']['even']}%</b>\n"
        f"Нечётные — <b>{stats['parity_pct']['odd']}%</b>\n\n"
        f"🎯 <b>Дюжины</b>\n"
        f"1–12 — <b>{stats['dozen_pct']['d1']}%</b>  ·  "
        f"13–24 — <b>{stats['dozen_pct']['d2']}%</b>  ·  "
        f"25–36 — <b>{stats['dozen_pct']['d3']}%</b>\n\n"
        f"🔥 <b>Чаще выпадали</b>\n"
    )
    text += "\n".join(
        f"• <b>{number}</b> — {count} раз"
        for number, count in stats["top_numbers"]
    )
    text += "\n\n🕒 <b>Последние спины</b>\n"
    text += "  ·  ".join(
        f"{EMOJI[color]}{number}" for number, color, _ in stats["last"]
    )
    text += "\n\n<i>Это история результатов, а не гарантия будущего исхода.</i>"
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
    top_color = max(("red", "black", "green"),
                    key=lambda c: color_counter.get(c, 0))
    color_pct = round(color_counter.get(top_color, 0) / total * 100)

    low = sum(1 for n in numbers if 1 <= n <= 18)
    high = sum(1 for n in numbers if 19 <= n <= 36)
    top_range = "1–18" if low > high else "19–36" if high > low else "поровну"

    even = sum(1 for n in numbers if n != 0 and n % 2 == 0)
    odd = sum(1 for n in numbers if n != 0 and n % 2 == 1)
    top_parity = "Чётные" if even > odd else "Нечётные" if odd > even else "поровну"

    return {
        "top_numbers": top_numbers,
        "top_color": top_color,
        "top_color_emoji": EMOJI[top_color],
        "color_pct": color_pct,
        "top_range": top_range,
        "top_parity": top_parity,
        "total": total,
    }


def format_prediction(pred):
    if not pred:
        return (
            "🔮 <b>АНАЛИЗ ЧАСТОТ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Пока мало данных. Добавь хотя бы 5 результатов."
        )

    nums = "  ·  ".join(str(n) for n in pred["top_numbers"])
    return (
        f"🔮 <b>АНАЛИЗ ПОСЛЕДНИХ {pred['total']} СПИНОВ</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎨 Чаще встречался цвет: {pred['top_color_emoji']} "
        f"<b>{COLOR_RU[pred['top_color']]}</b> ({pred['color_pct']}%)\n\n"
        f"📉 Диапазон: <b>{pred['top_range']}</b>\n"
        f"⚖️ Чётность: <b>{pred['top_parity']}</b>\n"
        f"🔥 Частые числа: <b>{nums}</b>\n\n"
        f"<i>Рулетка случайна: статистика не предсказывает следующий результат.</i>"
    )
