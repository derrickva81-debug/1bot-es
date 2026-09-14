import os
import time
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1234567890"))
CONTACT_LINK = os.environ.get("CONTACT_LINK", "https://t.me/your_contact")
GROUP_LINK = os.environ.get("GROUP_LINK", "https://t.me/your_group")
BACKUP_GROUP_LINK = os.environ.get("BACKUP_GROUP_LINK", "https://t.me/your_backup_group")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://your-app.railway.app")
DB_PATH = "users.db"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
app = Flask(__name__)

LANG = {
    "en": {
        "welcome": (
            "🌟🌟 WE'RE OPEN 24/7 — LIMITED TIME 50% OFF! 🌟🌟\n\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "✨ Services Available:\n"
            "🎫 Concerts / Events / Theme Parks\n"
            "🎡 Ticketmaster / AXS Ticketing\n"
            "🏨 Hotels & 🏩 Airbnb\n"
            "✈️ Flights\n"
            "🍔 Uber Eats / DoorDash / Grubhub\n"
            "🚗 Rides (Uber / Lyft)\n"
            "📟 Bill Payments / Parking / Dine-In\n"
            "🎥 Movie Tickets\n"
            "🚅 Bus & Train Tickets\n"
            "🚢 Cruise Bookings\n"
            "🚙 Car Rentals\n"
            "🧖 Spa Services\n"
            "🍜 Custom Restaurant Orders\n"
            "🥦 Groceries\n"
            "📦 IKEA & Home Orders\n\n"
            "🎢 Theme Parks Covered:\n"
            "Six Flags | Knott's Berry Farm | Disneyland | SeaWorld | Busch Gardens | LEGOLAND | Cedar Point | Hersheypark | Magic Kingdom\n\n"
            "━━━━━━━━━━━━━━━━━━━"
        ),
        "contact": "📞 Contact",
        "group": "👥 Group",
        "backup": "🔰 Backup Group",
        "toggle": "🌐 Español",
        "toggle_lang": "es",
        "fallback": "Use the buttons below to contact us."
    },
    "es": {
        "welcome": (
            "🌟🌟 ESTAMOS ABIERTOS 24/7 — ¡DESCUENTO 50% POR TIEMPO LIMITADO! 🌟🌟\n\n"
            "━━━━━━━━━━━━━━━━━━━\n\n"
            "✨ Servicios Disponibles:\n"
            "🎫 Conciertos / Eventos / Parques Temáticos\n"
            "🎡 Ticketmaster / AXS Ticketing\n"
            "🏨 Hoteles & 🏩 Airbnb\n"
            "✈️ Vuelos\n"
            "🍔 Uber Eats / DoorDash / Grubhub\n"
            "🚗 Viajes (Uber / Lyft)\n"
            "📟 Pagos de Facturas / Estacionamiento / Restaurantes\n"
            "🎥 Boletos de Cine\n"
            "🚅 Boletos de Autobús & Tren\n"
            "🚢 Reservas de Cruceros\n"
            "🚙 Renta de Autos\n"
            "🧖 Servicios de Spa\n"
            "🍜 Pedidos Personalizados de Restaurantes\n"
            "🥦 Comestibles\n"
            "📦 Pedidos de IKEA & Hogar\n\n"
            "🎢 Parques Temáticos Cubiertos:\n"
            "Six Flags | Knott's Berry Farm | Disneyland | SeaWorld | Busch Gardens | LEGOLAND | Cedar Point | Hersheypark | Magic Kingdom\n\n"
            "━━━━━━━━━━━━━━━━━━━"
        ),
        "contact": "📞 Contacto",
        "group": "👥 Grupo",
        "backup": "🔰 Grupo de Respaldo",
        "toggle": "🌐 English",
        "toggle_lang": "en",
        "fallback": "Usa los botones de abajo para contactarnos."
    }
}

user_lang = {}


# ---------- DATABASE ----------
def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        chat_id INTEGER,
        lang TEXT DEFAULT 'en',
        created_at TEXT
    )""")
    conn.commit()
    conn.close()


def save_user(user, chat_id, lang="en"):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO users (user_id, username, first_name, chat_id, lang, created_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
               username = excluded.username,
               first_name = excluded.first_name,
               chat_id = excluded.chat_id,
               lang = excluded.lang""",
        (user.id, user.username, user.first_name, chat_id, lang, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def update_lang(user_id, lang):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()


def get_users():
    conn = get_conn()
    rows = conn.execute("SELECT user_id, username, first_name, chat_id, lang, created_at FROM users").fetchall()
    conn.close()
    return rows


# ---------- UI ----------
def build_menu_buttons(lang="en", user_id=None):
    t = LANG[lang]
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(t["contact"], url=CONTACT_LINK),
        InlineKeyboardButton(t["group"], url=GROUP_LINK),
        InlineKeyboardButton(t["backup"], url=BACKUP_GROUP_LINK)
    )
    if user_id is not None and user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("📢 Broadcast", callback_data="bcast"))
    markup.add(InlineKeyboardButton(t["toggle"], callback_data="lang_" + t["toggle_lang"]))
    return markup


# ---------- COMMANDS ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    lang = user_lang.get(message.from_user.id, "en")
    save_user(message.from_user, message.chat.id, lang)
    bot.send_message(message.chat.id, LANG[lang]["welcome"], reply_markup=build_menu_buttons(lang, message.from_user.id))


@bot.message_handler(commands=['stats'])
def stats_command(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ You are not authorized to use this command.")
        return
    bot.reply_to(message, f"📊 *Total users:* {len(get_users())}")


# ---------- CALLBACKS ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def language_handler(call):
    lang = call.data[5:]
    user_lang[call.from_user.id] = lang
    update_lang(call.from_user.id, lang)
    bot.edit_message_text(
        LANG[lang]["welcome"],
        call.message.chat.id,
        call.message.message_id,
        reply_markup=build_menu_buttons(lang, call.from_user.id)
    )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "bcast")
def broadcast_callback(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Only admin can broadcast.")
        return
    msg = bot.send_message(call.message.chat.id, "📢 *Broadcast:* enter the message to send to all users:")
    bot.register_next_step_handler(msg, send_broadcast)
    bot.answer_callback_query(call.id)


def send_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text
    success = 0
    fail = 0
    for user_id, username, first_name, chat_id, lang, created_at in get_users():
        try:
            bot.send_message(chat_id, f"📢 *Broadcast:*\n\n{text}", parse_mode=None)
            success += 1
        except Exception:
            fail += 1
    bot.reply_to(message, f"✅ Broadcast sent to {success} users.\n❌ Failed: {fail}")


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    bot.answer_callback_query(call.id)


# ---------- DEFAULT HANDLER ----------
@bot.message_handler(func=lambda message: True)
def default_handler(message):
    lang = user_lang.get(message.from_user.id, "en")
    bot.reply_to(message, LANG[lang]["fallback"], reply_markup=build_menu_buttons(lang, message.from_user.id))


# ---------- FLASK WEBHOOK ----------
@app.route('/')
def home():
    return "Bot is running!"


@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data(as_text=True)
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return jsonify({"status": "ok"}), 200


def set_webhook():
    time.sleep(1)
    bot.remove_webhook()
    full_url = f"{WEBHOOK_URL.rstrip('/')}/webhook"
    bot.set_webhook(url=full_url)
    print(f"Webhook set to {full_url}")


if __name__ == '__main__':
    init_db()
    if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_STATIC_URL'):
        set_webhook()
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port)
    else:
        bot.remove_webhook()
        print("Starting polling...")
        bot.infinity_polling()