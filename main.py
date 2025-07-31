import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# Game status (in-memory for now)
player_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    player_data[user_id] = {'level': 1, 'coins': 0, 'xp': 0}
    
    await update.message.reply_text(
        f"🌴 Welcome to Jungle Safari, {update.effective_user.first_name}!\n"
        f"⭐ Level: 1   💰 Coins: 0   🔥 XP: 0",
        reply_markup=main_menu()
    )

def main_menu():
    buttons = [
        [InlineKeyboardButton("🎮 Start Adventure", callback_data="start_adventure")],
        [InlineKeyboardButton("🍍 Collect", callback_data="collect"),
         InlineKeyboardButton("🔍 Explore", callback_data="explore"),
         InlineKeyboardButton("🎒 Inventory", callback_data="inventory")],
    ]
    return InlineKeyboardMarkup(buttons)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = player_data.get(user_id, {'level': 1, 'coins': 0, 'xp': 0})

    if query.data == "start_adventure":
        data['xp'] += 10
        response = "🚶‍♂️ You venture into the jungle... +10 XP!"
    elif query.data == "collect":
        data['coins'] += 5
        response = "🍌 You collected jungle fruits! +5 Coins!"
    elif query.data == "explore":
        data['xp'] += 5
        response = "🔍 You explored deep into the trees! +5 XP!"
    elif query.data == "inventory":
        response = (
            f"🎒 Your Inventory:\n"
            f"⭐ Level: {data['level']}\n"
            f"💰 Coins: {data['coins']}\n"
            f"🔥 XP: {data['xp']}"
        )
    else:
        response = "🤔 Unknown action."

    # Level up
    if data['xp'] >= 100:
        data['xp'] -= 100
        data['level'] += 1
        response += f"\n🎉 You leveled up to Level {data['level']}!"

    await query.edit_message_text(
        text=f"{response}\n\n⭐ Level: {data['level']}   💰 Coins: {data['coins']}   🔥 XP: {data['xp']}",
        reply_markup=main_menu()
    )

if __name__ == '__main__':
    import os
    TOKEN = os.environ.get("8486321938:AAHmFKuoHE97vk7cbOLPE6nB1q2nbhZtAwk")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()
