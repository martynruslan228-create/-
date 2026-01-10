import logging
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# Налаштування (Токен можна вставити сюди або в налаштування хостингу)
TOKEN = "8076199435:AAG4i6xSDGOULIxGbDSEqW29foW653WiN7g"
CHANNEL_ID = "@autochopOdessa"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

MAKE, MODEL, YEAR, DISTRICT, TOWN, PRICE, DESCRIPTION, PHOTOS, CONTACTS, CONFIRM = range(10)
DISTRICTS = [["Одеський", "Білгород-Дністровський"], ["Болградський", "Ізмаїльський"], ["Подільський", "Роздільнянський"], ["Березівський"]]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(f"👋 Вітаємо, {user.first_name}!\nНатисніть /new для оголошення.")

async def new_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["photos"] = []
    await update.message.reply_text("🚗 Марка авто:", reply_markup=ReplyKeyboardRemove())
    return MAKE

async def make(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["make"] = update.message.text
    await update.message.reply_text("Модель:")
    return MODEL

async def model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["model"] = update.message.text
    await update.message.reply_text("Рік:")
    return YEAR

async def year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["year"] = update.message.text
    markup = ReplyKeyboardMarkup(DISTRICTS, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Район:", reply_markup=markup)
    return DISTRICT

async def district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dist"] = update.message.text
    await update.message.reply_text("Місто/село:")
    return TOWN

async def town(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["town"] = update.message.text
    await update.message.reply_text("Ціна ($):")
    return PRICE

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["price"] = update.message.text
    await update.message.reply_text("Опис:")
    return DESCRIPTION

async def description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["desc"] = update.message.text
    await update.message.reply_text("Надішліть до 10 фото. В кінці натисніть ✅ ГОТОВО.")
    return PHOTOS

async def photos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data["photos"].append(update.message.photo[-1].file_id)
        markup = ReplyKeyboardMarkup([["✅ ГОТОВО"]], resize_keyboard=True)
        await update.message.reply_text(f"📸 Фото додано ({len(context.user_data['photos'])}/10)", reply_markup=markup)
        return PHOTOS
    elif update.message.text == "✅ ГОТОВО":
        if not context.user_data.get("photos"):
            await update.message.reply_text("Додайте фото!")
            return PHOTOS
        await update.message.reply_text("📱 Ваш номер телефону (текстом):", reply_markup=ReplyKeyboardRemove())
        return CONTACTS
    return PHOTOS

async def contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    user = update.message.from_user
    username = f"@{user.username}" if user.username else f"ID: {user.id}"
    d = context.user_data
    caption = (f"🚗 *{d['make']} {d['model']}* ({d['year']})\n📍 {d['dist']} р-н, {d['town']}\n"
               f"💰 Ціна: {d['price']}$\n📝 {d['desc']}\n📞 {phone}\n👤 {username}")
    context.user_data["final_text"] = caption
    await update.message.reply_photo(photo=d["photos"][0], caption=f"Перевірка:\n\n{caption}\n\nОпублікувати? /save", parse_mode=ParseMode.MARKDOWN)
    return CONFIRM

async def save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    try:
        if len(d["photos"]) == 1:
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=d["photos"][0], caption=d["final_text"], parse_mode=ParseMode.MARKDOWN)
        else:
            media = [InputMediaPhoto(d["photos"][0], caption=d["final_text"], parse_mode=ParseMode.MARKDOWN)]
            for p in d["photos"][1:]: media.append(InputMediaPhoto(p))
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        await update.message.reply_text("✅ Опубліковано!")
    except Exception as e:
        await update.message.reply_text(f"Помилка: {e}")
    return ConversationHandler.END

def main():
    # Використовуємо змінні оточення для порту (важливо для Render)
    app = ApplicationBuilder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("new", new_ad)],
        states={
            MAKE: [MessageHandler(filters.TEXT & ~filters.COMMAND, make)],
            MODEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, model)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, year)],
            DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, district)],
            TOWN: [MessageHandler(filters.TEXT & ~filters.COMMAND, town)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            PHOTOS: [MessageHandler(filters.PHOTO | filters.Regex("^✅ ГОТОВО$"), photos_handler)],
            CONTACTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, contacts)],
            CONFIRM: [CommandHandler("save", save)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
