from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

players = {}

def get_status(user_id):
    stats = players.get(user_id, {"level": 1, "xp": 0, "coins": 0})
    return f"🔼 Level: {stats['level']}   💰 Coins: {stats['coins']}   ⭐ XP: {stats['xp']}"

def main_menu():
    buttons = [
        [InlineKeyboardButton("🎮 Start Adventure", callback_data="start_adventure")],
        [InlineKeyboardButton("🍍 Collect", callback_data="collect"),
         InlineKeyboardButton("🔍 Explore", callback_data="explore"),
         InlineKeyboardButton("🎒 Inventory", callback_data="inventory")]
    ]
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    players[user_id] = {"level": 1, "xp": 0, "coins": 0}
    await update.message.reply_text(
        f"{get_status(user_id)}\n\n🌴 Welcome to Jungle Safari! 🐾\nYour wild journey begins here...",
        reply_markup=main_menu()
    )

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in players:
        players[user_id] = {"level": 1, "xp": 0, "coins": 0}

    stats = players[user_id]

    if query.data == "start_adventure":
        stats["xp"] += 10
    elif query.data == "collect":
        stats["coins"] += 5
    elif query.data == "explore":
        stats["xp"] += 5
    elif query.data == "inventory":
        await query.edit_message_text("🎒 Inventory: Empty (coming soon!)", reply_markup=main_menu())
        return

    if stats["xp"] >= 100:
        stats["level"] += 1
        stats["xp"] = 0

    players[user_id] = stats
    await query.edit_message_text(
        f"{get_status(user_id)}\n\n🌴 Welcome to Jungle Safari! 🐾\nYour wild journey begins here...",
        reply_markup=main_menu()
    )

app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_button))
app.run_polling()
