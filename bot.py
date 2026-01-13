print("Скрипт розпочав роботу...") # Ваш запит

import os
import sqlite3
import threading
import logging
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# 1. НАЛАШТУВАННЯ ЛОГУВАННЯ (щоб ви бачили все в консолі Render)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 2. СЕРВЕР ДЛЯ ПІДТРИМКИ ЖИТТЯ (Щоб Render не видавав "Exited early")
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_server():
    # Render передає порт автоматично, ми його підхоплюємо
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Сервер перевірки (Health Check) запущено на порту {port}")
    server.serve_forever()

# 3. КОНФІГУРАЦІЯ
# ПЕРЕКОНАЙТЕСЯ, ЩО ЦЕЙ ТОКЕН СВІЖИЙ (ПІСЛЯ /REVOKE)
TOKEN = "8076199435:AAFOSQ0Ucvo6DpXUhs7Zy_jXhFZ_P7F3Xrw"
CHANNEL_ID = "@autochopOdessa"
DB_PATH = "/tmp/ads.db" # Тимчасова база для Render

# Етапи анкети
MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, TOWN, PRICE, DESCRIPTION, PHOTOS, SHOW_CONTACT, CONFIRM = range(13)

# Клавіатури
MAIN_MENU = [["➕ Нове оголошення"], ["🗂 Мої оголошення"]]
GEARBOX_KEYS = [["Механіка", "Автомат"], ["Робот", "Варіатор"]]
FUEL_KEYS = [["Бензин", "Дизель"], ["Газ/Бензин", "Електро"], ["Гібрид"]]
DRIVE_KEYS = [["Передній", "Задній"], ["Повний"]]
DISTRICTS = [["Одеський", "Березівський"], ["Білгород-Дністровський"], ["Болградський", "Ізмаїльський"], ["Подільський", "
                                                                                                          
