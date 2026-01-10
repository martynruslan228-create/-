import logging
import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# --- СЕРВЕР ДЛЯ RENDER ---
class H(BaseHTTPRequestHandler):
    def do_GET(self): 
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
def run_h(): 
    HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), H).serve_forever()

# --- НАЛАШТУВАННЯ ---
TOKEN = "8076199435:AAExPYs4SXOUA-ohjIoG2Wn3KPVU5XvEiGc"
CHANNEL_ID = "@autochopOdessa"

MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, PRICE, PHOTOS, CONFIRM = range(10)

GEARBOX_KEYS = [["Механіка", "Автомат"], ["Робот", "Варіатор"]]
FUEL_KEYS = [["Бензин", "Дизель"], ["Газ/Бензин", "Електро"], ["Гібрид"]]
DRIVE_KEYS = [["Передній", "Задній"], ["Повний"]]
DISTRICTS = [["Одеський", "Березівський"], ["Білгород-Дністровський"], ["Болградський", "Ізмаїльський"], ["Подільський", "Роздільнянський"]]

def init_db():
    conn = sqlite3.connect('ads.db')
    conn.execute('CREATE TABLE IF NOT EXISTS ads (user_id INTEGER, msg_id INTEGER, details TEXT)')
    conn.commit(); conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚗 Auto Chop Odessa\n/new - Додати авто\n/my - Мої оголошення")
    return ConversationHandler.END

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Введіть марку авто:")
    return MAKE

async def get_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['make'] = update.message.text
    await update.message.reply_text("Модель:")
    return MODEL

async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['model'] = update.message.text
    await update.message.reply_text("Рік:")
    return YEAR

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['year'] = update.message.text
    await update.message.reply_text("КПП:", reply_markup=ReplyKeyboardMarkup(GEARBOX_KEYS, one_time_keyboard=True))
    return GEARBOX

async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gearbox'] = update.message.text
    await update.message.reply_text("Паливо:", reply_markup=ReplyKeyboardMarkup(FUEL_KEYS, one_time_keyboard=True))
    return FUEL

async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fuel'] = update.message.text
    await update.message.reply_text("Привід:", reply_markup=ReplyKeyboardMarkup(DRIVE_KEYS, one_time_keyboard=True))
    return DRIVE

async def get_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['drive'] = update.message.text
    await update.message.reply_text("Район:", reply_markup=ReplyKeyboardMarkup(DISTRICTS, one_time_keyboard=True))
    return DISTRICT

async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['district'] = update.message.text
    await update.message.reply_text("Ціна ($):", reply_markup=ReplyKeyboardRemove())
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    context.user_data['photos'] = []
    await update.message.reply_text("Надсилайте фото по одному. Коли закінчите — натисніть /done")
    return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        context.user_data['photos'].append(file_id)
        # Бот відповідає, щоб ви знали, що він не завис
        await update.message.reply_text(f"✅ Фото {len(context.user_data['photos'])} отримано. Ще фото чи /done?")
    return PHOTOS

async def done_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('photos'):
        await update.message.reply_text("Треба хоча б одне фото!")
        return PHOTOS
    
    summary = (
        f"🚘 *{context.user_data['make']} {context.user_data['model']}*\n"
        f"📅 Рік: {context.user_data['year']}\n"
        f"⚙️ КПП: {context.user_data['gearbox']} | ⛽️ {context.user_data['fuel']}\n"
        f"⛓ Привід: {context.user_data['drive']}\n"
        f"📍 Район: {context.user_data['district']}\n"
        f"💰 *Ціна: {context.user_data['price']}$*\n\n"
        f"👤 Контакт: @{update.effective_user.username or 'немає'}"
    )
    context.user_data['summary'] = summary
    await update.message.reply_text(f"{summary}\n\nОпублікувати? (так/ні)", parse_mode=ParseMode.MARKDOWN)
