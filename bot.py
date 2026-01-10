import os
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 1. НАЛАШТУВАННЯ ЛОГІВ (щоб ми бачили помилки в Render)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 2. Твій ТОКЕН (переконайся, що він у лапках)
TOKEN = "8076199435:AAExPYs4SXOUA-ohjIoG2Wn3KPVU5XvEiGc"

# 3. ФЕЙКОВИЙ СЕРВЕР ДЛЯ RENDER (Health Check)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    httpd = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Health check server started on port {port}")
    httpd.serve_forever()

# 4. ОБРОБНИКИ КОМАНД
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Команда /start отримана!") # Це ми побачимо в логах
    await update.message.reply_text(
        "Привіт! Бот успішно запущений на Render. 🎉\n"
        "Використовуй /new, щоб створити оголошення."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Тут будуть інструкції для роботи з ботом.")

# 5. ГОЛОВНА ФУНКЦІЯ ЗАПУСКУ
def main():
    # Запускаємо веб-сервер у фоновому потоці
    threading.Thread(target=run_health_check_server, daemon=True).start()

    # Створюємо додаток бота
    app = ApplicationBuilder().token(TOKEN).build()

    # Додаємо команди
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    print("=== БОТ ОФІЦІЙНО ЗАПУЩЕНИЙ ===")
    
    # Запуск бота (polling)
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
