import os
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Логування
logging.basicConfig(level=logging.INFO)

TOKEN = "8076199435:AAGiwer-2fNz4tZHagOtjuIWVkyx1UFvH6k"

# Проста перевірка
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Базова версія запущена! Зв'язок є. Тепер ми можемо ставити основний код.")

# Веб-сервер для Render (щоб не було помилок)
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Бот працює")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), H)
    server.serve_forever()

if __name__ == "__main__":
    # Запуск веб-сервера в окремому потоці
    threading.Thread(target=run_web, daemon=True).start()
    
    # Запуск бота
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    print("Бот стартував...")
    app.run_polling(drop_pending_updates=True)
