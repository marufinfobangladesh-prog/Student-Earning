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
        self.wfile.write(b"Student Earning Bot is Running!")

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
    if user_id_str not in users_db:
        users_db[user_id_str] = {
            "name": first_name,
            "balance": 0.0,
            "completed_today": 0,
            "total_completed": 0,
            "referrals": [], # রেফার করা ইউজারদের আইডি লিস্ট
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

# ⏰ অটোমেটিক বা ম্যানুয়াল কাজ রিলিজ ফানশন
async def release_tasks_for_all(app: Application, manual=False):
    count = 0
    for uid, udata in users_db.items():
        udata["completed_today"] = 0
        count += 1
        try:
            msg = "🚀 **নতুন কাজ রিলিজ হয়েছে!**\n\nঅ্যাডমিন নতুন কাজ রিলিজ করেছেন। দ্রুত ১০টি কাজ সম্পন্ন করুন!" if manual else "🌅 **সকাল ৬:০০ AM আপডেট!**\n\nআপনার আজকের ১০টি নতুন কাজ চলে এসেছে। কাজ সম্পন্ন করুন এবং ইনকাম করুন!"
            await app.bot.send_message(chat_id=int(uid), text=msg, parse_mode="Markdown")
        except Exception:
            pass
    save_data(DB_FILE, users_db)
    return count

async def daily_reset_task(app: Application):
    logging.info("Running Daily Reset at 6:00 AM...")
    await release_tasks_for_all(app, manual=False)

async def post_init(app: Application) -> None:
    tz = pytz.timezone('Asia/Dhaka')
    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(daily_reset_task, 'cron', hour=6, minute=0, args=[app])
    scheduler.start()

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

    get_user_data(user_id_str, user.first_name, referrer_id)

    keyboard = [
        [InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=PAYMENT_CHANNEL_URL)],
        [InlineKeyboardButton("✅ জয়েন করেছি, চেক করুন", callback_data="check_join")]
    ]
    await update.message.reply_text(
        f"স্বাগতম **{user.first_name}** Student Earning-এ!\n\nকাজ করতে আগে আমাদের অফিসিয়াল চ্যানেলে জয়েন করুন:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user):
        await update.message.reply_text(f"❌ আপনি এই কমান্ডটি ব্যবহারের জন্য অনুমোদিত নন।")
        return

    total_users = len(users_db)
    pending_count = len(pending_db)
    
    text = (
        f"👑 **অ্যাডমিন কন্ট্রোল প্যানেল**\n\n"
        f"👥 মোট রেজিস্টার্ড ইউজার: `{total_users}` জন\n"
        f"⏳ পেন্ডিং কাজ জমা আছে: `{pending_count}` টি\n\n"
        f"নিচের বাটনগুলো থেকে অপশন সিলেক্ট করুন:"
    )
    
    keyboard = [
        [InlineKeyboardButton("📋 পেন্ডিং কাজ রিভিউ করুন", callback_data="review_pending")],
        [InlineKeyboardButton("👥 ইউজার তালিকা ও তথ্য", callback_data="list_users")],
        [InlineKeyboardButton("🚀 এক ক্লিকে সবার কাজ রিলিজ করুন", callback_data="release_all_now")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id_str = str(user.id)
    u = get_user_data(user_id_str, user.first_name)

    if query.data == "check_join":
        main_keyboard = [
            [InlineKeyboardButton("🚀 কাজ শুরু করুন (Task)", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton("💰 ব্যালেন্স", callback_data="balance"), InlineKeyboardButton("👥 রেফার করুন", callback_data="referral")],
            [InlineKeyboardButton("💳 উইথড্র", callback_data="withdraw"), InlineKeyboardButton("📢 পেমেন্ট প্রুফ", url=PAYMENT_CHANNEL_URL)]
        ]
        await query.edit_message_text("✅ ভেরিফিকেশন সফল! নিচের বাটন থেকে কাজ করুন:", reply_markup=InlineKeyboardMarkup(main_keyboard))

    elif query.data == "balance":
        remains = max(0, 10 - u['completed_today'])
        await query.message.reply_text(
            f"💰 **বর্তমান ব্যালেন্স:** ৳{u['balance']:.1f}\n"
            f"🎯 **আজকের সম্পূর্ণ কাজ:** {u['completed_today']}/১০\n"
            f"📌 **বাকি কাজ:** {remains}টি",
            parse_mode="Markdown"
        )

    elif query.data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_id_str}"
        total_refs = len(u.get("referrals", []))
        
        text = (
            f"👥 **রেফারেল প্রোগ্রাম**\n\n"
            f"🔗 **আপনার রেফার লিংক:**\n`{ref_link}`\n\n"
            f"📊 **আপনার রেফার হিস্ট্রি:**\n"
            f"👥 মোট রেফার করেছেন: `{total_refs}` জন\n\n"
            f"🎁 **নিয়ম:** আপনার রেফার লিংকে জয়েন করে কাজ করলে আকর্ষণীয় বোনাস পাবেন!"
        )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif query.data == "withdraw":
        if u['balance'] < 500:
            await query.answer("❌ সর্বনিম্ন উইথড্র ৳৫০০!", show_alert=True)
            await query.message.reply_text(f"❌ আপনার বর্তমান ব্যালেন্স ৳{u['balance']:.1f}। সর্বনিম্ন ৳৫০০ হলে বিকাশ নম্বরে টাকা তুলতে পারবেন।")
        else:
            await query.message.reply_text("📱 আপনার **বিকাশ (bKash)** নম্বরটি লিখুন:")
            context.user_data['waiting_bkash'] = True

    elif query.data == "list_users":
        if not is_admin(user):
            return
        
        msg = "📦 **ইউজার তালিকা ও পেন্ডিং স্ট্যাটাস:**\n\n"
        for uid, udata in users_db.items():
            user_pending = sum(1 for t in pending_db.values() if t["user_id"] == uid)
            msg += f"👤 **ইউজার:** {udata.get('name', 'N/A')}\n"
            msg += f"🆔 **ID:** `{uid}`\n"
            msg += f"💰 **ব্যালেন্স:** ৳{udata.get('balance', 0.0)}\n"
            msg += f"⏳ **পেন্ডিং কাজ:** {user_pending}টি | **আজকের কাজ:** {udata.get('completed_today', 0)}/১০\n"
            msg += "-----------------------------------\n"
        
        await query.message.reply_text(msg, parse_mode="Markdown")

    elif query.data == "release_all_now":
        if not is_admin(user):
            return
        count = await release_tasks_for_all(context.application, manual=True)
        await query.message.reply_text(f"✅ সফলভাবে মোট `{count}` জন ইউজারের ১০টি কাজ রিলিজ করা হয়েছে এবং নোটিফিকেশন পাঠানো হয়েছে!", parse_mode="Markdown")

    elif query.data == "review_pending":
        if not is_admin(user):
            return
        if not pending_db:
            await query.message.reply_text("✅ কোন পেন্ডিং কাজ জমা নেই!")
            return

        task_id, tdata = list(pending_db.items())[0]
        p_uid = tdata["user_id"]
        p_user = users_db.get(p_uid, {})
        
        btn = [
            [
                InlineKeyboardButton("✅ Approve (কনফার্ম)", callback_data=f"app_{task_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{task_id}")
            ]
        ]
        await query.message.reply_text(
            f"📌 **কাজ রিভিউ:**\n"
            f"👤 ইউজার: {p_user.get('name', 'N/A')} (`{p_uid}`)\n"
            f"📝 কাজের ধরণ: {tdata.get('type_name')}\n"
            f"💵 রিওয়ার্ড: ৳{tdata.get('reward')}\n"
            f"🕒 সময়: {tdata.get('time')}",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode="Markdown"
        )

    elif query.data.startswith("app_"):
        if not is_admin(user):
            return
        task_id = query.data.replace("app_", "")
        if task_id in pending_db:
            tdata = pending_db.pop(task_id)
            save_data(PENDING_FILE, pending_db)
            
            p_uid = tdata["user_id"]
            reward = tdata["reward"]
            
            pu = get_user_data(p_uid)
            pu["balance"] += reward
            pu["completed_today"] += 1
            pu["total_completed"] += 1
            save_data(DB_FILE, users_db)

            try:
                await context.bot.send_message(
                    chat_id=int(p_uid),
                    text=f"🎉 **অভিনন্দন!**\n\nআপনার জমা দেওয়া কাজটি সফলভাবে **কনফার্ম** করা হয়েছে! আপনার ব্যালেন্সে **৳{reward}** যোগ হয়েছে।\n\n💰 **বর্তমান ব্যালেন্স:** ৳{pu['balance']:.1f}\n\nআরো কাজ করুন এবং বেশি বেশি ইনকাম করুন! 🚀",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

            await query.edit_message_text(f"✅ Task `{task_id}` Approved and Balance Added!")

    elif query.data.startswith("rej_"):
        if not is_admin(user):
            return
        task_id = query.data.replace("rej_", "")
        if task_id in pending_db:
            tdata = pending_db.pop(task_id)
            save_data(PENDING_FILE, pending_db)
            await query.edit_message_text(f"❌ Task `{task_id}` Rejected!")

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_str = str(update.effective_user.id)
    u = get_user_data(user_id_str, update.effective_user.first_name)
    
    if not update.message or not update.message.web_app_data:
        return

    try:
        data = json.loads(update.message.web_app_data.data)
    except Exception as e:
        logging.error(f"JSON Parse Error: {e}")
        return

    if data.get("status") == "success":
        if u["completed_today"] >= 10:
            await update.message.reply_text("❌ আপনার আজকের ১০টি কাজের লিমিট শেষ! আগামীকাল সকাল ৬:০০ AM-এ আবার নতুন কাজ পাবেন।")
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

        task_id = f"task_{int(datetime.now().timestamp())}_{user_id_str}"
        
        pending_db[task_id] = {
            "user_id": user_id_str,
            "task_type": task_type,
            "type_name": type_name,
            "reward": reward,
            "time": datetime.now().strftime("%I:%M %p")
        }
        save_data(PENDING_FILE, pending_db)

        await update.message.reply_text(
            f"📥 **কাজটি জমা নেওয়া হয়েছে!**\n\n"
            f"📌 ধরণ: {type_name}\n"
            f"⏳ রিভিউ অ্যাডমিন কনফার্ম করলেই আপনার অ্যাকাউন্টে **৳{reward}** জমা হবে।",
            parse_mode="Markdown"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_bkash'):
        num = update.message.text
        user_id_str = str(update.effective_user.id)
        u = get_user_data(user_id_str)
        current_bal = u['balance']
        
        u['balance'] = 0.0
        save_data(DB_FILE, users_db)
        
        context.user_data['waiting_bkash'] = False
        await update.message.reply_text(
            f"✅ ৳{current_bal:.1f} টাকা উইথড্র রিকোয়েস্ট গ্রহণ করা হয়েছে!\n"
            f"📱 বিকাশ নম্বর: {num}\n\n"
            f"২৪ ঘণ্টার মধ্যে আপনার বিকাশ নম্বরে টাকা পাঠিয়ে দেয়া হবে।"
        )

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
