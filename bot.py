import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    ConversationHandler
)

# --- НАСТРОЙКИ ---
TOKEN = "8076199435:AAExPYs4SXOUA-ohjIoG2Wn3KPVU5XvEiGc"
CHANNEL_ID = "@autochopOdessa"

# Этапы разговора
MAKE, MODEL, YEAR, FUEL, GEARBOX, DRIVE, PRICE, DISTRICT, PHOTOS = range(9)

# Клавиатуры (кнопки)
FUEL_MENU = [["Бензин", "Газ/Бензин"], ["Дизель", "Электро", "Гибрид"]]
GEARBOX_MENU = [["Механика", "Автомат"], ["Типтроник", "Вариатор"]]
DRIVE_MENU = [["Передний", "Задний", "Полный"]]
DISTRICTS_MENU = [
    ["Одесский", "Березовский"],
    ["Белгород-Днестровский", "Болградский"],
    ["Измаильский", "Подольский"],
    ["Раздельнянский"]
]

logging.basicConfig(level=logging.INFO)

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), HealthCheckHandler).serve_forever()

# --- ЛОГИКА БОТА ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 **Добро пожаловать в AutoChop Odessa!**\n\n"
        "Я помогу вам быстро и правильно составить объявление для нашего канала.\n"
        "Подготовьте описание и фото вашего автомобиля.\n\n"
        "🚀 Чтобы начать, нажмите: /new"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['photos'] = []
    await update.message.reply_text("Введите марку авто (например: Mercedes-Benz):", reply_markup=ReplyKeyboardRemove())
    return MAKE

async def get_make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['make'] = update.message.text
    await update.message.reply_text("Введите модель:")
    return MODEL

async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['model'] = update.message.text
    await update.message.reply_text("Введите год выпуска:")
    return YEAR

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['year'] = update.message.text
    reply_markup = ReplyKeyboardMarkup(FUEL_MENU, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите вид топлива:", reply_markup=reply_markup)
    return FUEL

async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fuel'] = update.message.text
    reply_markup = ReplyKeyboardMarkup(GEARBOX_MENU, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите тип КПП:", reply_markup=reply_markup)
    return GEARBOX

async def get_gearbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['gearbox'] = update.message.text
    reply_markup = ReplyKeyboardMarkup(DRIVE_MENU, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите тип привода:", reply_markup=reply_markup)
    return DRIVE

async def get_drive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['drive'] = update.message.text
    await update.message.reply_text("Укажите цену в $:", reply_markup=ReplyKeyboardRemove())
    return PRICE

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    reply_markup = ReplyKeyboardMarkup(DISTRICTS_MENU, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Выберите район области:", reply_markup=reply_markup)
    return DISTRICT

async def get_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['district'] = update.message.text
    await update.message.reply_text("Пришлите до 3-х фото авто. После завершения нажмите /done", reply_markup=ReplyKeyboardRemove())
    return PHOTOS

async def get_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    context.user_data['photos'].append(photo_file.file_id)
    await update.message.reply_text(f"Фото добавлено ({len(context.user_data['photos'])}/3). Еще фото или /done?")
    return PHOTOS

async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    caption = (
        f"🚘 **ПРОДАЖА АВТО**\n\n"
        f"🔹 **Марка:** {data['make']}\n"
        f"🔹 **Модель:** {data['model']}\n"
        f"📅 **Год:** {data['year']}\n"
        f"⛽️ **Топливо:** {data['fuel']}\n"
        f"⚙️ **КПП:** {data['gearbox']}\n"
        f"🎡 **Привод:** {data['drive']}\n"
        f"📍 **Район:** {data['district']}\n"
        f"💰 **Цена:** {data['price']}$\n\n"
        f"👤 **Продавец:** @{update.effective_user.username or 'NoName'}"
    )

    try:
        if data['photos']:
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=data['photos'][0], caption=caption, parse_mode='Markdown')
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode='Markdown')
        await update.message.reply_text("✅ Ваше объявление опубликовано в @autochopOdessa")
    except Exception as e:
        await update.message.reply_text(f"Ошибка публикации: {e}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Размещение отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    threading.Thread(target=run_server, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("new", new_ad)],
        states={
            MAKE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_make)],
            MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_model)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_year)],
            FUEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fuel)],
            GEARBOX: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gearbox)],
            DRIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_drive)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_district)],
            PHOTOS: [MessageHandler(filters.PHOTO, get_photos), CommandHandler("done", finish)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
