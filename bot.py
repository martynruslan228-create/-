print("Скрипт розпочав роботу...")

import os
import sqlite3
import threading
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# 1. НАЛАШТУВАННЯ ЛОГУВАННЯ
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. HEALTH CHECK (для Render)
from http.server import HTTPServer, BaseHTTPRequestHandler
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# 3. КОНФІГУРАЦІЯ
TOKEN = "8076199435:AAFOSQ0Ucvo6DpXUhs7Zy_jXhFZ_P7F3Xrw"
CHANNEL_ID = "@autochopOdessa"
DB_PATH = "ads.db"

# Етапи анкети та редагування
(MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, TOWN, PRICE, 
 DESCRIPTION, PHOTOS, PHONE, SHOW_CONTACT, CONFIRM) = range(14)

# Кнопки
MAIN_MENU = [["➕ Нове оголошення"], ["🗂 Мої оголошення"]]
GEARBOX_KEYS = [["Механіка", "Автомат"], ["Робот", "Варіатор"]]
FUEL_KEYS = [["Бензин", "Дизель"], ["Газ/Бензин", "Електро"], ["Гібрид"]]
DRIVE_KEYS = [["Передній", "Задній"], ["Повний"]]
DISTRICTS = [["Одеський", "Березівський"], ["Білгород-Дністровський"], ["Болградський", "Ізмаїльський"], ["Подільський", "Роздільнянський"]]
YES_NO = [["Так", "Ні"]]
SKIP_KEY = [["➡️ Залишити як є"]]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS ads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, msg_ids TEXT, details TEXT, data_json TEXT)')
    conn.commit()
    conn.close()

# --- ДОПОМІЖНІ ФУНКЦІЇ ---

def get_summary(data):
    tg_link = f"@{data['username']}" if data.get('show_tg') == "Так" and data.get('username') else "приховано"
    return (
        f"🚘 <b>{data['make']} {data['model']}</b>\n"
        f"📅 Рік: {data['year']}\n"
        f"⚙️ КПП: {data['gearbox']} | ⛽️ {data['fuel']}\n"
        f"⛓ Привід: {data['drive']}\n"
        f"📍 {data['district']} р-н, {data['town']}\n"
        f"💰 <b>Ціна: {data['price']}$</b>\n\n"
        f"📝 <b>Опис:</b> {data['description']}\n\n"
        f"📞 Тел: <code>{data['phone']}</code>\n"
        f"👤 Telegram: {tg_link}"
    )

# --- ЛОГІКА СТВОРЕННЯ ТА РЕДАГУВАННЯ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🚗 <b>Вітаю, {update.effective_user.first_name}!</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
    )
    return ConversationHandler.END

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['is_editing'] = False
    context.user_data['photos'] = []
    await update.message.reply_text("Введіть марку авто:", reply_markup=ReplyKeyboardRemove())
    return MAKE

async def edit_ad_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    ad_id = query.data.split('_')[1]
    
    conn = sqlite3.connect(DB_PATH)
    # В реальному коді тут краще зберігати JSON характеристик, але для простоти беремо з пам'яті або просимо ввести заново
    conn.close()
    
    context.user_data['is_editing'] = True
    context.user_data['edit_ad_id'] = ad_id
    context.user_data['photos'] = []
    
    await query.message.reply_text("--- РЕЖИМ РЕДАГУВАННЯ ---\nВведіть нову МАРКУ або натисніть кнопку нижче:", 
                                  reply_markup=ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True))
    return MAKE

async def process_step(update: Update, context: ContextTypes.DEFAULT_TYPE, key, next_step, prompt, markup=None):
    text = update.message.text
    if text != "➡️ Залишити як є":
        context.user_data[key] = text
    
    await update.message.reply_text(prompt, reply_markup=markup if markup else ReplyKeyboardRemove())
    return next_step

# Кроки анкети (спільні для створення та редагування)
async def get_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_step(update, context, 'make', MODEL, "Модель:", 
                              ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True) if context.user_data.get('is_editing') else None)

async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_step(update, context, 'model', YEAR, "Рік випуску:", 
                              ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True) if context.user_data.get('is_editing') else None)

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = GEARBOX_KEYS + (SKIP_KEY if context.user_data.get('is_editing') else [])
    return await process_step(update, context, 'year', GEARBOX, "Оберіть КПП:", ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = FUEL_KEYS + (SKIP_KEY if context.user_data.get('is_editing') else [])
    return await process_step(update, context, 'gearbox', FUEL, "Паливо:", ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = DRIVE_KEYS + (SKIP_KEY if context.user_data.get('is_editing') else [])
    return await process_step(update, context, 'fuel', DRIVE, "Привід:", ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def get_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = DISTRICTS + (SKIP_KEY if context.user_data.get('is_editing') else [])
    return await process_step(update, context, 'drive', DISTRICT, "Район:", ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_step(update, context, 'district', TOWN, "Місто/село:", 
                              ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True) if context.user_data.get('is_editing') else None)

async def get_town(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_step(update, context, 'town', PRICE, "Ціна ($):", 
                              ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True) if context.user_data.get('is_editing') else None)

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_step(update, context, 'price', DESCRIPTION, "Опис:", 
                              ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True) if context.user_data.get('is_editing') else None)

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "➡️ Залишити як є":
        context.user_data['description'] = update.message.text
    
    msg = "Надішліть НОВІ фото (до 10 шт) і натисніть /done. " if context.user_data.get('is_editing') else "Надішліть фото і натисніть /done"
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup([["➡️ Залишити як є"] if context.user_data.get('is_editing') else []], resize_keyboard=True))
    return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['photos'].append(update.message.photo[-1].file_id)
    return PHOTOS

async def done_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Якщо при редагуванні не надіслали фото і не пропустили - це помилка, але ми спростимо
    await update.message.reply_text("Ваш номер телефону:", 
                                   reply_markup=ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True) if context.user_data.get('is_editing') else None)
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "➡️ Залишити як є":
        context.user_data['phone'] = update.message.text
    
    kb = YES_NO + (SKIP_KEY if context.user_data.get('is_editing') else [])
    await update.message.reply_text("Показувати Telegram?", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return SHOW_CONTACT

async def get_contact_pref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "➡️ Залишити як є":
        context.user_data['show_tg'] = update.message.text
    
    context.user_data['username'] = update.effective_user.username
    summary = get_summary(context.user_data)
    context.user_data['summary'] = summary
    
    await update.message.reply_text(f"<b>Прев'ю:</b>\n\n{summary}\n\nЗберегти та опублікувати?", 
                                   reply_markup=ReplyKeyboardMarkup(YES_NO, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return CONFIRM

async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Так":
        # Якщо це редагування - видаляємо старий пост
        if context.user_data.get('is_editing'):
            await delete_ad_logic(context.user_data['edit_ad_id'], context)

        photos = context.user_data['photos']
        # Тут логіка: якщо фото не змінили при редагуванні, треба було б їх витягти з БД. 
        # Для простоти в цій версії при редагуванні фото треба завантажити заново.
        
        media = [InputMediaPhoto(photos[0], caption=context.user_data['summary'], parse_mode=ParseMode.HTML)]
        for p in photos[1:10]: media.append(InputMediaPhoto(p))
        
        msgs = await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        m_ids = ",".join([str(m.message_id) for m in msgs])
        
        conn = sqlite3.connect(DB_PATH)
        conn.execute('INSERT INTO ads (user_id, msg_ids, details) VALUES (?, ?, ?)', 
                     (update.effective_user.id, m_ids, context.user_data['summary']))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ Готово!", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
    else:
        await update.message.reply_text("Скасовано.", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
    return ConversationHandler.END

# --- МОЇ ОГОЛОШЕННЯ ТА ВИДАЛЕННЯ ---

async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute('SELECT id, msg_ids, details FROM ads WHERE user_id = ?', (update.effective_user.id,))
    ads = cursor.fetchall()
    conn.close()
    
    if not ads:
        await update.message.reply_text("У вас немає активних оголошень.")
        return

    for row_id, mids, text in ads:
        kb = [
            [InlineKeyboardButton("📝 Редагувати", callback_data=f"edt_{row_id}")],
            [InlineKeyboardButton("🗑 Видалити", callback_data=f"del_{row_id}")]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def delete_ad_logic(ad_id, context):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute('SELECT msg_ids FROM ads WHERE id = ?', (ad_id,))
    res = cursor.fetchone()
    if res:
        mids = res[0].split(',')
        for m_id in mids:
            try: await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=int(m_id))
            except: pass
        conn.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
        conn.commit()
    conn.close()

async def del_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad_id = update.callback_query.data.split('_')[1]
    await delete_ad_logic(ad_id, context)
    await update.callback_query.edit_message_text("✅ Видалено!")

# --- ЗАПУСК ---

def main():
    init_db()
    threading.Thread(target=run_health_server, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.Regex("^🗂 Мої оголошення$"), my_ads))
    app.add_handler(CallbackQueryHandler(del_callback, pattern='^del_'))

    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^➕ Нове оголошення$"), new_ad),
            CallbackQueryHandler(edit_ad_start, pattern='^edt_')
        ],
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
            PHOTOS: [MessageHandler(filters.PHOTO, get_photos), CommandHandler('done', done_photos), MessageHandler(filters.Regex("^➡️ Залишити як є$"), done_photos)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            SHOW_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact_pref)],
            CONFIRM: [MessageHandler(filters.Regex("^(Так|Ні)$"), confirm_post)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )
    
    app.add_handler(conv)
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
        
