# test_cur_code.py
from windows11_ai_agent import _cur_code

tests = [
    "долларов", "доллар", "доллары",
    "рублях", "рублей", "рубль", "рубля", "рубли",
    "евро", "евра",
    "юаней", "юань",
    "фунтов", "фунт",
    "иен", "иена",
]

for t in tests:
    code = _cur_code(t)
    status = "✅" if code else "❌"
    print(f"{status} _cur_code({t!r:15}) = {code!r}")