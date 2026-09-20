# test_currency_tool.py
from windows11_ai_agent import Agent

agent = Agent()

tests = [
    "100 долларов в рублях",
    "1000 рублей в долларах",
    "5000 рублей в евро",
    "100 евро в долларах",
    "курс доллара",
]

for t in tests:
    print(f"\n{'='*60}")
    print(f"Вход: {t}")
    print(f"{'='*60}")
    print(agent._tool_currency(t))