import os
import sqlite3
import threading
import logging
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# 1. НАЛАШТУВАННЯ ЛОГІВ
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. КОНФІГУРАЦІЯ
TOKEN = "8076199435:AAHJ8hnLJaKvVl7DIhKiKZBi2aAFCg5ddEE"
CHANNEL_ID = "@autochopOdessa"
DB_PATH = "ads.db"

# Стейт-машина
(MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, TOWN, PRICE, 
 DESCRIPTION, PHOTOS, PHONE, SHOW_
 
