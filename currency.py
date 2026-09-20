# currency.py — курсы валют ЦБ РФ
import requests

def get_currency_rates() -> str:
    """Возвращает курсы валют ЦБ РФ."""
    try:
        url = "https://www.cbr-xml-daily.ru/daily_json.js"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        valutes = data.get("Valute", {})
        date = data.get("Date", "")[:10]
        
        lines = [f"💱 Курсы ЦБ РФ на {date}:"]
        
        for code in ["USD", "EUR", "CNY", "GBP", "JPY"]:
            if code in valutes:
                v = valutes[code]
                name = v["Name"]
                value = v["Value"] / v["Nominal"]
                lines.append(f"  {name}: {value:.2f} ₽")
        
        return "\n".join(lines)
    
    except Exception as e:
        return f"Ошибка получения курсов: {e}"


def convert_currency(amount: float, from_cur: str, to_cur: str = "RUB") -> str:
    """Конвертирует валюту."""
    try:
        url = "https://www.cbr-xml-daily.ru/daily_json.js"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        valutes = data.get("Valute", {})
        
        def get_rate(code):
            if code == "RUB":
                return 1.0
            if code in valutes:
                v = valutes[code]
                return v["Value"] / v["Nominal"]
            return None
        
        rate_from = get_rate(from_cur)
        rate_to = get_rate(to_cur)
        
        if rate_from is None:
            return f"Валюта {from_cur} не найдена"
        if rate_to is None:
            return f"Валюта {to_cur} не найдена"
        
        result = amount * rate_from / rate_to
        return f"{amount:.2f} {from_cur} = {result:.2f} {to_cur}"
    
    except Exception as e:
        return f"Ошибка конвертации: {e}"


if __name__ == "__main__":
    print(get_currency_rates())
    print()
    print(convert_currency(100, "USD", "RUB"))
    print(convert_currency(1000, "RUB", "USD"))