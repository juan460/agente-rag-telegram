from rag import ask
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
import os
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def start(update, context):
    await update.message.reply_text(
        "👋 ¡Hola! Soy tu asistente inteligente de los Planes de gobiernos de segunda vuelta 2026-2030.\n\n"
        "📄 Tengo acceso a los siguientes documentos:\n"
        "- Plan de Gobierno Cepeda 2026-2030\n"
        "- Propuestas del Tigre\n\n"
        "💬 Hazme cualquier pregunta sobre estos documentos."
    )
async def handle_message(update, context):
    query = update.message.text
    await update.message.reply_text("⏳ Consultando los planes de gobierno...")
    response = ask(query)
    await update.message.reply_text(response)

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"🤖 Token: {TOKEN}")
    print(f"🤖 Webhook URL: {WEBHOOK_URL}")
    application.run_webhook(
        listen="0.0.0.0",
        port=8444,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
    )

if __name__ == "__main__":
    main()