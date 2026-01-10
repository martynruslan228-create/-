import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    ConversationHandler
)

# --- НАЛАШТУВАННЯ ---
TOKEN = "8076199435:AAExPYs4SXOUA-ohjIoG2Wn3KPVU5XvEiGc"
CHANNEL_ID = "@autochopOdessa"

# Етапи розмови (додали DISTRICT)
MAKE, MODEL, YEAR, ENGINE, PRICE, DISTRICT, PHOTOS = range(7)

# Список районів Одеської області
ODESSA_DISTRICTS = [
    ["Одеський", "Березівський"],
    ["Білгород-Дністровський", "Болградський"],
    ["Ізмаїльський", "Подільський"],
    ["Роздільнянський", "Інший"]
]

logging.basicConfig(level=logging.INFO)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# --- ЛОГІКА БОТА ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Вітаю! Для створення оголошення натисніть /new")

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['photos'] = []
    await update.message.reply_text("Введіть марку авто (наприклад: Toyota):")
    return MAKE

async def get_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['make'] = update.message.text
    await update.message.reply_text("Введіть модель:")
    return MODEL

async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['model'] = update.message.text
    await update.message.reply_text("Введіть рік випуску:")
    return YEAR

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['year'] = update.message.text
    await update.message.reply_text("Введіть двигун (наприклад: 2.0 Газ/Бензин):")
    return ENGINE

async def get_engine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['engine'] = update.message.text
    await update.message.reply_text("Введіть ціну ($):")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    reply_markup = ReplyKeyboardMarkup(ODESSA_DISTRICTS, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Оберіть район Одеської області:", reply_markup=reply_markup)
    return DISTRICT

async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['district'] = update.message.text
    await update.message.reply_text("Надішліть фото авто. Коли закінчите, натисніть /done", reply_markup=ReplyKeyboardRemove())
    return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    context.user_data['photos'].append(photo_file.file_id)
    await update.message.reply_text(f"Фото додано ({len(context.user_data['photos'])}). Надішліть ще або натисніть /done")
    return PHOTOS

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    caption = (
        f"🚘 **ПРОДАЖ АВТО**\n\n"
        f"🔹 **Марка:** {data['make']}\n"
        f"🔹 **Модель:** {data['model']}\n"
        f"📅 **Рік:** {data['year']}\n"
        f"⛽️ **Двигун:** {data['engine']}\n"
        f"💰 **Ціна:** {data['price']}$\n"
        f"📍 **Район:** {data['district']}\n\n"
        f"👤 **Продавець:** @{update.effective_user.username or 'NoName'}"
    )

    try:
        if data['photos']:
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=data['photos'][0], caption=caption, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode='Markdown')
        await update.message.reply_text("✅ Опубліковано!")
    except Exception as e:
        await update.message.reply_text(f"Помилка: {e}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Скасовано.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    threading.Thread(target=run_server, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("new", new_ad)],
        states={
            MAKE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_make)],
            MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_model)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_year)],
            ENGINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_engine)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_district)],
            PHOTOS: [MessageHandler(filters.PHOTO, get_photos), CommandHandler("done", finish)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("=== BOT STARTED ===")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
