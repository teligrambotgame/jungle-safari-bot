import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# 🟢 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Play", callback_data="play")],
        [InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌴 Welcome to *Jungle Safari Game*! 🐾\n\nPress the button below to begin your jungle journey!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# 🟢 Button click handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "play":
        await query.edit_message_text("🚀 Game Started! (Coming soon...)")
    elif query.data == "stats":
        await query.edit_message_text("📈 XP: 0 | Level: 1 | Coins: 0")

# 🔵 Main
if __name__ == '__main__':
    TOKEN = os.environ.get("8486321938:AAErK9S_1gmIeGCEY0Flg5VZd4E9Ju3GquU")

    if not TOKEN:
        print("❌ BOT_TOKEN is missing in environment variables!")
        exit()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Jungle Safari Bot is running...")
    app.run_polling()
