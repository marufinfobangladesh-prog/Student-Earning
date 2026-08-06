import os
import logging
import json
from threading import Thread
from flask import Flask, send_file
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Flask Web Server Configuration
web_app = Flask(__name__)

@web_app.route('/')
def home():
    if os.path.exists('index.html'):
        return send_file('index.html')
    return "index.html file not found in root directory!", 404

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# Start Flask Web Server in background
Thread(target=run_flask, daemon=True).start()

# Bot Setup Configurations
TOKEN = "8906908546:AAE6gPXnqRaXB4G1EbZNjDz0KX_1fhoORSY"
PAYMENT_CHANNEL_URL = "https://t.me/Student_Earning_Payment_chanel"
WEB_APP_URL = "https://student-earningsn.onrender.com"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
users_db = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in users_db:
        users_db[user.id] = {"balance": 0.0, "completed_today": 0}

    keyboard = [
        [InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=PAYMENT_CHANNEL_URL)],
        [InlineKeyboardButton("✅ জয়েন করেছি, চেক করুন", callback_data="check_join")]
    ]
    await update.message.reply_text(
        f"স্বাগতম **{user.first_name}** Student Earning-এ!\n\nকাজ করতে আগে পেমেন্ট চ্যানেলে জয়েন করুন:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "check_join":
        main_keyboard = [
            [InlineKeyboardButton("🚀 কাজ শুরু করুন (Task)", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton("💰 ব্যালেন্স", callback_data="balance"), InlineKeyboardButton("💳 উইথড্র", callback_data="withdraw")],
            [InlineKeyboardButton("📢 পেমেন্ট প্রুফ চ্যানেল", url=PAYMENT_CHANNEL_URL)]
        ]
        await query.edit_message_text("✅ ভেরিফিকেশন সফল! নিচের বাটন থেকে কাজ করুন:", reply_markup=InlineKeyboardMarkup(main_keyboard))

    elif query.data == "balance":
        u = users_db.get(user_id, {"balance": 0.0, "completed_today": 0})
        await query.message.reply_text(f"💰 বর্তমান ব্যালেন্স: ৳{u['balance']}\n🎯 আজকের কাজ: {u['completed_today']}/১০")

    elif query.data == "withdraw":
        u = users_db.get(user_id, {"balance": 0.0})
        if u['balance'] < 500:
            await query.answer("❌ সর্বনিম্ন উইথড্র ৳৫০০!", show_alert=True)
            await query.message.reply_text(f"❌ আপনার ব্যালেন্স ৳{u['balance']}। সর্বনিম্ন ৳৫০০ হলে বিকাশ নম্বরে টাকা তুলতে পারবেন।")
        else:
            await query.message.reply_text("📱 আপনার **বিকাশ (bKash)** নম্বরটি লিখুন:")
            context.user_data['waiting_bkash'] = True

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        data = json.loads(update.message.web_app_data.data)
    except Exception:
        return

    if data.get("status") == "success":
        if user_id not in users_db:
            users_db[user_id] = {"balance": 0.0, "completed_today": 0}
        
        if users_db[user_id]["completed_today"] >= 10:
            await update.message.reply_text("❌ আপনার আজকের ১০টি কাজের লিমিট শেষ!")
            return

        task_type = data.get("task_type", "normal")
        
        if task_type == "download":
            reward = 10.0
            task_name = "📲 অ্যাপ ডাউনলোড"
        elif task_type == "spin":
            reward = 8.0
            task_name = "🎰 স্পিন টাস্ক"
        else:
            reward = 5.0
            task_name = "📜 নরমাল এড স্ক্রলিং"

        users_db[user_id]["completed_today"] += 1
        users_db[user_id]["balance"] += reward
        
        await update.message.reply_text(
            f"🎉 **{task_name}** সফলভাবে জমা হয়েছে!\n"
            f"➕ যোগ হয়েছে: ৳{reward}\n"
            f"💰 মোট ব্যালেন্স: ৳{users_db[user_id]['balance']}\n"
            f"🎯 আজকের মোট কাজ: {users_db[user_id]['completed_today']}/১০",
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_bkash'):
        num = update.message.text
        user_id = update.effective_user.id
        current_bal = users_db.get(user_id, {}).get('balance', 0.0)
        
        users_db[user_id]['balance'] = 0.0
        context.user_data['waiting_bkash'] = False
        await update.message.reply_text(
            f"✅ ৳{current_bal} টাকা উইথড্র রিকোয়েস্ট গ্রহণ করা হয়েছে!\n"
            f"📱 বিকাশ নম্বর: {num}\n\n"
            f"২৪ ঘণ্টার মধ্যে আপনার বিকাশ নম্বরে টাকা পাঠিয়ে দেয়া হবে।"
        )

def main():
    app = Application.builder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
