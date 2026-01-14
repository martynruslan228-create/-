from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

# Вставь сюда свой токен или используй переменную окружения
TOKEN = os.environ.get("8076199435:AAGiwer-2fNz4tZHagOtjuIWVkyx1UFvH6k", "PASTE_YOUR_TOKEN_HERE")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает ✅")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong 🏓")

def main():
    # Создаём приложение
    app = ApplicationBuilder().token(TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))

    # Запуск polling
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
