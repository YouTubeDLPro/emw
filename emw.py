import logging
from telegram import Update, InputFile, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberAdministrator
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    MessageHandler, CallbackQueryHandler, ConversationHandler, filters
)
from flask import Flask
from PIL import Image, ImageDraw, ImageFilter
import threading
import io

# Enable logging
logging.basicConfig(level=logging.INFO)

# Configs
BOT_TOKEN = '7968039028:AAHwLwMDzNppSkNzD_fsusdkaG8ybewIrZY'
GROUP_ID = -1002625930074
CHANNEL_USERNAME = '@RiyadVai_2025'
ALLOWED_USERS = [7975347391, 7489498193]
ADMIN_USER_ID = 7489498193

COORDINATES = [
    {"x": 19.3, "y": 326.2, "w": 155.2, "h": 24.9},
    {"x": 248.9, "y": 326.2, "w": 89.3, "h": 24.9},
    {"x": 148.5, "y": 36.9, "w": 103.2, "h": 24.9}
]

WAITING_IMAGE, WAITING_CAPTION, CONFIRM_POST = range(3)
user_data = {}

# Flask App
flask_app = Flask(__name__)

@flask_app.route("/health")
def health():
    return "OK", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=5000)

# Access Control Decorator
def user_check(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ALLOWED_USERS:
            await update.message.reply_text("আপনি এই বটটি ব্যবহারের অনুমতি পাননি।")
            return ConversationHandler.END
        # Make user admin if required
        if user_id == ADMIN_USER_ID:
            try:
                await context.bot.promote_chat_member(
                    chat_id=CHANNEL_USERNAME,
                    user_id=user_id,
                    privileges=ChatMemberAdministrator(can_post_messages=True, can_edit_messages=True)
                )
            except Exception as e:
                logging.warning(f"Could not promote user: {e}")
        return await func(update, context)
    return wrapper

@user_check
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("দয়া করে একটি ছবি পাঠান যেটি আপনি প্রক্রিয়া করতে চান।")
    return WAITING_IMAGE

@user_check
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    user_data[user_id] = {"image_bytes": image_bytes}
    await context.bot.send_photo(chat_id=GROUP_ID, photo=InputFile(io.BytesIO(image_bytes), filename="original.jpg"))
    processed_io = apply_blur_overlay(image_bytes)
    user_data[user_id]["processed_io"] = processed_io

    await update.message.reply_photo(
        photo=InputFile(processed_io, filename="preview.jpg"),
        caption="এই ছবির জন্য একটি ক্যাপশন লিখুন।"
    )
    return WAITING_CAPTION

@user_check
async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    caption = update.message.text
    user_data[user_id]["caption"] = caption
    processed_io = user_data[user_id]["processed_io"]
    processed_io.seek(0)

    await update.message.reply_photo(
        photo=InputFile(processed_io, filename="preview.jpg"),
        caption=caption
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("হ্যাঁ, পোস্ট করো", callback_data="confirm_post")],
        [InlineKeyboardButton("না, বাতিল", callback_data="cancel_post")]
    ])
    await update.message.reply_text("আপনি কি এই ছবিটি চ্যানেলে পোস্ট করতে চান?", reply_markup=keyboard)
    return CONFIRM_POST

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    data = user_data.get(user_id)
    if not data:
        await query.edit_message_text("সেশন শেষ হয়ে গেছে। দয়া করে আবার শুরু করুন।")
        return ConversationHandler.END

    if query.data == "confirm_post":
        data["processed_io"].seek(0)
        await context.bot.send_photo(
            chat_id=CHANNEL_USERNAME,
            photo=InputFile(data["processed_io"], filename="final.jpg"),
            caption=data["caption"]
        )
        await query.edit_message_text("ছবিটি সফলভাবে চ্যানেলে পোস্ট হয়েছে।")
    else:
        await query.edit_message_text("পোস্ট বাতিল করা হয়েছে।")

    user_data.pop(user_id, None)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("প্রক্রিয়া বাতিল করা হয়েছে।")
    return ConversationHandler.END

def apply_blur_overlay(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    for box in COORDINATES:
        x, y, w, h = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
        region = image.crop((x, y, x + w, y + h))
        blurred = region.filter(ImageFilter.GaussianBlur(radius=6))
        image.paste(blurred, (x, y))
    output = io.BytesIO()
    image.save(output, format="JPEG")
    output.seek(0)
    return output

def main():
    threading.Thread(target=run_flask).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_IMAGE: [MessageHandler(filters.PHOTO, handle_image)],
            WAITING_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption)],
            CONFIRM_POST: [CallbackQueryHandler(handle_confirmation)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
