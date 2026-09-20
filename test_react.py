# -*- coding: utf-8 -*-
"""
Тест ReAct-агента с реальной LLM.
"""
from transformers import pipeline
from react_agent import react_loop
from weather import extract_city, get_weather
from math_solver import solve as math_solve


# ==== Tools-обёртки ====
def tool_math(arg):
    result, expr = math_solve(arg)
    if result is not None:
        return f"{expr} = {result}"
    return "Не удалось решить"


def tool_weather(arg):
    city = extract_city(arg) if arg else "Москва"
    return get_weather(city)


def tool_search(arg):
    return f"Поиск: {arg}. Найдено 5 результатов."


def tool_greeting(arg):
    return "👋 Привет! Чем помочь?"


TOOLS = {
    "math": tool_math,
    "weather": tool_weather,
    "search": tool_search,
    "greeting": tool_greeting,
}


print("Загрузка LLM...")
pipe = pipeline(
    "text-generation",
    model="Qwen/Qwen2.5-1.5B-Instruct",
    torch_dtype="auto",
)

tests = [
    "2+2",
    "погода в Москве",
    "расскажи про нейросети",
]

for t in tests:
    print(f"\n{'='*60}")
    print(f"Вопрос: {t}")
    result = react_loop(t, pipe, TOOLS, max_steps=2)
    print(f"\nSteps: {len(result['steps'])}")
    print(f"Final: {result['final'][:200]}")
    print(f"Stopped: {result['stopped']}")