import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import re
from flask import Flask
import threading
import signal
import sys
import os

# Bot configuration
TOKEN = os.getenv("TOKEN")  # Ensure the variable name matches the one set in Render
if not TOKEN:
    print("Error: TOKEN is not defined")
    
CHANNEL_ID = '@easymatchwin'

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello, World!'

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Steps for collecting user input
steps = [
    ("date_time", "Please provide the date and time of the match (e.g., 2025-04-02 15:30:45):"),
    ("team_a", "Please provide Team A:"),
    ("team_b", "Please provide Team B:"),
    ("odds", "Please provide the odds (e.g., 2.5):"),
    ("score", "Please provide the correct score prediction (e.g., 2-1):"),
    ("link", "Please provide the match link:"),
    ("image", "Please upload the image for the match:")
]

# Temporary storage for user data
user_data = {}

# Validation functions
def validate_date(date_str):
    return re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', date_str)

def validate_odds(odds_str):
    return re.match(r'\d+(\.\d+)?', odds_str)

def validate_score(score_str):
    return re.match(r'\d+-\d+', score_str)

# Flask application
app = Flask(__name__)
flask_thread = None
running = True

@app.route('/')
def health_check():
    return "Server is running", 200

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# Telegram bot handlers
async def start_command(update: Update, context):
    user_id = update.message.from_user.id
    logging.info(f"User {user_id} started the bot with /start.")
    welcome_message = (
        "🎉 Welcome to the Easy Match Win - Betting Signal Bot! 🎉\n\n"
        "I'm here to help you submit betting signals quickly and easily.\n"
        "To get started, use the /betting_signal command.\n\n"
        "If you need help at any time, just type /help."
    )
    await update.message.reply_text(welcome_message)

async def betting_signal(update: Update, context):
    user_id = update.message.from_user.id
    logging.info(f"User {user_id} started betting signal process.")
    user_data[user_id] = {"step": 0, "data": {}}
    await update.message.reply_text(steps[0][1])

async def cancel(update: Update, context):
    user_id = update.message.from_user.id
    if user_id in user_data:
        logging.info(f"User {user_id} cancelled the process.")
        del user_data[user_id]
        await update.message.reply_text("Process cancelled. Start again with /betting_signal.")
    else:
        await update.message.reply_text("Nothing to cancel. Start with /betting_signal.")

async def handle_text(update: Update, context):
    user_id = update.message.from_user.id
    if user_id not in user_data or "step" not in user_data[user_id]:
        await update.message.reply_text("Please start with /betting_signal")
        return

    current_step = user_data[user_id]["step"]
    step_key, _ = steps[current_step]

    if step_key == "image":
        await update.message.reply_text("Please upload an image for this step, not text.")
        return

    text = update.message.text

    if step_key == "date_time" and not validate_date(text):
        await update.message.reply_text("Invalid date format. Please use YYYY-MM-DD HH:MM:SS.")
        return
    elif step_key == "odds" and not validate_odds(text):
        await update.message.reply_text("Invalid odds format. Please provide a decimal number (e.g., 2.5).")
        return
    elif step_key == "score" and not validate_score(text):
        await update.message.reply_text("Invalid score format. Please use X-Y where X and Y are integers (e.g., 2-1).")
        return

    user_data[user_id]["data"][step_key] = text
    user_data[user_id]["step"] += 1

    if user_data[user_id]["step"] < len(steps):
        next_step_key, next_prompt = steps[user_data[user_id]["step"]]
        await update.message.reply_text(next_prompt)
    else:
        await send_summary(user_id, context)

async def handle_photo(update: Update, context):
    user_id = update.message.from_user.id
    if user_id not in user_data or "step" not in user_data[user_id]:
        await update.message.reply_text("Please start with /betting_signal")
        return

    current_step = user_data[user_id]["step"]
    step_key, _ = steps[current_step]

    if step_key != "image":
        await update.message.reply_text("Please send text for this step, not an image.")
        return

    if not update.message.photo:
        await update.message.reply_text("Please upload an image.")
        return

    user_data[user_id]["data"][step_key] = update.message.photo[-1].file_id
    user_data[user_id]["step"] += 1

    if user_data[user_id]["step"] < len(steps):
        next_step_key, next_prompt = steps[user_data[user_id]["step"]]
        await update.message.reply_text(next_prompt)
    else:
        await send_summary(user_id, context)

async def send_summary(user_id, context):
    data = user_data[user_id]["data"]
    summary = f"""
Please confirm the following details:

📅 Date: {data['date_time']}
🏟️ Team: {data['team_a']} vs {data['team_b']}
📈 Odds: {data['odds']}
🔢 Correct Score: {data['score']}
📋 Match Type: Football
🔗 Match Link: {data['link']}
    """
    keyboard = [
        [InlineKeyboardButton("Confirm", callback_data="confirm"),
         InlineKeyboardButton("Edit", callback_data="edit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text=summary, reply_markup=reply_markup)

async def handle_callback(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    if query.data == "confirm":
        logging.info(f"User {user_id} confirmed the signal.")
        await send_betting_signal(user_id, context)
        await query.answer("Betting signal sent successfully!")
    elif query.data == "edit":
        logging.info(f"User {user_id} chose to edit.")
        await show_edit_options(user_id, context)
        await query.answer("Please select a field to edit.")
    elif query.data == "back_to_summary":
        logging.info(f"User {user_id} went back to summary.")
        await send_summary(user_id, context)
        await query.answer("Returned to summary.")
    else:
        step_index = int(query.data)
        field = steps[step_index][0]
        logging.info(f"User {user_id} selected to edit {field}.")
        user_data[user_id]["step"] = step_index
        step_key, prompt = steps[step_index]
        await context.bot.send_message(chat_id=user_id, text=f"Editing {step_key}. {prompt}")
        await query.answer()

async def show_edit_options(user_id, context):
    keyboard = [
        [InlineKeyboardButton("Date", callback_data="0"),
         InlineKeyboardButton("Team A", callback_data="1"),
         InlineKeyboardButton("Team B", callback_data="2")],
        [InlineKeyboardButton("Odds", callback_data="3"),
         InlineKeyboardButton("Score", callback_data="4"),
         InlineKeyboardButton("Link", callback_data="5")],
        [InlineKeyboardButton("Image", callback_data="6")],
        [InlineKeyboardButton("Back to Summary", callback_data="back_to_summary")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text="Which field would you like to edit?", reply_markup=reply_markup)

async def send_betting_signal(user_id, context):
    data = user_data[user_id]["data"]
    message = f"""
⚽️ Easy Match Win - Betting Signal 📊

📅 Date: {data['date_time']}
🏟️ Team: {data['team_a']} vs {data['team_b']}
📈 Odds: {data['odds']}
🔢 Correct Score: {data['score']}
📋 Match Type: Football
🔗 Match Link: {data['link']}

🚨 This data has been confirmed by insiders! 🚨

Stay tuned for more updates!
Good Luck and Bet Smart! 🍀
"""
    await context.bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=data['image'],
        caption=message
    )
    logging.info(f"User {user_id} sent the betting signal.")
    del user_data[user_id]
    await context.bot.send_message(chat_id=user_id, text="Signal has been sent to the channel.")

def signal_handler(sig, frame):
    global running
    running = False
    print("\nShutting down gracefully...")
    sys.exit(0)

def main():
    global flask_thread, running
    
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info("Flask server started on http://0.0.0.0:5000")
    
    # Set up and run Telegram bot
    telegram_app = ApplicationBuilder().token(TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("betting_signal", betting_signal))
    telegram_app.add_handler(CommandHandler("cancel", cancel))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    telegram_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    telegram_app.add_handler(CallbackQueryHandler(handle_callback))
    
    logging.info("Starting Telegram bot polling...")
    telegram_app.run_polling()
    
    # Wait for Ctrl+C
    while running:
        threading.Event().wait(1)

if __name__ == "__main__":
    main()
