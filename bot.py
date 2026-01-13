import os
import sqlite3
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

# --- 1. СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- 2. НАСТРОЙКИ ---
TOKEN = "8076199435:AAExPYs4SXOUA-ohjIoG2Wn3KPVU5XvEiGc"
CHANNEL_ID = "@autochopOdessa"
DB_PATH = "/tmp/ads.db"

# Этапы диалога
MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, TOWN, PRICE, DESCRIPTION, PHOTOS, SHOW_CONTACT, CONFIRM = range(13)

# Клавиатуры (Главное меню теперь всегда доступно)
MAIN_MENU = [["➕ Нове оголошення"], ["🗂 Мої оголошення"]]
GEARBOX_KEYS = [["Механіка", "Автомат"], ["Робот", "Варіатор"]]
FUEL_KEYS = [["Бензин", "Дизель"], ["Газ/Бензин", "Електро"], ["Гібрид"]]
DRIVE_KEYS = [["Передній", "Задній"], ["Повний"]]
DISTRICTS = [["Одеський", "Березівський"], ["Білгород-Дністровський"], ["Болградський", "Ізмаїльський"], ["Подільський", "Роздільнянський"]]
YES_NO = [["Так", "Ні"]]

# --- 3. БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS ads (user_id INTEGER, msg_ids TEXT, details TEXT)')
    conn.commit()
    conn.close()

# --- 4. ЛОГИКА ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Принудительно отправляем кнопки меню
    await update.message.reply_text(
        f"🚗 <b>Вітаю, {update.effective_user.first_name}!</b>\n\nВикористовуйте кнопки нижче для керування ботом:",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True, persistent=True)
    )
    return ConversationHandler.END

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['photos'] = []
    # Убираем меню на время заполнения анкеты
    await update.message.reply_text("Введіть марку авто (напр. Honda):", reply_markup=ReplyKeyboardRemove())
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
    await update.message.reply_text("Оберіть КПП:", reply_markup=ReplyKeyboardMarkup(GEARBOX_KEYS, one_time_keyboard=True, resize_keyboard=True))
    return GEARBOX

async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gearbox'] = update.message.text
    await update.message.reply_text("Тип палива:", reply_markup=ReplyKeyboardMarkup(FUEL_KEYS, one_time_keyboard=True, resize_keyboard=True))
    return FUEL

async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fuel'] = update.message.text
    await update.message.reply_text("Привід:", reply_markup=ReplyKeyboardMarkup(DRIVE_KEYS, one_time_keyboard=True, resize_keyboard=True))
    return DRIVE

async def get_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['drive'] = update.message.text
    await update.message.reply_text("Оберіть район:", reply_markup=ReplyKeyboardMarkup(DISTRICTS, one_time_keyboard=True, resize_keyboard=True))
    return DISTRICT

async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['district'] = update.message.text
    await update.message.reply_text("Напишіть місто/село (вручну):", reply_markup=ReplyKeyboardRemove())
    return TOWN

async def get_town(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['town'] = update.message.text
    await update.message.reply_text("Введіть ціну ($):")
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("Додайте опис авто:")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Надішліть фото. Коли закінчите, натисніть /done")
    return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['photos'].append(update.message.photo[-1].file_id)
    return PHOTOS

async def done_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('photos'):
        await update.message.reply_text("Надішліть хоча б одне фото!")
        return PHOTOS
    await update.message.reply_text("Показувати посилання на ваш профіль?", 
                                   reply_markup=ReplyKeyboardMarkup(YES_NO, one_time_keyboard=True, resize_keyboard=True))
    return SHOW_CONTACT

async def get_contact_pref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if update.message.text == "Так":
        context.user_data['contact'] = f"@{u.username}" if u.username else "username приховано в налаштуваннях ТГ"
    else:
        context.user_data['contact'] = "приховано"
    
    summary = (
        f"🚘 <b>{context.user_data['make']} {context.user_data['model']}</b>\n"
        f"📅 Рік: {context.user_data['year']}\n"
        f"⚙️ КПП: {context.user_data['gearbox']} | ⛽️ {context.user_data['fuel']}\n"
        f"📍 {context.user_data['district']} р-н, {context.user_data['town']}\n"
        f"💰 <b>Ціна: {context.user_data['price']}$</b>\n\n"
        f"📝 <b>Опис:</b> {context.user_data['description']}\n"
        f"👤 Контакт: {context.user_data['contact']}"
    )
    context.user_data['summary'] = summary
    await update.message.reply_text(f"<b>Перевірка:</b>\n\n{summary}\n\nОпублікувати?", 
                                   reply_markup=ReplyKeyboardMarkup(YES_NO, one_time_keyboard=True, resize_keyboard=True),
                                   parse_mode=ParseMode.HTML)
    return CONFIRM

async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Так":
        photos = context.user_data['photos']
        media = [InputMediaPhoto(photos[0], caption=context.user_data['summary'], parse_mode=ParseMode.HTML)]
        for p in photos[1:10]: media.append(InputMediaPhoto(p))
        
        msgs = await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        m_ids = ",".join([str(m.message_id) for m in msgs])
        
        conn = sqlite3.connect(DB_PATH)
        conn.execute('INSERT INTO ads VALUES (?, ?, ?)', (update.effective_user.id, m_ids, context.user_data['summary']))
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ Опубліковано!", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
    else:
        await update.message.reply_text("Скасовано.", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
    return ConversationHandler.END

async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute('SELECT msg_ids, details FROM ads WHERE user_id = ?', (update.effective_user.id,))
    ads = cursor.fetchall()
    conn.close()
    if not ads:
        await update.message.reply_text("У вас немає активних оголошень.")
        return
    for mids, text in ads:
        kb = [[InlineKeyboardButton("🗑 Видалити", callback_data=f"del_{mids}")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def del_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mids = update.callback_query.data.split('_')[1].split(',')
    try:
        for m_id in mids: await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=int(m_id))
        conn = sqlite3.connect(DB_PATH)
        conn.execute('DELETE FROM ads WHERE msg_ids = ?', (",".join(mids),))
        conn.commit()
        conn.close()
        await update.callback_query.edit_message_text("✅ Видалено!")
    except:
        await update.callback_query.answer("Помилка видалення")

def main():
    init_db()
    threading.Thread(target=run_health_server, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[
            # Теперь реагирует и на команду, и на кнопку
            CommandHandler('new', new_ad),
            MessageHandler(filters.Regex("^➕ Нове оголошення$"), new_ad)
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
            PHOTOS: [MessageHandler(filters.PHOTO, get_photos), CommandHandler('done', done_photos)],
            SHOW_CONTACT: [MessageHandler(filters.Regex("^(Так|Ні)$"), get_contact_pref)],
            CONFIRM: [MessageHandler(filters.Regex("^(Так|Ні)$"), confirm_post)],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    app.add_handler(CommandHandler('start', start))
    # Обработка кнопки "Мои объявления" вне диалога
    app.add_handler(MessageHandler(filters.Regex("^🗂 Мої оголошення$"), my_ads))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(del_callback, pattern='^del_'))
    
    app.run_polling()

if __name__ == "__main__":
    main()
    
