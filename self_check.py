# -*- coding: utf-8 -*-
"""
Самопроверка ответов агента.
"""
import re


def check_math(question: str, answer: str, original_result) -> dict:
    """
    Проверяет математический ответ.
    original_result — результат из math_solver (int/float или None)
    """
    if original_result is None:
        return {"ok": True, "reason": "не математика"}

    numbers = re.findall(r"-?\d+\.?\d*", answer)
    if not numbers:
        return {"ok": False, "reason": "нет числа в ответе"}

    try:
        expected = float(original_result)
        found = [float(n) for n in numbers]

        if any(abs(f - expected) < 0.001 for f in found):
            return {"ok": True, "reason": "число совпадает"}
        else:
            return {
                "ok": False,
                "reason": f"ожидалось {expected}, найдено {found}",
            }
    except Exception as e:
        return {"ok": False, "reason": f"ошибка проверки: {e}"}


def check_rag(question: str, answer: str) -> dict:
    """
    Проверяет RAG-ответ.
    """
    # 1. Пустой?
    if not answer or len(answer.strip()) < 10:
        return {"ok": False, "reason": "ответ пустой или слишком короткий"}

    # 2. Английский?
    latin = len(re.findall(r"[a-zA-Z]", answer))
    cyrillic = len(re.findall(r"[а-яА-Я]", answer))

    if cyrillic < 5 and latin > 20:
        return {"ok": False, "reason": "ответ на английском, а не на русском"}

    # 3. Остался префикс?
    if answer.strip().startswith(("Согласно собранной", "Ответ:", "Ответ на")):
        return {"ok": False, "reason": "в ответе остался служебный префикс"}

    # 4. Слишком длинный?
    if len(answer) > 3500:
        return {"ok": False, "reason": "ответ слишком длинный"}

    # 5. Есть ли стоп-слова?
    bad_phrases = [
        "как языковая модель",
        "I cannot",
        "as an AI",
        "я не могу",
    ]
    for phrase in bad_phrases:
        if phrase.lower() in answer.lower():
            return {"ok": False, "reason": f"ответ содержит шаблонную фразу: {phrase}"}

    return {"ok": True, "reason": "проверки пройдены"}


def check(question: str, answer: str, kind: str = "normal", math_result=None) -> dict:
    """Главная функция проверки."""
    if kind == "math":
        return check_math(question, answer, math_result)

    if kind in ("normal", "short", "detailed", "list", "yesno"):
        return check_rag(question, answer)

    if kind == "weather":
        if "температура" in answer.lower() or "°C" in answer:
            return {"ok": True, "reason": "погода получена"}
        return {"ok": False, "reason": "не удалось получить погоду"}

    return {"ok": True, "reason": "нет проверки для типа"}


if __name__ == "__main__":
    print("--- Математика ---")
    print(check("2+2", "2+2 = 4", kind="math", math_result=4))
    print(check("2+2", "2+2 = 5", kind="math", math_result=4))

    print("\n--- RAG ---")
    print(check("что такое AI", "Искусственный интеллект — это...", kind="normal"))
    print(check("что такое AI", "", kind="normal"))
    print(check("что такое AI", "AI is artificial intelligence...", kind="normal"))
    print(check("что такое AI", "Согласно собранной информации, это...", kind="normal"))

    print("\n--- Погода ---")
    print(check("погода", "🌤 Температура: 5°C", kind="weather"))
    print(check("погода", "Не удалось получить", kind="weather"))