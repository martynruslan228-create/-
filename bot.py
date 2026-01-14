import os
import sqlite3
import threading
import logging
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# Логирование (поможет увидеть ошибки в панели Render)
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8076199435:AAHJ8hnLJaKvVl7DIhKiKZBi2aAFCg5ddEE"
CHANNEL_ID = "@autochopOdessa"
DB_PATH = "ads.db"

# Состояния
(MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, TOWN, PRICE, 
 DESCRIPTION, PHOTOS, PHONE, SHOW_CONTACT, CONFIRM) = range(14)

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS ads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, msg_ids TEXT, details TEXT)')
    conn.commit()
    conn.close()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def generate_summary(data):
    tg = f"@{data['username']}" if data.get('show_tg') == "Так" and data.get('username') else "приховано"
    return (
        f"🚘 <b>{data['make']} {data['model']}</b>\n"
        f"📅 Рік: {data['year']}\n"
        f"⚙️ КПП: {data['gearbox']} | ⛽️ {data['fuel']}\n"
        f"📍 {data['district']} р-н, {data['town']}\n"
        f"💰 <b>Ціна: {data['price']}$</b>\n\n"
        f"📝 <b>Опис:</b> {data['description']}\n\n"
        f"📞 Тел: <code>{data['phone']}</code>\n"
        f"👤 Telegram: {tg}"
    )

# --- ОБРАБОТЧИКИ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚗 Вітаю!", reply_markup=ReplyKeyboardMarkup([["➕ Нове оголошення"], ["🗂 Мої оголошення"]], resize_keyboard=True))
    return ConversationHandler.END

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['photos'] = []
    await update.message.reply_text("Марка авто:", reply_markup=ReplyKeyboardRemove())
    return MAKE

async def step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, key, next_st, msg, kb=None):
    if update.message.text != "➡️ Залишити як є":
        context.user_data[key] = update.message.text
    # Если мы в режиме редактирования (is_edit), показываем кнопку пропуска
    markup = kb if kb else (ReplyKeyboardMarkup([["➡️ Залишити як є"]], resize_keyboard=True) if context.user_data.get('is_edit') else ReplyKeyboardRemove())
    await update.message.reply_text(msg, reply_markup=markup)
    return next_st

# Краткие версии шагов (логика не менялась)
async def get_make(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'make', MODEL, "Модель:")
async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'model', YEAR, "Рік:")
async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'year', GEARBOX, "КПП:", ReplyKeyboardMarkup([["Механіка", "Автомат"], ["➡️ Залишити як є"]], resize_keyboard=True))
async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'gearbox', FUEL, "Паливо:", ReplyKeyboardMarkup([["Бензин", "Дизель"], ["Газ/Бензин", "Електро"]], resize_keyboard=True))
async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'fuel', DRIVE, "Привід:", ReplyKeyboardMarkup([["Передній", "Задній", "Повний"]], resize_keyboard=True))
async def get_drive(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'drive', DISTRICT, "Район:", ReplyKeyboardMarkup([["Одеський", "Березівський", "Болградський"]], resize_keyboard=True))
async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'district', TOWN, "Місто:")
async def get_town(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'town', PRICE, "Ціна ($):")
async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'price', DESCRIPTION, "Опис:")

async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "➡️ Залишити як є": context.user_data['description'] = update.message.text
    await update.message.reply_text("Надішліть фото та натисніть /done або кнопку нижче:", reply_markup=ReplyKeyboardMarkup([["➡️ Залишити як є"]], resize_keyboard=True))
    return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo: context.user_data['photos'].append(update.message.photo[-1].file_id)
    return PHOTOS

async def done_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Телефон:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "➡️ Залишити як є": context.user_data['phone'] = update.message.text
    await update.message.reply_text("Показувати Telegram?", reply_markup=ReplyKeyboardMarkup([["Так", "Ні"]], resize_keyboard=True))
    return SHOW_CONTACT

async def get_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "➡️ Залишити як є": context.user_data['show_tg'] = update.message.text
    context.user_data['username'] = update.effective_user.username
    summary = generate_summary(context.user_data)
    context.user_data['summary'] = summary
    await update.message.reply_text(f"Прев'ю:\n\n{summary}\n\nОпублікувати?", reply_markup=ReplyKeyboardMarkup([["Так", "Ні"]], resize_keyboard=True), parse_mode=ParseMode.HTML)
    return CONFIRM

async def final_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Так":
        photos = context.user_data.get('photos', [])
        cap = context.user_data['summary']
        try:
            if not photos:
                msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=cap, parse_mode=ParseMode.HTML)
                m_ids = str(msg.message_id)
            elif len(photos) == 1:
                msg = await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photos[0], caption=cap, parse_mode=ParseMode.HTML)
                m_ids = str(msg.message_id)
            else:
                media = [InputMediaPhoto(photos[0], caption=cap, parse_mode=ParseMode.HTML)]
                for p in photos[1:10]: media.append(InputMediaPhoto(p))
                msgs = await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
                m_ids = ",".join([str(m.message_id) for m in msgs])

            conn = sqlite3.connect(DB_PATH)
            conn.execute('INSERT INTO ads (user_id, msg_ids, details) VALUES (?, ?, ?)', (update.effective_user.id, m_ids, cap))
            conn.commit()
            conn.close()
            await update.message.reply_text("✅ Опубліковано!", reply_markup=ReplyKeyboardMarkup([["➕ Нове оголошення"], ["🗂 Мої оголошення"]], resize_keyboard=True))
        except Exception as e:
            await update.message.reply_text(f"❌ Помилка: {e}")
    return ConversationHandler.END

# --- ЗАПУСК ---
async def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    
    # ПРИНУДИТЕЛЬНАЯ ОЧИСТКА (Выбивает старую копию)
    await app.bot.delete_webhook(drop_pending_updates=True)

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
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_desc)],
            PHOTOS: [MessageHandler(filters.PHOTO, get_photos), CommandHandler('done', done_photos), MessageHandler(filters.Regex("^➡️ Залишити як є$"), done_photos)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            SHOW_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tg)],
            CONFIRM: [MessageHandler(filters.Regex("^(Так|Ні)$"), final_post)],
        },
        fallbacks=[CommandHandler('start', start)]
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv)
    
    # Запуск polling
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    # Health Check в отдельном потоке
    def run_h():
        port = int(os.environ.get("PORT", 8080))
        HTTPServer(('0.0.0.0', port), lambda *args: None).serve_forever()
    threading.Thread(target=run_h, daemon=True).start()
    
    asyncio.run(main())
                                                                                                                                                                      
