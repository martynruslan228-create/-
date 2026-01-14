import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = "8076199435:AAGiwer-2fNz4tZHagOtjuIWVkyx1UFvH6k"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 ЕСТЬ КОНТАКТ! Система чиста, бот работает.")

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), H).serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    
    # Создаем приложение
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    # ЗАПУСК С ПОЛНОЙ ОЧИСТКОЙ (это уберет ошибку Conflict)
    print("Очистка очереди и запуск...")
    app.run_polling(drop_pending_updates=True, close_loop=False)
    
