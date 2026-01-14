from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Вставляем твой токен прямо сюда
TOKEN = "8076199435:AAGiwer-2fNz4tZHagOtjuIWVkyx1UFvH6k"

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает ✅")

# Команда /ping для теста
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong 🏓")

def main():
    # Создаём приложение
    app = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))

    # Запуск polling (не будет конфликта с webhook)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
