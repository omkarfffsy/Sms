import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import requests
import time
import json
import os

# ---------------- CONFIG ----------------
BOT_TOKEN = "8301758540:AAEqnioHlG1wKqGSgm1J9D8q1cf8G_SAN2A"
API_KEY = "bb_2gAP3u87Vpk7GyrlpvCHaitEZtUws3mK"

QR_IMAGE_URL = "https://thumbs2.imgbox.com/d4/88/XLFtnVRd_t.png"

SMS_COST = 2   # 2 coins per SMS
SECRET_CODE = "/omkaradmin198"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

user_state = {}
user_balance = {}
payment_requests = {}
request_counter = 0
history = []
cooldown = {}
COOLDOWN_TIME = 10

# ---------------- ADMIN STORAGE ----------------
ADMIN_FILE = "admins.json"

def load_admins():
    if os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, "r") as f:
            return json.load(f)
    return []

def save_admins(data):
    with open(ADMIN_FILE, "w") as f:
        json.dump(data, f)

ADMIN_IDS = load_admins()

# ---------------- MENUS ----------------
def main_menu(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📤 Send SMS", "💰 Balance")
    markup.row("💳 Add Balance")
    if user_id in ADMIN_IDS:
        markup.row("👑 Admin Panel")
    return markup

def cancel_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("❌ Cancel")
    return markup

def payment_menu():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ I Paid", callback_data="paid"),
        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
    )
    return markup

# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_balance.setdefault(user_id, 0)
    if user_id in ADMIN_IDS:
        bot.send_message(user_id, "👑 <b>Welcome Admin</b>", reply_markup=main_menu(user_id))
    else:
        bot.send_message(user_id, "🤖 <b>Welcome User</b>", reply_markup=main_menu(user_id))

# ---------------- MAIN HANDLER ----------------
@bot.message_handler(func=lambda m: True)
def handle(message):
    global request_counter

    user_id = message.chat.id
    text = message.text.strip()

    # 🔐 ADMIN LOGIN
    if text == SECRET_CODE:
        if user_id not in ADMIN_IDS:
            ADMIN_IDS.append(user_id)
            save_admins(ADMIN_IDS)
        bot.send_message(user_id, "👑 <b>Admin Access Granted</b>", reply_markup=main_menu(user_id))
        return

    # ⏳ COOLDOWN
    if user_id in cooldown and time.time() - cooldown[user_id] < COOLDOWN_TIME:
        bot.send_message(user_id, "⏳ Please wait...")
        return

    # ---------------- MANUAL COIN APPROVAL ----------------
    if user_id in user_state:
        step = user_state[user_id].get("step")

        if step == "manual_approve":
            rid = user_state[user_id]["rid"]
            req = payment_requests.get(rid)
            if not req:
                bot.send_message(user_id, "❌ Request already processed")
                user_state.pop(user_id)
                return
            try:
                coins = int(text)
                uid = req["user_id"]
                user_balance[uid] = user_balance.get(uid,0) + coins

                history.append({
                    "type": "approved",
                    "name": req['name'],
                    "username": req['username'],
                    "user_id": uid,
                    "coins": coins,
                    "time": time.strftime("%d-%m-%Y %H:%M:%S")
                })

                bot.send_message(uid, f"✅ Payment Approved\n💰 +{coins} coins")
                bot.send_message(user_id, f"✅ Added {coins} coins to User {uid}")

                # Remove request from pending
                del payment_requests[rid]
                user_state.pop(user_id)
                return
            except:
                bot.send_message(user_id, "❌ Invalid number")
                return

        # ---------------- ADD / REMOVE COINS ----------------
        if step in ["add_user_amt", "remove_user_amt"]:
            try:
                target = user_state[user_id]["target"]
                amt = int(text)
                if step == "add_user_amt":
                    user_balance[target] = user_balance.get(target,0) + amt
                    history.append({
                        "type": "approved",
                        "name": "Manual",
                        "username": "admin",
                        "user_id": target,
                        "coins": amt,
                        "time": time.strftime("%d-%m-%Y %H:%M:%S")
                    })
                    bot.send_message(target, f"💰 +{amt} coins added")
                else:
                    user_balance[target] = max(0,user_balance.get(target,0)-amt)
                    bot.send_message(target, f"💰 -{amt} coins removed")
                bot.send_message(user_id, "✅ Done")
                user_state.pop(user_id)
                return
            except:
                bot.send_message(user_id,"❌ Invalid number")
                return

        # ---------------- PAYMENT REQUEST ----------------
        if step == "utr":
            if len(text) < 6:
                bot.send_message(user_id, "❌ Invalid UTR ID")
                return
            request_counter += 1
            payment_requests[request_counter] = {
                "user_id": user_id,
                "utr": text,
                "status": "PENDING",
                "name": message.from_user.first_name,
                "username": message.from_user.username or "none",
                "time": time.strftime("%d-%m-%Y %H:%M:%S")
            }
            for admin in ADMIN_IDS:
                bot.send_message(
                    admin,
                    f"🆕 <b>Payment Request</b>\n\n"
                    f"🆔 <code>{user_id}</code>\n"
                    f"👤 {message.from_user.first_name}\n"
                    f"📛 @{message.from_user.username}\n"
                    f"🧾 <code>{text}</code>\n"
                    f"🕒 {payment_requests[request_counter]['time']}\n"
                    f"📌 PENDING"
                )
            bot.send_message(user_id, "✅ Request sent to admin", reply_markup=main_menu(user_id))
            user_state.pop(user_id)
            return

    # ---------------- ADMIN PANEL ----------------
    if user_id in ADMIN_IDS:
        if text == "👑 Admin Panel":
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.row("📊 API Balance", "📋 Requests")
            markup.row("➕ Add Coins", "➖ Remove Coins")
            markup.row("📜 History", "❌ Close")
            bot.send_message(user_id, "👑 <b>Admin Panel</b>", reply_markup=markup)
            return
        if text == "📊 API Balance":
            try:
                res = requests.get(
                    "https://india-sms-290441563653.asia-south1.run.app/account-balance",
                    headers={"Authorization": f"Bearer {API_KEY}"}
                )
                data = res.json()
                bot.send_message(user_id, f"💰 <b>API Balance:</b> {data.get('balance', 'N/A')}")
            except:
                bot.send_message(user_id, "❌ Failed to fetch balance")
            return
        if text == "📋 Requests":
            if not payment_requests:
                bot.send_message(user_id, "📭 No pending requests")
            else:
                for rid, req in payment_requests.items():
                    markup = InlineKeyboardMarkup()
                    markup.add(
                        InlineKeyboardButton("✅ Approve (Enter Coins)", callback_data=f"approve_{rid}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{rid}")
                    )
                    bot.send_message(
                        user_id,
                        f"🆔 <code>{req['user_id']}</code>\n"
                        f"👤 {req['name']}\n"
                        f"📛 @{req['username']}\n"
                        f"🧾 <code>{req['utr']}</code>\n"
                        f"🕒 {req['time']}\n"
                        f"📌 {req['status']}",
                        reply_markup=markup
                    )
            return
        if text == "➕ Add Coins":
            user_state[user_id] = {"step":"add_user"}
            bot.send_message(user_id,"🔢 Enter User ID:")
            return
        if text == "➖ Remove Coins":
            user_state[user_id] = {"step":"remove_user"}
            bot.send_message(user_id,"🔢 Enter User ID:")
            return
        if text == "📜 History":
            if not history:
                bot.send_message(user_id, "📭 No history yet")
            else:
                msg = "📜 <b>Recent Activity (Last 10)</b>\n\n"
                for item in reversed(history[-10:]):
                    if item["type"] == "approved":
                        msg += f"✅ {item['coins']} coins → {item['user_id']} ({item['name']})\n🕒 {item['time']}\n\n"
                    else:
                        msg += f"❌ Rejected → {item['user_id']} ({item['name']})\n🕒 {item['time']}\n\n"
                bot.send_message(user_id,msg)
            return

    # ---------------- USER FEATURES ----------------
    if text == "💰 Balance":
        bot.send_message(user_id, f"💰 Your Balance: <b>{user_balance.get(user_id,0)} coins</b>")
        return
    if text == "💳 Add Balance":
        user_state[user_id] = {"step":"payment"}
        bot.send_photo(user_id, QR_IMAGE_URL,
                       caption="💳 <b>Add Balance</b>\n\n1️⃣ Scan QR\n2️⃣ Pay\n3️⃣ Click I Paid\n4️⃣ Send UTR")
        bot.send_message(user_id,"👇 After payment:", reply_markup=payment_menu())
        return
    if text == "📤 Send SMS":
        user_state[user_id] = {"step":"num"}
        bot.send_message(user_id,"📱 Enter number:", reply_markup=cancel_menu())
        return
    if text == "✅ I Paid":
        if user_state.get(user_id,{}).get("step") != "payment":
            bot.send_message(user_id,"⚠️ Click Add Balance first")
            return
        user_state[user_id]["step"] = "utr"
        bot.send_message(user_id,"📩 Send your UTR ID:", reply_markup=ReplyKeyboardRemove())
        return
    if text == "❌ Cancel" or text == "❌ Close":
        user_state.pop(user_id,None)
        bot.send_message(user_id,"❌ Cancelled", reply_markup=main_menu(user_id))
        return

    # ---------------- SMS SENDING ----------------
    if user_id in user_state:
        step = user_state[user_id].get("step")
        if step == "num":
            num = text.replace("+91","").replace("91","")
            if not num.isdigit() or len(num)!=10:
                bot.send_message(user_id,"❌ Invalid number")
                return
            user_state[user_id]["num"]=num
            user_state[user_id]["step"]="msg"
            bot.send_message(user_id,"✉️ Enter message:")
            return
        if step == "msg":
            if user_balance.get(user_id,0)<SMS_COST:
                bot.send_message(user_id,"❌ Not enough balance", reply_markup=main_menu(user_id))
                user_state.pop(user_id)
                return
            payload={"apiKey":API_KEY,"phone":user_state[user_id]["num"],"message":text}
            try:
                r=requests.post("https://india-sms-290441563653.asia-south1.run.app/send-sms",json=payload)
                if "success" in r.text.lower():
                    user_balance[user_id]-=SMS_COST
                    bot.send_message(user_id,"✅ SMS Sent")
                else:
                    bot.send_message(user_id,"❌ Failed")
            except Exception as e:
                bot.send_message(user_id,str(e))
            user_state.pop(user_id)
            cooldown[user_id]=time.time()
            bot.send_message(user_id,"✔️ Done",reply_markup=main_menu(user_id))
            return

# ---------------- CALLBACK ----------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id=call.from_user.id
    data=call.data

    if data=="paid":
        if user_state.get(user_id,{}).get("step")!="payment":
            bot.answer_callback_query(call.id,"⚠️ Click Add Balance first")
            return
        user_state[user_id]["step"]="utr"
        bot.edit_message_reply_markup(user_id,call.message.message_id,reply_markup=None)
        bot.send_message(user_id,"📩 Send your UTR ID:",reply_markup=ReplyKeyboardRemove())
        bot.answer_callback_query(call.id,"Proceed to send UTR")
        return
    elif data=="cancel":
        user_state.pop(user_id,None)
        bot.edit_message_reply_markup(user_id,call.message.message_id,reply_markup=None)
        bot.send_message(user_id,"❌ Payment cancelled",reply_markup=main_menu(user_id))
        bot.answer_callback_query(call.id,"Cancelled")
        return
    elif data.startswith("approve_"):
        rid=int(data.split("_")[1])
        req=payment_requests.get(rid)
        if req:
            user_state[user_id]={"step":"manual_approve","rid":rid}
            bot.send_message(user_id,f"🔢 Enter coins for User {req['user_id']}:")
            bot.answer_callback_query(call.id,"Enter coins manually")
    elif data.startswith("reject_"):
        rid=int(data.split("_")[1])
        req=payment_requests.get(rid)
        if req:
            uid=req["user_id"]
            history.append({
                "type":"rejected",
                "name":req['name'],
                "username":req['username'],
                "user_id":uid,
                "time":time.strftime("%d-%m-%Y %H:%M:%S")
            })
            bot.send_message(uid,"❌ Payment Rejected")
            del payment_requests[rid]
            bot.edit_message_text("❌ REJECTED",call.message.chat.id,call.message.message_id)

# ---------------- RUN ----------------
print("🚀 Bot Running...")
while True:
    try:
        bot.infinity_polling()
    except Exception as e:
        print(e)
        time.sleep(3)