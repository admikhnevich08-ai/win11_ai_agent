# -*- coding: utf-8 -*-
"""
Память диалога на SQLite — переживает перезапуск.
API совместим со старой версией:
    add_message(user_id, role, content)
    get_history(user_id, limit=10)
    clear_history(user_id)
    get_all_users()
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from threading import Lock


DB_PATH = Path("./agent_data/memory.db")
DB_PATH.parent.mkdir(exist_ok=True)

_lock = Lock()


def _connect():
    """Открывает соединение с SQLite."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_time
        ON messages(user_id, id)
    """)
    conn.commit()
    return conn


# Одно глобальное соединение — SQLite в одном потоке
_conn = None


def _get_conn():
    global _conn
    if _conn is None:
        _conn = _connect()
    return _conn


def add_message(user_id, role: str, content: str):
    """Добавляет сообщение в историю пользователя."""
    if not content:
        return
    with _lock:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO messages (user_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (int(user_id), role, content, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()


def get_history(user_id, limit: int = 10):
    """Возвращает последние N сообщений (в хронологическом порядке)."""
    with _lock:
        conn = _get_conn()
        cur = conn.execute(
            """
            SELECT role, content FROM (
                SELECT id, role, content FROM messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) ORDER BY id ASC
            """,
            (int(user_id), int(limit)),
        )
        rows = cur.fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]


def clear_history(user_id):
    """Очищает историю пользователя."""
    with _lock:
        conn = _get_conn()
        conn.execute("DELETE FROM messages WHERE user_id = ?", (int(user_id),))
        conn.commit()


def get_all_users():
    """Список user_id, у которых есть история."""
    with _lock:
        conn = _get_conn()
        cur = conn.execute("SELECT DISTINCT user_id FROM messages")
        return [r[0] for r in cur.fetchall()]


def get_total_count(user_id=None):
    """Всего сообщений (для отладки)."""
    with _lock:
        conn = _get_conn()
        if user_id is None:
            cur = conn.execute("SELECT COUNT(*) FROM messages")
        else:
            cur = conn.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (int(user_id),))
        return cur.fetchone()[0]


if __name__ == "__main__":
    # Тест
    user = 999
    clear_history(user)

    add_message(user, "user", "привет")
    add_message(user, "assistant", "Привет! Чем помочь?")
    add_message(user, "user", "расскажи про нейросети")
    add_message(user, "assistant", "Нейросети — это...")

    print("История:")
    for m in get_history(user, limit=10):
        print(f"  [{m['role']}] {m['content'][:50]}")

    print(f"\nВсего у {user}: {get_total_count(user)}")
    print(f"Пользователи: {get_all_users()}")

    clear_history(user)
    print(f"После очистки: {get_history(user)}")