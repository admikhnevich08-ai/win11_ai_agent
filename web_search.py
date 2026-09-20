# -*- coding: utf-8 -*-
"""
Поиск в интернете: Wikipedia REST API.
Без DuckDuckGo — работает из РФ.
"""
import re
import requests
from bs4 import BeautifulSoup


HEADERS = {"User-Agent": "Windows11AIAgent/1.0 (contact: local)"}


def search_wikipedia(query: str, lang: str = "ru"):
    """
    Ищет в Wikipedia через REST API.
    1. Пробует прямую статью по названию.
    2. Если нет — ищет по ключевым словам.
    """
    # ==== 1. Прямая статья ====
    try:
        # Заменяем пробелы на подчёркивания
        title_clean = query.strip().replace(" ", "_")
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title_clean}"
        r = requests.get(url, headers=HEADERS, timeout=10)

        if r.status_code == 200:
            data = r.json()
            extract = data.get("extract", "")
            if len(extract) > 100:
                return {
                    "title": data.get("title", query),
                    "summary": extract[:2500],
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                }
    except Exception as e:
        print(f"[wiki] direct error: {e}")

    # ==== 2. Поиск по ключевым словам ====
    try:
        search_url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 3,
            "utf8": 1,
        }
        r = requests.get(search_url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = data.get("query", {}).get("search", [])

        for res in results:
            title = res["title"]
            # Берём summary найденной статьи
            title_clean = title.replace(" ", "_")
            page_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title_clean}"
            r2 = requests.get(page_url, headers=HEADERS, timeout=10)

            if r2.status_code == 200:
                d = r2.json()
                extract = d.get("extract", "")
                if len(extract) > 100:
                    return {
                        "title": d.get("title", title),
                        "summary": extract[:2500],
                        "url": d.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    }
    except Exception as e:
        print(f"[wiki] search error: {e}")

    return None


def fetch_page_text(url: str, max_chars: int = 2500) -> str:
    """Скачивает страницу и вытаскивает текст."""
    try:
        r = requests.get(url, timeout=10, headers=HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:max_chars]
    except Exception as e:
        print(f"[web] fetch error {url}: {e}")
        return ""


def web_search(query: str, max_pages: int = 2) -> dict:
    """
    Ищет в Wikipedia.
    Возвращает {context, sources, wiki_used}.
    """
    # 1. Wikipedia (единственный источник)
    wiki = search_wikipedia(query)

    if wiki and len(wiki["summary"]) > 100:
        return {
            "context": f"[Wikipedia: {wiki['title']}]\n{wiki['summary']}",
            "sources": [wiki["url"]],
            "wiki_used": True,
        }

    # 2. Не нашли — возвращаем пусто
    return {"context": "", "sources": [], "wiki_used": False}


if __name__ == "__main__":
    tests = [
        "Vogue",
        "Флаг России",
        "Дональд Трамп",
        "Python",
        "когда вышел последний выпуск Vogue",
        "цвета российского флага",
    ]
    for t in tests:
        print(f"\n{'=' * 60}")
        print(f"Запрос: {t}")
        result = web_search(t)
        print(f"Wiki: {result['wiki_used']}")
        print(f"Символов: {len(result['context'])}")
        print(f"Источников: {len(result['sources'])}")
        if result["context"]:
            print(f"Первые 300 символов:\n{result['context'][:300]}")
        else:
            print("❌ Ничего не найдено")