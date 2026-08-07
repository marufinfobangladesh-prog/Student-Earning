import os
import logging
import json
from datetime import datetime
from threading import Thread
from http.server import HTTPServer, SimpleHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

TOKEN = "8906908546:AAHzB9xXXaseFaBUl_nDec5EmbCgYLCKfVs"
PAYMENT_CHANNEL_URL = "https://t.me/Student_Earning_Payment_chanel"
WEB_APP_URL = "https://student-earning-gray.vercel.app"

ADMIN_ID = 1892149781  
ADMIN_USERNAME = "ariyan_maruf009"

DB_FILE = "users.json"
PENDING_FILE = "pending_tasks.json"

class SimpleHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is Running!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

Thread(target=run_server, daemon=True).start()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

def load_data(file_name):
    if os.path.exists(file_name):
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(file_name, data):
    try:
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving {file_name}: {e}")

users_db = load_data(DB_FILE)
pending_db = load_data(PENDING_FILE)

def get_user_data(user_id_str, first_name="", referrer_id=None):
    user_id_str = str(user_id_str)
    if user_id_str not in users_db:
        users_db[user_id_str] = {
            "name": first_name,
            "balance": 0.0,
            "completed_today": 0,
            "total_completed": 0,
            "referrals": [],
            "referred_by": str(referrer_id) if referrer_id else None,
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if referrer_id and str(referrer_id) in users_db:
            if user_id_str not in users_db[str(referrer_id)].get("referrals", []):
                users_db[str(referrer_id)].setdefault("referrals", []).append(user_id_str)
        save_data(DB_FILE, users_db)
    elif first_name and users_db[user_id_str].get("name") != first_name:
        users_db[user_id_str]["name"] = first_name
        save_data(DB_FILE, users_db)
    return users_db[user_id_str]

def is_admin(user):
    is_id_match = (user.id == ADMIN_ID)
    is_username_match = (user.username and user.username.lower() == ADMIN_USERNAME.lower())
    return is_id_match or is_username_match

async def release_tasks_for_all(app: Application, manual=False):
    count = 0
    for uid, udata in users_db.items():
        udata["completed_today"] = 0
        count += 1
        try:
            msg = "🚀 **নতুন কাজ রিলিজ হয়েছে!**" if manual else "🌅 **সকাল ৬:০০ AM আপডেট!**\n\nআপনার আজকের ১০টি কাজ চলে এসেছে।"
            await app.bot.send_message(chat_id=int(uid), text=msg, parse_mode="Markdown")
        except Exception:
            pass
    save_data(DB_FILE, users_db)
    return count

async def daily_reset_task(app: Application):
    await release_tasks_for_all(app, manual=False)

async def post_init(app: Application) -> None:
    tz = pytz.timezone('Asia/Dhaka')
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(daily_reset_task, 'cron', hour=6, minute=0, args=[app])
    scheduler.start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id_str = str(user.id)
    get_user_data(user_id_str, user.first_name)

    keyboard = [
        [InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=PAYMENT_CHANNEL_URL)],
        [InlineKeyboardButton("✅ জয়েন করেছি, চেক করুন", callback_data="check_join")]
    ]
    await update.message.reply_text(
        f"স্বাগতম **{user.first_name}** Student Earning-এ!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user): return

    keyboard = [
        [InlineKeyboardButton("📋 পেন্ডিং কাজ রিভিউ করুন", callback_data="review_pending")],
        [InlineKeyboardButton("🚀 এক ক্লিকে সবার কাজ রিলিজ করুন", callback_data="release_all_now")]
    ]
    await update.message.reply_text(f"👑 **অ্যাডমিন প্যানেল**\nপেন্ডিং কাজ: `{len(pending_db)}`টি", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id_str = str(user.id)
    u = get_user_data(user_id_str, user.first_name)

    if query.data == "check_join":
        main_keyboard = [
            [InlineKeyboardButton("🚀 কাজ শুরু করুন (Task)", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton("💰 ব্যালেন্স", callback_data="balance"), InlineKeyboardButton("👥 রেফার করুন", callback_data="referral")]
        ]
        await query.edit_message_text("✅ ভেরিফিকেশন সফল! কাজের লিস্ট ওপেন করুন:", reply_markup=InlineKeyboardMarkup(main_keyboard))

    elif query.data == "balance":
        await query.message.reply_text(f"💰 **বর্তমান ব্যালেন্স:** ৳{u['balance']:.1f}\n🎯 **আজকের কাজ:** {u['completed_today']}/১০")

    elif query.data == "review_pending" and is_admin(user):
        if not pending_db:
            await query.message.reply_text("✅ কোন পেন্ডিং কাজ নেই!")
            return
        task_id, tdata = list(pending_db.items())[0]
        btn = [[InlineKeyboardButton("✅ Approve", callback_data=f"app_{task_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"rej_{task_id}")]]
        await query.message.reply_text(f"📌 **কাজ রিভিউ:**\n🆔 ইউজার: `{tdata['user_id']}`\n📝 ধরণ: {tdata['type_name']}\n💵 টাকা: ৳{tdata['reward']}", reply_markup=InlineKeyboardMarkup(btn), parse_mode="Markdown")

    elif query.data.startswith("app_") and is_admin(user):
        task_id = query.data.replace("app_", "")
        if task_id in pending_db:
            tdata = pending_db.pop(task_id)
            save_data(PENDING_FILE, pending_db)
            
            p_uid = tdata["user_id"]
            pu = get_user_data(p_uid)
            pu["balance"] += tdata["reward"]
            pu["completed_today"] += 1
            save_data(DB_FILE, users_db)

            try:
                await context.bot.send_message(chat_id=int(p_uid), text=f"🎉 আপনার কাজটি অ্যাপ্রুভ হয়েছে! ৳{tdata['reward']} যোগ হয়েছে।")
            except: pass
            await query.edit_message_text("✅ Approved & Balance Added!")

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_str = str(update.effective_user.id)
    u = get_user_data(user_id_str, update.effective_user.first_name)
    
    if not update.message or not update.message.web_app_data: return

    try:
        data = json.loads(update.message.web_app_data.data)
        if data.get("status") == "success":
            task_type = data.get("task_type", "normal")
            reward = 5.0 if task_type == "normal" else (8.0 if task_type == "spin" else 10.0)
            type_name = "নরমাল এড" if task_type == "normal" else ("স্পিন টাস্ক" if task_type == "spin" else "অ্যাপ ডাউনলোড")

            task_id = f"task_{int(datetime.now().timestamp())}_{user_id_str}"
            pending_db[task_id] = {"user_id": user_id_str, "type_name": type_name, "reward": reward}
            save_data(PENDING_FILE, pending_db)

            await update.message.reply_text(f"📥 কাজটি অ্যাডমিন রিভিউতে জমা হয়েছে! কনফার্ম করলেই ৳{reward} ব্যালেন্সে যোগ হবে।")
    except Exception as e:
        logging.error(f"Error: {e}")

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
