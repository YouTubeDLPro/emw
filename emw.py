import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import re
from flask import Flask
import threading
import signal
import sys
import os

# Load ADMIN_ID from Render's environment variable
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Default to 0 if not set

# Load TOKEN from environment variable
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("Error: TOKEN is not defined")
    sys.exit(1)
    
CHANNEL_ID = '@easymatchwin'
CHANNEL_URL = "https://t.me/easymatchwin"

# Flask application for health check
app = Flask(__name__)

@app.route('/')
def home():
    return 'Easy Match Win - Admin Bot is Running Smoothly!'

@app.route('/health')
def health_check():
    return "Server is up and running!", 200

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Define steps for collecting user input
steps = [
    ("date_time", "📅 Please enter the match date and time (e.g., 03-04-2025 15:30:45):"),
    ("team_a", "🏟️ Enter Team A’s name:"),
    ("team_b", "🏟️ Enter Team B’s name:"),
    ("odds", "📈 Provide the odds (e.g., 2.5):"),
    ("score", "🔢 Enter the predicted score (e.g., 2-1):"),
    ("link", "🔗 Share the match link (must start with http:// or https://):"),
    ("image", "📸 Upload the match image:")
]

# Temporary storage for user session data
user_data = {}

# Validation functions
def validate_date(date_str):
    return re.match(r'^(0[1-9]|[12]\d|3[01])-(0[1-9]|1[0-2])-(\d{4}) ([01]\d|2[0-3]):([0-5]\d):([0-5]\d)$', date_str)

def validate_odds(odds_str):
    return re.match(r'\d+(\.\d+)?$', odds_str)

def validate_score(score_str):
    return re.match(r'\d+-\d+', score_str)

def validate_url(url_str):
    return re.match(r'https?://\S+', url_str)

# Flask setup
flask_thread = None
running = True

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# Telegram bot handlers
async def start_command(update: Update, context):
    if not update.message:
        return
    user = update.message.from_user
    user_id = user.id
    if user_id not in ADMIN_ID:
        username = user.username or user.first_name
        message = (
            f"👋 *Welcome, {username}, to Easy Match Win!* 👋\n\n"
            "🔥 *The #1 Source for GUARANTEED Betting Wins!* 🔥\n"
            "- Insider tips from top experts\n"
            "- Proven strategies for massive payouts\n"
            "- Exclusive signals you won’t find anywhere else\n\n"
            "💰 *Join our elite community NOW* and start winning BIG!\n"
            "👇 Tap below to unlock the action! 👇"
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Join the Winning Team!", url=CHANNEL_URL)]])
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')
        return

    # Admin welcome
    logging.info(f"Admin {user_id} initiated the bot with /start.")
    welcome_message = (
        "🎉 Welcome to the Easy Match Win Admin Bot! 🎉\n\n"
        "Ready to post winning betting signals? Use /betting_signal to get started. "
        "Ensure all details are spot-on before posting!"
    )
    await update.message.reply_text(welcome_message)

async def betting_signal(update: Update, context):
    if not update.message:
        return
    user = update.message.from_user
    user_id = user.id
    if user_id not in ADMIN_ID:
        username = user.username or user.first_name
        message = (
            f"👋 *Hey {username}, Ready to Win Big?* 👋\n\n"
            "🎯 *Easy Match Win* delivers unbeatable betting signals!\n"
            "- Insider secrets for 100% success\n"
            "- Expert predictions that CASH IN\n"
            "- Join the pros and stack your profits!\n\n"
            "🔥 *Join our channel now* for exclusive access!"
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Join the Winning Team!", url=CHANNEL_URL)]])
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')
        return

    logging.info(f"Admin {user_id} began the betting signal process.")
    user_data[user_id] = {"step": 0, "data": {}, "editing": False}
    await update.message.reply_text(steps[0][1])

async def cancel(update: Update, context):
    if not update.message:
        return
    user_id = update.message.from_user.id
    if user_id in user_data:
        logging.info(f"Admin {user_id} cancelled the session.")
        del user_data[user_id]
        await update.message.reply_text("✅ Session cancelled. Use /betting_signal to start over.")
    else:
        await update.message.reply_text("ℹ️ No active session found. Begin with /betting_signal.")

async def handle_text(update: Update, context):
    if not update.message:
        return
    user_id = update.message.from_user.id
    if user_id not in user_data or "step" not in user_data[user_id]:
        await update.message.reply_text("ℹ️ Please begin with /betting_signal.")
        return

    current_step = user_data[user_id]["step"]
    step_key, _ = steps[current_step]

    if step_key == "image":
        await update.message.reply_text("📸 Please upload an image instead of text for this step.")
        return

    text = update.message.text.strip()

    if step_key == "date_time" and not validate_date(text):
        await update.message.reply_text("❌ Invalid format. Use DD-MM-YYYY HH:MM:SS (e.g., 03-04-2025 15:30:45).")
        return
    elif step_key == "odds" and not validate_odds(text):
        await update.message.reply_text("❌ Invalid odds. Enter a number like 2.5.")
        return
    elif step_key == "score" and not validate_score(text):
        await update.message.reply_text("❌ Invalid score. Use X-Y format (e.g., 2-1).")
        return
    elif step_key == "link" and not validate_url(text):
        await update.message.reply_text("❌ Invalid URL. Ensure it starts with http:// or https://.")
        return

    user_data[user_id]["data"][step_key] = text

    if user_data[user_id]["editing"]:
        user_data[user_id]["editing"] = False
        await send_summary(user_id, context)
    elif current_step < len(steps) - 1:
        user_data[user_id]["step"] += 1
        next_step_key, next_prompt = steps[user_data[user_id]["step"]]
        await update.message.reply_text(next_prompt)
    else:
        await send_summary(user_id, context)

async def handle_photo(update: Update, context):
    if not update.message or not update.message.photo:
        return
    user_id = update.message.from_user.id
    if user_id not in user_data or "step" not in user_data[user_id]:
        await update.message.reply_text("ℹ️ Please start with /betting_signal.")
        return

    current_step = user_data[user_id]["step"]
    step_key, _ = steps[current_step]

    if step_key != "image":
        await update.message.reply_text("❌ Unexpected image. Please provide text for this step.")
        return

    user_data[user_id]["data"][step_key] = update.message.photo[-1].file_id
    await send_summary(user_id, context)

async def send_summary(user_id, context):
    data = user_data[user_id]["data"]
    required_fields = {step[0] for step in steps}
    if not all(field in data for field in required_fields):
        await context.bot.send_message(chat_id=user_id, text="⚠️ Missing details. Please complete all steps.")
        return

    summary = f"""
📋 *Match Details Preview:*

📅 *Date & Time:* {data['date_time']}
🏟️ *Teams:* {data['team_a']} vs {data['team_b']}
📈 *Odds:* {data['odds']}
🔢 *Predicted Score:* {data['score']}
🔗 *Match Link:* {data['link']}

✅ Look good? Confirm or edit below.
    """
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="confirm"),
         InlineKeyboardButton("✏️ Edit", callback_data="edit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text=summary, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_callback(update: Update, context):
    query = update.callback_query
    if not query:
        return
    user_id = query.from_user.id
    if query.data == "confirm":
        logging.info(f"Admin {user_id} confirmed the details.")
        await send_betting_signal(user_id, context)
        await query.answer("🎉 Signal posted successfully!")
    elif query.data == "edit":
        logging.info(f"Admin {user_id} chose to edit details.")
        await show_edit_options(user_id, context)
        await query.answer("✏️ Pick a field to update.")
    elif query.data == "back_to_summary":
        logging.info(f"Admin {user_id} returned to summary.")
        await send_summary(user_id, context)
        await query.answer("📋 Back to preview.")
    else:
        try:
            step_index = int(query.data)
            field = steps[step_index][0]
            logging.info(f"Admin {user_id} editing field: {field}.")
            user_data[user_id]["step"] = step_index
            user_data[user_id]["editing"] = True
            await context.bot.send_message(chat_id=user_id, text=steps[step_index][1])
            await query.answer()
        except ValueError:
            pass

async def show_edit_options(user_id, context):
    keyboard = [
        [InlineKeyboardButton("📅 Date & Time", callback_data="0"),
         InlineKeyboardButton("🏟️ Team A", callback_data="1")],
        [InlineKeyboardButton("🏟️ Team B", callback_data="2"),
         InlineKeyboardButton("📈 Odds", callback_data="3")],
        [InlineKeyboardButton("🔢 Score", callback_data="4"),
         InlineKeyboardButton("🔗 Link", callback_data="5")],
        [InlineKeyboardButton("📸 Image", callback_data="6")],
        [InlineKeyboardButton("📋 Back to Preview", callback_data="back_to_summary")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text="✏️ Which field would you like to edit?", reply_markup=reply_markup)

async def send_betting_signal(user_id, context):
    data = user_data[user_id]["data"]
    message = f"""
⚽ *EASY MATCH WIN – INSIDER BETTING SIGNAL* ⚽

📅 *Date & Time:* {data['date_time']}
🏟️ *Match:* {data['team_a']} vs {data['team_b']}
📈 *Odds:* {data['odds']}
🔢 *Prediction:* {data['score']}
🔗 *Bet Now:* {data['link']}

🔥 *INSIDER CONFIRMATION:* Straight from our top sources! 🔥
🏆 *100% MATCH WIN GUARANTEED* – Lock in your profits NOW! 🏆

📢 Powered by Easy Match Win Admin Bot
    """
    await context.bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=data['image'],
        caption=message,
        parse_mode='Markdown'
    )
    logging.info(f"Admin {user_id} posted a betting signal successfully.")
    del user_data[user_id]

async def error_handler(update: object, context):
    logging.error(f"Error occurred: {context.error}")
    if update and hasattr(update, "message") and update.message:
        await update.message.reply_text("⚠️ Oops! Something went wrong. Please try again.")

def signal_handler(sig, frame):
    global running
    running = False
    print("\nShutting down gracefully...")
    sys.exit(0)

def main():
    global flask_thread, running

    signal.signal(signal.SIGINT, signal_handler)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("Flask server started at http://0.0.0.0:5000")

    telegram_app = ApplicationBuilder().token(TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("betting_signal", betting_signal))
    telegram_app.add_handler(CommandHandler("cancel", cancel))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    telegram_app.add_handler(CallbackQueryHandler(handle_callback))
    telegram_app.add_error_handler(error_handler)

    logging.info("Telegram bot polling started...")
    telegram_app.run_polling()

    while running:
        threading.Event().wait(1)

if __name__ == "__main__":
    main()
