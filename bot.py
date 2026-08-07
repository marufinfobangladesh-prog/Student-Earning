import os
import logging
import json
from threading import Thread
from http.server import HTTPServer, SimpleHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8906908546:AAHzB9xXXaseFaBUl_nDec5EmbCgYLCKfVs"
PAYMENT_CHANNEL_URL = "https://t.me/Student_Earning_Payment_chanel"
WEB_APP_URL = "https://student-earning-gray.vercel.app"
DB_FILE = "users.json"

# Web Server
class SimpleHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is Running Perfectly!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

Thread(target=run_server, daemon=True).start()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Persistent JSON Database Handler
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(db):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving DB: {e}")

users_db = load_db()

def get_user_data(user_id_str, referrer_id=None):
    if user_id_str not in users_db:
        users_db[user_id_str] = {
            "balance": 0.0,
            "completed_today": 0,
            "total_completed": 0,
            "referred_by": str(referrer_id) if referrer_id else None,
            "referral_rewarded": False
        }
        save_db(users_db)
    return users_db[user_id_str]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id_str = str(user.id)
    
    referrer_id = None
    if context.args:
        try:
            possible_id = int(context.args[0])
            if possible_id != user.id:
                referrer_id = possible_id
        except ValueError:
            pass

    get_user_data(user_id_str, referrer_id)

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
    user_id_str = str(query.from_user.id)
    u = get_user_data(user_id_str)

    if query.data == "check_join":
        main_keyboard = [
            [InlineKeyboardButton("🚀 কাজ শুরু করুন (Task)", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton("💰 ব্যালেন্স", callback_data="balance"), InlineKeyboardButton("👥 রেফার করুন", callback_data="referral")],
            [InlineKeyboardButton("💳 উইথড্র", callback_data="withdraw"), InlineKeyboardButton("📢 পেমেন্ট প্রুফ", url=PAYMENT_CHANNEL_URL)]
        ]
        await query.edit_message_text("✅ ভেরিফিকেশন সফল! নিচের বাটন থেকে কাজ করুন:", reply_markup=InlineKeyboardMarkup(main_keyboard))

    elif query.data == "balance":
        await query.message.reply_text(f"💰 বর্তমান ব্যালেন্স: ৳{u['balance']:.1f}\n🎯 আজকের কাজ: {u['completed_today']}/১০")

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_id_str}"
        text = (
            f"👥 **রেফারেল প্রোগ্রাম**\n\n"
            f"আপনার রেফারেল লিংক:\n`{ref_link}`\n\n"
            f"🎁 **নিয়ম:** আপনার লিংকে কেউ জয়েন করে **২টি কাজ** সম্পন্ন করলেই আপনি পাবেন **৳১০** বোনাস!"
        )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif query.data == "withdraw":
        if u['balance'] < 500:
            await query.answer("❌ সর্বনিম্ন উইথড্র ৳৫০০!", show_alert=True)
            await query.message.reply_text(f"❌ আপনার ব্যালেন্স ৳{u['balance']:.1f}। সর্বনিম্ন ৳৫০০ হলে বিকাশ নম্বরে টাকা তুলতে পারবেন।")
        else:
            await query.message.reply_text("📱 আপনার **বিকাশ (bKash)** নম্বরটি লিখুন:")
            context.user_data['waiting_bkash'] = True

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_str = str(update.effective_user.id)
    u = get_user_data(user_id_str)
    
    if not update.message or not update.message.web_app_data:
        return

    try:
        data = json.loads(update.message.web_app_data.data)
    except Exception as e:
        logging.error(f"JSON Parse Error: {e}")
        return

    if data.get("status") == "success":
        if u["completed_today"] >= 10:
            await update.message.reply_text("❌ আপনার আজকের ১০টি কাজের লিমিট শেষ!")
            return

        task_type = data.get("task_type", "normal")
        reward = 5.0
        type_name = "নরমাল এড স্ক্রলিং"

        if task_type == "spin":
            reward = 8.0
            type_name = "স্পিন টাস্ক"
        elif task_type == "app":
            reward = 10.0
            type_name = "অ্যাপ ডাউনলোড / বেটিং এড"

        # Update User Records
        u["completed_today"] += 1
        u["total_completed"] += 1
        u["balance"] += reward

        # Check Referral Rewards
        referrer_id_str = u.get("referred_by")
        if referrer_id_str and not u.get("referral_rewarded", False):
            if u["total_completed"] >= 2:
                u["referral_rewarded"] = True
                ref_user = get_user_data(referrer_id_str)
                ref_user["balance"] += 10.0
                try:
                    await context.bot.send_message(
                        chat_id=int(referrer_id_str),
                        text=f"🎉 **রেফারেল বোনাস!**\nআপনার ইনভাইট করা ইউজার ২টি কাজ শেষ করায় আপনি **৳১০** বোনাস পেয়েছেন!",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

        save_db(users_db)

        await update.message.reply_text(
            f"🎉 **কাজ জমা সফল হয়েছে!**\n"
            f"📌 ধরণ: {type_name}\n"
            f"➕ যোগ হয়েছে: ৳{reward}\n"
            f"💰 বর্তমান মোট ব্যালেন্স: ৳{u['balance']:.1f}\n"
            f"🎯 আজকের মোট কাজ সম্পন্ন: {u['completed_today']}/১০",
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_bkash'):
        num = update.message.text
        user_id_str = str(update.effective_user.id)
        u = get_user_data(user_id_str)
        current_bal = u['balance']
        
        u['balance'] = 0.0
        save_db(users_db)
        
        context.user_data['waiting_bkash'] = False
        await update.message.reply_text(
            f"✅ ৳{current_bal:.1f} টাকা উইথড্র রিকোয়েস্ট গ্রহণ করা হয়েছে!\n"
            f"📱 বিকাশ নম্বর: {num}\n\n"
            f"২৪ ঘণ্টার মধ্যে আপনার বিকাশ নম্বরে টাকা পাঠিয়ে দেয়া হবে।"
        )

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
