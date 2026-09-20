# -*- coding: utf-8 -*-
"""
Telegram-бот в фоновом режиме.
Запускается через pythonw.exe (без окна).
Все логи пишутся в telegram_bot.log
"""
import sys
import os
from pathlib import Path
from datetime import datetime

from config import BASE_DIR, TELEGRAM_BOT_TOKEN, TELEGRAM_LOG

# Переходим в папку проекта
project = BASE_DIR
sys.path.insert(0, str(project))
os.chdir(project)

# Перенаправляем stdout и stderr в файл
log_path = TELEGRAM_LOG
log_file = open(log_path, "a", encoding="utf-8", buffering=1)
sys.stdout = log_file
sys.stderr = log_file

print(f"\n{'=' * 60}")
print(f"BOT START: {datetime.now()}")
print(f"{'=' * 60}")

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from windows11_ai_agent import Agent

TOKEN = TELEGRAM_BOT_TOKEN

agent = None


def get_agent():
    global agent
    if agent is None:
        print(f"[{datetime.now()}] Загрузка Agent...")
        agent = Agent()
        print(f"[{datetime.now()}] Agent загружен. Документов: {len(agent.kb.texts)}")
    return agent


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[{datetime.now()}] /start")
    await update.message.reply_text(
        "👋 Привет! Я локальный AI-агент.\n\n"
        "Просто напиши вопрос — отвечу.\n\n"
        "Что умею:\n"
        "• Погода: «погода в Москве»\n"
        "• Математика: «2+2», «15 умножить на 7»\n"
        "• Поиск в базе знаний\n\n"
        "Команды:\n"
        "/ask <вопрос>\n"
        "/search <запрос>\n"
        "/stats\n"
        "/learn\n"
        "/errors — журнал ошибок"
    )


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = " ".join(context.args) if context.args else ""
    if not q:
        await update.message.reply_text("Использование: /ask <вопрос>")
        return
    print(f"[{datetime.now()}] /ask: {q}")
    msg = await update.message.reply_text("🤔 Думаю...")
    try:
        answer = get_agent().ask(q, stream=False, user_id=update.effective_user.id)
        if len(answer) > 4000:
            answer = answer[:4000] + "..."
        await msg.edit_text(answer)
        print(f"[{datetime.now()}] Ответ отправлен ({len(answer)} симв.)")
    except Exception:
        import traceback
        traceback.print_exc()
        await msg.edit_text(f"Ошибка: {traceback.format_exc()[:3500]}")


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = " ".join(context.args) if context.args else ""
    if not q:
        await update.message.reply_text("Использование: /search <запрос>")
        return
    print(f"[{datetime.now()}] /search: {q}")
    try:
        docs = get_agent().kb.search(q, k=5)
        if not docs:
            await update.message.reply_text("Ничего не найдено.")
            return
        txt = "\n\n".join(
            f"[{i+1}] {d[:300]}{'...' if len(d) > 300 else ''}"
            for i, d in enumerate(docs)
        )
        await update.message.reply_text(txt[:4000])
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[{datetime.now()}] /stats")
    try:
        a = get_agent()
        await update.message.reply_text(
            f"📊 Документов: {len(a.kb.texts)}\n"
            f"Эмбеддинги: {None if a.kb.embeddings is None else a.kb.embeddings.shape}\n"
            f"LLM: {a.llm is not None}"
        )
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


async def cmd_learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[{datetime.now()}] /learn")
    msg = await update.message.reply_text("📥 Собираю RSS...")
    try:
        added = get_agent().learn()
        await msg.edit_text(f"✅ Добавлено: {added}. Всего: {len(get_agent().kb.texts)}")
    except Exception as e:
        await msg.edit_text(f"Ошибка: {e}")


async def cmd_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать журнал ошибок самоанализа."""
    print(f"[{datetime.now()}] /errors")
    try:
        from self_log import get_stats
        stats = get_stats()
        if stats["total"] == 0:
            await update.message.reply_text("✅ Ошибок не было!")
            return

        lines = [f"⚠️ Всего проблем: {stats['total']}\n"]
        for reason, count in sorted(stats["reasons"].items(), key=lambda x: -x[1]):
            lines.append(f"• {reason}: {count}")

        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.message.text.strip()

    # Фильтр приветствий (только чистые приветствия)
    lower = q.lower().strip("!?., ")
    greetings = {
        "привет", "здравствуй", "здравствуйте", "хай", "hi", "hello",
        "добрый день", "добрый вечер", "доброе утро", "ку", "прив",
        "как дела", "как ты", "что делаешь", "спасибо", "благодарю",
        "пока", "до свидания", "bye", "start", "старт",
    }
    if lower in greetings:
        await update.message.reply_text(
            "👋 Привет! Я AI-агент по новостям IT/AI.\n\n"
            "Задай конкретный вопрос, например:\n"
            "• расскажи про нейросети\n"
            "• что пишут про OpenAI\n"
            "• погода в Москве\n"
            "• 2+2\n"
            "• /stats — статистика базы\n"
            "• /learn — обновить базу\n"
            "• /errors — журнал ошибок"
        )
        return

    print(f"[{datetime.now()}] Вопрос: {q}")
    msg = await update.message.reply_text("🤔 Думаю...")
    try:
        answer = get_agent().ask(q, stream=False, user_id=update.effective_user.id)
        if len(answer) > 4000:
            answer = answer[:4000] + "..."
        await msg.edit_text(answer)
        print(f"[{datetime.now()}] Ответ отправлен ({len(answer)} симв.)")
    except Exception as e:
        print(f"[{datetime.now()}] ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        await msg.edit_text(f"Ошибка: {e}")


def main():
    print(f"[{datetime.now()}] Запуск...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("learn", cmd_learn))
    app.add_handler(CommandHandler("errors", cmd_errors))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    print(f"[{datetime.now()}] Бот запущен в фоне.")
    app.run_polling()


if __name__ == "__main__":
    main()