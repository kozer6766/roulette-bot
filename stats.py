from collections import Counter
from database import get_all_spins

EMOJI = {"red": "🔴", "black": "⚫", "green": "🟢"}
COLOR_RU = {
    "red": "Красный",
    "black": "Чёрный",
    "green": "Зеро",
}


def get_stats():
    spins = get_all_spins()
    if not spins:
        return None

    numbers = [int(s[0]) for s in spins]
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
        "color_pct": {
            c: round(color_counter.get(c, 0) / total * 100, 1)
            for c in ("red", "black", "green")
        },
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
            "📊 <b>СТАТИСТИКА РУЛЕТКИ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Пока нет данных.\n\n"
            "Добавь результаты, например: "
            "<code>7 18 15 5 35</code>"
        )

    text = (
        "📊 <b>СТАТИСТИКА РУЛЕТКИ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🎲 Всего спинов: <b>{stats['total']}</b>\n\n"
        "🎨 <b>Цвета</b>\n"
        f"🔴 Красный — <b>{stats['color_pct']['red']}%</b>\n"
        f"⚫ Чёрный — <b>{stats['color_pct']['black']}%</b>\n"
        f"🟢 Зеро — <b>{stats['color_pct']['green']}%</b>\n\n"
        "📉 <b>Диапазоны</b>\n"
        f"1–18 — <b>{stats['range_pct']['low']}%</b>\n"
        f"19–36 — <b>{stats['range_pct']['high']}%</b>\n"
        f"Зеро — <b>{stats['range_pct']['zero']}%</b>\n\n"
        "⚖️ <b>Чётность</b>\n"
        f"Чётные — <b>{stats['parity_pct']['even']}%</b>\n"
        f"Нечётные — <b>{stats['parity_pct']['odd']}%</b>\n\n"
        "🎯 <b>Дюжины</b>\n"
        f"1–12 — <b>{stats['dozen_pct']['d1']}%</b> · "
        f"13–24 — <b>{stats['dozen_pct']['d2']}%</b> · "
        f"25–36 — <b>{stats['dozen_pct']['d3']}%</b>\n\n"
        "🔥 <b>Чаще выпадали</b>\n"
    )

    text += "\n".join(
        f"• <b>{number}</b> — {count} раз"
        for number, count in stats["top_numbers"]
    )

    text += "\n\n🕒 <b>Последние спины</b>\n"
    text += " · ".join(
        f"{EMOJI.get(color, '🎲')}{number}"
        for number, color, *_ in stats["last"]
    )

    text += (
        "\n\n<i>История показывает прошлые результаты, "
        "но не гарантирует будущий исход.</i>"
    )
    return text


def _rank_candidates(history, method):
    """Возвращает семь кандидатов, исключая последнее число."""
    candidates = [
        n for n in range(37)
        if not history or n != history[-1]
    ]

    if not candidates:
        return []

    recent = history[-50:]
    counts = Counter(recent)
    scores = {n: 0.0 for n in candidates}

    if method == "frequency":
        for n in candidates:
            scores[n] = counts[n]

    elif method == "weighted":
        # Взвешиваем недавние результаты сильнее старых.
        for index, number in enumerate(recent):
            if number in scores:
                weight = (index + 1) / len(recent)
                scores[number] += weight

                
    elif method == "sequence":
        # Проверяем, какие числа следовали за таким же
        # предыдущим числом в исторических последовательностях.
        if history:
            previous = history[-1]
            for index in range(len(history) - 1):
                if history[index] == previous:
                    following = history[index + 1]
                    if following in scores:
                        scores[following] += 1

        for number in candidates:
            scores[number] += counts[number] * 0.1

    # При равном счёте порядок разрешается по номеру.
    ranked = sorted(
        candidates,
        key=lambda number: (scores[number], -number),
        reverse=True,
    )
    return ranked[:7]


def _backtest(spins):
    """Проверяет прошлые прогнозы только на будущих для них спинах."""
    methods = ("frequency", "weighted", "sequence")
    hits = {method: 0 for method in methods}

    # Тестируем максимум последние 100 спинов.
    start = max(5, len(spins) - 100)
    tested = 0

    for index in range(start, len(spins)):
        history = spins[:index]
        actual = spins[index]

        for method in methods:
            candidates = _rank_candidates(history, method)
            if actual in candidates:
                hits[method] += 1

        tested += 1

    if tested == 0:
        return "frequency", 0, 0

    # При равенстве результатов порядок методов остаётся стабильным.
    best = max(methods, key=lambda method: hits[method])
    return best, hits[best], tested


def get_prediction(limit=50):
    spins = get_all_spins()

    if len(spins) < 6:
        return None

    # База данных хранит новые результаты первыми.
    # Для проверки последовательностей разворачиваем историю.
    chronological = [
        int(spin[0])
        for spin in reversed(spins)
    ]

    # Проверка метода по предыдущим результатам.
    method, hits, tested = _backtest(chronological)

    # Прогноз строится по последним 50 спинам.
    recent = chronological[-50:]
    top_numbers = _rank_candidates(recent, method)

    method_names = {
        "frequency": "Частоты",
        "weighted": "Взвешенные частоты",
        "sequence": "Повторяющиеся переходы",
    }

    return {
        "top_numbers": top_numbers,
        "method": method_names[method],
        "tested": tested,
        "hits": hits,
        "hit_pct": round(hits / tested * 100, 1)
        if tested else 0,
        "total": len(recent),
        "last_number": recent[-1],
    }


def format_prediction(pred):
    if not pred:
        return (
            "🔮 <b>АНАЛИЗ РУЛЕТКИ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Нужно минимум 6 результатов для анализа."
        )

    numbers = pred["top_numbers"]
    nums = " · ".join(str(number) for number in numbers)

    text = (
        "🔮 <b>АНАЛИЗ РУЛЕТКИ — ТОП-7</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📚 История анализа: <b>{pred['total']} спинов</b>\n"
        f"🚫 Последнее число исключено: "
        f"<b>{pred['last_number']}</b>\n\n"
        f"🎯 <b>7 кандидатов:</b>\n"
        f"<code>{nums}</code>\n\n"
        f"🧠 Метод: <b>{pred['method']}</b>\n"
    )

    if pred["tested"] > 0:
        text += (
            f"🧪 Проверено прошлых прогнозов: "
            f"<b>{pred['tested']}</b>\n"
            f"✅ Попаданий в топ-7: <b>{pred['hits']}</b>\n"
            f"📊 Доля попаданий: <b>{pred['hit_pct']}%</b>\n"
        )
    else:
        text += (
            "🧪 Пока недостаточно истории для "
            "проверки методов.\n"
        )

    text += (
        "\n<i>Это статистический эксперимент. "
        "На честной рулетке прошлые результаты "
        "не позволяют надёжно предсказать следующий спин.</i>"
    )

    return text
