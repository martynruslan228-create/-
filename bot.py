import os
import sqlite3
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# Налаштування логування (щоб бачити помилки в панелі Render)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- СЕРВЕР ДЛЯ ПІДТРИМКИ ЖИТТЯ (Health Check) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logging.info(f"Health check server started on port {port}")
    server.serve_forever()

# --- КОНФІГУРАЦІЯ ---
# ВСТАВТЕ СЮДИ ВАШ НОВИЙ ТОКЕН ПІСЛЯ /REVOKE
TOKEN = "8076199435:AAFOSQ0Ucvo6DpXUhs7Zy_jXhFZ_P7F3Xrw"
CHANNEL_ID = "@autochopOdessa"
DB_PATH = "/tmp/ads.db"

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
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS ads (user_id INTEGER, msg_ids TEXT, details TEXT)')
    conn.commit()
    conn.close()

# --- ОБРОБНИКИ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🚗 <b>Вітаю, {update.effective_user.first_name}!</b>\nВикористовуйте кнопки для керування:",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True, persistent=True)
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
    await update.message.reply_text("КПП:", reply_markup=ReplyKeyboardMarkup(GEARBOX_KEYS, one_time_keyboard=True, resize_keyboard=True))
    return GEARBOX

async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gearbox'] = update.message.text
    await update.message
