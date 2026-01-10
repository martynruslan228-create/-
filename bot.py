import logging
import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# --- ФЕЙКОВИЙ СЕРВЕР ДЛЯ RENDER ---
class H(BaseHTTPRequestHandler):
    def do_GET(self): 
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
def run_h(): 
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), H).serve_forever()

# --- НАЛАШТУВАННЯ ---
TOKEN = "8076199435:AAExPYs4SXOUA-ohjIoG2Wn3KPVU5XvEiGc"
CHANNEL_ID = "@autochopOdessa"

# Етапи діалогу
MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, PRICE, PHOTOS, CONFIRM = range(10)

# Кнопки
GEARBOX_KEYS = [["Механіка", "Автомат"], ["Робот", "Варіатор"]]
FUEL_KEYS = [["Бензин", "Дизель"], ["Газ/Бензин", "Електро"], ["Гібрид"]]
DRIVE_KEYS = [["Передній", "Задній"], ["Повний"]]
DISTRICTS = [["Одеський", "Березівський"], ["Білгород-Дністровський"], ["Болградський", "Ізмаїльський"], ["Подільський", "Роздільнянський"]]

# --- БАЗА ДАНИХ ---
def init_db():
    conn = sqlite3.connect('ads.db')
    conn.execute('CREATE TABLE IF NOT EXISTS ads (user_id INTEGER, msg_id INTEGER, details TEXT)')
    conn.commit()
    conn.close()

# --- ЛОГІКА БОТА ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚗 Вітаю в Auto Chop Odessa!\n\nКоманди:\n/new - Створити оголошення\n/my - Мої оголошення (видалення)",
        reply_markup=ReplyKeyboardRemove()
    )

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Введіть марку авто (наприклад, BMW):")
    return MAKE

async def get_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['make'] = update.message.text
    await update.message.reply_text("Введіть модель (наприклад, X5):")
    return MODEL

async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['model'] = update.message.text
    await update.message.reply_text("Введіть рік випуску:")
    return YEAR

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['year'] = update.message.text
    await update.message.reply_text("Оберіть КПП:", reply_markup=ReplyKeyboardMarkup(GEARBOX_KEYS, one_time_keyboard=True))
    return GEARBOX

async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gearbox'] = update.message.text
    await update.message.reply_text("Оберіть тип палива:", reply_markup=ReplyKeyboardMarkup(FUEL_KEYS, one_time_keyboard=True))
    return FUEL

async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fuel'] = update.message.text
    await update.message.reply_text("Оберіть привід:", reply_markup=ReplyKeyboardMarkup(DRIVE_KEYS, one_time_keyboard=True))
    return DRIVE

async def get_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['drive'] = update.message.text
    await update.message.reply_text("Оберіть район області:", reply_markup=ReplyKeyboardMarkup(DISTRICTS, one_time_keyboard=True))
    return DISTRICT

async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['district'] = update.message.text
    await update.message.reply_text("Введіть ціну в $:", reply_markup=ReplyKeyboardRemove())
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    context.user_data['photos'] = [] # Ініціалізація списку фото
    await update.message.reply_text("Надішліть фото авто. Коли закінчите, обов'язково натисніть або напишіть /done")
    return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['photos'].append(update.message.photo[-1].file_id)
    return PHOTOS

async def done_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('photos'):
        await update.message.reply_text("Будь ласка, надішліть хоча б одне фото, а потім натисніть /done")
        return PHOTOS
    
    user = update.effective_user
    contact = f"@{user.username}" if user.username else "не вказано (налаштуйте username)"
    
    # Формуємо текст без символів, які можуть зламати Markdown
    summary = (
        f"🚘 *{context.user_data['make']} {context.user_data['model']}*\n"
        f"📅 Рік: {context.user_data['year']}\n"
        f"⚙️ КПП: {context.user_data['gearbox']} | ⛽️ {context.user_data['fuel']}\n"
        f"⛓ Привід: {context.user_data['drive']}\n"
        f"📍 Район: {context.user_data['district']}\n"
        f"💰 *Ціна: {context.user_data['price']}$*\n\n"
        f"👤 Продавець: {contact}"
    )
    context.user_data['summary'] = summary
    
    await update.message.reply_text(
        f"Ось ваше оголошення:\n\n{summary}\n\nОпублікувати в канал? (Напишіть 'так' або 'ні')",
        parse_mode=ParseMode.MARKDOWN
    )
    return CONFIRM

async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    decision = update.message.text.lower()
    if decision == 'так':
        photos = context.user_data['photos']
        # Відправка першого фото з описом у канал
        msg = await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=photos[0],
            caption=context.user_data['summary'],
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Запис у базу для подальшого видалення
        conn = sqlite3.connect('ads.db')
        conn.execute('INSERT INTO ads VALUES (?, ?, ?)', (update.effective_user.id, msg.message_id, context.user_data['summary']))
        conn.commit()
        conn.close()
        
        await update.message.reply_text("✅ Опубліковано! Ви можете знайти та видалити його через команду /my")
    else:
        await update.message.reply_text("Оголошення скасовано.")
    
    return ConversationHandler.END

# --- КЕРУВАННЯ СВОЇМИ ОГОЛОШЕННЯМИ ---
async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('ads.db')
    cursor = conn.execute('SELECT msg_id, details FROM ads WHERE user_id = ?', (update.effective_user.id,))
    ads = cursor.fetchall()
    conn.close()
    
    if not ads:
        await update.message.reply_text("У вас поки немає активних оголошень.")
        return

    for msg_id, details in ads:
        keyboard = [[InlineKeyboardButton("🗑 Видалити з каналу", callback_data=f"del_{msg_id}")]]
        await update.message.reply_text(
            f"Ваше оголошення:\n\n{details}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg_id = int(query.data.split('_')[1])
    try:
        await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=msg_id)
        conn = sqlite3.connect('ads.db')
        conn.execute('DELETE FROM ads WHERE msg_id = ?', (msg_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text("✅ Оголошення видалено з каналу та бази.")
    except Exception:
        await query.answer("Помилка: Не вдалося видалити. Можливо, пост вже видалено.")

def main():
    init_db()
    # Запуск сервера для Render
    threading.Thread(target=run_h, daemon=True).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('new', new_ad)],
        states={
            MAKE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_make)],
            MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_model)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_year)],
            GEARBOX: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gearbox)],
            FUEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fuel)],
            DRIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get
