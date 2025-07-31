import telebot
import os

TOKEN = os.getenv("8486321938:AAGvAj1D6UBbJLkrxEMh29VNAriMMennGec")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🌴 Welcome to Jungle Safari Bot! Let's begin your adventure!")

bot.polling()
