# -*- coding: utf-8 -*-
"""
Погода через wttr.in — универсально для любого города.
"""
import re
import requests


def extract_city(question: str) -> str:
    """
    Извлекает название города из вопроса.
    Примеры:
        "какая погода в Красногорске?" → "Красногорск"
        "погода в Москве"               → "Москва"
        "температура в Санкт-Петербурге"→ "Санкт-Петербург"
        "погода"                        → "Москва" (по умолчанию)
    """
    q = question.strip()

    # Убираем знаки препинания
    q = re.sub(r"[?!.,;]", " ", q)

    # Убираем вопросительные и служебные слова (регистронезависимо)
    stop_words = [
        "какая", "какой", "какое", "какие", "как",
        "погода", "погоду", "погоды", "погоде",
        "температура", "температуру",
        "прогноз",
        "сколько", "градусов",
        "сейчас", "сегодня", "завтра", "послезавтра",
        "на", "в", "во", "по",
        "в городе", "городе", "город",
        "скажи", "подскажи", "узнай", "расскажи",
        "будет", "ли",
    ]

    q_lower = q.lower()
    for word in stop_words:
        q_lower = re.sub(rf"\b{re.escape(word)}\b", " ", q_lower)

    # Убираем лишние пробелы
    city = re.sub(r"\s+", " ", q_lower).strip()

    # Если пусто — Москва по умолчанию
    if not city:
        return "Москва"

    # Убираем оставшиеся служебные слова
    city = city.strip(" -–—")

    # Делаем каждое слово с заглавной буквы
    city = " ".join(w.capitalize() for w in city.split())

    return city


def get_weather(city: str) -> str:
    """
    Возвращает погоду для указанного города.
    city — "Красногорск", "Москва", "Лондон", "New York"
    """
    if not city:
        city = "Москва"

    try:
        # wttr.in — без API-ключа, без регистрации
        url = f"https://wttr.in/{city}"
        params = {
            "format": "j1",   # JSON
            "lang": "ru",     # Русский
        }

        r = requests.get(
            url,
            params=params,
            timeout=15,
            headers={"User-Agent": "curl/7.68.0"},
        )
        r.raise_for_status()
        data = r.json()

        cur = data["current_condition"][0]
        temp = cur["temp_C"]
        feels = cur["FeelsLikeC"]
        humidity = cur["humidity"]
        wind = cur["windspeedKmph"]

        # Описание — по-русски, если есть
        desc = cur["weatherDesc"][0]["value"]
        if "lang_ru" in cur and cur["lang_ru"]:
            desc = cur["lang_ru"][0]["value"]

        # Прогноз на завтра
        tomorrow_str = ""
        if len(data.get("weather", [])) > 1:
            t = data["weather"][1]
            t_max = t.get("maxtempC", "?")
            t_min = t.get("mintempC", "?")
            tomorrow_str = f"\n\n📅 Завтра: от {t_min}°C до {t_max}°C"

        return (
            f"🌤 Погода в {city}:\n\n"
            f"🌡 Температура: {temp}°C\n"
            f"🤔 Ощущается как: {feels}°C\n"
            f"☁ {desc}\n"
            f"💧 Влажность: {humidity}%\n"
            f"💨 Ветер: {wind} км/ч"
            f"{tomorrow_str}"
        )

    except requests.exceptions.Timeout:
        return f"⚠️ Не удалось получить погоду для «{city}»: сервер не отвечает. Попробуй позже."
    except requests.exceptions.HTTPError as e:
        return f"⚠️ Ошибка запроса для «{city}»: {e}"
    except requests.exceptions.RequestException as e:
        return f"⚠️ Сеть недоступна: {e}"
    except (KeyError, IndexError, ValueError) as e:
        return f"⚠️ Не удалось разобрать ответ для «{city}»: {e}"


# Тест
if __name__ == "__main__":
    tests = [
        "какая погода в Красногорске?",
        "погода в Москве",
        "погода в Лондоне",
        "погода в Санкт-Петербурге",
        "температура в Токио",
        "погода",
        "погода в Нью-Йорке",
    ]
    for t in tests:
        city = extract_city(t)
        print(f"\n{'='*60}")
        print(f"Вопрос: {t!r}")
        print(f"Город:  {city!r}")
        print(f"{'-'*60}")
        print(get_weather(city))