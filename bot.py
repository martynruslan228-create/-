import logging
import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# --- 1. СЕРВЕР ДЛЯ ПІДТРИМКИ ЖИТТЯ ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- 2. НАЛАШТУВАННЯ ---
TOKEN = "8076199435:AAExPYs4SXOUA-ohjIoG2Wn3KPVU5XvEiGc"
CHANNEL_ID = "@autochopOdessa"
# Шлях до бази у тимчасовій папці Render для уникнення помилок запису
DB_PATH = "/tmp/ads.db"

MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, PRICE, PHOTOS, CONFIRM = range(10)

GEARBOX_KEYS = [["Механіка", "Автомат"], ["Робот", "Варіатор"]]
FUEL_KEYS = [["Бензин", "Дизель"], ["Газ/Бензин", "Електро"], ["Гібрид"]]
DRIVE_KEYS = [["Передній", "Задній"], ["Повний"]]
DISTRICTS = [["Одеський", "Березівський"], ["Білгород-Дністровський"], ["Болградський", "Ізмаїльський"], ["Подільський", "Роздільнянський"]]

# --- 3. БАЗА ДАНИХ ---
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('CREATE TABLE IF NOT EXISTS ads (user_id INTEGER, msg_id INTEGER, details TEXT)')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Помилка бази даних: {e}")

# --- 4. ЛОГІКА ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🚗 <b>Привіт, {update.effective_user.first_name}!</b>\n\nКоманди:\n🔹 /new — Створити оголошення\n🔹 /my — Мої оголошення",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove()
    )

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Введіть марку авто:")
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
    await update.message.reply_text("КПП:", reply_markup=ReplyKeyboardMarkup(GEARBOX_KEYS, one_time_keyboard=True, resize_keyboard=True))
    return GEARBOX

async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gearbox'] = update.message.text
    await update.message.reply_text("Паливо:", reply_markup=ReplyKeyboardMarkup(FUEL_KEYS, one_time_keyboard=True, resize_keyboard=True))
    return FUEL

async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fuel'] = update.message.text
    await update.message.reply_text("Привід:", reply_markup=ReplyKeyboardMarkup(DRIVE_KEYS, one_time_keyboard=True, resize_keyboard=True))
    return DRIVE

async def get_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['drive'] = update.message.text
    await update.message.reply_text("Район:", reply_markup=ReplyKeyboardMarkup(DISTRICTS, one_time_keyboard=True, resize_keyboard=True))
    return DISTRICT

async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['district'] = update.message.text
    await update.message.reply_text("Ціна ($):", reply_markup=ReplyKeyboardRemove())
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    context.user_data['photos'] = []
    await update.message.reply_text("Надішліть фото, потім натисніть /done")
    return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['photos'].append(update.message.photo[-1].file_id)
    return PHOTOS

async def done_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('photos'):
        await update.message.reply_text("Треба фото!")
        return PHOTOS
    
    u = update.effective_user
    contact = f"@{u.username}" if u.username else "не вказано"
    summary = (
        f"🚘 <b>{context.user_data['make']} {context.user_data['model']}</b>\n"
        f"📅 Рік: {context.user_data['year']}\n"
        f"⚙️ КПП: {context.user_data['gearbox']} | {context.user_data['fuel']}\n"
        f"📍 Район: {context.user_data['district']}\n"
        f"💰 <b>Ціна: {context.user_data['price']}$</b>\n\n"
        f"👤 Контакт: {contact}"
    )
    context.user_data['summary'] = summary
    await update.message.reply_text(f"Перевірка:\n\n{summary}\n\nОпублікувати? (так/ні)", parse_mode=ParseMode.HTML)
    return CONFIRM

async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'так':
        msg = await context.bot.send_photo(chat_id=CHANNEL_ID, photo=context.user_data['photos'][0], caption=context.user_data['summary'], parse_mode=ParseMode.HTML)
        conn = sqlite3.connect(DB_PATH)
        conn.execute('INSERT INTO ads VALUES (?, ?, ?)', (update.effective_user.id, msg.message_id, context.user_data['summary']))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ Готово!")
    else:
        await update.message.reply_text("Скасовано.")
    return ConversationHandler.END

async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute('SELECT msg_id, details FROM ads WHERE user_id = ?', (update.effective_user.id,))
    ads = cursor.fetchall()
    conn.close()
    if not ads:
        await update.message.reply_text("Немає оголошень.")
        return
    for mid, text in ads:
        kb = [[InlineKeyboardButton("🗑 Видалити", callback_data=f"del_{mid}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def del_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mid = int(update.callback_query.data.split('_')[1])
    try:
        await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=mid)
        conn = sqlite3.connect(DB_PATH)
        conn.execute('DELETE FROM ads WHERE msg_id = ?', (mid,))
        conn.commit()
        conn.close()
        await update.callback_query.edit_message_text("Видалено!")
    except:
        await update.callback_query.answer("Помилка видалення")

def main():
    init_db()
    threading.Thread(target=run_health_server, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler('new', new_ad)],
        states={
            MAKE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_make)],
            MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_model)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_year)],
            GEARBOX: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gearbox)],
            FUEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fuel)],
            DRIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_drive)],
            DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_district)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            PHOTOS: [MessageHandler(filters.PHOTO, get_photos), CommandHandler('done', done_photos)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_post)],
        },
        fallbacks=[]
    )
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('my', my_ads))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(del_callback, pattern='^del_'))
    app.run_polling()

if __name__ == "__main__":
    main()
