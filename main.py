# main.py
# Copy this file exactly into your repo (replace existing main.py)

import os
import time
import logging
import aiosqlite
from flask import Flask, request, send_from_directory, jsonify
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

# ---------- Configuration ----------
BOT_TOKEN = os.getenv("8486321938:AAFDrNNueo-I6-VTwtgPs2fokBDsWOXQUqQ")  # Must be set in Render env
RENDER_HOST = os.getenv("RENDER_HOST")  # e.g. jungle-safari-bot.onrender.com (no https)
DB_PATH = os.getenv("DB_PATH", "jungle_safari.db")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required. Set it in Render settings.")
if not RENDER_HOST:
    raise RuntimeError("RENDER_HOST environment variable is required. Set it to your-render-host.onrender.com")

GAME_PATH = "/game"  # served at https://<RENDER_HOST>/game

# ---------- Flask App ----------
app = Flask(__name__, static_folder="static", static_url_path="/static")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jungle-safari")

# ---------- Simple DB helpers (aiosqlite) ----------
CREATE_SQL = """
CREATE TABLE IF NOT EXISTS players (
  user_id INTEGER PRIMARY KEY,
  first_name TEXT,
  best_score INTEGER DEFAULT 0,
  last_seen REAL
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_SQL)
        await db.commit()

async def upsert_player(user_id: int, first_name: str):
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO players(user_id, first_name, last_seen) VALUES(?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET first_name=excluded.first_name, last_seen=excluded.last_seen",
            (user_id, first_name, now),
        )
        await db.commit()

async def record_score(user_id: int, score: int, first_name: str = "Player"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO players(user_id, first_name, best_score, last_seen) VALUES(?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET best_score=CASE WHEN excluded.best_score>best_score THEN excluded.best_score ELSE best_score END, last_seen=excluded.last_seen",
            (user_id, first_name, int(score), time.time()),
        )
        await db.commit()

async def top_players(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT first_name, best_score FROM players ORDER BY best_score DESC LIMIT ?", (limit,))
        rows = await cur.fetchall()
        await cur.close()
        return rows

# ---------- Telegram Bot helpers ----------
def make_main_keyboard(user_id: int, first_name: str) -> InlineKeyboardMarkup:
    play_url = f"https://{RENDER_HOST}{GAME_PATH}?user_id={user_id}&first_name={first_name}"
    keyboard = [
        [InlineKeyboardButton("▶️ Play Jungle Safari", url=play_url)],
        [InlineKeyboardButton("🏆 Top Players", callback_data="top")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    name = (user.first_name or "Ranger")[:64]
    await upsert_player(uid, name)
    text = (
        f"👋 Hi {name}!\n"
        "Welcome to Jungle Safari Adventure.\n"
        "Tap Play to open the game and collect coins & high scores!"
    )
    await update.message.reply_text(text, reply_markup=make_main_keyboard(uid, name))

async def top_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rows = await top_players(10)
    if not rows:
        await query.edit_message_text("No players yet. Be the first to play!")
        return
    lines = ["🏆 Top Players"]
    for i, (name, best_score) in enumerate(rows, start=1):
        lines.append(f"{i}. {name} — Score: {best_score}")
    await query.edit_message_text("\n".join(lines))

# ---------- Telegram Application ----------
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start_handler))
telegram_app.add_handler(CallbackQueryHandler(top_cb, pattern="^top$"))

async def on_startup(app):
    await init_db()
    logger.info("Database initialized at %s", DB_PATH)

telegram_app.post_init = on_startup

# ---------- Flask routes ----------
@app.route("/")
def index():
    return "Jungle Safari Bot is running."

@app.route(GAME_PATH, methods=["GET"])
def serve_game():
    # serves static/index.html
    return send_from_directory("static", "index.html")

@app.route("/api/score", methods=["POST"])
def api_score():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"ok": False, "error": "invalid json"}), 400
    try:
        user_id = int(data.get("user_id"))
        score = int(data.get("score"))
        first_name = str(data.get("first_name", "Player"))[:64]
    except Exception as e:
        return jsonify({"ok": False, "error": "bad params", "detail": str(e)}), 400

    # schedule async DB writes
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(upsert_player(user_id, first_name))
    loop.create_task(record_score(user_id, score, first_name))
    return jsonify({"ok": True})

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    json_update = request.get_json(force=True)
    update = Update.de_json(json_update, telegram_app.bot)
    telegram_app.update_queue.put(update)
    return "ok", 200

# ---------- run (local dev) ----------
if __name__ == "__main__":
    import asyncio
    async def _run():
        await telegram_app.initialize()
        await telegram_app.start()
        # run Flask dev server for local testing (not used on Render)
        from hypercorn.config import Config
        from hypercorn.asyncio import serve
        cfg = Config()
        cfg.bind = ["0.0.0.0:5000"]
        await serve(app, cfg)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass
