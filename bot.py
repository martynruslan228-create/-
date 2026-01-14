import os, sqlite3, threading, logging, asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO)

TOKEN = "8076199435:AAEjUFAdiIZWRpBTUN531R4eRw-GAuUUrac"
CHANNEL_ID = "@autochopOdessa"
DB_PATH = "ads.db"

# Стейты - ВСЕ СКОБКИ ПРОВЕРЕНЫ
(MAKE, MODEL, YEAR, GEARBOX, FUEL, DRIVE, DISTRICT, TOWN, PRICE, 
 DESCRIPTION, PHOTOS, PHONE, SHOW_CONTACT, CONFIRM) = range(14)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS ads (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, details TEXT)')
    conn.commit()
    conn.close()

def generate_summary(data):
    tg = f"@{data['username']}" if data.get('show_tg') == "Так" and data.get('username') else "скрыт"
    return (f"🚘 <b>{data['make']} {data['model']}</b>\n📅 Год: {data['year']}\n"
            f"⚙️ КПП: {data['gearbox']} | ⛽️ {data['fuel']}\n🛣 Привод: {data['drive']}\n"
            f"📍 {data['district']} р-н, {data['town']}\n💰 <b>Цена: {data['price']}$</b>\n\n"
            f"📝 <b>Описание:</b> {data['description']}\n\n📞 Тел: <code>{data['phone']}</code>\n👤 TG: {tg}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚗 Бот работает!", 
        reply_markup=ReplyKeyboardMarkup([["➕ Новое объявление"], ["🗂 Мои объявления"]], resize_keyboard=True))
    return ConversationHandler.END

async def my_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute('SELECT id, details FROM ads WHERE user_id = ? ORDER BY id DESC LIMIT 5', (user_id,))
    rows = cursor.fetchall(); conn.close()
    if not rows: await update.message.reply_text("Объявлений нет.")
    else:
        for r in rows:
            kb = [[InlineKeyboardButton("🗑 Удалить", callback_data=f"del_{r[0]}")]]
            await update.message.reply_text(r[1], parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; ad_id = query.data.split("_")[1]
    conn = sqlite3.connect(DB_PATH); conn.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
    conn.commit(); conn.close(); await query.answer(); await query.edit_message_text("🗑 Удалено.")

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear(); context.user_data['photos'] = []
    await update.message.reply_text("Марка:", reply_markup=ReplyKeyboardRemove()); return MAKE

async def get_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['make'] = update.message.text; await update.message.reply_text("Модель:"); return MODEL

async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['model'] = update.message.text; await update.message.reply_text("Год:"); return YEAR

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['year'] = update.message.text
    await update.message.reply_text("КПП:", reply_markup=ReplyKeyboardMarkup([["Автомат", "Механика"]], resize_keyboard=True)); return GEARBOX

async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gearbox'] = update.message.text
    await update.message.reply_text("Топливо:", reply_markup=ReplyKeyboardMarkup([["Бензин", "Дизель", "Газ"]], resize_keyboard=True)); return FUEL

async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fuel'] = update.message.text
    await update.message.reply_text("Привод:", reply_markup=ReplyKeyboardMarkup([["Передний", "Полный"]], resize_keyboard=True)); return DRIVE

async def get_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['drive'] = update.message.text; await update.message.reply_text("Район:"); return DISTRICT

async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['district'] = update.message.text; await update.message.reply_text("Город:"); return TOWN

async def get_town(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['town'] = update.message.text; await update.message.reply_text("Цена ($):"); return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text; await update.message.reply_text("Описание:"); return DESCRIPTION

async def get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Фото (скинь и нажми /done):", 
                                   reply_markup=ReplyKeyboardMarkup([["➡️ Без фото"]], resize_keyboard=True)); return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo: context.user_data['photos'].append(update.message.photo[-1].file_id)
    return PHOTOS

async def done_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Телефон:", reply_markup=ReplyKeyboardRemove()); return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("Показать TG?", reply_markup=ReplyKeyboardMarkup([["Так", "Ні"]], resize_keyboard=True)); return SHOW_CONTACT

async def get_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['show_tg'] = update.message.text; context.user_data['username'] = update.effective_user.username
    res = generate_summary(context.user_data); context.user_data['summary'] = res
    await update.message.reply_text(f"{res}\n\nОпубликовать?", reply_markup=ReplyKeyboardMarkup([["Так", "Ні"]], resize_keyboard=True), parse_mode=ParseMode.HTML); return CONFIRM

async def final_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Так":
        ps = context.user_data.get('photos', []); cap = context.user_data['summary']
        if not ps: await context.bot.send_message(CHANNEL_ID, cap, parse_mode=ParseMode.HTML)
        else:
            media = [InputMediaPhoto(ps[0], caption=cap, parse_mode=ParseMode.HTML)]
            for p in ps[1:10]: media.append(InputMediaPhoto(p))
            await context.bot.send_media_group(CHANNEL_ID, media)
        conn = sqlite3.connect(DB_PATH); conn.execute('INSERT INTO ads (user_id, details) VALUES (?, ?)', (update.effective_user.id, cap))
        conn.commit(); conn.close()
        await update.message.reply_text("✅ Готово!", reply_markup=ReplyKeyboardMarkup([["➕ Новое объявление"]], resize_keyboard=True))
    return ConversationHandler.END

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
def run(): HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), H).serve_forever()

async def main():
    init_db(); threading.Thread(target=run, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Новое объявление$"), new_ad)],
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
            PHOTOS: [MessageHandler(filters.PHOTO, get_photos), CommandHandler('done', done_photos), MessageHandler(filters.Regex("^➡️ Без фото$"), done_photos)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            SHOW_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tg)],
            CONFIRM: [MessageHandler(filters.Regex("^(Так|Ні)$"), final_post)],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.Regex("^🗂 Мої оголошення$"), my_ads))
    app.add_handler(CallbackQueryHandler(delete_callback, pattern="^del_"))
    app.add_handler(conv)
    await app.initialize()
    await app.bot.delete_webhook(drop_pending_updates=True) 
    await app.updater.start_polling(drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
