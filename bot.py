import os
import sqlite3
import threading
import logging
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

# Етапи діалогу
(MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, TOWN, PRICE, 
 DESCRIPTION, PHOTOS, PHONE, SHOW_CONTACT, CONFIRM) = range(14)

# Клавіатури
MAIN_MENU = [["➕ Нове оголошення"], ["🗂 Мої оголошення"]]
GEARBOX_KEYS = [["Механіка", "Автомат"], ["Робот", "Варіатор"]]
FUEL_KEYS = [["Бензин", "Дизель"], ["Газ/Бензин", "Електро"], ["Гібрид"]]
DRIVE_KEYS = [["Передній", "Задній", "Повний"]]
# Повний список районів Одеської області
DISTRICT_KEYS = [
    ["Одеський", "Березівський"],
    ["Білгород-Дністровський", "Болградський"],
    ["Ізмаїльський", "Подільський"],
    ["Роздільнянський"]
]
YES_NO = [["Так", "Ні"]]
SKIP_KEY = [["➡️ Залишити як є"]]

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
        f"🛣 Привід: {data['drive']}\n"
        f"📍 {data['district']} р-н, {data['town']}\n"
        f"💰 <b>Ціна: {data['price']}$</b>\n\n"
        f"📝 <b>Опис:</b> {data['description']}\n\n"
        f"📞 Тел: <code>{data['phone']}</code>\n"
        f"👤 Telegram: {tg}"
    )

# --- ОБРОБНИКИ ДІАЛОГУ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚗 Вітаю в автоботі Одещини!", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
    return ConversationHandler.END

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['photos'] = []
    await update.message.reply_text("Введіть марку авто (наприклад, Toyota):", reply_markup=ReplyKeyboardRemove())
    return MAKE

async def get_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['make'] = update.message.text
    await update.message.reply_text("Введіть модель:")
    return MODEL

async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['model'] = update.message.text
    await update.message.reply_text("Введіть рік випуску:")
    return YEAR

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['year'] = update.message.text
    await update.message.reply_text("Оберіть КПП:", reply_markup=ReplyKeyboardMarkup(GEARBOX_KEYS, resize_keyboard=True))
    return GEARBOX

async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gearbox'] = update.message.text
    await update.message.reply_text("Оберіть вид палива:", reply_markup=ReplyKeyboardMarkup(FUEL_KEYS, resize_keyboard=True))
    return FUEL

async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fuel'] = update.message.text
    await update.message.reply_text("Оберіть привід:", reply_markup=ReplyKeyboardMarkup(DRIVE_KEYS, resize_keyboard=True))
    return DRIVE

async def get_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['drive'] = update.message.text
    await update.message.reply_text("Оберіть район Одеської області:", reply_markup=ReplyKeyboardMarkup(DISTRICT_KEYS, resize_keyboard=True))
    return DISTRICT

async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['district'] = update.message.text
    await update.message.reply_text("Введіть населений пункт (місто/село):", reply_markup=ReplyKeyboardRemove())
    return TOWN

async def get_town(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['town'] = update.message.text
    await update.message.reply_text("Введіть ціну в $:")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("Введіть опис авто:")
    return DESCRIPTION

async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Надішліть фото (до 10 штук). Коли закінчите, натисніть /done або кнопку нижче:", 
                                   reply_markup=ReplyKeyboardMarkup(SKIP_KEY, resize_keyboard=True))
    return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['photos'].append(update.message.photo[-1].file_id)
    return PHOTOS

async def done_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введіть номер телефону для зв'язку:", reply_markup=ReplyKeyboardRemove())
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("Показувати ваше посилання на Telegram в оголошенні?", reply_markup=ReplyKeyboardMarkup(YES_NO, resize_keyboard=True))
    return SHOW_CONTACT

async def get_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['show_tg'] = update.message.text
    context.user_data['username'] = update.effective_user.username
    summary = generate_summary(context.user_data)
    context.user_data['summary'] = summary
    await update.message.reply_text(f"Ось ваше оголошення:\n\n{summary}\n\nОпублікувати?", reply_markup=ReplyKeyboardMarkup(YES_NO, resize_keyboard=True), parse_mode=ParseMode.HTML)
    return CONFIRM

async def final_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Так":
        photos = context.user_data.get('photos', [])
        caption = context.user_data['summary']
        try:
            if not photos:
                msg = await context.bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode=ParseMode.HTML)
                m_ids = str(msg.message_id)
            elif len(photos) == 1:
                msg = await context.bot.send_photo(chat_id=CHANNEL_ID, photo=photos[0], caption=caption, parse_mode=ParseMode.HTML)
                m_ids = str(msg.message_id)
            else:
                media = [InputMediaPhoto(photos[0], caption=caption, parse_mode=ParseMode.HTML)]
                for p in photos[1:10]: media.append(InputMediaPhoto(p))
                msgs = await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
                m_ids = ",".join([str(m.message_id) for m in msgs])

            conn = sqlite3.connect(DB_PATH)
            conn.execute('INSERT INTO ads (user_id, msg_ids, details) VALUES (?, ?, ?)', (update.effective_user.id, m_ids, caption))
            conn.commit()
            conn.close()
            await update.message.reply_text("✅ Опубліковано успішно!", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
        except Exception as e:
            await update.message.reply_text(f"❌ Помилка при публікації: {e}", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
    else:
        await update.message.reply_text("Публікацію скасовано.", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
    return ConversationHandler.END

# --- HEALTH CHECK SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is live")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# --- ЗАПУСК ---
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

    print("Бот запущений через run_polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
