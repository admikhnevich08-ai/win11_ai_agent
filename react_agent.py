# -*- coding: utf-8 -*-
"""
ReAct-агент: LLM сам решает, какие инструменты вызывать.
Цикл: think → act → observe → repeat.
С few-shot промптом + валидацией.
"""
import re


# ==== Описание инструментов ====
TOOLS_PROMPT = """
Доступные инструменты:
- math: арифметика, уравнения (например: "2+2", "15% от 300", "x² - 5x + 6 = 0")
- weather: погода в городе (например: "погода в Москве", "Лондон погода")
- currency: курсы валют ЦБ РФ и конвертация (например: "курс доллара", "сколько стоит евро", "100 долларов в рублях", "курс валют")
- search: поиск в базе знаний (новости IT/AI) и Wikipedia (например: "нейросети", "Vogue")
- greeting: приветствия, спасибо (например: "привет", "спасибо")
"""


def react_loop(question: str, llm_pipe, tools: dict, max_steps: int = 2) -> dict:
    """
    ReAct-цикл. LLM решает, какие инструменты вызывать.

    tools = {
        "math": callable,
        "weather": callable,
        "search": callable,
        "greeting": callable,
    }

    Возвращает: {"steps": [...], "final": "...", "stopped": "..."}
    """
    steps = []
    observations = []

    for step_num in range(1, max_steps + 1):
        # ==== Промпт ====
        prompt = _build_react_prompt(question, observations, step_num, max_steps)

        try:
            text = llm_pipe(
                prompt,
                max_tokens=300,
                temperature=0.0,
            )
            text = text.strip() if isinstance(text, str) else str(text).strip()
        except Exception as e:
            print(f"[react] LLM error: {e}")
            break

        # ==== Парсинг ответа LLM ====
        action = _parse_react_action(text)
        print(f"[react] шаг {step_num}: {action}")

        # ==== ВАЛИДАЦИЯ: FINAL на шаге 1 запрещён ====
        if step_num == 1 and action["type"] == "final":
            print(f"[react] LLM схитрила на шаге 1 — выходим в planner")
            return {
                "steps": [],
                "final": "",
                "stopped": "cheat",
            }

        # ==== Если финальный ответ ====
        if action["type"] == "final":
            return {
                "steps": steps,
                "final": action["answer"],
                "stopped": "final",
            }

        # ==== Иначе — вызов инструмента ====
        tool_name = action["tool"]
        tool_arg = action["arg"]

        # ЗАЩИТА: если arg пустой — используем исходный вопрос
        if not tool_arg or not tool_arg.strip():
            print(f"[react] ⚠️ пустой arg — используем исходный вопрос")
            tool_arg = question.strip()

        if tool_name not in tools:
            print(f"[react] неизвестный tool: {tool_name}, fallback")
            break

        try:
            result = tools[tool_name](tool_arg)
            steps.append({"tool": tool_name, "arg": tool_arg, "result": result})
            observations.append(f"Шаг {step_num}: {tool_name}({tool_arg!r}) → {result[:300]}")
            print(f"[react] результат: {result[:100]}...")
        except Exception as e:
            print(f"[react] ошибка tool {tool_name}: {e}")
            observations.append(f"Шаг {step_num}: {tool_name}({tool_arg!r}) → ошибка: {e}")

    # ==== Лимит шагов — возвращаем лучшее, что есть ====
    if steps:
        return {
            "steps": steps,
            "final": steps[-1]["result"],
            "stopped": "max_steps",
        }

    return {"steps": [], "final": "", "stopped": "error"}


def _build_react_prompt(question: str, observations: list, step: int, max_steps: int) -> str:
    """Жёсткий ReAct-промпт с few-shot примерами."""
    obs_text = ""
    if observations:
        obs_text = "\n\nЧто уже сделано:\n" + "\n".join(observations)

    if step == 1:
        instruction = (
            "🛑 ПРАВИЛА ПЕРВОГО ШАГА:\n"
            "1. ТЫ ОБЯЗАН ВЫЗВАТЬ ИНСТРУМЕНТ.\n"
            "2. ЗАПРЕЩЕНО писать FINAL на первом шаге.\n"
            "3. ЗАПРЕЩЕНО отвечать из своих знаний.\n"
            "4. Если сомневаешься — используй ACTION: search.\n\n"

            "📋 ПРИМЕРЫ ПРАВИЛЬНОГО ПОВЕДЕНИЯ:\n\n"

            "Вопрос: 2+2\n"
            "ACTION: math\n"
            "ARG: 2+2\n\n"

            "Вопрос: сколько будет 100 минус 42\n"
            "ACTION: math\n"
            "ARG: 100 минус 42\n\n"

            "Вопрос: погода в Москве\n"
            "ACTION: weather\n"
            "ARG: Москва\n\n"

            "Вопрос: какая погода в Лондоне\n"
            "ACTION: weather\n"
            "ARG: Лондон\n\n"

            "Вопрос: курс доллара\n"
            "ACTION: currency\n"
            "ARG: курс доллара\n\n"

            "Вопрос: сколько стоит евро\n"
            "ACTION: currency\n"
            "ARG: сколько стоит евро\n\n"

            "Вопрос: 100 долларов в рублях\n"
            "ACTION: currency\n"
            "ARG: 100 долларов в рублях\n\n"

            "Вопрос: расскажи про нейросети\n"
            "ACTION: search\n"
            "ARG: нейросети\n\n"

            "Вопрос: что такое Python\n"
            "ACTION: search\n"
            "ARG: Python\n\n"

            "Вопрос: а поподробнее?\n"
            "ACTION: search\n"
            "ARG: (продолжи предыдущую тему)\n\n"

            "Вопрос: привет\n"
            "ACTION: greeting\n"
            "ARG: привет\n\n"

            "❌ ПРИМЕРЫ НЕПРАВИЛЬНОГО ПОВЕДЕНИЯ (ТАК НЕЛЬЗЯ):\n\n"

            "Вопрос: 2+2\n"
            "FINAL: 4                          ← ОШИБКА! Нужен ACTION: math\n\n"

            "Вопрос: погода в Москве\n"
            "FINAL: В Москве тепло              ← ОШИБКА! Нужен ACTION: weather\n\n"

            "Вопрос: расскажи про нейросети\n"
            "FINAL: Нейросети — это...          ← ОШИБКА! Нужен ACTION: search\n\n"

            "🎯 ТВОЙ ОТВЕТ ДОЛЖЕН НАЧИНАТЬСЯ С 'ACTION:'"
        )
    else:
        instruction = (
            "📋 ПРАВИЛА ПОСЛЕДУЮЩИХ ШАГОВ:\n"
            "1. Посмотри на результаты инструментов выше.\n"
            "2. Если вопрос требует ещё действия — ACTION.\n"
            "3. Если информации достаточно — FINAL.\n"
            "4. Используй ТОЛЬКО данные из инструментов, не выдумывай.\n\n"
            "ФОРМАТ:\n"
            "ACTION: <tool>\n"
            "ARG: <arg>\n\n"
            "или\n\n"
            "FINAL: <ответ>"
        )

    return (
        "Ты — ReAct-агент. Ты ОБЯЗАН вызывать инструменты для получения точной информации.\n"
        "Ты НЕ имеешь права отвечать из своих знаний — только через инструменты.\n\n"
        f"{TOOLS_PROMPT}\n"
        f"Вопрос: {question}"
        f"{obs_text}\n\n"
        f"{instruction}\n\n"
        "Твой ответ (одна строка):\n"
    )


def _parse_react_action(text: str) -> dict:
    """Парсит ответ LLM. Обрезает мусор после первого ACTION/FINAL."""
    text = text.strip()
    
    # ==== Находим позиции первого ACTION и первого FINAL ====
    m_action = re.search(r"ACTION\s*:\s*(\w+)", text, re.IGNORECASE)
    m_final = re.search(r"FINAL\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    
    pos_action = m_action.start() if m_action else -1
    pos_final = m_final.start() if m_final else -1
    
    # ==== Если ACTION идёт раньше FINAL — это ACTION ====
    if pos_action >= 0 and (pos_final < 0 or pos_action < pos_final):
        # Ищем ARG после ACTION
        m_arg = re.search(
            r"ARG\s*:\s*(.+?)(?:\n|$)",
            text[pos_action:],
            re.IGNORECASE,
        )
        arg = m_arg.group(1).strip() if m_arg else ""
        
        # Обрезаем мусор после arg
        arg = re.split(
            r"\s+(?:ACTION|FINAL|TOOL|TOOLS|ARG|FORMAT|Пример|Например|Твой ответ)\s*:",
            arg, maxsplit=1, flags=re.IGNORECASE,
        )[0].strip()
        arg = arg.split("\n")[0].strip()
        
        return {
            "type": "action",
            "tool": m_action.group(1).lower().strip(),
            "arg": arg,
        }
    
    # ==== Если FINAL есть — это FINAL ====
    if pos_final >= 0:
        answer = m_final.group(1).strip()
        
        # Обрезаем всё после ACTION: или FINAL: внутри ответа
        for marker in ["ACTION:", "FINAL:", "ARG:"]:
            # Ищем маркер с учётом регистра
            for variant in [marker, marker.lower(), marker.capitalize()]:
                pos = answer.find(variant)
                if pos > 0:
                    answer = answer[:pos].strip()
                    break
        
        return {"type": "final", "answer": answer}
    
    # ==== Fallback ====
    return {"type": "final", "answer": text}


if __name__ == "__main__":
    # Тест парсера без LLM
    tests = [
        "ACTION: math\nARG: 2+2",
        "FINAL: 2+2 = 4",
        "ACTION: weather\nARG: Москва",
        "ACTION: search\nARG: нейросети TOOLS: search",
    ]
    for t in tests:
        result = _parse_react_action(t)
        print(f"{t!r:50} → {result}")