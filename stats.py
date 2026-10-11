from collections import Counter, defaultdict
from database import get_all_spins

EMOJI = {"red": "🔴", "black": "⚫", "green": "🟢"}
COLOR_RU = {"red": "Красный", "black": "Чёрный", "green": "Зеро"}

HISTORY_LIMIT = 50
CANDIDATE_COUNT = 7


def _numbers_from_spins(spins):
    """База возвращает спины от новых к старым."""
    return [
        int(spin[0])
        for spin in reversed(spins)
        if 0 <= int(spin[0]) <= 36
    ]


def _rank_candidates(history, count=CANDIDATE_COUNT):
    """
    Строит рейтинг по частотам и повторениям пар/троек.
    history передаётся от старых результатов к новым.
    Последнее число исключается.
    """
    if len(history) < 2:
        return []

    excluded = history[-1]
    usable = history[-HISTORY_LIMIT:]
    freq = Counter(usable)

    # Какие числа выпадали после такой же пары или тройки.
    pair_next = Counter()
    triple_next = Counter()
    pair_total = 0
    triple_total = 0

    for i in range(2, len(usable)):
        if usable[i - 2:i] == usable[-2:]:
            pair_next[usable[i]] += 1
            pair_total += 1

    if len(usable) >= 3:
        for i in range(3, len(usable)):
            if usable[i - 3:i] == usable[-3:]:
                triple_next[usable[i]] += 1
                triple_total += 1

    max_freq = max(freq.values(), default=1)
    scores = []

    for number in range(37):
        if number == excluded:
            continue

        # Частота — основной показатель.
        frequency_score = freq[number] / max_freq

        # Повторения последовательностей — дополнительный сигнал.
        pair_score = (
            pair_next[number] / pair_total
            if pair_total else 0
        )
        triple_score = (
            triple_next[number] / triple_total
            if triple_total else 0
        )

        # Небольшое сглаживание не даёт редким совпадениям
        # слишком сильно влиять на рейтинг.
        score = (
            0.60 * frequency_score
            + 0.25 * pair_score
            + 0.15 * triple_score
        )

        scores.append((number, score, freq[number]))

    # При равных оценках порядок определяется номером.
    scores.sort(key=lambda item: (-item[1], item[0]))
    return scores[:count]


def _backtest(numbers, min_history=10):
    """
    Проверка по принципу walk-forward:
    каждый прогноз использует только результаты до проверяемого спина.
    """
    hits = 0
    trials = 0

    # Проверяем, как топ-7 работал на следующих исторических результатах.
    for i in range(min_history, len(numbers)):
        past = numbers[max(0, i - HISTORY_LIMIT):i]
        actual = numbers[i]

        if len(past) < 2:
            continue

        ranked = _rank_candidates(past)
        candidates = [item[0] for item in ranked]

        # Повтор последнего числа исключён из кандидатов по правилу бота.
        # Если он выпал снова, прогноз не засчитывается как попадание.
        trials += 1
        if actual in candidates:
            hits += 1

    rate = (hits / trials * 100) if trials else None
    return {
        "hits": hits,
        "trials": trials,
        "rate": round(rate, 1) if rate is not None else None,
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
        f"1–12 — <b>{stats['dozen_pct']['d1']}%</b> · "
        f"13–24 — <b>{stats['dozen_pct']['d2']}%</b> · "
        f"25–36 — <b>{stats['dozen_pct']['d3']}%</b>\n\n"
        f"🔥 <b>Чаще выпадали</b>\n"
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
        "\n\n<i>Статистика описывает прошлые результаты "
        "и не гарантирует будущий исход.</i>"
    )
    return text


def get_prediction(limit=HISTORY_LIMIT):
    spins = get_all_spins()
    numbers = _numbers_from_spins(spins)

    if len(numbers) < 5:
        return None

    recent = numbers[-min(limit, HISTORY_LIMIT):]
    if len(recent) < 2:
        return None

    ranked = _rank_candidates(recent)
    if not ranked:
        return None

    color_counts = Counter(
        "green" if n == 0 else
        "red" if n in {
            1, 3, 5, 7, 9, 12, 14, 16, 18,
            19, 21, 23, 25, 27, 30, 32, 34, 36
        } else "black"
        for n in recent
    )

    top_color = max(
        ("red", "black", "green"),
        key=lambda c: color_counts.get(c, 0)
    )

    low = sum(1 for n in recent if 1 <= n <= 18)
    high = sum(1 for n in recent if 19 <= n <= 36)
    even = sum(1 for n in recent if n != 0 and n % 2 == 0)
    odd = sum(1 for n in recent if n % 2 == 1)

    backtest = _backtest(numbers)

    # Считаем, как часто в истории встречались пары и тройки.
    pair_count = 0
    triple_count = 0
    for i in range(2, len(recent)):
        if recent[i - 2:i] == recent[-2:]:
            pair_count += 1
    if len(recent) >= 3:
        for i in range(3, len(recent)):
            if recent[i - 3:i] == recent[-3:]:
                triple_count += 1

    return {
        "top_numbers": [item[0] for item in ranked],
        "ranked": ranked,
        "excluded": recent[-1],
        "top_color": top_color,
        "top_color_emoji": EMOJI[top_color],
        "color_pct": round(
            color_counts.get(top_color, 0) / len(recent) * 100
        ),
        "top_range": (
            "1–18" if low > high else
            "19–36" if high > low else "поровну"
        ),
        "top_parity": (
            "Чётные" if even > odd else
            "Нечётные" if odd > even else "поровну"
        ),
        "total": len(recent),
        "pair_matches": pair_count,
        "triple_matches": triple_count,
        "backtest": backtest,
    }


def format_prediction(pred):
    if not pred:
        return (
            "🔮 <b>АНАЛИЗ РУЛЕТКИ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Пока мало данных. Добавь хотя бы 5 результатов."
        )

    lines = []
    for position, (number, score, frequency) in enumerate(
        pred["ranked"], start=1
    ):
        color = (
            "🟢" if number == 0 else
            "🔴" if number in {
                1, 3, 5, 7, 9, 12, 14, 16, 18,
                19, 21, 23, 25, 27, 30, 32, 34, 36
            } else "⚫"
        )
        lines.append(
            f"{position}. {color} <b>{number}</b>"
            f" — рейтинг {score * 100:.1f}/100"
            f" · встречалось {frequency} раз"
        )

    test = pred["backtest"]
    if test["rate"] is None:
        test_text = "Недостаточно прошлых спинов для проверки."
    else:
        test_text = (
            f"{test['hits']} попаданий из {test['trials']} проверок "
            f"({test['rate']}%)."
        )

    return (
        f"🔮 <b>АНАЛИЗ ПОСЛЕДНИХ {pred['total']} СПИНОВ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🚫 Последнее число исключено: <b>{pred['excluded']}</b>\n\n"
        "🎯 <b>ТОП-7 КАНДИДАТОВ</b>\n"
        + "\n".join(lines)
        + "\n\n"
        f"🎨 Чаще был цвет: {pred['top_color_emoji']} "
        f"<b>{COLOR_RU[pred['top_color']]}</b> "
        f"({pred['color_pct']}%)\n"
        f"📉 Диапазон: <b>{pred['top_range']}</b>\n"
        f"⚖️ Чётность: <b>{pred['top_parity']}</b>\n\n"
        "🔁 <b>Повторения последовательностей</b>\n"
        f"Совпадения пар: <b>{pred['pair_matches']}</b>\n"
        f"Совпадения троек: <b>{pred['triple_matches']}</b>\n\n"
        "🧪 <b>Проверка на прошлых результатах</b>\n"
        f"{test_text}\n"
        "Случайный ориентир для топ-7 — около 18,9% "
        "при независимых равновероятных спинах.\n\n"
        "<i>Рейтинг — относительная оценка по истории, "
        "не вероятность выпадения числа. Исключённое число "
        "может выпасть снова. Гарантии точности нет.</i>"
    )
