import logging
from telegram import Update, InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    MessageHandler, CallbackQueryHandler, ConversationHandler, filters
)
from PIL import Image, ImageDraw, ImageFilter
import io

# Enable logging
logging.basicConfig(level=logging.INFO)

# Configs
BOT_TOKEN = '7968039028:AAHwLwMDzNppSkNzD_fsusdkaG8ybewIrZY'
GROUP_ID = -1002625930074
CHANNEL_USERNAME = '@RiyadVai_2024'

# Rectangle coordinates
COORDINATES = [
    {"x": 19.3, "y": 326.2, "w": 155.2, "h": 24.9},
    {"x": 248.9, "y": 326.2, "w": 89.3, "h": 24.9},
    {"x": 148.5, "y": 36.9, "w": 103.2, "h": 24.9}
]

# Conversation states
WAITING_IMAGE, WAITING_CAPTION, CONFIRM_POST = range(3)

# In-memory session
user_data = {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("দয়া করে একটি ছবি পাঠান যেটি আপনি প্রক্রিয়া করতে চান।")
    return WAITING_IMAGE

# Handle image
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo = update.message.photo[-1]
    file = await photo.get_file()
    image_bytes = await file.download_as_bytearray()

    user_data[user_id] = {"image_bytes": image_bytes}

    # Send raw image to group
    await context.bot.send_photo(chat_id=GROUP_ID, photo=InputFile(io.BytesIO(image_bytes), filename="original.jpg"))

    # Process image and store stream
    processed_io = apply_blur_overlay(image_bytes)
    user_data[user_id]["processed_io"] = processed_io

    # Preview processed image to user
    await update.message.reply_photo(
        photo=InputFile(processed_io, filename="preview.jpg"),
        caption="এই ছবির জন্য একটি ক্যাপশন লিখুন।"
    )

    return WAITING_CAPTION

# Handle caption input
async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data[user_id]["caption"] = update.message.text

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("হ্যাঁ, পোস্ট করো", callback_data="confirm_post")],
        [InlineKeyboardButton("না, বাতিল", callback_data="cancel_post")]
    ])

    await update.message.reply_text(
        "আপনি কি এই ছবিটি চ্যানেলে পোস্ট করতে চান?",
        reply_markup=keyboard
    )

    return CONFIRM_POST

# Confirmation handler
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

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("প্রক্রিয়া বাতিল করা হয়েছে।")
    return ConversationHandler.END

# Apply blur to rectangles
def apply_blur_overlay(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    for box in COORDINATES:
        x, y, w, h = int(box["x"]), int(box["y"]), int(box["w"]), int(box["h"])
        region = image.crop((x, y, x + w, y + h))
        blurred = region.filter(ImageFilter.GaussianBlur(radius=6))  # Blur strength
        image.paste(blurred, (x, y))

    output = io.BytesIO()
    image.save(output, format="JPEG")
    output.seek(0)
    return output

# Bot runner
def main():
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
