# config.py
"""
Единая точка загрузки настроек проекта.
Все пути и параметры берутся из .env (если заданы) или по умолчанию.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# === Базовые пути ===
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# === Данные ===
AGENT_DATA_DIR = BASE_DIR / os.getenv("AGENT_DATA_DIR", "agent_data")
MODELS_DIR = BASE_DIR / os.getenv("MODELS_DIR", "models")

TEXTS_JSON = AGENT_DATA_DIR / "texts.json"
EMBEDDINGS_NPY = AGENT_DATA_DIR / "embeddings.npy"
HASHES_JSON = AGENT_DATA_DIR / "hashes.json"
MEMORY_DB = AGENT_DATA_DIR / "memory.db"
AGENT_LOG = AGENT_DATA_DIR / "agent.log"
TELEGRAM_LOG = BASE_DIR / "telegram_bot.log"

# === Telegram ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# === LLM ===
LLM_MODEL_PATH = BASE_DIR / os.getenv(
    "LLM_MODEL_PATH",
    "models/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf",
)
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")

# === RAG ===
RAG_THRESHOLD = float(os.getenv("RAG_THRESHOLD", "0.60"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

# === Проверки ===
def validate(require_token: bool = False) -> None:
    """Проверяет ключевые настройки. Вызывать при старте."""
    if require_token and not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN не задан. Скопируй .env.example → .env и впиши токен."
        )
    if not LLM_MODEL_PATH.exists():
        print(f"[config] ⚠️  Модель не найдена: {LLM_MODEL_PATH}")
    if not TEXTS_JSON.exists():
        print(f"[config] ⚠️  База знаний не найдена: {TEXTS_JSON}")

# === Создаём папки, если их нет ===
AGENT_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# === Отладочный вывод (если запустить config.py напрямую) ===
if __name__ == "__main__":
    print(f"BASE_DIR       = {BASE_DIR}")
    print(f"AGENT_DATA_DIR = {AGENT_DATA_DIR}")
    print(f"MODELS_DIR     = {MODELS_DIR}")
    print(f"LLM_MODEL_PATH = {LLM_MODEL_PATH} (exists={LLM_MODEL_PATH.exists()})")
    print(f"TEXTS_JSON     = {TEXTS_JSON} (exists={TEXTS_JSON.exists()})")
    print(f"MEMORY_DB      = {MEMORY_DB}")
    print(f"EMBED_MODEL    = {EMBED_MODEL}")
    print(f"RAG_THRESHOLD  = {RAG_THRESHOLD}")
    print(f"TOKEN set      = {bool(TELEGRAM_BOT_TOKEN)}")