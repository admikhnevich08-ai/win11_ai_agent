# test_parse.py — тест парсинга ReAct
from react_agent import _parse_react_action

tests = [
    # 1. Нормальный ACTION
    ("ACTION: math\nARG: 2+2", "action"),
    
    # 2. Нормальный FINAL
    ("FINAL: 2+2 = 4", "final"),
    
    # 3. Мусор: FINAL с ACTION внутри
    ("FINAL: Нейронная сеть — это модель. ACTION: search('ещё') FINAL: Продолжение", "final"),
    
    # 4. Мусор: зацикливание (как в 2+2)
    ("4\nОшибка, не используй FINAL.\nACTION: math\nARG: 2+2\nFINAL: 4\nОшибка...\nACTION: math\nARG: 2+2\nFINAL: 4", "action"),
    
    # 5. ACTION с мусором после
    ("ACTION: weather\nARG: Москва\nFINAL: Погода", "action"),
    
    # 6. Чистый финальный ответ
    ("Нейронная сеть — это математическая модель.", "final"),
]

for text, expected in tests:
    print(f"\n{'='*60}")
    print(f"Вход: {text[:70]}...")
    r = _parse_react_action(text)
    print(f"Выход: type={r['type']}, ожидалось={expected}")
    if r['type'] == 'action':
        print(f"  tool={r.get('tool')}, arg={r.get('arg')}")
    else:
        print(f"  answer={r.get('answer', '')[:100]}...")
    
    if r['type'] != expected:
        print(f"  ⚠️  НЕСОВПАДЕНИЕ!")
    else:
        print(f"  ✅ OK")