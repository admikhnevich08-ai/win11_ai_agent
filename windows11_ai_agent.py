# -*- coding: utf-8 -*-
"""
Windows 11 AI Agent (RU) - Qwen 7B int4 через llama.cpp
С ReAct-циклом и поддержкой контекста
"""

import json
import hashlib
import logging
from pathlib import Path

import numpy as np
import feedparser
import requests
from bs4 import BeautifulSoup

from sentence_transformers import SentenceTransformer

# ==== Подключаем чистку вывода и защиту от инъекций ====
from text_fixes_v2 import clean_llm_output
from prompt_guard import is_injection


# ==== Вспомогательное: код валюты по названию ====
def _cur_code(name: str) -> str:
    """Преобразует 'доллар' → 'USD', 'евро' → 'EUR' и т.д."""
    name = name.lower().strip()
    mapping = {
        # Доллар
        "доллар": "USD", "доллара": "USD", "долларов": "USD", "доллары": "USD",
        "долларам": "USD", "долларах": "USD", "долларами": "USD",
        "долл": "USD", "дол": "USD", "usd": "USD", "$": "USD",
        # Евро
        "евро": "EUR", "евра": "EUR", "евров": "EUR", "евры": "EUR",
        "еврам": "EUR", "еврах": "EUR", "еврами": "EUR",
        "eur": "EUR", "€": "EUR",
        # Юань
        "юань": "CNY", "юаня": "CNY", "юаней": "CNY", "юани": "CNY",
        "юаням": "CNY", "юанях": "CNY", "юанями": "CNY",
        "cny": "CNY", "¥": "CNY",
        # Фунт
        "фунт": "GBP", "фунта": "GBP", "фунтов": "GBP", "фунты": "GBP",
        "фунтам": "GBP", "фунтах": "GBP", "фунтами": "GBP",
        "gbp": "GBP", "£": "GBP",
        # Иена
        "иена": "JPY", "иены": "JPY", "иен": "JPY", "иенов": "JPY",
        "иенам": "JPY", "иенах": "JPY", "иенами": "JPY",
        "йена": "JPY", "йены": "JPY", "йен": "JPY",
        "jpy": "JPY",
        # Рубль — ВСЕ ПАДЕЖИ
        "рубль": "RUB", "рубля": "RUB", "рублей": "RUB", "рубли": "RUB",
        "рублям": "RUB", "рублях": "RUB", "рублями": "RUB",
        "руб": "RUB", "rub": "RUB", "rur": "RUB", "₽": "RUB",
    }
    return mapping.get(name, "")


# ============================================================
# CONFIG
# ============================================================
DATA_DIR = Path("./agent_data")
DATA_DIR.mkdir(exist_ok=True)
TEXTS_PATH = DATA_DIR / "texts.json"
EMBS_PATH = DATA_DIR / "embeddings.npy"
HASHES_PATH = DATA_DIR / "hashes.json"
LOG_PATH = DATA_DIR / "agent.log"

EMBED_MODEL = "BAAI/bge-m3"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("agent")


# ============================================================
# KNOWLEDGE BASE
# ============================================================
class KnowledgeBase:
    def __init__(self, embed_model=EMBED_MODEL):
        log.info(f"Loading embedder: {embed_model}")
        self.embedder = SentenceTransformer(embed_model)
        self.texts = []
        self.embeddings = None
        self.hashes = set()
        self._load()

    def _load(self):
        if TEXTS_PATH.exists() and EMBS_PATH.exists():
            try:
                with open(TEXTS_PATH, "r", encoding="utf-8") as f:
                    self.texts = json.load(f)
                self.embeddings = np.load(EMBS_PATH)
                if HASHES_PATH.exists():
                    with open(HASHES_PATH, "r", encoding="utf-8") as f:
                        self.hashes = set(json.load(f))
                else:
                    self.hashes = {self._hash(t) for t in self.texts}
                log.info(f"KB loaded: {len(self.texts)} docs")
            except Exception as e:
                log.error(f"KB load failed: {e}")
                self.texts, self.embeddings, self.hashes = [], None, set()
        else:
            log.info("KB is empty (fresh start)")

    def save(self):
        with open(TEXTS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.texts, f, ensure_ascii=False)
        if self.embeddings is not None:
            np.save(EMBS_PATH, self.embeddings)
        with open(HASHES_PATH, "w", encoding="utf-8") as f:
            json.dump(list(self.hashes), f)
        log.info(f"KB saved: {len(self.texts)} docs")

    @staticmethod
    def _hash(text):
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def add_texts(self, texts):
        fresh = []
        for t in texts:
            t = t.strip()
            if len(t) < 40:
                continue
            h = self._hash(t)
            if h in self.hashes:
                continue
            self.hashes.add(h)
            fresh.append(t)
        if not fresh:
            return 0
        new_embs = self.embedder.encode(
            fresh, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
        )
        self.texts.extend(fresh)
        self.embeddings = new_embs if self.embeddings is None else np.vstack([self.embeddings, new_embs])
        log.info(f"KB += {len(fresh)} docs (total {len(self.texts)})")
        return len(fresh)

    def search(self, query, k=3):
        if not self.texts or self.embeddings is None:
            return []
        q = self.embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
        sims = self.embeddings @ q
        idx = np.argsort(sims)[::-1][:k]
        return [self.texts[i] for i in idx if sims[i] > 0.60]


# ============================================================
# RSS COLLECTOR
# ============================================================
class RSSCollector:
    SOURCES = [
        "https://news.ycombinator.com/rss",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/rss",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://habr.com/ru/rss/hub/machine_learning/all/?fl=ru",
        "https://habr.com/ru/rss/hub/artificial_intelligence/all/?fl=ru",
        "https://habr.com/ru/rss/hub/bigdata/all/?fl=ru",
        "https://nplus1.ru/rss",
        "https://3dnews.ru/news/rss/",
        "https://tass.ru/rss/v2.xml",
    ]

    def __init__(self, timeout=10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows11AIAgent/1.0)"})

    def collect(self, max_per_source=20):
        data = []
        for url in self.SOURCES:
            try:
                r = self.session.get(url, timeout=self.timeout)
                feed = feedparser.parse(r.content)
                for entry in feed.entries[:max_per_source]:
                    title = getattr(entry, "title", "") or ""
                    summary = getattr(entry, "summary", "") or ""
                    summary = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)
                    text = f"{title}. {summary}".strip()
                    if len(text) > 40:
                        data.append(text)
                log.info(f"RSS ok: {url} ({len(feed.entries)} entries)")
            except Exception as e:
                log.warning(f"RSS failed {url}: {e}")
        return data


# ============================================================
# LOCAL LLM (Qwen 7B int4 через llama.cpp)
# ============================================================
from llm_gguf import LocalLLM_GGUF as LocalLLM


# ============================================================
# AGENT
# ============================================================
class Agent:
    def __init__(self):
        self.kb = KnowledgeBase()
        self.rss = RSSCollector()
        self.llm = None

    def _ensure_llm(self):
        if self.llm is None:
            self.llm = LocalLLM()

    def learn(self, save=True):
        texts = self.rss.collect()
        added = self.kb.add_texts(texts)
        if save and added:
            self.kb.save()
        return added

    # ============================================================
    # ReAct-методы
    # ============================================================
    def _tool_math(self, arg):
        try:
            from math_solver import solve as math_solve
            result, expr = math_solve(arg)
            if result is not None:
                return f"{expr} = {result}"
            return "Не удалось решить пример."
        except Exception as e:
            return f"Ошибка математики: {e}"

    def _tool_weather(self, arg):
        try:
            from weather import extract_city, get_weather
            city = extract_city(arg) if arg else "Москва"
            return get_weather(city)
        except Exception as e:
            return f"Ошибка погоды: {e}"

    def _tool_currency(self, arg):
        try:
            from currency import get_currency_rates, convert_currency
            import re as _re

            # Ищем: "100 долларов в рублях", "1000 рублей в долларах"
            m = _re.search(
                r"(\d+(?:[.,]\d+)?)\s*([а-яa-z]+)\s+в\s+([а-яa-z]+)",
                arg.lower(),
            )
            if m:
                amount = float(m.group(1).replace(",", "."))
                from_cur = _cur_code(m.group(2))
                to_cur = _cur_code(m.group(3))
                if from_cur and to_cur:
                    return convert_currency(amount, from_cur, to_cur)

            # Иначе — просто курсы
            return get_currency_rates()
        except Exception as e:
            return f"Ошибка валют: {e}"

    def _tool_search(self, arg):
        try:
            # ЗАЩИТА: пустой arg → "Информация не найдена"
            if not arg or not arg.strip():
                return "Информация не найдена."

            docs = self.kb.search(arg, k=3)
            if not docs:
                try:
                    from web_search import web_search
                    web = web_search(arg, max_pages=1)
                    if web["context"]:
                        return web["context"][:1500]
                except ImportError:
                    pass
                return "Информация не найдена."

            context = "\n\n---\n\n".join(docs)
            self._ensure_llm()
            answer = self.llm.answer(arg, context, stream=False, max_new_tokens=500)
            return answer
        except Exception as e:
            return f"Ошибка поиска: {e}"

    def _tool_greeting(self, arg):
        return (
            "👋 Привет! Я AI-агент по новостям IT/AI.\n\n"
            "Задай конкретный вопрос, например:\n"
            "• расскажи про нейросети\n"
            "• что пишут про OpenAI\n"
            "• погода в Москве\n"
            "• 2+2"
        )

    def _react_ask(self, question, user_id=None, stream=True, search_query=None):
        """ReAct-режим с поддержкой контекста из памяти."""
        tools = {
            "math": self._tool_math,
            "weather": self._tool_weather,
            "currency": self._tool_currency,
            "search": self._tool_search,
            "greeting": self._tool_greeting,
        }

        # Если есть search_query (прошлый вопрос) — передаём как контекст
        react_question = question
        if search_query and search_query != question:
            react_question = (
                f"{question}\n\n"
                f"[Контекст: пользователь ранее спрашивал: {search_query}]"
            )
            print(f"[react] контекст передан: {search_query!r}")

        try:
            from react_agent import react_loop
            self._ensure_llm()
            result = react_loop(react_question, self.llm.generate, tools, max_steps=2)
        except ImportError:
            return None
        except Exception as e:
            print(f"[react] ошибка: {e}")
            return None

        answer = result.get("final", "")
        if not answer:
            return None

        # Убираем мусор (ACTION, FINAL и т.п.)
        import re
        answer = re.split(
            r"\s*ACTION\s*:|\s*FINAL\s*:", answer, maxsplit=1, flags=re.IGNORECASE
        )[0].strip()

        # ==== Чистим китайский мусор и обрезаем незавершённые предложения ====
        answer = clean_llm_output(answer)

        try:
            from text_fixes import fix_english
            answer = fix_english(answer)
        except ImportError:
            pass

        if user_id is not None and answer:
            try:
                from memory import add_message
                add_message(user_id, "assistant", answer[:500])
            except ImportError:
                pass

        if stream:
            print(answer)
        return answer

    # ============================================================
    # Основной метод ask
    # ============================================================
    def ask(self, question, k=None, stream=True, user_id=None):
        # ==== ЗАЩИТА ОТ ПРОМПТ-ИНЪЕКЦИЙ ====
        bad, reason = is_injection(question)
        if bad:
            msg = f"⚠️ Запрос отклонён: {reason}"
            if stream:
                print(msg)
            return msg

        # ==== Память диалога ====
        history_context = ""
        previous_question = None

        if user_id is not None:
            try:
                from memory import get_history, add_message

                history = get_history(user_id, limit=10)

                for msg in reversed(history):
                    if msg["role"] == "user" and len(msg["content"]) > 15:
                        previous_question = msg["content"]
                        break

                add_message(user_id, "user", question)

                if history:
                    history_lines = []
                    for msg in history[-6:]:
                        role = "Ты" if msg["role"] == "user" else "Бот"
                        history_lines.append(f"{role}: {msg['content'][:300]}")
                    history_context = "\n".join(history_lines)
                    print(f"[memory] история: {len(history)} сообщений")
            except ImportError:
                pass

        # ==== Определяем search_query с учётом контекста (ДО ReAct) ====
        search_query = question
        context_words = [
            "поподробнее", "подробнее", "ещё", "еще", "дальше",
            "а что", "а как", "примеры", "а примеры", "продолжи",
            "расскажи ещё", "расскажи еще", "а почему", "а зачем",
            "а какая", "а какой", "а какие", "а какое",
            "завтра", "послезавтра", "сегодня",
            "а там", "а это", "а оно",
        ]
        is_context_question = any(w in question.lower() for w in context_words)
        if is_context_question and previous_question:
            search_query = previous_question
            print(f"[memory] поиск по прошлому: {search_query!r}")

        # ==== ReAct-режим ====
        use_react = True   # True = комбинирует tools, False = только planner

        if use_react:
            try:
                result = self._react_ask(
                    question, user_id=user_id, stream=stream,
                    search_query=search_query if is_context_question else None,
                )
                if result is not None:
                    return result
            except Exception as e:
                print(f"[react] ошибка: {e}, fallback на planner")

        # ==== Анализ вопроса: LLM-планировщик ====
        params = None

        try:
            from planner import llm_decide_tool

            self._ensure_llm()
            llm_result = llm_decide_tool(question, self.llm.pipe)
            tool = llm_result["tool"]
            arg = llm_result["arg"]

            print(f"[planner] tool={tool}, arg={arg!r}")

            if tool == "math":
                params = {"kind": "math", "max_new_tokens": 50, "k": 0, "temperature": 0.1, "skip_llm": False}
            elif tool == "weather":
                params = {"kind": "weather", "max_new_tokens": 0, "k": 0, "temperature": 0, "skip_llm": False}
            elif tool == "currency":
                params = {"kind": "currency", "max_new_tokens": 0, "k": 0, "temperature": 0, "skip_llm": False}
            elif tool == "greeting":
                params = {"kind": "greeting", "max_new_tokens": 0, "k": 0, "temperature": 0, "skip_llm": True}
            else:
                params = {"kind": "short", "max_new_tokens": 400, "k": 3, "temperature": 0.4, "skip_llm": False}
        except ImportError:
            params = None
        except Exception as e:
            print(f"[planner] ошибка: {e}")
            params = None

        # Fallback на старый анализатор
        if params is None:
            try:
                from question_analyzer import analyze
                params = analyze(question)
                print(f"[analyzer] fallback: kind={params['kind']}")
            except ImportError:
                params = {
                    "kind": "normal",
                    "max_new_tokens": 400,
                    "k": 3,
                    "temperature": 0.4,
                    "skip_llm": False,
                }

        # Приветствия
        if params["skip_llm"]:
            msg = (
                "👋 Привет! Я AI-агент по новостям IT/AI.\n\n"
                "Задай конкретный вопрос, например:\n"
                "• расскажи про нейросети\n"
                "• что пишут про OpenAI\n"
                "• погода в Москве\n"
                "• 2+2\n"
                "• /stats — статистика базы\n"
                "• /learn — обновить базу"
            )
            if stream:
                print(msg)
            if user_id is not None:
                try:
                    from memory import add_message
                    add_message(user_id, "assistant", msg[:500])
                except ImportError:
                    pass
            return msg

        k = k or params["k"]
        max_tokens = params["max_new_tokens"]
        temperature = params["temperature"]
        kind = params["kind"]

        print(f"[analyzer] тип={kind}, k={k}, max_tokens={max_tokens}, temp={temperature}")

        # ==== Математика ====
        if kind == "math":
            try:
                from math_solver import solve as math_solve
                result, expr = math_solve(question)
                if result is not None:
                    msg = f"{expr} = {result}"

                    try:
                        from self_check import check
                        from self_log import log_issue
                        check_result = check(question, msg, kind="math", math_result=result)
                        print(f"[self-check] {check_result['reason']}")
                        if not check_result["ok"]:
                            log_issue(question, msg, check_result)
                    except ImportError:
                        pass

                    if stream:
                        print(msg)
                    if user_id is not None:
                        try:
                            from memory import add_message
                            add_message(user_id, "assistant", msg[:500])
                        except ImportError:
                            pass
                    return msg
            except ImportError:
                pass

        # ==== Погода ====
        if kind == "weather":
            try:
                from weather import extract_city, get_weather
                city = extract_city(question)
                msg = get_weather(city)
                if stream:
                    print(msg)
                if user_id is not None:
                    try:
                        from memory import add_message
                        add_message(user_id, "assistant", msg[:500])
                    except ImportError:
                        pass
                return msg
            except ImportError:
                pass
            except Exception as e:
                msg = f"⚠️ Ошибка погоды: {e}"
                if stream:
                    print(msg)
                return msg

        # ==== Курсы валют ====
        if kind == "currency":
            try:
                from currency import get_currency_rates, convert_currency
                import re as _re

                m = _re.search(
                    r"(\d+(?:[.,]\d+)?)\s*([а-яa-z]+)\s+в\s+([а-яa-z]+)",
                    question.lower(),
                )
                if m:
                    amount = float(m.group(1).replace(",", "."))
                    from_cur = _cur_code(m.group(2))
                    to_cur = _cur_code(m.group(3))
                    if from_cur and to_cur:
                        msg = convert_currency(amount, from_cur, to_cur)
                    else:
                        msg = get_currency_rates()
                else:
                    msg = get_currency_rates()

                if stream:
                    print(msg)
                if user_id is not None:
                    try:
                        from memory import add_message
                        add_message(user_id, "assistant", msg[:500])
                    except ImportError:
                        pass
                return msg
            except ImportError:
                pass
            except Exception as e:
                msg = f"⚠️ Ошибка валют: {e}"
                if stream:
                    print(msg)
                return msg

        # ==== RAG (search_query уже определён выше) ====
        docs = self.kb.search(search_query, k=k)
        context = "\n\n---\n\n".join(docs) if docs else ""
        source_label = "база"

        # ==== Wikipedia ====
        if not docs or len(context) < 300:
            print("[web] поиск в Wikipedia...")
            try:
                from web_search import web_search

                simplified = search_query
                stop_words = [
                    "когда", "где", "как", "какая", "какой", "какие",
                    "расскажи", "назови", "что такое", "кто такой",
                    "сколько", "почему", "зачем",
                    "вышел", "вышла", "вышло", "был", "была", "было",
                    "последний", "последняя", "последнее",
                ]
                for w in stop_words:
                    simplified = simplified.replace(w, "")
                simplified = " ".join(simplified.split()).strip(" ?!.,")

                if simplified:
                    print(f"[web] упрощённый запрос: {simplified!r}")
                    web_result = web_search(simplified, max_pages=2)
                else:
                    web_result = web_search(search_query, max_pages=2)

                if web_result["context"]:
                    context = web_result["context"]
                    source_label = "Wikipedia"
                    print(f"[web] {len(context)} симв., источников: {len(web_result['sources'])}")
                else:
                    msg = "Не удалось найти информацию ни в базе, ни в Wikipedia."
                    if stream:
                        print(msg)
                    if user_id is not None:
                        try:
                            from memory import add_message
                            add_message(user_id, "assistant", msg[:500])
                        except ImportError:
                            pass
                    return msg
            except ImportError:
                msg = "В собранных данных нет информации по этому вопросу. Попробуйте learn."
                if stream:
                    print(msg)
                if user_id is not None:
                    try:
                        from memory import add_message
                        add_message(user_id, "assistant", msg[:500])
                    except ImportError:
                        pass
                return msg

        if not context:
            msg = "Не удалось получить контекст."
            if stream:
                print(msg)
            return msg

        # ==== История в контекст ====
        if history_context:
            context = f"[Предыдущий диалог]\n{history_context}\n\n[Текущий контекст]\n{context}"

        self._ensure_llm()
        answer = self.llm.answer(
            question, context,
            stream=stream,
            max_new_tokens=max_tokens,
            temperature=temperature,
        )

        if source_label == "Wikipedia":
            answer += "\n\n📖 _Источник: Wikipedia_"

        # ==== Чистка вывода ====
        answer = clean_llm_output(answer)

        # ==== Самоанализ ====
        try:
            from self_check import check
            from self_log import log_issue
            check_result = check(question, answer, kind=kind)
            print(f"[self-check] {check_result['reason']}")
            if not check_result["ok"]:
                log_issue(question, answer, check_result)
        except ImportError:
            pass

        # ==== Память ====
        if user_id is not None and answer:
            try:
                from memory import add_message
                add_message(user_id, "assistant", answer[:500])
            except ImportError:
                pass

        return answer


# ============================================================
# CLI
# ============================================================
def main():
    agent = Agent()
    print("\n=== Windows 11 AI Agent (Qwen 7B int4 + ReAct) ===")
    print("Команды: learn | ask <вопрос> | search <запрос> | stats | exit\n")

    while True:
        try:
            raw = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not raw:
            continue

        cmd, _, arg = raw.partition(" ")
        cmd = cmd.lower()

        if cmd in ("exit", "quit"):
            break
        elif cmd == "learn":
            print("Собираю RSS...")
            try:
                n = agent.learn()
                print(f"Добавлено: {n}. Всего: {len(agent.kb.texts)}")
            except Exception:
                import traceback
                print("ОШИБКА В LEARN:")
                traceback.print_exc()
        elif cmd == "search":
            if not arg:
                print("Использование: search <запрос>")
                continue
            try:
                for i, d in enumerate(agent.kb.search(arg, k=5), 1):
                    print(f"\n[{i}] {d[:400]}{'...' if len(d) > 400 else ''}")
            except Exception:
                import traceback
                print("ОШИБКА В SEARCH:")
                traceback.print_exc()
        elif cmd == "stats":
            print(f"Документов: {len(agent.kb.texts)}")
            print(f"Эмбеддинги: {None if agent.kb.embeddings is None else agent.kb.embeddings.shape}")
            print(f"LLM загружена: {agent.llm is not None}")
            if agent.llm is not None:
                print(f"LLM модель: {agent.llm.model_name}")
        elif cmd == "ask":
            if not arg:
                print("Использование: ask <вопрос>")
                continue
            try:
                print("Agent> ", end="", flush=True)
                agent.ask(arg, stream=True, user_id=1)
            except Exception:
                print()
                print("=" * 60)
                import traceback
                print("ОШИБКА ПРИ ВЫПОЛНЕНИИ ASK:")
                traceback.print_exc()
                print("=" * 60)
        else:
            try:
                print("Agent> ", end="", flush=True)
                agent.ask(raw, stream=True, user_id=1)
            except Exception:
                print()
                print("=" * 60)
                import traceback
                print("ОШИБКА ПРИ ОБРАБОТКЕ ВОПРОСА:")
                traceback.print_exc()
                print("=" * 60)


if __name__ == "__main__":
    main()