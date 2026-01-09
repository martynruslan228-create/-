from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import os

# Токен бота и канал
TOKEN = os.environ.get("BOT_TOKEN")  # добавьте BOT_TOKEN в переменные Render
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # добавьте CHANNEL_ID в переменные Render

# Временное хранение данных пользователей
user_data = {}
# Хранение ID сообщений в канале
ads_data = {}

# Районы Одесской области на украинском
districts = [
    "Білгород-Дністровський", "Ізмаїл", "Котовськ", "Подільськ",
    "Роздільна", "Татарбунари", "Одеський район"
]

# Старт бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    await update.message.reply_text(
        "Привіт! Давайте створимо оголошення про авто.\nЯ буду задавати питання по черзі."
    )
    await ask_brand(update, context)

# Вопросы по шагам
async def ask_brand(update, context):
    await update.message.reply_text("Вкажіть марку авто:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_data:
        await start(update, context)
        return

    data = user_data[user_id]

    if "brand" not in data:
        data["brand"] = text
        await update.message.reply_text("Вкажіть модель авто:")
    elif "model" not in data:
        data["model"] = text
        await update.message.reply_text("Вкажіть рік випуску:")
    elif "year" not in data:
        data["year"] = text
        await update.message.reply_text("Вкажіть ціну в доларах:")
    elif "price" not in data:
        data["price"] = text
        await update.message.reply_text("Надішліть фото авто:")
    elif "photo" not in data:
        if update.message.photo:
            data["photo"] = update.message.photo[-1].file_id
            # Выбираем район
            buttons = [[InlineKeyboardButton(d, callback_data=d)] for d in districts]
            reply_markup = InlineKeyboardMarkup(buttons)
            await update.message.reply_text("Виберіть район:", reply_markup=reply_markup)
        else:
            await update.message.reply_text("Будь ласка, надішліть фото авто:")
    elif "district" not in data:
        # Ждём район через CallbackQuery
        pass
    elif "city" not in data:
        data["city"] = text
        await update.message.reply_text("Напишіть короткий опис авто:")
    elif "description" not in data:
        data["description"] = text
        await publish_ad(update, context)
    else:
        await update.message.reply_text("Оголошення вже зібрано, щоб створити нове - /start")

# Обработка выбора района
async def handle_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = user_data[user_id]
    data["district"] = query.data
    await query.message.reply_text("Вкажіть населений пункт:")

# Публикация объявления в канал
async def publish_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]

    text = f"🚗 Нове оголошення:\n\n" \
           f"Марка: {data['brand']}\n" \
           f"Модель: {data['model']}\n" \
           f"Рік: {data['year']}\n" \
           f"Ціна: {data['price']}$\n" \
           f"Район: {data.get('district','')}\n" \
           f"Населений пункт: {data.get('city','')}\n" \
           f"Опис: {data.get('description','')}"

    if "photo" in data:
        msg = await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=data["photo"],
            caption=text
        )
    else:
        msg = await context.bot.sen
