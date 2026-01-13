print("Скрипт розпочав роботу...")

import os
import sqlite3
import threading
import logging
import sys

# Спроба імпорту бібліотеки з виводом помилки в логи
try:
    from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
    from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
    from telegram.constants import ParseMode
except ImportError as e:
    print(f"Критична помилка: Бібліотеку python-telegram-bot не знайдено! {e}")
    sys.exit(1)

from http.server import HTTPServer, BaseHTTPRequestHandler

# 1. НАЛАШТУВАННЯ ЛОГУВАННЯ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. HEALTH CHECK СЕРВЕР
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Health check запуск на порту {port}")
    server.serve_forever()

# 3. КОНФІГУРАЦІЯ
TOKEN = "8076199435:AAFOSQ0Ucvo6DpXUhs7Zy_jXhFZ_P7F3Xrw"
CHANNEL_ID = "@autochopOdessa"
DB_PATH = "ads.db" # Змінив шлях на локальний для стабільності

# Етапи анкети
MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, TOWN, PRICE, DESCRIPTION, PHOTOS, SHOW_CONTACT, CONFIRM = range(13)

# Кнопки
MAIN_MENU = [["➕ Нове оголошення"], ["🗂 Мої оголошення"]]
GEARBOX_KEYS = [["Механіка", "Автомат"], ["Робот", "Варіатор"]]
FUEL_KEYS = [["Бензин", "Дизель"], ["Газ/Бензин", "Електро"], ["Гібрид"]]
DRIVE_KEYS = [["Передній", "Задній"], ["Повний"]]
DISTRICTS = [["Одеський", "Березівський"], ["Білгород-Дністровський"], ["Болградський", "Ізмаїльський"], ["Подільський", "Роздільнянський"]]
YES_NO = [["Так", "Ні"]]

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('CREATE TABLE IF NOT EXISTS ads (user_id INTEGER, msg_ids TEXT, details TEXT)')
        conn.commit()
        conn.close()
        logger.info("База даних ініціалізована.")
    except Exception as e:
        logger.error(f"Помилка БД: {e}")

# --- ОБРОБНИКИ (Скорочено для стабільності) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🚗 Вітаю, {update.effective_user.first_name}!",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
    )
    return ConversationHandler.END

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['photos'] = []
    await update.message.reply_text("Введіть марку авто:", reply_markup=ReplyKeyboardRemove())
    return MAKE

async def get_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['make'] = update.message.text
    await update.message.reply_text("Введіть модель:")
    return MODEL

async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['model'] = update.message.text
    await update.message.reply_text("Введіть рік:")
    return YEAR

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['year'] = update.message.text
    await update.message.reply_text("КПП:", reply_markup=ReplyKeyboardMarkup(GEARBOX_KEYS, resize_keyboard=True))
    return GEARBOX

async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gearbox'] = update.message.text
    await update.message.reply_text("Паливо:", reply_markup=ReplyKeyboardMarkup(FUEL_KEYS, resize_keyboard=True))
    return FUEL

async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fuel'] = update.message.text
    await update.message.reply_text("Привід:", reply_markup=ReplyKeyboardMarkup(DRIVE_KEYS, resize_keyboard=True))
    return DRIVE

async def get_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['drive'] = update.message.text
    await update.message.reply_text("Район:", reply_markup=ReplyKeyboardMarkup(DISTRICTS, resize_keyboard=True))
    return DISTRICT

async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['district'] = update.message.text
    await update.message.reply_text("Місто/село:")
    return TOWN

async def get_town(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['town'] = update.message.text
    await update.message.reply_text("Ціна ($):")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("Опис:")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Надішліть фото, потім /done")
    return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['photos'].append(update.message.photo[-1].file_id)
    return PHOTOS

async def done_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Показувати контакт?", reply_markup=ReplyKeyboardMarkup(YES_NO, resize_keyboard=True))
    return SHOW_CONTACT

async def get_contact_pref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    context.user_data['contact'] = f"@{u.username}" if update.message.text == "Так" and u.username else "приховано"
    summary = f"🚘 {context.user_data['make']} {context.user_data['model']}\n💰 Ціна: {context.user_data['price']}$"
    context.user_data['summary'] = summary
    await update.message.reply_text(f"Прев'ю:\n{summary}\n\nОпублікувати?", reply_markup=ReplyKeyboardMarkup(YES_NO, resize_keyboard=True))
    return CONFIRM

async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Так":
        photos = context.user_data['photos']
        media = [InputMediaPhoto(photos[0], caption=context.user_data['summary'])]
        for p in photos[1:10]: media.append(InputMediaPhoto(p))
        await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        await update.message.reply_text("✅ Готово!", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
    return ConversationHandler.END

async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Функція перегляду в розробці.")

def main():
    init_db()
    threading.Thread(target=run_health_server, daemon=True).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Нове оголошення$"), new_ad)],
        states={
            MAKE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_make)],
            MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_model)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_year)],
            GEARBOX: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gearbox)],
            FUEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fuel)],
            DRIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_drive)],
            DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_district)],
            TOWN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_town)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            PHOTOS: [MessageHandler(filters.PHOTO, get_photos), CommandHandler('done', done_photos)],
            SHOW_CONTACT: [MessageHandler(filters.Regex("^(Так|Ні)$"), get_contact_pref)],
            CONFIRM: [MessageHandler(filters.Regex("^(Так|Ні)$"), confirm_post)],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.Regex("^🗂 Мої оголошення$"), my_ads))
    app.add_handler(conv)
    
    logger.info("Бот запускається через Polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
    
