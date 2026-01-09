from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os
import uuid

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Состояния разговора
MARCA, MODEL, YEAR, PRICE, PHOTO, DISTRICT, CITY, DESCRIPTION, CONFIRM = range(9)

# Временное хранилище объявлений
ads_storage = {}

# Актуальные районы Одесской области (2020)
districts = [
    "Одеський",
    "Березівський",
    "Білгород-Дністровський",
    "Болградський",
    "Ізмаїльський",
    "Подільський",
    "Раздельнянський"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт! Давай створимо твоє оголошення про авто.\n"
        "Я буду питати по черзі всі дані."
    )
    await update.message.reply_text("1️⃣ Введи марку авто:")
    return MARCA

async def marca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['marca'] = update.message.text
    await update.message.reply_text("2️⃣ Введи модель авто:")
    return MODEL

async def model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['model'] = update.message.text
    await update.message.reply_text("3️⃣ Введи рік випуску авто:")
    return YEAR

async def year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['year'] = update.message.text
    await update.message.reply_text("4️⃣ Введи ціну авто (у доларах):")
    return PRICE

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['price'] = update.message.text
    await update.message.reply_text("5️⃣ Надішли фото авто:")
    return PHOTO

async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['photo'] = update.message.photo[-1].file_id
    # Клавіатура з районами
    keyboard = [[d] for d in districts]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("6️⃣ Вибери район:", reply_markup=reply_markup)
    return DISTRICT

async def district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['district'] = update.message.text
    await update.message.reply_text("7️⃣ Введи населений пункт:", reply_markup=ReplyKeyboardRemove())
    return CITY

async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['city'] = update.message.text
    await update.message.reply_text("8️⃣ Введи короткий опис авто:")
    return DESCRIPTION

async def description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    ad_id = str(uuid.uuid4())[:8]
    context.user_data['ad_id'] = ad_id

    text = (
        f"ID: {ad_id}\n"
        f"Марка: {context.user_data['marca']}\n"
        f"Модель: {context.user_data['model']}\n"
        f"Рік: {context.user_data['year']}\n"
        f"Ціна: {context.user_data['price']}$\n"
        f"Район: {context.user_data['district']}\n"
        f"Населений пункт: {context.user_data['city']}\n"
        f"Опис: {context.user_data['description']}"
    )
    await update.message.reply_photo(photo=context.user_data['photo'], caption=text)
    await update.message.reply_text("✅ Підтверджуєш публікацію в канал? (так/ні)")
    return CONFIRM

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.lower()
    user_id = update.message.from_user.id
    ad_id = context.user_data['ad_id']

    if answer == 'так':
        text = (
            f"📢 Оголошення про авто:\n\n"
            f"ID: {ad_id}\n"
            f"Марка: {context.user_data['marca']}\n"
            f"Модель: {context.user_data['model']}\n"
            f"Рік: {context.user_data['year']}\n"
            f"Ціна: {context.user_data['price']}$\n"
            f"Район: {context.user_data['district']}\n"
            f"Населений пункт: {context.user_data['city']}\n"
            f"Опис: {context.user_data['description']}"
        )
        msg = await context.bot.send_photo(chat_id=CHANNEL_ID, photo=context.user_data['photo'], caption=text)
        if user_id not in ads_storage:
            ads_storage[user_id] = []
        ads_storage[user_id].append({
            'id': ad_id,
            'data': context.user_data.copy(),
            'channel_message_id': msg.message_id
        })
        await update.message.reply_text(f"✅ Оголошення опубліковано! ID: {ad_id}")
    else:
        await update.message.reply_text("❌ Оголошення скасовано.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Створення оголошення скасовано.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Показ всех объявлений пользователя
async def myads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ads_storage or not ads_storage[user_id]:
        await update.message.reply_text("У тебе немає опублікованих оголошень.")
        return
    text = "Твої оголошення:\n\n"
    for ad in ads_storage[user_id]:
        text += f"ID: {ad['id']}, Марка: {ad['data']['marca']}, Модель: {ad['data']['model']}\n"
    await update.message.reply_text(text)

# Удаление объявления
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if len(context.args) == 0:
        await update.message.reply_text("Вкажи ID оголошення після команди /delete <ID>")
        return
    ad_id = context.args[0]
    if user_id not in ads_storage:
        await update.message.reply_text("У тебе немає оголошень з таким ID.")
        return
    for ad in ads_storage[user_id]:
        if ad['id'] == ad_id:
            try:
                await context.bot.delete_message(chat_id=CHANNEL_ID, message_id=ad['channel_message_id'])
            except:
                pass
            ads_storage[user_id].remove(ad)
            await update.message.reply_text(f"Оголошення {ad_id} видалено.")
            return
    await update.message.reply_text("Оголошення з таким ID не знайдено.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MARCA: [MessageHandler(filters.TEXT & ~filters.COMMAND, marca)],
            MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, model)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, year)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price)],
            PHOTO: [MessageHandler(filters.PHOTO, photo)],
            DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, district)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('myads', myads))
    app.add_handler(CommandHandler('delete', delete))

    app.run_polling()

if __name__ == "__main__":
    main()
