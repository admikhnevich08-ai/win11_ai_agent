# -*- coding: utf-8 -*-
"""
Тест LLM-планировщика с реальной моделью.
"""
from transformers import pipeline
from planner import llm_decide_tool

print("Загрузка LLM...")
pipe = pipeline(
    "text-generation",
    model="Qwen/Qwen2.5-1.5B-Instruct",
    torch_dtype="auto",
)

tests = [
    "привет",
    "2+2",
    "100 минус 42",
    "погода в Москве",
    "какая погода в Лондоне",
    "расскажи про нейросети",
    "Vogue",
    "что такое Python",
]

for t in tests:
    result = llm_decide_tool(t, pipe)
    print(f"{t!r:40} -> tool={result['tool']:10} arg={result['arg']!r}")