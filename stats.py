from collections import Counter
from database import get_all_spins

EMOJI = {"red": "🔴", "black": "⚫", "green": "🟢"}
COLOR_RU = {"red": "Красный", "black": "Чёрный", "green": "Зеро"}
WHEEL_NUMBERS = tuple(range(37))
ANALYSIS_WINDOW = 50
TOP_K = 7
METHOD_NAMES = {
    "frequency": "Частоты за 50 спинов",
    "weighted": "Взвешенные частоты (10/25/50)",
    "patterns": "Частоты + последовательности",
    "ensemble": "Комбинированный рейтинг",
}


def _counts(spins):
    return Counter(int(s[0]) for s in spins if 0 <= int(s[0]) <= 36)


def _recent(spins, size=ANALYSIS_WINDOW):
    """Database rows are newest-first."""
    return list(spins[:min(size, len(spins))])


def _scores(spins_newest_first, method):
    """Return relative ranking scores. These are not probabilities."""
    if not spins_newest_first:
        return {n: 0.0 for n in WHEEL_NUMBERS}

    recent = spins_newest_first[:ANALYSIS_WINDOW]
    chronological = list(reversed(recent))
    counts50 = _counts(recent)
    total = len(recent)

    if method == "frequency":
        return {n: counts50.get(n, 0) / max(total, 1) for n in WHEEL_NUMBERS}

    # Weighted frequency: short-term results matter more, but longer window
    # reduces sensitivity to a few recent spins.
    windows = ((10, 0.50), (25, 0.30), (50, 0.20))
    weighted = {n: 0.0 for n in WHEEL_NUMBERS}
    used = 0.0
    for size, weight in windows:
        sample = recent[:min(size, len(recent))]
        if not sample:
            continue
        counts = _counts(sample)
        denom = len(sample)
        for n in WHEEL_NUMBERS:
            weighted[n] += weight * counts.get(n, 0) / denom
        used += weight
    if used:
        weighted = {n: v / used for n, v in weighted.items()}

    if method == "weighted":
        return weighted

    # The ensemble combines three differently constructed rankings. It is an
    # experimental candidate generator, not a claim of true probabilities.
    if method == "ensemble":
        frequency = _scores(spins_newest_first, "frequency")
        patterns = _scores(spins_newest_first, "patterns")
        return {
            n: 0.35 * frequency[n] + 0.35 * weighted[n] + 0.30 * patterns[n]
            for n in WHEEL_NUMBERS
        }

    # Pattern method: combine weighted frequencies with observed transitions
    # after the latest number and latest two-number sequence. If no matching
    # historical context exists, fall back to the weighted frequency score.
    latest = int(recent[0][0])
    previous = int(recent[1][0]) if len(recent) > 1 else None
    transitions = Counter()
    transition_total = 0
    triple_transitions = Counter()
    triple_total = 0

    for i in range(len(chronological) - 1):
        if int(chronological[i][0]) == latest:
            transitions[int(chronological[i + 1][0])] += 1
            transition_total += 1
        if previous is not None and i + 2 < len(chronological):
            if (int(chronological[i][0]) == previous and
                    int(chronological[i + 1][0]) == latest):
                triple_transitions[int(chronological[i + 2][0])] += 1
                triple_total += 1

    result = {}
    for n in WHEEL_NUMBERS:
        transition_rate = (transitions[n] / transition_total
                           if transition_total else weighted[n])
        triple_rate = (triple_transitions[n] / triple_total
                       if triple_total else weighted[n])
        result[n] = 0.60 * weighted[n] + 0.25 * transition_rate + 0.15 * triple_rate
    return result


def _ranked(spins_newest_first, method, exclude_latest=True):
    scores = _scores(spins_newest_first, method)
    excluded = int(spins_newest_first[0][0]) if exclude_latest and spins_newest_first else None
    eligible = [n for n in WHEEL_NUMBERS if n != excluded]
    # Deterministic tie-break: higher score, then more recent appearance, then lower number.
    recent_order = {}
    for i, spin in enumerate(spins_newest_first):
        n = int(spin[0])
        if n not in recent_order:
            recent_order[n] = i
    eligible.sort(key=lambda n: (-scores[n], recent_order.get(n, 10**9), n))
    return [(n, scores[n]) for n in eligible]


def _backtest(spins, history_size=ANALYSIS_WINDOW):
    """Walk-forward test; each prediction sees only earlier outcomes."""
    chronological = list(reversed(spins))
    if len(chronological) <= history_size:
        return {m: None for m in METHOD_NAMES}

    stats = {m: {"tested": 0, "hits": 0} for m in METHOD_NAMES}
    for i in range(history_size, len(chronological)):
        # History ends before the outcome being tested. Reverse to newest-first.
        training = list(reversed(chronological[max(0, i-history_size):i]))
        actual = int(chronological[i][0])
        for method in METHOD_NAMES:
            candidates = [n for n, _ in _ranked(training, method)[:TOP_K]]
            stats[method]["tested"] += 1
            if actual in candidates:
                stats[method]["hits"] += 1

    result = {}
    for method, item in stats.items():
        result[method] = {
            "tested": item["tested"],
            "hits": item["hits"],
            "pct": round(item["hits"] / item["tested"] * 100, 1) if item["tested"] else 0.0,
            "baseline_pct": round(TOP_K / 37 * 100, 1),
        }
    return result


def _sequence_summary(spins):
    chronological = [int(s[0]) for s in reversed(spins[:ANALYSIS_WINDOW])]
    pairs = Counter(zip(chronological, chronological[1:]))
    triples = Counter(zip(chronological, chronological[1:], chronological[2:]))
    common_pairs = [(seq, count) for seq, count in pairs.most_common() if count > 1][:3]
    common_triples = [(seq, count) for seq, count in triples.most_common() if count > 1][:3]
    return common_pairs, common_triples


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
    dozens = [sum(1 for n in numbers if a <= n <= b)
              for a, b in ((1, 12), (13, 24), (25, 36))]

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
            "📊 <b>СТАТИСТИКА РУЛЕТКИ</b>\n"
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
    text += "\n".join(f"• <b>{number}</b> — {count} раз" for number, count in stats["top_numbers"])
    text += "\n\n🕒 <b>Последние спины</b>\n"
    text += "  ·  ".join(f"{EMOJI.get(color, '🎲')}{number}" for number, color, *_ in stats["last"])
    text += "\n\n<i>Исторические частоты не гарантируют будущий исход.</i>"
    return text


def get_prediction(limit=ANALYSIS_WINDOW):
    """Compatibility function used by bot.py. Uses last 50 spins by default."""
    spins = get_all_spins()
    if len(spins) < 10:
        return None

    recent = _recent(spins, min(limit, ANALYSIS_WINDOW))
    numbers = [int(s[0]) for s in recent]
    colors = [s[1] for s in recent]
    counter = Counter(numbers)
    color_counter = Counter(colors)
    top_color = max(("red", "black", "green"), key=lambda c: color_counter.get(c, 0))
    color_pct = round(color_counter.get(top_color, 0) / len(recent) * 100, 1)

    low = sum(1 for n in numbers if 1 <= n <= 18)
    high = sum(1 for n in numbers if 19 <= n <= 36)
    top_range = "1–18" if low > high else "19–36" if high > low else "поровну"
    even = sum(1 for n in numbers if n != 0 and n % 2 == 0)
    odd = sum(1 for n in numbers if n != 0 and n % 2 == 1)
    top_parity = "Чётные" if even > odd else "Нечётные" if odd > even else "поровну"

    backtests = _backtest(spins)
    available_tests = [v for v in backtests.values() if v and v["tested"] >= 30]
    if available_tests:
        # Prefer the best past walk-forward result, but when methods are close,
        # prefer the ensemble to reduce dependence on one noisy heuristic.
        eligible_methods = [m for m, v in backtests.items() if v and v["tested"] >= 30]
        best_method = max(
            eligible_methods,
            key=lambda m: (
                backtests[m]["pct"] + (0.5 if m == "ensemble" else 0.0),
                backtests[m]["hits"],
            ),
        )
        selected_reason = "выбран по исторической walk-forward проверке; результаты прошлого не гарантируют будущие"
    else:
        best_method = "weighted"
        selected_reason = "временно выбран смешанный по окнам метод: пока мало тестов для надёжного сравнения"

    ranked = _ranked(recent, best_method)
    best_score = ranked[0][1] if ranked else 0.0
    candidates = [
        {"number": n, "count": counter.get(n, 0),
         "index": round(score / best_score * 100) if best_score else 0}
        for n, score in ranked[:TOP_K]
    ]
    pairs, triples = _sequence_summary(recent)

    return {
        "candidates": candidates,
        "top_numbers": [n for n, _ in counter.most_common(5)],
        "top_color": top_color,
        "top_color_emoji": EMOJI[top_color],
        "color_pct": color_pct,
        "top_range": top_range,
        "top_parity": top_parity,
        "total": len(recent),
        "all_total": len(spins),
        "excluded_latest": numbers[0],
        "best_method": best_method,
        "best_method_name": METHOD_NAMES[best_method],
        "selected_reason": selected_reason,
        "backtests": backtests,
        "pairs": pairs,
        "triples": triples,
    }


def format_prediction(pred):
    if not pred:
        return (
            "🔮 <b>АНАЛИЗ КАНДИДАТОВ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Пока мало данных. Добавь хотя бы 10 результатов. "
            "Для сравнения методов желательно иметь несколько сотен спинов."
        )

    candidate_lines = [
        f"• <b>{item['number']}</b> — индекс рейтинга <b>{item['index']}/100</b> "
        f"(в последних спинах: {item['count']} раз)"
        for item in pred["candidates"]
    ]
    text = (
        f"🔮 <b>ТОП-{TOP_K} КАНДИДАТОВ</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📚 Анализ: <b>{pred['total']}</b> последних спинов; в базе: <b>{pred['all_total']}</b>\n"
        f"🚫 Исключено последнее число: <b>{pred['excluded_latest']}</b>\n\n"
        f"🎯 <b>Кандидаты (не вероятности):</b>\n" + "\n".join(candidate_lines) +
        f"\n\n🧠 Метод: <b>{pred['best_method_name']}</b>\n"
        f"<i>{pred['selected_reason']}</i>\n"
        f"🎨 Частый цвет в выборке: {pred['top_color_emoji']} <b>{COLOR_RU[pred['top_color']]}</b> ({pred['color_pct']}%)\n"
        f"📉 Диапазон: <b>{pred['top_range']}</b> · ⚖️ Чётность: <b>{pred['top_parity']}</b>\n"
    )

    text += "\n🧪 <b>Walk-forward проверка методов</b> (каждый прогноз использует только прошлые данные)\n"
    any_backtest = False
    for method, name in METHOD_NAMES.items():
        result = pred["backtests"].get(method)
        if result:
            any_backtest = True
            marker = " ⭐" if method == pred["best_method"] else ""
            text += f"• {name}: <b>{result['pct']}%</b> ({result['hits']}/{result['tested']}){marker}\n"
    if not any_backtest:
        text += "Пока недостаточно истории: нужно больше 50 спинов.\n"
    text += f"Случайный ориентир для 7 чисел: около <b>{round(7 / 37 * 100, 1)}%</b>.\n"

    if pred["pairs"]:
        text += "\n🔁 <b>Повторявшиеся пары в последних 50</b>\n"
        text += "\n".join(f"• {a} → {b}: {count} раз" for (a, b), count in pred["pairs"])
        text += "\n"
    if pred["triples"]:
        text += "\n🔗 <b>Повторявшиеся тройки в последних 50</b>\n"
        text += "\n".join(f"• {a} → {b} → {c}: {count} раз" for (a, b, c), count in pred["triples"])
        text += "\n"

    text += (
        "\n⚠️ <b>Важно:</b> индекс 100 — это лидер рейтинга, а не 100% шанс. "
        "В честной европейской рулетке каждое число имеет шанс 1/37 (≈2,7%) на каждом спине. "
        "Прошлые результаты и последовательности не гарантируют будущий исход."
    )
    return text
