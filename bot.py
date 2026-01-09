import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Берём данные из переменных окружения (будем задавать на Render)
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 👋\n"
        "Отправь фото авто и описание — я опубликую объявление в канале."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если прислали фото
    if update.message.photo:
        photo = update.message.photo[-1].file_id
        caption = update.message.caption or "Без описания"

        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=photo,
            caption=caption
        )
        await update.message.reply_text("✅ Объявление опубликовано")
    else:
        await update.message.reply_text("❗ Отправь фото с описанием автомобиля.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
