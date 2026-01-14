import os
import sqlite3
import threading
import logging
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# 1. ЛОГУВАННЯ
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. КОНФІГУРАЦІЯ
TOKEN = "8076199435:AAHJ8hnLJaKvVl7DIhKiKZBi2aAFCg5ddEE"
CHANNEL_ID = "@autochopOdessa"
DB_PATH = "ads.db"

(MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, TOWN, PRICE, 
 DESCRIPTION, PHOTOS, PHONE, SHOW_CONTACT, CONFIRM) = range(14)

MAIN_MENU = [["➕ Нове оголошення"], ["🗂 Мої оголошення"]]
SKIP_KEY = [["➡️ Залишити як є"]]
YES_NO = [["Так", "Ні"]]
GEARBOX_KEYS = [["Механіка", "Автомат"], ["Робот", "Варіатор"]]
FUEL_KEYS = [["Бензин", "Дизель"], ["Газ/Бензин", "Електро"], ["Гібрид"]]
DRIVE_KEYS = [["Передній", "Задній"], ["Повний"]]
DISTRICTS = [["Одеський", "Березівський"], ["Білгород-Дністровський"], ["Болградський", "Ізмаїльський"], ["Подільський", "Роздільнянський"]]

# 3. БАЗА ДАНИХ
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS ads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, msg_ids TEXT, details TEXT)')
    conn.commit()
    conn.close()

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

# --- ОБРОБНИКИ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚗 Вітаю!", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
    return ConversationHandler.END

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['is_edit'] = False
    context.user_data['photos'] = []
    await update.message.reply_text("Марка авто:", reply_markup=ReplyKeyboardRemove())
    return MAKE

async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ad_id = update.callback_query.data.split('_')[1]
    context.user_data['is_edit'] = True
    context.user_data['old_ad_id'] = ad_id
    context.user_data['photos'] = []
    await update.callback_query.message.reply_text("🔧 Редагування. Нова марка або:", reply_markup=ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True))
    return MAKE

async def step_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, key, next_st, msg, kb=None):
    if update.message.text != "➡️ Залишити як є":
        context.user_data[key] = update.message.text
    markup = kb if kb else (ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True) if context.user_data.get('is_edit') else ReplyKeyboardRemove())
    await update.message.reply_text(msg, reply_markup=markup)
    return next_st

async def get_make(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'make', MODEL, "Модель:")
async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'model', YEAR, "Рік:")
async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    k = GEARBOX_KEYS + (SKIP_KEY if context.user_data.get('is_edit') else [])
    return await step_handler(update, context, 'year', GEARBOX, "КПП:", ReplyKeyboardMarkup(k, resize_keyboard=True))
async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    k = FUEL_KEYS + (SKIP_KEY if context.user_data.get('is_edit') else [])
    return await step_handler(update, context, 'gearbox', FUEL, "Паливо:", ReplyKeyboardMarkup(k, resize_keyboard=True))
async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    k = DRIVE_KEYS + (SKIP_KEY if context.user_data.get('is_edit') else [])
    return await step_handler(update, context, 'fuel', DRIVE, "Привід:", ReplyKeyboardMarkup(k, resize_keyboard=True))
async def get_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    k = DISTRICTS + (SKIP_KEY if context.user_data.get('is_edit') else [])
    return await step_handler(update, context, 'drive', DISTRICT, "Район:", ReplyKeyboardMarkup(k, resize_keyboard=True))
async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'district', TOWN, "Місто:")
async def get_town(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'town', PRICE, "Ціна ($):")
async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE): return await step_handler(update, context, 'price', DESCRIPTION, "Опис:")
async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "➡️ Залишити як є": context.user_data['description'] = update.message.text
    await update.message.reply_text("Надішліть фото та натисніть /done або кнопку нижче:", reply_markup=ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True))
    return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo: context.user_data['photos'].append(update.message.photo[-1].file_id)
    return PHOTOS

async def done_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Телефон:", reply_markup=ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True) if context.user_data.get('is_edit') else None)
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "➡️ Залишити як є": context.user_data['phone'] = update.message.text
    k = YES_NO + (SKIP_KEY if context.user_data.get('is_edit') else [])
    await update.message.reply_text("Показувати Telegram?", reply_markup=ReplyKeyboardMarkup(k, resize_keyboard=True))
    return SHOW_CONTACT

async def get_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text != "➡️ Залишити як є": context.user_data['show_tg'] = update.message.text
    context.user_data['username'] = update.effective_user.username
    text = generate_summary(context.user_data)
    context.user_data['summary'] = text
    await update.message.reply_text(f"Прев'ю:\n\n{text}\n\nОпублікувати?", reply_markup=ReplyKeyboardMarkup(YES_NO, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return CONFIRM

async def del_logic(ad_id, context):
    conn = sqlite3.connect(DB_PATH)
    res = conn.execute('SELECT msg_ids FROM ads WHERE id = ?', (ad_id,)).fetchone()
    if res:
        for m in res[0].split(','):
            try: await context.bot.delete_message(CHANNEL_ID, int(m))
            except: pass
        conn.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
        conn.commit()
    conn.close()

async def final_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Так":
        try:
            if context.user_data.get('is_edit'):
                await del_logic(context.user_data['old_ad_id'], context)
            
            photos = context.user_data.get('photos', [])
            txt = context.user_data['summary']
            
            if not photos:
                msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=txt, parse_mode=ParseMode.HTML)
                m_ids = str(msg.message_id)
            elif len(photos) == 1:
                msg = await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photos[0], caption=txt, parse_mode=ParseMode.HTML)
                m_ids = str(msg.message_id)
            else:
                media = [InputMediaPhoto(photos[0], caption=txt, parse_mode=ParseMode.HTML)]
                for p in photos[1:10]: media.append(InputMediaPhoto(p))
                msgs = await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
                m_ids = ",".join([str(m.message_id) for m in msgs])

            conn = sqlite3.connect(DB_PATH)
            conn.execute('INSERT INTO ads (user_id, msg_ids, details) VALUES (?, ?, ?)', (update.effective_user.id, m_ids, txt))
            conn.commit()
            conn.close()
            await update.message.reply_text("✅ Готово!", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
        except Exception as e:
            await update.message.reply_text(f"❌ Помилка: {e}")
    return ConversationHandler.END

async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute('SELECT id, details FROM ads WHERE user_id = ?', (update.effective_user.id,)).fetchall()
    conn.close()
    if not rows: return await update.message.reply_text("Порожньо.")
    for r_id, txt in rows:
        kb = [[InlineKeyboardButton("📝 Ред", callback_data=f"edt_{r_id}"), InlineKeyboardButton("🗑 Вид", callback_data=f"del_{r_id}")]]
        await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def cb_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await del_logic(update.callback_query.data.split('_')[1], context)
    await update.callback_query.edit_message_text("🗑 Видалено")

# --- HEALTH SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

def main():
    init_db()
    threading.Thread(target=run_health_server, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Нове оголошення$"), new_ad), CallbackQueryHandler(edit_start, pattern="^edt_")],
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
    app.add_handler(MessageHandler(filters.Regex("^🗂 Мої оголошення$"), my_ads))
    app.add_handler(CallbackQueryHandler(cb_del, pattern="^del_"))
    app.add_handler(conv)

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
