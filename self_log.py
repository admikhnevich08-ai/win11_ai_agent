# -*- coding: utf-8 -*-
"""
Журнал ошибок самоанализа.
"""
import json
from pathlib import Path
from datetime import datetime

LOG_PATH = Path("agent_data/self_check_log.json")


def log_issue(question: str, answer: str, check_result: dict):
    """Записывает проблему в журнал."""
    LOG_PATH.parent.mkdir(exist_ok=True)

    entry = {
        "time": datetime.now().isoformat(),
        "question": question[:200],
        "answer": answer[:500],
        "reason": check_result.get("reason", "unknown"),
    }

    if LOG_PATH.exists():
        try:
            data = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = []
    else:
        data = []

    data.append(entry)
    data = data[-1000:]

    LOG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_stats() -> dict:
    """Статистика проблем."""
    if not LOG_PATH.exists():
        return {"total": 0, "reasons": {}}

    try:
        data = json.loads(LOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"total": 0, "reasons": {}}

    reasons = {}
    for entry in data:
        r = entry.get("reason", "unknown")
        reasons[r] = reasons.get(r, 0) + 1

    return {"total": len(data), "reasons": reasons}


if __name__ == "__main__":
    log_issue("2+2", "2+2 = 5", {"reason": "ожидалось 4, найдено 5"})
    print(get_stats())