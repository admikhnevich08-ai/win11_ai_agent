# test_regex.py
import re

tests = [
    "100 долларов в рублях",
    "1000 рублей в долларах",
    "5000 рублей в евро",
    "100 евро в долларах",
]

pattern = r"(\d+(?:[.,]\d+)?)\s*([а-яa-z]+)\s+в\s+([а-яa-z]+)"

for t in tests:
    m = re.search(pattern, t.lower())
    if m:
        print(f"✅ {t!r}")
        print(f"   amount={m.group(1)!r}, from={m.group(2)!r}, to={m.group(3)!r}")
    else:
        print(f"❌ {t!r} — regex не нашёл")