from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ⬇⬇⬇ ВОТ СЮДА, БЕЗ КАВЫЧЕК ВНУТРИ ⬇⬇⬇
TOKEN = "8076199435:AAGiwer-2fNz4tZHagOtjuIWVkyx1UFvH6k"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает ✅")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
