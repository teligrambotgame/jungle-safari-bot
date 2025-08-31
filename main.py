import asyncio import logging import math import os import time from dataclasses import dataclass from datetime import datetime, timezone

import aiosqlite from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update from telegram.constants import ParseMode from telegram.ext import ( Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, )

-------------------------

Config

-------------------------

BOT_TOKEN = os.getenv("8486321938:AAFDrNNueo-I6-VTwtgPs2fokBDsWOXQUqQ")

DB_PATH = os.getenv("DB_PATH", "jungle_safari.db")

Anti-spam: minimum seconds between taps counted

TAP_COOLDOWN = 0.15  # ~6 taps/second MAX_ENERGY = 100 ENERGY_REGEN_PER_MIN = 10  # energy per minute XP_PER_TAP_BASE = 5 COINS_PER_TAP_BASE = 1

JUNGLE_THEMES = [ (1, 10, "Green Jungle Meadows 🌿"), (11, 30, "Deep Dark Forest 🌳"), (31, 50, "River Safari 🐊"), (51, 70, "Rocky Hills 🏔️"), (71, 90, "Haunted Jungle 👻"), (91, 100, "Treasure Island 🏝️"), ]

-------------------------

Data model

-------------------------

@dataclass class Player: user_id: int first_name: str level: int = 1 xp: int = 0 coins: int = 0 energy: int = MAX_ENERGY last_tap_ts: float = 0.0 last_energy_ts: float = time.time()

@property
def theme(self) -> str:
    for lo, hi, name in JUNGLE_THEMES:
        if lo <= self.level <= hi:
            return name
    return JUNGLE_THEMES[-1][2]

def xp_needed_for_next(self) -> int:
    # Progressive curve: level^2 * 20
    return max(20, int((self.level ** 2) * 20))

def regen_energy(self):
    now = time.time()
    minutes = (now - self.last_energy_ts) / 60.0
    if minutes <= 0:
        return
    gained = int(minutes * ENERGY_REGEN_PER_MIN)
    if gained > 0:
        self.energy = min(MAX_ENERGY, self.energy + gained)
        self.last_energy_ts = now

-------------------------

DB helpers

-------------------------

CREATE_SQL = """ CREATE TABLE IF NOT EXISTS players ( user_id INTEGER PRIMARY KEY, first_name TEXT, level INTEGER, xp INTEGER, coins INTEGER, energy INTEGER, last_tap_ts REAL, last_energy_ts REAL ); """

async def init_db(): async with aiosqlite.connect(DB_PATH) as db: await db.execute(CREATE_SQL) await db.commit()

async def get_player(user_id: int, first_name: str) -> Player: async with aiosqlite.connect(DB_PATH) as db: async with db.execute("SELECT user_id, first_name, level, xp, coins, energy, last_tap_ts, last_energy_ts FROM players WHERE user_id=?", (user_id,)) as cur: row = await cur.fetchone() if row: p = Player(*row) p.regen_energy() # Persist any regen changes lazily await save_player(p) return p # New player p = Player(user_id=user_id, first_name=first_name) await save_player(p) return p

async def save_player(p: Player): async with aiosqlite.connect(DB_PATH) as db: await db.execute( "REPLACE INTO players (user_id, first_name, level, xp, coins, energy, last_tap_ts, last_energy_ts) VALUES (?,?,?,?,?,?,?,?)", (p.user_id, p.first_name, p.level, p.xp, p.coins, p.energy, p.last_tap_ts, p.last_energy_ts), ) await db.commit()

async def top_players(limit: int = 10): async with aiosqlite.connect(DB_PATH) as db: async with db.execute( "SELECT first_name, level, xp, coins FROM players ORDER BY level DESC, xp DESC LIMIT ?", (limit,), ) as cur: rows = await cur.fetchall() return rows

-------------------------

UI helpers

-------------------------

def progress_bar(current: int, total: int, width: int = 16) -> str: if total <= 0: total = 1 filled = int(width * min(current, total) / total) return "█" * filled + "░" * (width - filled)

def main_keyboard() -> InlineKeyboardMarkup: return InlineKeyboardMarkup( [ [InlineKeyboardButton("▶️ Play", callback_data="play")], [ InlineKeyboardButton("🎒 Inventory", callback_data="inv"), InlineKeyboardButton("🏆 Leaderboard", callback_data="top"), ], [InlineKeyboardButton("ℹ️ Help", callback_data="help")], ] )

def play_keyboard() -> InlineKeyboardMarkup: return InlineKeyboardMarkup( [ [InlineKeyboardButton("🖐️ Collect", callback_data="collect")], [ InlineKeyboardButton("⬆️ Upgrade", callback_data="upgrade"), InlineKeyboardButton("🏕️ Camp", callback_data="camp"), ], [InlineKeyboardButton("🏠 Home", callback_data="home")], ] )

def format_status(p: Player) -> str: need = p.xp_needed_for_next() bar = progress_bar(p.xp, need) return ( f"<b>Jungle Safari</b> — <i>{p.theme}</i>\n" f"Level: <b>{p.level}</b> | XP: <b>{p.xp}</b> / {need}\n" f"{bar}\n" f"Energy: <b>{p.energy}</b> / {MAX_ENERGY} | Coins: <b>{p.coins}</b>\n" f"Tap <b>Collect</b> to gather jungle shards!" )

-------------------------

Handlers

-------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user p = await get_player(user.id, user.first_name or "Ranger") text = ( f"👋 Welcome, <b>{p.first_name}</b>!\n\n" "Your adventure begins in the <b>Jungle Meadows</b>.\n" "Earn XP by tapping <b>Collect</b>, level up to unlock new zones up to <b>Level 100</b>.\n\n" "Buttons appear <i>below this message</i> — just like game UIs." ) await update.message.reply_text(text, reply_markup=main_keyboard(), parse_mode=ParseMode.HTML)

async def help_cb(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() msg = ( "<b>How to play</b>\n" "• Tap <b>Collect</b> to earn XP and coins.\n" "• Energy regenerates over time.\n" "• Level up to move through zones and reach <b>Treasure Island</b>.\n" "• Use <b>Upgrade</b> to increase tap rewards.\n" "• /top shows the leaderboard." ) await query.edit_message_text(msg, reply_markup=main_keyboard(), parse_mode=ParseMode.HTML)

async def home_cb(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user = query.from_user p = await get_player(user.id, user.first_name or "Ranger") await query.edit_message_text(format_status(p), reply_markup=play_keyboard(), parse_mode=ParseMode.HTML)

async def play_cb(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user = query.from_user p = await get_player(user.id, user.first_name or "Ranger") await query.edit_message_text(format_status(p), reply_markup=play_keyboard(), parse_mode=ParseMode.HTML)

async def inv_cb(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user = query.from_user p = await get_player(user.id, user.first_name or "Ranger") msg = ( f"<b>Inventory</b>\nCoins: <b>{p.coins}</b>\n" "Upgrades: Tap Power, Energy Regen (coming soon)." ) await query.edit_message_text(msg, reply_markup=main_keyboard(), parse_mode=ParseMode.HTML)

async def camp_cb(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer("Resting by the campfire 🔥")

async def collect_cb(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query user = query.from_user p = await get_player(user.id, user.first_name or "Ranger")

# Cooldown check
now = time.time()
if now - p.last_tap_ts < TAP_COOLDOWN:
    await query.answer("Too fast!", show_alert=False)
    return

# Energy check
p.regen_energy()
if p.energy <= 0:
    await save_player(p)
    await query.answer("Out of energy! It refills over time.", show_alert=True)
    return

# Rewards (could scale with level)
tap_power = 1 + (p.level // 10)  # boost per 10 levels
xp_gain = XP_PER_TAP_BASE * tap_power
coin_gain = COINS_PER_TAP_BASE * tap_power

p.energy -= 1
p.xp += xp_gain
p.coins += coin_gain
p.last_tap_ts = now

# Level up
leveled_up = False
while p.xp >= p.xp_needed_for_next() and p.level < 100:
    p.xp -= p.xp_needed_for_next()
    p.level += 1
    leveled_up = True

await save_player(p)

if leveled_up:
    await query.answer(f"Level Up! You are now Level {p.level} 🎉", show_alert=True)
else:
    await query.answer("+XP +Coins", show_alert=False)

await query.edit_message_text(format_status(p), reply_markup=play_keyboard(), parse_mode=ParseMode.HTML)

async def upgrade_cb(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query user = query.from_user p = await get_player(user.id, user.first_name or "Ranger")

# Simple upgrade: spend coins to increase max energy (caps at 150)
cost = 100 * (1 + (p.level // 10))
if p.coins >= cost and MAX_ENERGY > 0:
    p.coins -= cost
    # Soft increase by granting instant energy boost
    p.energy = min(MAX_ENERGY, p.energy + 10)
    await save_player(p)
    await query.answer(f"Upgrade purchased! (+10 energy) Cost: {cost} coins", show_alert=True)
else:
    await query.answer(f"Not enough coins. Need {cost}", show_alert=True)

await query.edit_message_text(format_status(p), reply_markup=play_keyboard(), parse_mode=ParseMode.HTML)

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE): rows = await top_players(10) if not rows: await update.message.reply_text("No players yet. Be the first! /start") return lines = ["<b>🏆 Top Rangers</b>"] for i, (name, lvl, xp, coins) in enumerate(rows, start=1): lines.append(f"{i}. {name} — L{lvl} | XP {xp} | 💰{coins}") await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

async def top_cb(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() rows = await top_players(10) if not rows: await query.edit_message_text("No players yet. Use /start to play.") return lines = ["<b>🏆 Top Rangers</b>"] for i, (name, lvl, xp, coins) in enumerate(rows, start=1): lines.append(f"{i}. {name} — L{lvl} | XP {xp} | 💰{coins}") await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=main_keyboard())

-------------------------

App setup

-------------------------

async def on_startup(app: Application): await init_db() logging.info("DB initialized at %s", DB_PATH)

def build_app() -> Application: app = ApplicationBuilder().token(BOT_TOKEN).concurrent_updates(True).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("top", top_cmd))

app.add_handler(CallbackQueryHandler(play_cb, pattern="^play$"))
app.add_handler(CallbackQueryHandler(collect_cb, pattern="^collect$"))
app.add_handler(CallbackQueryHandler(upgrade_cb, pattern="^upgrade$"))
app.add_handler(CallbackQueryHandler(camp_cb, pattern="^camp$"))
app.add_handler(CallbackQueryHandler(home_cb, pattern="^home$"))
app.add_handler(CallbackQueryHandler(inv_cb, pattern="^inv$"))
app.add_handler(CallbackQueryHandler(top_cb, pattern="^top$"))
app.add_handler(CallbackQueryHandler(help_cb, pattern="^help$"))

app.post_init = on_startup
return app

if name == "main": logging.basicConfig(level=logging.INFO) application = build_app() application.run_polling(close_loop=False)

