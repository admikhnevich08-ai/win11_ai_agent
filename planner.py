# -*- coding: utf-8 -*-
"""
LLM-планировщик: определяет, какой инструмент использовать для вопроса.
Вариант А: LLM + fallback-проверки.
"""
import re


TOOLS_DESCRIPTION = """
- math: арифметика, уравнения, вычисления (например: "2+2", "100 минус 42", "x² - 5x + 6 = 0")
- weather: погода в городе (например: "погода в Москве", "какая погода в Лондоне")
- greeting: приветствия, спасибо, пока (например: "привет", "спасибо", "как дела")
- currency: курсы валют ЦБ РФ и конвертация (например: "курс доллара", "сколько стоит евро", "100 долларов в рублях", "курс валют")
- search: поиск информации в базе знаний (новости IT/AI) и Wikipedia
"""


def llm_decide_tool(question: str, llm_pipe) -> dict:
    """
    Использует LLM для выбора инструмента + fallback-проверки.

    Логика:
    1. Быстрое правило (для явных случаев) — если уверено, сразу возвращаем.
    2. Иначе — спрашиваем LLM.
    3. Проверяем LLM на типичные ошибки — если ошибся, откат на правило.
    """
    # 1. Быстрое правило
    quick_tool = _fallback_tool(question)
    q_len = len(question.strip())

    # 2. Явные случаи — сразу правило
    if quick_tool == "greeting" and q_len < 15:
        return {"tool": "greeting", "arg": question}

    if quick_tool == "math":
        return {"tool": "math", "arg": question}

    if quick_tool == "weather":
        return {"tool": "weather", "arg": question}

    if quick_tool == "currency":
        return {"tool": "currency", "arg": question}

    # 3. Иначе — спрашиваем LLM
    prompt = (
        "Ты — планировщик AI-агента. Определи, какой инструмент использовать.\n\n"
        f"Доступные инструменты:\n{TOOLS_DESCRIPTION}\n"
        f"Вопрос пользователя: {question}\n\n"
        "Ответь СТРОГО в формате:\n"
        "TOOL: <имя>\n"
        "ARG: <аргумент>\n\n"
        "Например:\n"
        "Вопрос: 2+2\n"
        "TOOL: math\n"
        "ARG: 2+2\n\n"
        "Вопрос: погода в Москве\n"
        "TOOL: weather\n"
        "ARG: Москва\n\n"
        "Вопрос: курс доллара\n"
        "TOOL: currency\n"
        "ARG: курс доллара\n\n"
        "Твой ответ:\n"
    )

    try:
        out = llm_pipe(
            prompt,
            max_new_tokens=150,
            do_sample=False,
            return_full_text=False,
        )
        text = out[0]["generated_text"]
        parsed = _parse_tool_response(text, question)
        llm_tool = parsed["tool"]

        # 4. Проверки на ошибки LLM
        # Если quick_tool ≠ greeting, а LLM говорит greeting → откат
        if llm_tool == "greeting" and quick_tool != "greeting":
            print(f"[planner] LLM ошибся (greeting вместо {quick_tool}), fallback")
            return {"tool": quick_tool, "arg": question}

        if llm_tool == "search" and quick_tool == "math":
            print(f"[planner] LLM ошибся (search вместо math), fallback")
            return {"tool": "math", "arg": question}

        return parsed
    except Exception as e:
        print(f"[planner] LLM error: {e}")
        return {"tool": quick_tool, "arg": question}


def _parse_tool_response(text: str, original_question: str) -> dict:
    """Парсит ответ LLM и возвращает {tool, arg}."""
    tool = None
    arg = original_question

    # Ищем TOOL: ...
    m = re.search(r"TOOL\s*:\s*(\w+)", text, re.IGNORECASE)
    if m:
        tool = m.group(1).lower().strip()

    # Ищем ARG: ...
    m = re.search(r"ARG\s*:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    if m:
        arg = m.group(1).strip()
        # Обрезаем мусор после ARG
        arg = re.split(
            r"\s+(?:TOOLS|FORMAT|FINAL|ACTION|ARG|Пример|Например|Твой ответ|Ответь)\s*:",
            arg,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()
        arg = arg.split("\n")[0].strip()

    # Валидация
    valid_tools = {"math", "weather", "greeting", "currency", "search"}
    if tool not in valid_tools:
        tool = _fallback_tool(original_question)
        arg = original_question

    return {"tool": tool, "arg": arg}


def _fallback_tool(question: str) -> str:
    """Простой fallback, если LLM не справился."""
    q = question.lower().strip()

    # Приветствия
    greetings = {
        "привет", "здравствуй", "здравствуйте", "хай", "hi", "hello",
        "добрый день", "добрый вечер", "доброе утро", "ку",
        "как дела", "как ты", "спасибо", "благодарю",
        "пока", "до свидания", "bye",
    }
    if q.strip("!?., ") in greetings:
        return "greeting"

    # Математика
    if re.search(r"\d+\s*[\+\-\*\/]\s*\d+", q):
        return "math"
    if any(w in q for w in ["плюс", "минус", "умножить", "разделить", "в квадрате"]):
        return "math"

    # Погода
    if any(w in q for w in ["погода", "погоду", "температура"]):
        return "weather"

    # Курсы валют
    if any(w in q for w in [
        "курс", "валюта", "валют", "доллар", "евро", "юань", "фунт",
        "иена", "иен", "рубл", "usd", "eur", "cny", "gbp", "jpy",
        "конверт", "обмен",
    ]):
        return "currency"

    # Всё остальное — поиск
    return "search"


if __name__ == "__main__":
    # Тест без LLM — только fallback
    tests = [
        "привет",
        "2+2",
        "100 минус 42",
        "погода в Москве",
        "курс доллара",
        "сколько стоит евро",
        "100 долларов в рублях",
        "расскажи про нейросети",
        "как дела",
        "Vogue",
    ]
    for t in tests:
        result = _parse_tool_response("", t)
        print(f"{t!r:40} -> tool={result['tool']:10} arg={result['arg']!r}")