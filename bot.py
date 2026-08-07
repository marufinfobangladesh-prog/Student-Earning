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
        self.wfile.write(b"Bot is Running Perfectly!")

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

def get_user_data(user_id_str, first_name=""):
    user_id_str = str(user_id_str)
    if user_id_str not in users_db:
        users_db[user_id_str] = {
            "name": first_name,
            "balance": 0.0,
            "completed_today": 0,
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_data(DB_FILE, users_db)
    return users_db[user_id_str]

def is_admin(user):
    is_id_match = (user.id == ADMIN_ID)
    is_username_match = (user.username and user.username.lower() == ADMIN_USERNAME.lower())
    return is_id_match or is_username_match

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user_data(str(user.id), user.first_name)

    keyboard = [
        [InlineKeyboardButton("🚀 কাজ শুরু করুন (Task)", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton("💰 ব্যালেন্স", callback_data="balance")]
    ]
    await update.message.reply_text(
        f"স্বাগতম **{user.first_name}** Student Earning-এ!\nনিচের বাটন থেকে কাজ শুরু করুন:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user): return

    keyboard = [
        [InlineKeyboardButton("📋 পেন্ডিং কাজ রিভিউ করুন", callback_data="review_pending")]
    ]
    await update.message.reply_text(f"👑 **অ্যাডমিন প্যানেল**\nমোট পেন্ডিং কাজ: `{len(pending_db)}`টি", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    u = get_user_data(str(user.id), user.first_name)

    if query.data == "balance":
        await query.message.reply_text(f"💰 **আপনার বর্তমান ব্যালেন্স:** ৳{u['balance']:.1f}")

    elif query.data == "review_pending" and is_admin(user):
        if not pending_db:
            await query.message.reply_text("✅ কোনো পেন্ডিং কাজ নেই!")
            return
        
        task_key, tdata = list(pending_db.items())[0]
        btn = [[InlineKeyboardButton("✅ Approve", callback_data=f"app_{task_key}"), InlineKeyboardButton("❌ Reject", callback_data=f"rej_{task_key}")]]
        await query.message.reply_text(
            f"📌 **কাজ রিভিউ:**\n🆔 ইউজার: `{tdata['user_id']}`\n🎯 টাস্ক নম্বর: #{tdata['task_id']}\n📝 ধরণ: {tdata['type_name']}\n💵 টাকা: ৳{tdata['reward']}", 
            reply_markup=InlineKeyboardMarkup(btn), 
            parse_mode="Markdown"
        )

    elif query.data.startswith("app_") and is_admin(user):
        task_key = query.data.replace("app_", "")
        if task_key in pending_db:
            tdata = pending_db.pop(task_key)
            save_data(PENDING_FILE, pending_db)
            
            p_uid = tdata["user_id"]
            pu = get_user_data(p_uid)
            pu["balance"] += tdata["reward"]
            save_data(DB_FILE, users_db)

            try:
                await context.bot.send_message(chat_id=int(p_uid), text=f"🎉 আপনার টাস্ক #{tdata['task_id']} অনুমোদিত হয়েছে! ৳{tdata['reward']} ব্যালেন্সে যোগ করা হয়েছে।")
            except: pass
            await query.edit_message_text("✅ কাজ সফলভাবে Approved করা হয়েছে!")

    elif query.data.startswith("rej_") and is_admin(user):
        task_key = query.data.replace("rej_", "")
        if task_key in pending_db:
            tdata = pending_db.pop(task_key)
            save_data(PENDING_FILE, pending_db)
            
            try:
                await context.bot.send_message(chat_id=int(tdata["user_id"]), text=f"❌ আপনার টাস্ক #{tdata['task_id']} বাতিল করা হয়েছে।")
            except: pass
            await query.edit_message_text("❌ কাজ বাতিল করা হয়েছে!")

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_str = str(update.effective_user.id)
    get_user_data(user_id_str, update.effective_user.first_name)
    
    if not update.message or not update.message.web_app_data: return

    try:
        data = json.loads(update.message.web_app_data.data)
        if data.get("status") == "success":
            task_id = data.get("task_id")
            type_name = data.get("type_name")
            reward = data.get("reward")

            task_key = f"task_{int(datetime.now().timestamp())}_{user_id_str}"
            pending_db[task_key] = {
                "user_id": user_id_str, 
                "task_id": task_id,
                "type_name": type_name, 
                "reward": reward
            }
            save_data(PENDING_FILE, pending_db)

            await update.message.reply_text(f"📥 টাস্ক #{task_id} পেন্ডিং তালিকায় জমা হয়েছে! অ্যাডমিন অ্যাপ্রুভ করলে ৳{reward} যুক্ত হবে।")
    except Exception as e:
        logging.error(f"Error: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
