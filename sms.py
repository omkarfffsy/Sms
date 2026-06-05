import telebot
import requests
import sqlite3
import threading
import time
import logging
import re
from io import BytesIO
from datetime import datetime
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# --- NEW IMPORTS FOR CLOUD STORAGE ---
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("WARNING: firebase-admin module not found. Run: pip install firebase-admin")

# =================================================================
# 1. SYSTEM CONFIGURATION & SECURITY
# =================================================================
BOT_TOKEN = "8286825977:AAFMeepQ_vHLGOlbydShBmRsrJnhWsqbtak"
ADMIN_IDS = [7624898265]  # Omkar ID (Master Admin)
COUNTRY_CODE = "22"
DB_NAME = "userdata.db"
APP_ID = "sms_monolith_live" 

QUICK_SERVICES = {
    "google": "🌐 Google",
    "whatsapp": "🟢 WhatsApp",
    "telegram": "✈️ Telegram",
    "zomato": "🍔 Zomato",
    "bigbasket": "🛒 Big Basket",   
    "jiomart": "🛍️ JioMart"      
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s')
logger = logging.getLogger("SMS_MONOLITH")

def format_date(date_str):
    if not date_str: return "Unknown Date"
    try:
        clean_str = str(date_str).split('.')[0]
        dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y, %I:%M %p")
    except:
        return str(date_str)[:16]

def strip_html(text):
    if not text: return ""
    return re.sub('<[^<]+>', '', text)

# =================================================================
# 2. HIGH PERFORMANCE DATABASE (WAL MODE)
# =================================================================
class DatabaseManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA temp_store = MEMORY")
        self._bootstrap()

    def _bootstrap(self):
        with self.lock:
            self.conn.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0.0, joined_at DATETIME
                );
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY, user_id INTEGER, phone TEXT, cost REAL, 
                    status TEXT, otp TEXT, created_at DATETIME
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    trx_id TEXT PRIMARY KEY, user_id INTEGER, amount REAL, status TEXT, timestamp DATETIME
                );
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE IF NOT EXISTS api_services (
                    code TEXT PRIMARY KEY, name TEXT, provider_price REAL, custom_price REAL DEFAULT NULL
                );
                CREATE TABLE IF NOT EXISTS live_servers (
                    code TEXT, server_id TEXT, provider_price REAL,
                    PRIMARY KEY(code, server_id)
                );
                CREATE TABLE IF NOT EXISTS force_sub (
                    channel_id TEXT PRIMARY KEY, channel_url TEXT
                );
                CREATE TABLE IF NOT EXISTS spam_tracker (
                    user_id INTEGER PRIMARY KEY, last_time REAL, strikes INTEGER, 
                    penalty_until REAL, req_count INTEGER, window_start REAL
                );
                CREATE TABLE IF NOT EXISTS tracked_menus (
                    chat_id INTEGER, menu_type TEXT, message_id INTEGER,
                    PRIMARY KEY(chat_id, menu_type)
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    description TEXT, reward REAL, status TEXT DEFAULT 'AVAILABLE', 
                    locked_by INTEGER DEFAULT NULL, locked_until REAL DEFAULT 0, created_at DATETIME,
                    msg_chat_id INTEGER, msg_id INTEGER
                );
                CREATE TABLE IF NOT EXISTS task_proofs (
                    proof_id INTEGER PRIMARY KEY AUTOINCREMENT, task_id INTEGER, user_id INTEGER,
                    proof_data TEXT, status TEXT DEFAULT 'PENDING'
                );
                CREATE TABLE IF NOT EXISTS withdraw_requests (
                    w_id TEXT PRIMARY KEY, user_id INTEGER, amount REAL, method TEXT, 
                    upi_id TEXT, status TEXT DEFAULT 'PENDING', created_at DATETIME
                );
            ''')
            
            try: self.conn.execute("ALTER TABLE orders ADD COLUMN service_code TEXT")
            except: pass 
            try: self.conn.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
            except: pass
            try: self.conn.execute("ALTER TABLE users ADD COLUMN task_balance REAL DEFAULT 0.0")
            except: pass
                
            self.conn.execute("INSERT OR IGNORE INTO settings VALUES ('global_margin', '5.0')")
            self.conn.execute("INSERT OR IGNORE INTO settings VALUES ('upi_id', 'admin@ybl')")
            self.conn.execute("INSERT OR IGNORE INTO settings VALUES ('api_base_url', 'https://meowsms.shop/stubs/handler_api.php')")
            self.conn.execute("INSERT OR IGNORE INTO settings VALUES ('api_key', 's8HFzuPl74cIjQjAWl9pfgVhUMpfK5Sw')")
            self.conn.execute("INSERT OR IGNORE INTO settings VALUES ('maintenance_mode', '0')")
            self.conn.execute(f"INSERT OR IGNORE INTO settings VALUES ('admin_ids', '{ADMIN_IDS[0]}')")
            self.conn.execute("INSERT OR IGNORE INTO settings VALUES ('bp_merchant_id', '')")
            self.conn.execute("INSERT OR IGNORE INTO settings VALUES ('bp_token', '')")
            self.conn.commit()

    def execute(self, sql: str, params: tuple = ()):
        with self.lock:
            try:
                self.conn.execute(sql, params)
                self.conn.commit()
                return True
            except Exception as e:
                logger.error(f"DB EXECUTE ERROR: {e}")
                return False

    def query(self, sql: str, params: tuple = ()):
        with self.lock:
            return self.conn.execute(sql, params).fetchall()

    def update_balance(self, user_id: int, amount: float, wallet_type="main"):
        with self.lock:
            try:
                if wallet_type == "main":
                    self.conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
                else:
                    self.conn.execute("UPDATE users SET task_balance = task_balance + ? WHERE user_id = ?", (amount, user_id))
                self.conn.commit()
                return True
            except:
                self.conn.rollback()
                return False

    def get_setting(self, key, default=""):
        res = self.query("SELECT value FROM settings WHERE key = ?", (key,))
        return res[0][0] if res else default

db = DatabaseManager()

# =================================================================
# 2.5 ADVANCED CLOUD STORAGE ENGINE (FIRESTORE)
# =================================================================
cloud_db = None
if FIREBASE_AVAILABLE:
    try:
        cred = credentials.Certificate("firebase-adminsdk.json")
        firebase_admin.initialize_app(cred)
        cloud_db = firestore.client()
        logger.info("☁️ Cloud Storage Active: Connected to Firestore.")
    except Exception as e:
        logger.warning(f"☁️ Cloud Storage Offline: {e}")

class CloudSyncEngine:
    @staticmethod
    def sync_all_data():
        if not cloud_db: return
        while True:
            try:
                base_ref = cloud_db.collection('artifacts').document(APP_ID).collection('public').document('data')
                
                users = db.query("SELECT user_id, username, balance, joined_at, is_banned, task_balance FROM users")
                for u in users:
                    u_data = {"user_id": u[0], "username": u[1], "balance": u[2], "joined_at": str(u[3]), "is_banned": u[4], "task_balance": u[5]}
                    base_ref.collection('users').document(str(u[0])).set(u_data, merge=True)
                
                orders = db.query("SELECT order_id, user_id, phone, cost, status, service_code, created_at FROM orders WHERE status = 'SUCCESS' OR status = 'WAITING'")
                for o in orders:
                    o_data = {"order_id": o[0], "user_id": o[1], "phone": o[2], "cost": o[3], "status": o[4], "service_code": o[5], "created_at": str(o[6])}
                    base_ref.collection('orders').document(str(o[0])).set(o_data, merge=True)

                trxs = db.query("SELECT trx_id, user_id, amount, status FROM transactions")
                for t in trxs:
                    t_data = {"trx_id": t[0], "user_id": t[1], "amount": t[2], "status": t[3]}
                    base_ref.collection('transactions').document(str(t[0])).set(t_data, merge=True)

            except Exception as e:
                pass
            time.sleep(600)

    @staticmethod
    def restore_from_cloud():
        if not cloud_db: return False, "Firebase not connected."
        try:
            base_ref = cloud_db.collection('artifacts').document(APP_ID).collection('public').document('data')
            
            users = base_ref.collection('users').stream()
            for doc in users:
                d = doc.to_dict()
                db.execute("REPLACE INTO users (user_id, username, balance, joined_at, is_banned, task_balance) VALUES (?, ?, ?, ?, ?, ?)", 
                           (d.get('user_id'), d.get('username'), d.get('balance', 0.0), d.get('joined_at'), d.get('is_banned', 0), d.get('task_balance', 0.0)))
            
            orders = base_ref.collection('orders').stream()
            for doc in orders:
                d = doc.to_dict()
                db.execute("REPLACE INTO orders (order_id, user_id, phone, cost, status, service_code, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                           (d.get('order_id'), d.get('user_id'), d.get('phone'), d.get('cost'), d.get('status'), d.get('service_code'), d.get('created_at')))

            trxs = base_ref.collection('transactions').stream()
            for doc in trxs:
                d = doc.to_dict()
                db.execute("REPLACE INTO transactions (trx_id, user_id, amount, status) VALUES (?, ?, ?, ?)", 
                           (d.get('trx_id'), d.get('user_id'), d.get('amount'), d.get('status')))
            
            return True, "Data successfully restored from Cloud!"
        except Exception as e:
            return False, str(e)


if FIREBASE_AVAILABLE:
    threading.Thread(target=CloudSyncEngine.sync_all_data, daemon=True, name="CloudSyncThread").start()

def is_admin(user_id): 
    try:
        admin_str = db.get_setting("admin_ids", str(ADMIN_IDS[0]))
        admin_list = [int(x.strip()) for x in admin_str.split(",") if x.strip()]
        return user_id in admin_list or user_id in ADMIN_IDS
    except:
        return user_id in ADMIN_IDS

def get_display_price(code):
    c_data = db.query("SELECT custom_price FROM api_services WHERE code = ?", (code,))
    if c_data and c_data[0][0] is not None: return float(c_data[0][0])
    l_data = db.query("SELECT MIN(provider_price) FROM live_servers WHERE code = ?", (code,))
    prov_price = l_data[0][0] if l_data and l_data[0][0] is not None else 10.0
    return prov_price + float(db.get_setting('global_margin', '5.0'))

def calculate_price_for_user(code, provider_price):
    c_data = db.query("SELECT custom_price FROM api_services WHERE code = ?", (code,))
    if c_data and c_data[0][0] is not None: return float(c_data[0][0])
    return float(provider_price) + float(db.get_setting('global_margin', '5.0'))

# =================================================================
# 3. BACKGROUND SYNC & TASK REAPER
# =================================================================
def auto_background_engine():
    while True:
        try:
            api_url = db.get_setting('api_base_url')
            api_key = db.get_setting('api_key')
            s_req = requests.get(api_url, params={"api_key": api_key, "action": "getServers"}, timeout=15)
            active_servers = []
            if s_req.status_code == 200:
                try:
                    for s_id, info in s_req.json().items():
                        if info.get("countryCode") == COUNTRY_CODE: active_servers.append(s_id)
                except: pass
            
            if not active_servers: active_servers = [""] 
            temp_live = []
            for srv in active_servers:
                params = {"api_key": api_key, "action": "getServices", "country": COUNTRY_CODE}
                if srv: params["server"] = srv
                r = requests.get(api_url, params=params, timeout=15)
                if r.status_code == 200:
                    for code, info in r.json().items():
                        name, price = info.get('name', 'Unknown'), float(info.get('price', 0.0))
                        db.execute("INSERT OR IGNORE INTO api_services (code, name, provider_price) VALUES (?, ?, ?)", (code, name, price))
                        temp_live.append((code, srv, price))
            if temp_live:
                db.execute("DELETE FROM live_servers")
                for item in temp_live:
                    db.execute("INSERT INTO live_servers (code, server_id, provider_price) VALUES (?, ?, ?)", item)
            
            waiting_orders = db.query("SELECT order_id, user_id, cost, created_at FROM orders WHERE status = 'WAITING'")
            for o_id, u_id, cost, date_str in waiting_orders:
                try:
                    clean_str = str(date_str).split('.')[0]
                    dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
                    if (datetime.now() - dt).total_seconds() > 1500:
                        db.update_balance(u_id, cost)
                        db.execute("UPDATE orders SET status = 'TIMEOUT' WHERE order_id = ?", (o_id,))
                except: pass
                
            db.execute("DELETE FROM spam_tracker WHERE last_time < ?", (time.time() - 3600,))
            db.execute("UPDATE tasks SET status = 'AVAILABLE', locked_by = NULL, locked_until = 0 WHERE status = 'LOCKED' AND locked_until < ?", (time.time(),))
                
        except Exception: pass
        time.sleep(2400)

threading.Thread(target=auto_background_engine, daemon=True).start()

# =================================================================
# 4. BOT CORE 
# =================================================================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

def check_spam(user_id):
    if is_admin(user_id): return False
    user_info = db.query("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    if user_info and user_info[0][0] == 1: return "BANNED"
    now = time.time()
    record = db.query("SELECT last_time, strikes, penalty_until, req_count, window_start FROM spam_tracker WHERE user_id = ?", (user_id,))
    if record: last_time, strikes, penalty_until, req_count, window_start = record[0]
    else: last_time, strikes, penalty_until, req_count, window_start = 0.0, 0, 0.0, 0, now
    if now < penalty_until: return "PENALTY"
    if now - window_start > 10.0: req_count, window_start = 0, now
    req_count += 1
    time_diff = now - last_time
    if time_diff < 0.5 or req_count > 8: strikes += 1
    elif time_diff > 5.0: strikes = max(0, strikes - 1)
    if strikes >= 3:
        penalty_until = now + 10.0 
        strikes, req_count = 0, 0
        db.execute("REPLACE INTO spam_tracker (user_id, last_time, strikes, penalty_until, req_count, window_start) VALUES (?, ?, ?, ?, ?, ?)", (user_id, now, strikes, penalty_until, req_count, window_start))
        return "PENALTY"
    db.execute("REPLACE INTO spam_tracker (user_id, last_time, strikes, penalty_until, req_count, window_start) VALUES (?, ?, ?, ?, ?, ?)", (user_id, now, strikes, penalty_until, req_count, window_start))
    return False

def track_and_delete_old(chat_id, new_msg_id, menu_type):
    old = db.query("SELECT message_id FROM tracked_menus WHERE chat_id = ? AND menu_type = ?", (chat_id, menu_type))
    if old:
        try: bot.delete_message(chat_id, old[0][0])
        except: pass
    db.execute("REPLACE INTO tracked_menus (chat_id, menu_type, message_id) VALUES (?, ?, ?)", (chat_id, menu_type, new_msg_id))

def safe_delete_user_command(message):
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass

def stealth_admin_logger(user_id, service, raw_error):
    try:
        admin_str = db.get_setting("admin_ids", str(ADMIN_IDS[0]))
        admin_list = [int(x.strip()) for x in admin_str.split(",") if x.strip()]
        for adm in admin_list:
            try: bot.send_message(adm, f"⚠️ <b>SILENT ALERT</b>\n👤 User: <code>{user_id}</code>\n🛒 App: {service}\n❌ Err: <code>{raw_error}</code>")
            except: pass
    except: pass

# =================================================================
# 5. FORCE SUBSCRIBE MIDDLEWARE
# =================================================================
def check_fsub(user_id):
    channels = db.query("SELECT channel_id, channel_url FROM force_sub")
    if not channels: return True 
    markup, not_joined = InlineKeyboardMarkup(row_width=1), False
    for ch_id, url in channels:
        try:
            if bot.get_chat_member(ch_id, user_id).status in ['left', 'kicked']:
                markup.add(InlineKeyboardButton(f"📢 Join Channel", url=url))
                not_joined = True
        except: pass
    if not_joined:
        markup.add(InlineKeyboardButton("✅ I have joined", callback_data="check_join_status"))
        return markup
    return True

@bot.callback_query_handler(func=lambda call: call.data == "check_join_status")
def verify_join_click(call):
    spam_status = check_spam(call.from_user.id)
    if spam_status == "BANNED": return bot.answer_callback_query(call.id, "🚫 You are banned.", show_alert=True)
    if spam_status == "PENALTY": return bot.answer_callback_query(call.id, "⚠️ Too fast! Wait 10s.", show_alert=True)
    if check_fsub(call.from_user.id) is True:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ Welcome! You have full access.", reply_markup=UIFactory.reply_main_menu())
    else: bot.answer_callback_query(call.id, "❌ You haven't joined all channels yet!", show_alert=True)

# =================================================================
# 6. INTERFACE FACTORY (FULLY UPDATED WITH DIAGNOSTICS)
# =================================================================
class UIFactory:
    @staticmethod
    def reply_main_menu():
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(KeyboardButton("🛒 Buy Number"), KeyboardButton("👤 My Wallet"))
        markup.add(KeyboardButton("💰 Deposit Funds"), KeyboardButton("💼 Earn Money"))
        markup.add(KeyboardButton("📜 Order History"))
        return markup

    @staticmethod
    def hybrid_service_menu(user_id):
        markup = InlineKeyboardMarkup(row_width=2)
        recents = db.query("SELECT DISTINCT service_code FROM orders WHERE user_id = ? AND service_code IS NOT NULL ORDER BY created_at DESC LIMIT 4", (user_id,))
        recent_codes = [r[0] for r in recents] if recents else []
        display_codes = []
        for code in recent_codes:
            if code not in display_codes: display_codes.append(code)
        for code in QUICK_SERVICES.keys():
            if code not in display_codes: display_codes.append(code)
        display_codes = display_codes[:8] 
        buttons = []
        for code in display_codes:
            name = QUICK_SERVICES.get(code)
            if not name:
                n_data = db.query("SELECT name FROM api_services WHERE code = ?", (code,))
                name = n_data[0][0] if n_data else str(code).capitalize()
            prefix = "⏱ " if code in recent_codes and code not in QUICK_SERVICES else ""
            price = get_display_price(code)
            buttons.append(InlineKeyboardButton(f"{prefix}{name} - ₹{price:.2f}", callback_data=f"buy_srv_{code}"))
        markup.add(*buttons)
        markup.add(InlineKeyboardButton("🔍 Search 300+ Services", callback_data="action_search_app"))
        markup.add(InlineKeyboardButton("❌ Close Menu", callback_data="ui_close"))
        return markup

    @staticmethod
    def admin_panel():
        markup = InlineKeyboardMarkup()
        # Row 1
        markup.row(InlineKeyboardButton("📊 Test BP Connection", callback_data="adm_test_bp"), InlineKeyboardButton("☁️ Restore DB", callback_data="adm_restore_cloud"))
        # Row 2
        markup.row(InlineKeyboardButton("👥 Manage Users", callback_data="adm_users_list"), InlineKeyboardButton("🕵️ Track User", callback_data="adm_user_history"))
        # Row 3
        markup.row(InlineKeyboardButton("💰 Add Funds", callback_data="adm_add_bal"), InlineKeyboardButton("➖ Deduct Funds", callback_data="adm_sub_bal"))
        # Row 4
        markup.row(InlineKeyboardButton("📋 Task System", callback_data="adm_tasks"), InlineKeyboardButton("🏦 Withdrawals", callback_data="adm_withdrawals"))
        # Row 5
        markup.row(InlineKeyboardButton("🚫 Ban Control", callback_data="adm_ban_user"), InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"))
        # Row 6
        markup.row(InlineKeyboardButton("👑 Admins", callback_data="adm_manage_admins"), InlineKeyboardButton("🚧 Maintenance", callback_data="adm_toggle_maint"))
        # Row 7
        markup.row(InlineKeyboardButton("🌐 API Server", callback_data="adm_set_server"), InlineKeyboardButton("🔑 API Key", callback_data="adm_set_apikey"))
        # Row 8
        markup.row(InlineKeyboardButton("📈 Margin", callback_data="adm_set_margin"), InlineKeyboardButton("💎 Custom Price", callback_data="adm_override_price"))
        # Row 9
        markup.row(InlineKeyboardButton("⌛ Pending Trx", callback_data="adm_list_trx"), InlineKeyboardButton("🔍 Find Order", callback_data="adm_find_order"))
        # Row 10
        markup.row(InlineKeyboardButton("🔍 Fetch Apps", callback_data="adm_fetch_api"), InlineKeyboardButton("📢 Force Sub", callback_data="adm_manage_fsub"))
        # Row 11
        markup.row(InlineKeyboardButton("🏦 Set UPI QR", callback_data="adm_set_upi"), InlineKeyboardButton("❌ Close Panel", callback_data="ui_close"))
        # Row 12 - BharatPe Settings
        markup.row(InlineKeyboardButton("🔑 BP MID", callback_data="adm_set_bp_mid"), InlineKeyboardButton("🔑 BP Token", callback_data="adm_set_bp_token"))
        return markup

    @staticmethod
    def back_button(target):
        return InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Back", callback_data=target))

    @staticmethod
    def trx_approval(trx_id):
        return InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Approve", callback_data=f"approve_pay_{trx_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_pay_{trx_id}"))

# =================================================================
# 7. SMS PROVIDER CLIENT 
# =================================================================
class SMSClient:
    @staticmethod
    def request_number(service_code, server_id=None):
        api_url = db.get_setting('api_base_url')
        api_key = db.get_setting('api_key')
        params = {"api_key": api_key, "action": "getNumber", "service": service_code, "country": COUNTRY_CODE, "operator": "any"}
        if server_id: params["server"] = server_id
        try:
            r = requests.get(api_url, params=params, timeout=10)
            if r.status_code == 429: return {"success": False, "error": "RATE_LIMIT_EXCEEDED"}
            if r.text.startswith("ACCESS_NUMBER:"): return {"success": True, "id": r.text.split(":")[1], "phone": r.text.split(":")[2]}
            return {"success": False, "error": r.text.strip()}
        except: return {"success": False, "error": "NETWORK_TIMEOUT"}

    @staticmethod
    def get_status(order_id):
        try: return requests.get(db.get_setting('api_base_url'), params={"api_key": db.get_setting('api_key'), "action": "getStatus", "id": order_id}, timeout=10).text
        except: return "STATUS_WAIT_CODE"

    @staticmethod
    def set_status(order_id, status_code):
        try: return requests.get(db.get_setting('api_base_url'), params={"api_key": db.get_setting('api_key'), "action": "setStatus", "id": order_id, "status": status_code}, timeout=10).text
        except: return "ERROR"

sms = SMSClient()

# =================================================================
# 8. SEARCH & BUYING LOGIC
# =================================================================
@bot.message_handler(func=lambda message: message.text == "🛒 Buy Number")
def show_service_menu(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    safe_delete_user_command(message) 
    u_id = message.from_user.id
    if check_spam(u_id) == "BANNED": return bot.send_message(u_id, "🚫 <b>Access Denied:</b> You have been banned.")
    if check_spam(u_id): return
    if db.get_setting("maintenance_mode", "0") == "1":
        return bot.send_message(message.chat.id, "🚧 <b>Bot is under maintenance.</b>\nBuying new numbers is temporarily paused.")
    fsub = check_fsub(u_id)
    if fsub is not True: return bot.send_message(u_id, "🛑 <b>Access Denied:</b> Join our channels first.", reply_markup=fsub)
    msg = bot.send_message(message.chat.id, "🛒 <b>Select a Service or Search:</b>", reply_markup=UIFactory.hybrid_service_menu(u_id))
    track_and_delete_old(message.chat.id, msg.message_id, 'user_shop')

@bot.callback_query_handler(func=lambda call: call.data == "action_search_app")
def trigger_search_engine(call):
    if check_spam(call.from_user.id) == "BANNED": return bot.answer_callback_query(call.id, "🚫 Banned", show_alert=True)
    if check_spam(call.from_user.id): return
    bot.edit_message_text("🔍 <b>Search Engine:</b>\nType the name of the app (e.g. <code>Amazon</code>).\n\n<i>Type 'cancel' to abort.</i>", call.message.chat.id, call.message.message_id)
    bot.register_next_step_handler(call.message, execute_live_search, call.message.message_id)

def execute_live_search(message, menu_id):
    safe_delete_user_command(message) 
    query = message.text.strip().lower() if message.text else ""
    if len(query) > 30: query = query[:30]
    
    if query == 'cancel': 
        return bot.edit_message_text("🛒 <b>Select a Quick Service or Search:</b>", message.chat.id, menu_id, reply_markup=UIFactory.hybrid_service_menu(message.from_user.id))
    
    query_clean = query.replace("'", "").replace("s", "").strip() 
    results = db.query("SELECT code, name FROM api_services WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ? LIMIT 14", (f"%{query}%", f"%{query_clean}%"))
    
    unique_res = {}
    for c, n in (results or []):
        if c not in unique_res: unique_res[c] = n
        
    if not unique_res: 
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("🔄 Try Another Search", callback_data="action_search_app"))
        markup.add(InlineKeyboardButton("⬅️ Back to Main Shop", callback_data="back_to_shop"))
        return bot.edit_message_text(f"❌ No apps found for '<b>{query}</b>'.\n\n<i>Tip: Try keeping it short and sweet—like 'domino' instead of 'dominos'.</i>", message.chat.id, menu_id, reply_markup=markup)
        
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = [InlineKeyboardButton(f"{name} - ₹{get_display_price(code):.2f}", callback_data=f"buy_srv_{code}") for code, name in unique_res.items()]
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("⬅️ Back to Main Shop", callback_data="back_to_shop"))
    bot.edit_message_text(f"🔍 <b>Search Results for '{query}':</b>", message.chat.id, menu_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_shop")
def back_to_main_shop(call):
    if check_spam(call.from_user.id): return
    bot.edit_message_text("🛒 <b>Select a Quick Service or Search:</b>", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.hybrid_service_menu(call.from_user.id))

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_srv_"))
def process_service_click(call):
    u_id = call.from_user.id
    if check_spam(u_id) == "BANNED": return bot.answer_callback_query(call.id, "🚫 Banned", show_alert=True)
    if check_spam(u_id): return
    code = call.data.split("buy_srv_")[1]
    servers = db.query("SELECT server_id, provider_price FROM live_servers WHERE code = ?", (code,))
    if not servers: servers = [("", 10.0)]
    if len(servers) > 1:
        markup = InlineKeyboardMarkup(row_width=1)
        name_data = db.query("SELECT name FROM api_services WHERE code = ?", (code,))
        name = name_data[0][0] if name_data else str(code).capitalize()
        for srv_id, prov_price in servers:
            final_price = calculate_price_for_user(code, prov_price)
            srv_label = srv_id.upper() if srv_id else "Main"
            markup.add(InlineKeyboardButton(f"Server {srv_label} (₹{final_price:.2f})", callback_data=f"runbuy_{code}_{srv_id}"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="back_to_shop"))
        bot.edit_message_text(f"🌐 <b>Multiple Servers Found for {name}</b>\n\nChoose a server below.", call.message.chat.id, call.message.message_id, reply_markup=markup)
    else:
        srv_id, prov_price = servers[0]
        execute_final_buy(call, code, srv_id, prov_price)

@bot.callback_query_handler(func=lambda call: call.data.startswith("runbuy_"))
def handle_server_selection(call):
    if check_spam(call.from_user.id): return
    parts = call.data.split("_")
    code = parts[1]
    srv_id = parts[2] if len(parts) > 2 else ""
    p_data = db.query("SELECT provider_price FROM live_servers WHERE code = ? AND server_id = ?", (code, srv_id))
    prov_price = p_data[0][0] if p_data else 10.0
    execute_final_buy(call, code, srv_id, prov_price)

def execute_final_buy(call, code, server_id, prov_price):
    u_id = call.from_user.id
    balance = db.query("SELECT balance FROM users WHERE user_id = ?", (u_id,))[0][0]
    price = calculate_price_for_user(code, prov_price)
    if balance < price: return bot.answer_callback_query(call.id, "❌ Insufficient Balance! Deposit Funds.", show_alert=True)

    bot.delete_message(call.message.chat.id, call.message.message_id)
    msg = bot.send_message(call.message.chat.id, f"💰 <b>Cost:</b> ₹{price:.2f}\n📡 <b>Connecting to Server...</b>")
    db.update_balance(u_id, -price, "main") 
    result = sms.request_number(code, server_id)
    
    if not result["success"]:
        db.update_balance(u_id, price, "main") 
        stealth_admin_logger(u_id, f"{code} ({server_id})", result['error'])
        try: bot.edit_message_text(f"❌ <b>Error:</b> Server is currently busy.\nBalance Refunded.", msg.chat.id, msg.message_id, reply_markup=UIFactory.back_button("back_to_shop"))
        except: pass
        return

    o_id, phone = result["id"], result["phone"]
    db.execute("INSERT INTO orders (order_id, user_id, phone, cost, status, otp, created_at, service_code) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (o_id, u_id, phone, price, "WAITING", "", datetime.now(), code))
    threading.Thread(target=otp_watcher, args=(msg.chat.id, msg.message_id, o_id, u_id, price, phone)).start()

# =================================================================
# 9. HIGH-SPEED OTP WATCHER
# =================================================================
def otp_watcher(chat_id, message_id, o_id, u_id, price, phone):
    start_time, max_time, cancel_lock_time = time.time(), 1200, 130
    otps_received = []
    last_api_check = 0
    last_ui_update = 0  
    status = "STATUS_WAIT_CODE"
    last_sent_text = ""

    while time.time() - start_time < max_time:
        order_db = db.query("SELECT status FROM orders WHERE order_id = ?", (o_id,))
        if not order_db or order_db[0][0] == 'CANCELLED': return
            
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(max_time - elapsed, 60)
        timer_str = f"{mins:02d}:{secs:02d}"
        new_otp_found = False
        
        if time.time() - last_api_check >= 6:
            status = sms.get_status(o_id)
            last_api_check = time.time()
            if "STATUS_OK" in status:
                raw_otp = status.split(":", 1)[1]
                current_otp = raw_otp.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
                
                if current_otp not in otps_received:
                    otps_received.append(current_otp)
                    db.execute("UPDATE orders SET status = 'SUCCESS', otp = ? WHERE order_id = ?", (",".join(otps_received), o_id))
                    new_otp_found = True  
            elif "STATUS_CANCEL" in status:
                if not otps_received:
                    db.update_balance(u_id, price, "main")
                    db.execute("UPDATE orders SET status = 'CANCELLED' WHERE order_id = ?", (o_id,))
                    try: bot.delete_message(chat_id, message_id)
                    except: pass
                return
        
        if time.time() - last_ui_update >= 10 or new_otp_found:
            last_ui_update = time.time()
            if otps_received:
                if "STATUS_WAIT" in status:
                    markup = InlineKeyboardMarkup()
                    text = f"⏳ <b>Waiting for Next OTP...</b>\n\n📱 Number: <code>+{phone}</code>\n\n"
                    for i, code in enumerate(otps_received): text += f"✅ OTP {i+1}: <code>{code}</code>\n"
                    text += f"\n⏱ Live Timer: {timer_str}"
                else:
                    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔄 Request Next OTP", callback_data=f"next_otp_{o_id}"))
                    text = f"🎉 <b>OTP RECEIVED!</b>\n\n📱 Number: <code>+{phone}</code>\n💰 Cost: ₹{price}\n\n"
                    for i, code in enumerate(otps_received): text += f"✉️ <b>OTP {i+1}:</b> <code>{code}</code>\n"
                    text += f"\n<i>Live for {timer_str} more.</i>"
                if text != last_sent_text:
                    try: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup); last_sent_text = text
                    except: pass
            elif "STATUS_WAIT_CODE" in status:
                markup = InlineKeyboardMarkup()
                if elapsed >= cancel_lock_time: markup.add(InlineKeyboardButton("❌ Cancel Number", callback_data=f"cancel_ord_{o_id}"))
                else: 
                    lock_remaining = int(cancel_lock_time - elapsed)
                    markup.add(InlineKeyboardButton(f"⏳ Cancel in {lock_remaining}s", callback_data="ignore"))
                text = f"⏳ <b>Waiting for OTP...</b>\n\n📱 Number: <code>+{phone}</code>\n💰 Cost: ₹{price}\n\n⏱ Live Timer: <b>{timer_str}</b>"
                if text != last_sent_text:
                    try: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup); last_sent_text = text
                    except: pass
        time.sleep(3) 
        
    if not otps_received:
        db.update_balance(u_id, price, "main")
        sms.set_status(o_id, "8")
        db.execute("UPDATE orders SET status = 'TIMEOUT' WHERE order_id = ?", (o_id,))
        try: bot.delete_message(chat_id, message_id)
        except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_ord_"))
def cancel_order_manually(call):
    if check_spam(call.fromuser.id): return
    bot.answer_callback_query(call.id, "Cancelling order...", show_alert=False)
    o_id = call.data.split("_")[2]
    order = db.query("SELECT cost, status FROM orders WHERE order_id = ?", (o_id,))
    if not order or order[0][1] != 'WAITING': return bot.answer_callback_query(call.id, "Already finished.", show_alert=True)
    price, u_id = order[0][0], call.from_user.id
    sms.set_status(o_id, "8")
    db.update_balance(u_id, price, "main")
    db.execute("UPDATE orders SET status = 'CANCELLED' WHERE order_id = ?", (o_id,))
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("next_otp_"))
def request_next_otp(call):
    if check_spam(call.from_user.id): return bot.answer_callback_query(call.id, "Blocked.")
    sms.set_status(call.data.split("_")[2], "3")
    bot.answer_callback_query(call.id, "Requested! Watch the live timer.", show_alert=True)

# =================================================================
# 10. TASK & EARN SYSTEM 
# =================================================================
@bot.message_handler(func=lambda message: message.text == "💼 Earn Money")
def show_task_menu(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    safe_delete_user_command(message) 
    u_id = message.from_user.id
    if check_spam(u_id): return
    
    tasks = db.query("SELECT task_id, reward, status FROM tasks WHERE status = 'AVAILABLE' OR (status = 'LOCKED' AND locked_by = ?) LIMIT 15", (u_id,))
    if not tasks: 
        msg = bot.send_message(message.chat.id, "📭 <b>No active tasks right now. Check back later!</b>")
        track_and_delete_old(message.chat.id, msg.message_id, 'user_tasks')
        return
        
    markup = InlineKeyboardMarkup(row_width=1)
    for t_id, rw, st in tasks:
        prefix = "🔓" if st == 'AVAILABLE' else "⏳ (Locked by You)"
        markup.add(InlineKeyboardButton(f"{prefix} Task #{t_id} - Earn ₹{rw:.2f}", callback_data=f"view_task_{t_id}"))
    
    msg = bot.send_message(message.chat.id, "💼 <b>Select a Task to earn money:</b>\n\n<i>Note: Activating a task locks it to you for 30 minutes. You may only hold ONE active task at a time.</i>", reply_markup=markup)
    track_and_delete_old(message.chat.id, msg.message_id, 'user_tasks')

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_task_"))
def view_specific_task(call):
    t_id = call.data.split("_")[2]
    u_id = call.from_user.id
    task_db = db.query("SELECT msg_chat_id, msg_id, reward, status, locked_by, locked_until, description FROM tasks WHERE task_id = ?", (t_id,))
    
    if not task_db: return bot.answer_callback_query(call.id, "Task deleted.", show_alert=True)
    msg_chat_id, msg_id, rw, st, l_by, l_until, desc = task_db[0]
    
    if st == 'LOCKED' and l_by != u_id and time.time() < l_until:
        return bot.answer_callback_query(call.id, "Another user is doing this right now.", show_alert=True)

    markup = InlineKeyboardMarkup()
    if st == 'AVAILABLE' or (st == 'LOCKED' and time.time() >= l_until):
        markup.add(InlineKeyboardButton("🚀 Start Task Now", callback_data=f"lock_task_{t_id}"))
    elif st == 'LOCKED' and l_by == u_id:
        markup.add(InlineKeyboardButton("✅ Submit Proof (Photo Only)", callback_data=f"submit_proof_{t_id}"))
        markup.add(InlineKeyboardButton("❌ Cancel Task", callback_data=f"unlock_task_{t_id}"))
    markup.add(InlineKeyboardButton("⬅️ Back to Tasks", callback_data="back_to_tasks"))

    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, f"📝 <b>Task #{t_id}</b>\n💰 <b>Reward:</b> ₹{rw:.2f}\n\n👇 <b>Task Instructions Below:</b> 👇")
    
    try:
        if msg_chat_id and msg_id:
            bot.copy_message(call.message.chat.id, msg_chat_id, msg_id, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, desc if desc else "No description provided.", reply_markup=markup)
    except Exception as e:
        logger.error(f"Failed to copy task: {e}")
        bot.send_message(call.message.chat.id, "❌ Error loading task instructions. The admin may have deleted the original post.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_tasks")
def back_to_task_list(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_task_menu(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lock_task_"))
def lock_task_for_user(call):
    t_id = call.data.split("_")[2]
    u_id = call.from_user.id
    
    active_tasks = db.query("SELECT task_id FROM tasks WHERE status = 'LOCKED' AND locked_by = ? AND locked_until > ?", (u_id, time.time()))
    if active_tasks:
        if str(active_tasks[0][0]) != str(t_id):
            return bot.answer_callback_query(call.id, f"❌ You already have Task #{active_tasks[0][0]} active! Complete or cancel it first.", show_alert=True)

    current = db.query("SELECT status, locked_until FROM tasks WHERE task_id = ?", (t_id,))
    if not current or (current[0][0] == 'LOCKED' and time.time() < current[0][1]):
        return bot.answer_callback_query(call.id, "Too late! Someone else just took it.", show_alert=True)

    lock_time = time.time() + 1800 # 30 mins lock
    db.execute("UPDATE tasks SET status = 'LOCKED', locked_by = ?, locked_until = ? WHERE task_id = ?", (u_id, lock_time, t_id))
    bot.answer_callback_query(call.id, "Locked for 30 minutes! Submit proof soon.", show_alert=True)
    call.data = f"view_task_{t_id}"
    view_specific_task(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("unlock_task_"))
def user_unlocks_task(call):
    t_id = call.data.split("_")[2]
    db.execute("UPDATE tasks SET status = 'AVAILABLE', locked_by = NULL, locked_until = 0 WHERE task_id = ? AND locked_by = ?", (t_id, call.from_user.id))
    bot.answer_callback_query(call.id, "Task cancelled.", show_alert=True)
    call.data = "back_to_tasks"
    back_to_task_list(call)

@bot.callback_query_handler(func=lambda call: call.data.startswith("submit_proof_"))
def handle_proof_click(call):
    t_id = call.data.split("_")[2]
    bot.edit_message_text("📸 <b>Upload Photo Proof:</b>\nYou MUST send a clear screenshot. Text is NOT accepted.\n\n<i>Type 'cancel' to abort.</i>", call.message.chat.id, call.message.message_id)
    bot.register_next_step_handler(call.message, process_user_proof, t_id)

def process_user_proof(message, t_id):
    safe_delete_user_command(message)
    if message.text and message.text.lower() == 'cancel':
        return bot.send_message(message.chat.id, "Submission cancelled.")
        
    if not message.photo:
        msg = bot.send_message(message.chat.id, "❌ <b>Invalid Input!</b>\nYou MUST send a PHOTO (screenshot). Text is not allowed.\n\nSend a photo or type 'cancel'.")
        return bot.register_next_step_handler(msg, process_user_proof, t_id)
        
    u_id = message.from_user.id
    proof_data = message.photo[-1].file_id
    
    db.execute("UPDATE tasks SET status = 'PENDING' WHERE task_id = ?", (t_id,))
    db.execute("INSERT INTO task_proofs (task_id, user_id, proof_data) VALUES (?, ?, ?)", (t_id, u_id, proof_data))
    bot.send_message(message.chat.id, "✅ <b>Proof Submitted!</b> An admin will review it shortly.")
    
    task_info = db.query("SELECT description FROM tasks WHERE task_id = ?", (t_id,))
    desc_clean = strip_html(task_info[0][0])[:300] + "..." if task_info and task_info[0][0] else "No Description"
    
    admin_str = db.get_setting("admin_ids", str(ADMIN_IDS[0]))
    for adm in [int(x.strip()) for x in admin_str.split(",") if x.strip()]:
        try:
            markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("✅ Approve", callback_data=f"adm_app_proof_{t_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej_proof_{t_id}")
            )
            bot.send_photo(adm, proof_data, caption=f"🚨 <b>New Task Proof!</b>\nTask ID: <code>{t_id}</code>\nUser: <code>{u_id}</code>\n\n<b>Task:</b> <i>{desc_clean}</i>", reply_markup=markup)
        except: pass

@bot.callback_query_handler(func=lambda call: call.data == "req_withdraw")
def user_withdraw_menu(call):
    u_id = call.from_user.id
    bal = db.query("SELECT task_balance FROM users WHERE user_id = ?", (u_id,))[0][0]
    if bal < 20: return bot.answer_callback_query(call.id, f"Minimum withdraw is ₹20. You have ₹{bal}", show_alert=True)
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🤖 Withdraw to Bot Wallet (No Fee)", callback_data="with_bot"))
    markup.add(InlineKeyboardButton("🏦 Withdraw to UPI", callback_data="with_upi"))
    bot.edit_message_text(f"💸 <b>Withdraw Earnings</b>\n\nAvailable: ₹{bal:.2f}\nSelect destination:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["with_bot", "with_upi"])
def process_withdraw_method(call):
    u_id = call.from_user.id
    bal = db.query("SELECT task_balance FROM users WHERE user_id = ?", (u_id,))[0][0]
    if bal < 20: return
    
    method = "BOT" if call.data == "with_bot" else "UPI"
    if method == "BOT":
        bot.edit_message_text(f"Send amount to withdraw to Bot Wallet (Max: {bal}):\n<i>Type 'cancel' to abort</i>", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, execute_withdraw, method, bal)
    else:
        bot.edit_message_text("Send your UPI ID first:\n<i>Type 'cancel' to abort</i>", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, ask_upi_amount, bal)

def ask_upi_amount(message, max_bal):
    safe_delete_user_command(message)
    if message.text.lower() == 'cancel': return bot.send_message(message.chat.id, "Cancelled.")
    upi_id = message.text.strip()
    msg = bot.send_message(message.chat.id, f"UPI ID: <code>{upi_id}</code>\nEnter amount to withdraw (Max {max_bal}):")
    bot.register_next_step_handler(msg, execute_withdraw, "UPI", max_bal, upi_id)

def execute_withdraw(message, method, max_bal, upi_id="N/A"):
    safe_delete_user_command(message)
    if message.text.lower() == 'cancel': return bot.send_message(message.chat.id, "Cancelled.")
    try:
        amt = float(message.text)
        if amt < 20 or amt > max_bal: return bot.send_message(message.chat.id, "❌ Invalid amount. Must be >= 20 and <= your balance.")
        
        db.update_balance(message.from_user.id, -amt, "task")
        w_id = f"WD{int(time.time())}"
        
        db.execute("INSERT INTO withdraw_requests VALUES (?, ?, ?, ?, ?, 'PENDING', ?)", (w_id, message.from_user.id, amt, method, upi_id, datetime.now()))
        bot.send_message(message.chat.id, f"✅ <b>Withdrawal Submitted!</b>\nAmount: ₹{amt}\nMethod: {method}\n\n<i>Admin will review within 24 hours.</i>")
        
        admin_str = db.get_setting("admin_ids", str(ADMIN_IDS[0]))
        for adm in [int(x.strip()) for x in admin_str.split(",") if x.strip()]:
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Approve", callback_data=f"adm_app_wd_{w_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej_wd_{w_id}"))
            try: bot.send_message(adm, f"💸 <b>New Withdrawal!</b>\nID: <code>{w_id}</code>\nUser: <code>{message.from_user.id}</code>\nAmount: ₹{amt}\nMethod: {method}\nUPI: <code>{upi_id}</code>", reply_markup=markup)
            except: pass
    except: bot.send_message(message.chat.id, "❌ Invalid number.")

# =================================================================
# 11. MAIN NAVIGATION & RECEIPTS 
# =================================================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    safe_delete_user_command(message) 
    u_id = message.from_user.id
    if check_spam(u_id) == "BANNED": return bot.send_message(u_id, "🚫 <b>Access Denied:</b> You have been banned.")
    if check_spam(u_id): return
    db.execute("INSERT OR IGNORE INTO users (user_id, username, joined_at) VALUES (?, ?, ?)", (u_id, message.from_user.username, datetime.now()))
    fsub = check_fsub(u_id)
    if fsub is not True: return bot.send_message(u_id, "🛑 <b>Action Required:</b> Please join our channels.", reply_markup=fsub)
    bot.send_message(u_id, "🚀 <b>Welcome to Premium SMS & Earn Service</b>", reply_markup=UIFactory.reply_main_menu())

@bot.message_handler(func=lambda message: message.text == "👤 My Wallet")
def handle_wallet_text(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    safe_delete_user_command(message)
    u_id = message.from_user.id
    if check_spam(u_id) == "BANNED": return bot.send_message(u_id, "🚫 You are banned.")
    if check_spam(u_id): return
    fsub = check_fsub(u_id)
    if fsub is not True: return bot.send_message(u_id, "🛑 <b>Access Denied.</b>", reply_markup=fsub)
    
    data = db.query("SELECT balance, task_balance FROM users WHERE user_id = ?", (u_id,))
    if data:
        text = f"👤 <b>Your Wallets:</b>\n\n💰 <b>Deposit Balance:</b> ₹{data[0][0]:.2f}\n<i>(Used for buying numbers)</i>\n\n💼 <b>Earned Balance:</b> ₹{data[0][1]:.2f}\n<i>(Earned from tasks)</i>"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("💸 Withdraw Earnings", callback_data="req_withdraw"))
        msg = bot.send_message(message.chat.id, text, reply_markup=markup)
        track_and_delete_old(message.chat.id, msg.message_id, 'user_wallet')

@bot.message_handler(func=lambda message: message.text == "📜 Order History")
def handle_history_text(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    safe_delete_user_command(message)
    u_id = message.from_user.id
    if check_spam(u_id) == "BANNED": return bot.send_message(u_id, "🚫 You are banned.")
    if check_spam(u_id): return
    orders = db.query("SELECT order_id, service_code, phone, cost, status, created_at, otp FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (u_id,))
    if not orders: 
        msg = bot.send_message(message.chat.id, "📜 You have no recent orders.")
        track_and_delete_old(message.chat.id, msg.message_id, 'user_history')
        return
        
    text = "📜 <b>Your Recent Orders:</b>\n\n"
    for o_id, code, phone, cost, status, date, otp_code in orders:
        app_name = "Legacy Service"
        if code:
            name_data = db.query("SELECT name FROM api_services WHERE code = ?", (code,))
            app_name = name_data[0][0] if name_data else str(code).capitalize()
            
        safe_otp = str(otp_code).replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;') if otp_code else ""
        
        if status == "SUCCESS":
            status_disp = "✅ <b>Success</b>"
            otp_disp = f"\n├ <b>OTP:</b> <code>{safe_otp}</code>"
        elif status in ["CANCELLED", "TIMEOUT"]:
            status_disp = "❌ <b>Refunded/Failed</b>"
            otp_disp = ""
        else:
            status_disp = "⏳ <b>Waiting...</b>"
            otp_disp = ""
        f_date = format_date(date)
        text += f"🛒 <b>{app_name}</b> <code>(+{phone})</code>\n├ <b>Order ID:</b> <code>{o_id}</code>\n├ <b>Cost:</b> ₹{cost:.2f}\n├ <b>Status:</b> {status_disp}{otp_disp}\n└ <b>Date:</b> <i>{f_date}</i>\n\n"
    msg = bot.send_message(message.chat.id, text)
    track_and_delete_old(message.chat.id, msg.message_id, 'user_history')

@bot.callback_query_handler(func=lambda call: call.data == "ui_close")
def nav_close(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)

# =================================================================
# 12. ENTERPRISE ADMIN PANEL & BP TEST
# =================================================================
@bot.message_handler(commands=['omkar99', 'admin'])
def handle_admin_entry(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    safe_delete_user_command(message)
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "🛠 <b>Enterprise Admin Panel</b>", reply_markup=UIFactory.admin_panel())
    track_and_delete_old(message.chat.id, msg.message_id, 'admin_panel')

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callbacks(call):
    if not is_admin(call.from_user.id): return
    
    if call.data == "adm_test_bp":
        mid = db.get_setting("bp_merchant_id", "")
        token = db.get_setting("bp_token", "")
        if not mid or not token:
            bot.answer_callback_query(call.id, "Missing MID or Token!", show_alert=True)
            return
        bot.edit_message_text("⏳ Testing Connection...", call.message.chat.id, call.message.message_id)
        res = verify_bharatpe_transaction("TEST_PING_000", mid, token)
        
        if "NOT_FOUND_IN_LIST" in res.get("error", ""):
            msg = f"✅ <b>CONNECTION SUCCESS!</b>\n\nHTTP 200 OK.\nThe bot successfully connected to BharatPe. (Test UTR not found, as expected)."
        else:
            msg = f"❌ <b>CONNECTION FAILED!</b>\n\nError: <code>{res.get('error', res.get('debug', 'Unknown'))}</code>\n\nIf HTTP_ERROR_401, your token is expired!"
            
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))

    elif call.data == "adm_back_main":
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        bot.edit_message_text("🛠 <b>Enterprise Admin Panel</b>", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.admin_panel())

    elif call.data == "adm_restore_cloud":
        bot.edit_message_text("⚠️ <b>Warning!</b>\nThis will download and replace your local database with the live data from Firebase.\n\nAre you sure you want to restore?", call.message.chat.id, call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Yes, Restore Data", callback_data="adm_confirm_restore"), InlineKeyboardButton("❌ Cancel", callback_data="adm_back_main")))
        
    elif call.data == "adm_confirm_restore":
        bot.edit_message_text("⏳ <b>Restoring data from Firebase...</b> Please wait.", call.message.chat.id, call.message.message_id)
        success, msg = CloudSyncEngine.restore_from_cloud()
        if success:
            bot.edit_message_text(f"✅ {msg}", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        else:
            bot.edit_message_text(f"❌ Restore Failed: {msg}", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))

    elif call.data == "adm_tasks":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Add New Task", callback_data="adm_add_task"))
        markup.add(InlineKeyboardButton("📸 Pending Proofs", callback_data="adm_pending_proofs"))
        markup.add(InlineKeyboardButton("🔍 View Active Tasks", callback_data="adm_view_tasks"))
        markup.add(InlineKeyboardButton("🗑 Wipe All Tasks", callback_data="adm_wipe_tasks"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="adm_back_main"))
        bot.edit_message_text("📋 <b>Task Manager</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "adm_add_task":
        bot.edit_message_text("💰 Enter reward amount for this task (e.g., 15.5):", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, admin_task_get_reward)
        
    elif call.data == "adm_pending_proofs":
        pending = db.query("SELECT p.proof_data, p.task_id, p.user_id, t.description FROM task_proofs p JOIN tasks t ON p.task_id = t.task_id WHERE p.status = 'PENDING'")
        if not pending: return bot.answer_callback_query(call.id, "No pending task proofs.", show_alert=True)
        
        bot.edit_message_text("📸 <b>Pending Proofs sent below:</b>", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_tasks"))
        for p_data, t_id, u_id, desc in pending:
            markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("✅ Approve", callback_data=f"adm_app_proof_{t_id}"), 
                InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej_proof_{t_id}")
            )
            desc_clean = strip_html(desc)[:300] + "..." if desc else "No Description"
            caption = f"🚨 <b>Pending Proof!</b>\nTask ID: <code>{t_id}</code>\nUser: <code>{u_id}</code>\n\n<b>Task Details:</b>\n<i>{desc_clean}</i>"
            try: bot.send_photo(call.message.chat.id, p_data, caption=caption, reply_markup=markup)
            except: pass

    elif call.data == "adm_view_tasks":
        tasks = db.query("SELECT task_id, reward, status, locked_by, description FROM tasks ORDER BY task_id DESC LIMIT 20")
        if not tasks: return bot.answer_callback_query(call.id, "No tasks exist.", show_alert=True)
        text = "📋 <b>Active Tasks (Latest 20)</b>\n\n"
        for tid, rw, st, lby, desc in tasks:
            lock_info = f" (Locked by {lby})" if st == 'LOCKED' else ""
            desc_clean = strip_html(desc)[:40].replace('\n', ' ') + "..." if desc else "No Description"
            text += f"ID: <code>{tid}</code> | ₹{rw} | {st}{lock_info}\n📝 <i>{desc_clean}</i>\n\n"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🗑 Delete Task by ID", callback_data="adm_manage_task_id"))
        markup.add(InlineKeyboardButton("⬅️ Back", callback_data="adm_tasks"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        
    elif call.data == "adm_manage_task_id":
        bot.edit_message_text("Enter Task ID to delete/cancel (or 'cancel'):", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, admin_delete_task_by_id, call.message.message_id)

    elif call.data == "adm_wipe_tasks":
        db.execute("DELETE FROM tasks")
        bot.answer_callback_query(call.id, "All tasks wiped!", show_alert=True)

    elif call.data.startswith("adm_app_proof_"):
        t_id = call.data.split("_")[3]
        task_data = db.query("SELECT reward FROM tasks WHERE task_id = ?", (t_id,))
        proof_data = db.query("SELECT user_id FROM task_proofs WHERE task_id = ? AND status = 'PENDING'", (t_id,))
        if not task_data or not proof_data: return bot.answer_callback_query(call.id, "Already processed or deleted.", show_alert=True)
        
        u_id, rw = proof_data[0][0], task_data[0][0]
        db.update_balance(u_id, rw, "task")
        db.execute("UPDATE tasks SET status = 'COMPLETED' WHERE task_id = ?", (t_id,))
        db.execute("UPDATE task_proofs SET status = 'APPROVED' WHERE task_id = ?", (t_id,))
        
        bot.answer_callback_query(call.id, "Proof Approved!", show_alert=False)
        try:
            bot.edit_message_caption(f"✅ <b>Proof Approved!</b>\n₹{rw} credited to user <code>{u_id}</code>.", call.message.chat.id, call.message.message_id, reply_markup=None)
        except: pass
        
        try: bot.send_message(u_id, f"🎉 <b>Task #{t_id} Approved!</b>\n₹{rw} has been added to your Task Wallet.")
        except: pass

    elif call.data.startswith("adm_rej_proof_"):
        t_id = call.data.split("_")[3]
        proof_data = db.query("SELECT user_id FROM task_proofs WHERE task_id = ? AND status = 'PENDING'", (t_id,))
        if not proof_data: return bot.answer_callback_query(call.id, "Already processed.", show_alert=True)
        
        u_id = proof_data[0][0]
        db.execute("UPDATE tasks SET status = 'AVAILABLE', locked_by = NULL, locked_until = 0 WHERE task_id = ?", (t_id,))
        db.execute("UPDATE task_proofs SET status = 'REJECTED' WHERE task_id = ?", (t_id,))
        
        bot.answer_callback_query(call.id, "Proof Rejected!", show_alert=False)
        try:
            bot.edit_message_caption(f"❌ <b>Proof Rejected.</b>\nTask returned to the pool.", call.message.chat.id, call.message.message_id, reply_markup=None)
        except: pass
        
        try: bot.send_message(u_id, f"❌ <b>Task #{t_id} Rejected.</b>\nYour proof was invalid, and the task has been cancelled.")
        except: pass

    elif call.data == "adm_withdrawals":
        pending = db.query("SELECT w_id, user_id, amount, method, upi_id FROM withdraw_requests WHERE status = 'PENDING'")
        if not pending: return bot.answer_callback_query(call.id, "No pending withdrawals.", show_alert=True)
        bot.edit_message_text("⌛ <b>Pending Withdrawals sent below:</b>", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        for w_id, u_id, amt, method, upi in pending:
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ Approve", callback_data=f"adm_app_wd_{w_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej_wd_{w_id}"))
            bot.send_message(call.message.chat.id, f"💸 <b>Withdrawal Request</b>\nID: <code>{w_id}</code>\nUser: <code>{u_id}</code>\nAmount: ₹{amt}\nMethod: {method}\nUPI: <code>{upi}</code>", reply_markup=markup)

    elif call.data.startswith("adm_app_wd_"):
        w_id = call.data.split("_")[3]
        w_data = db.query("SELECT user_id, amount, method FROM withdraw_requests WHERE w_id = ? AND status = 'PENDING'", (w_id,))
        if not w_data: return bot.answer_callback_query(call.id, "Already processed.", show_alert=True)
        
        u_id, amt, method = w_data[0]
        db.execute("UPDATE withdraw_requests SET status = 'APPROVED' WHERE w_id = ?", (w_id,))
        if method == "BOT": db.update_balance(u_id, amt, "main")
            
        bot.edit_message_text(f"✅ Withdrawal {w_id} Approved.", call.message.chat.id, call.message.message_id)
        try: bot.send_message(u_id, f"🎉 <b>Withdrawal Approved!</b> (ID: {w_id})\nAmount: ₹{amt}\nMethod: {method}")
        except: pass

    elif call.data.startswith("adm_rej_wd_"):
        w_id = call.data.split("_")[3]
        w_data = db.query("SELECT user_id, amount FROM withdraw_requests WHERE w_id = ? AND status = 'PENDING'", (w_id,))
        if not w_data: return bot.answer_callback_query(call.id, "Already processed.", show_alert=True)
        
        u_id, amt = w_data[0]
        db.execute("UPDATE withdraw_requests SET status = 'REJECTED' WHERE w_id = ?", (w_id,))
        db.update_balance(u_id, amt, "task") # Refund to task wallet
        
        bot.edit_message_text(f"❌ Withdrawal {w_id} Rejected. Funds returned to user.", call.message.chat.id, call.message.message_id)
        try: bot.send_message(u_id, f"❌ <b>Withdrawal Rejected.</b> (ID: {w_id})\nFunds returned to Task Wallet.")
        except: pass

    elif call.data == "adm_fetch_api":
        bot.answer_callback_query(call.id, "Generating API Codes file...", show_alert=False)
        services = db.query("SELECT name, code FROM api_services ORDER BY name ASC")
        if not services:
            return bot.edit_message_text("❌ No services found in the database.", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        content = "📱 Official API Codes:\n\n"
        for name, code in services: content += f"App: {name} -> Code: {code}\n"
        file_stream = BytesIO(content.encode('utf-8'))
        file_stream.name = "API_Codes.txt"
        bot.send_document(call.message.chat.id, file_stream, caption="✅ Here is the complete list of all currently synced API codes.")
        bot.edit_message_text("🛠 <b>Enterprise Admin Panel</b>", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.admin_panel())

    elif call.data == "adm_manage_admins":
        admins = db.get_setting("admin_ids", str(ADMIN_IDS[0]))
        bot.edit_message_text(f"👑 <b>Current Admin IDs:</b>\n<code>{admins}</code>\n\nEnter User ID to Add/Remove as Admin (or 'cancel'):", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, admin_toggle_admin, call.message.message_id)

    elif call.data == "adm_toggle_maint":
        current = db.get_setting("maintenance_mode", "0")
        new_val = "0" if current == "1" else "1"
        db.execute("UPDATE settings SET value = ? WHERE key = 'maintenance_mode'", (new_val,))
        state = "ON 🚧" if new_val == "1" else "OFF ✅"
        bot.edit_message_text(f"Maintenance Mode is now <b>{state}</b>.", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))

    elif call.data == "adm_ban_user":
        bot.edit_message_text("🚫 Enter User ID to Ban/Unban (or 'cancel'):", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, admin_toggle_ban, call.message.message_id)

    elif call.data == "adm_broadcast":
        bot.edit_message_text("📢 Send the message you want to broadcast to all users (or type 'cancel'):", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, admin_broadcast_msg, call.message.message_id)

    elif call.data == "adm_set_margin":
        curr = db.get_setting("global_margin", "5.0")
        bot.edit_message_text(f"📈 Current Margin: <b>+₹{curr}</b>\n\nEnter new margin (e.g. 5.0) or type 'cancel':", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        bot.register_next_step_handler(call.message, admin_save_global_margin, call.message.message_id)

    elif call.data == "adm_override_price":
        bot.edit_message_text("💎 <b>Custom Price Override</b>\nType exact app name (or type 'cancel'):", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        bot.register_next_step_handler(call.message, admin_search_override_app, call.message.message_id)
        
    elif call.data == "adm_user_history":
        bot.edit_message_text("🕵️ <b>User Tracker</b>\nEnter the User ID you want to inspect (or 'cancel'):", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        bot.register_next_step_handler(call.message, admin_check_user_history, call.message.message_id)

    elif call.data == "adm_find_order":
        bot.edit_message_text("🔍 <b>Order Tracker</b>\nEnter the exact Order ID you want to inspect (or 'cancel'):", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        bot.register_next_step_handler(call.message, admin_check_order_id, call.message.message_id)

    elif call.data == "adm_manage_fsub":
        chans = db.query("SELECT channel_id, channel_url FROM force_sub")
        text = "📢 <b>Force Sub Channels:</b>\n\n" + "".join([f"ID: <code>{c}</code> | {u}\n" for c, u in chans]) if chans else "No channels configured."
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("➕ Add", callback_data="fsub_add"), InlineKeyboardButton("➖ Del", callback_data="fsub_del")).add(InlineKeyboardButton("⬅️ Back", callback_data="adm_back_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "adm_set_upi":
        curr_upi = db.get_setting("upi_id", "Not Set")
        bot.edit_message_text(f"🏦 <b>Current UPI QR (Visible to users):</b> <code>{curr_upi}</code>\nEnter New UPI ID (or type 'cancel'):", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        bot.register_next_step_handler(call.message, admin_save_upi, call.message.message_id)
        
    elif call.data == "adm_set_server":
        curr_server = db.get_setting("api_base_url", "Not Set")
        bot.edit_message_text(f"🌐 <b>Current API Server:</b>\n<code>{curr_server}</code>\n\nSend new Base URL (or type 'cancel'):", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        bot.register_next_step_handler(call.message, admin_save_server, call.message.message_id)

    elif call.data == "adm_set_apikey":
        curr_key = db.get_setting("api_key", "Not Set")
        bot.edit_message_text(f"🔑 <b>Current API Key:</b>\n<code>{curr_key}</code>\n\nSend new API Key (or type 'cancel'):", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        bot.register_next_step_handler(call.message, admin_save_apikey, call.message.message_id)
        
    elif call.data == "adm_set_bp_mid":
        curr_mid = db.get_setting("bp_merchant_id", "Not Set")
        bot.edit_message_text(f"🔑 <b>Current BP Merchant ID:</b>\n<code>{curr_mid}</code>\n\nSend new Merchant ID from BharatPe dashboard (or type 'cancel'):", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        bot.register_next_step_handler(call.message, admin_save_bp_setting, "bp_merchant_id", call.message.message_id)
        
    elif call.data == "adm_set_bp_token":
        curr_token = db.get_setting("bp_token", "Not Set")
        status = "Active ✅" if len(curr_token) > 20 else "Missing/Invalid ❌"
        bot.edit_message_text(f"🔑 <b>Current BP Token Status:</b> {status}\n\nSend new token header string from BharatPe network tab (or type 'cancel'):\n\n<i>Note: This token usually expires every 24-48 hours.</i>", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        bot.register_next_step_handler(call.message, admin_save_bp_setting, "bp_token", call.message.message_id)

    elif call.data == "adm_list_trx":
        pending = db.query("SELECT trx_id, user_id FROM transactions WHERE status = 'PENDING'")
        if not pending: return bot.answer_callback_query(call.id, "No pending deposits.", show_alert=True)
        bot.edit_message_text("⌛ <b>Check new messages below for pending transactions.</b>", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        for t_id, u_id in pending: bot.send_message(call.message.chat.id, f"💳 <b>Deposit</b>\nUser: {u_id}\nTRX: <code>{t_id}</code>", reply_markup=UIFactory.trx_approval(t_id))

    elif call.data == "adm_users_list":
        bot.answer_callback_query(call.id, "Refreshing list...", show_alert=False)
        users = db.query("SELECT user_id, username, balance FROM users ORDER BY balance DESC LIMIT 40")
        text = "👥 <b>Top Users:</b>\n\n" + "".join([f"<code>{u}</code> | @{n if n else 'NoName'} | ₹{b:.1f}\n" for u, n, b in users]) if users else "No users."
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔄 Refresh", callback_data="adm_users_list"), InlineKeyboardButton("⬅️ Back", callback_data="adm_back_main")))

    elif call.data in ["adm_add_bal", "adm_sub_bal"]:
        act = "ADD" if call.data == "adm_add_bal" else "DEDUCT"
        bot.edit_message_text(f"👤 Enter User ID to <b>{act}</b> balance (or type 'cancel'):", call.message.chat.id, call.message.message_id, reply_markup=UIFactory.back_button("adm_back_main"))
        bot.register_next_step_handler(call.message, admin_ask_manual_amount, call.data, call.message.message_id)

def admin_delete_task_by_id(message, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    try:
        t_id = int(message.text)
        db.execute("DELETE FROM tasks WHERE task_id = ?", (t_id,))
        bot.edit_message_text(f"✅ Task {t_id} deleted successfully.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_tasks"))
    except:
        bot.edit_message_text("❌ Invalid ID.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_tasks"))

def admin_task_get_reward(message):
    if message.text.lower() == 'cancel': return
    try:
        rw = float(message.text)
        bot.send_message(message.chat.id, "📝 Send the full task description.\n<i>Tip: ALL formatting (links, monospace, bold, etc.) will be cloned perfectly for the user. Do NOT delete this message after sending it.</i>")
        bot.register_next_step_handler(message, admin_task_save, rw)
    except: bot.send_message(message.chat.id, "❌ Invalid reward.")

def admin_task_save(message, rw):
    if message.text and message.text.lower() == 'cancel': return
    db.execute("INSERT INTO tasks (msg_chat_id, msg_id, reward, created_at) VALUES (?, ?, ?, ?)", (message.chat.id, message.message_id, rw, datetime.now()))
    bot.send_message(message.chat.id, f"✅ <b>Task Created!</b>\nReward: ₹{rw}\n\n<i>Note: Please do not delete your original message from this chat history, as the bot uses it as a template to copy to users.</i>", reply_markup=UIFactory.admin_panel())

def check_cancel(message, menu_id):
    if not message.text: return False
    if message.text.strip().lower() == 'cancel':
        bot.delete_message(message.chat.id, message.message_id)
        bot.edit_message_text("🛠 <b>Enterprise Admin Panel</b>", message.chat.id, menu_id, reply_markup=UIFactory.admin_panel())
        return True
    return False

def admin_save_bp_setting(message, key_name, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    db.execute(f"UPDATE settings SET value = ? WHERE key = '{key_name}'", (message.text.strip(),))
    bot.edit_message_text(f"✅ BharatPe Settings Updated.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

def admin_toggle_admin(message, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    try:
        target_id = str(int(message.text.strip()))
        current_admins = [x.strip() for x in db.get_setting("admin_ids", str(ADMIN_IDS[0])).split(",") if x.strip()]
        if target_id in current_admins:
            current_admins.remove(target_id)
            action = "Removed"
        else:
            current_admins.append(target_id)
            action = "Added"
        db.execute("UPDATE settings SET value = ? WHERE key = 'admin_ids'", (",".join(current_admins),))
        bot.edit_message_text(f"✅ Admin {action}: <code>{target_id}</code>", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
    except:
        bot.edit_message_text("❌ Invalid ID format.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

def admin_toggle_ban(message, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    try:
        t_uid = int(message.text.strip())
        user = db.query("SELECT is_banned FROM users WHERE user_id = ?", (t_uid,))
        if not user: return bot.edit_message_text("❌ User not found in database.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
        new_status = 0 if user[0][0] == 1 else 1
        db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_status, t_uid))
        state = "BANNED 🚫" if new_status == 1 else "UNBANNED ✅"
        bot.edit_message_text(f"✅ User <code>{t_uid}</code> is now <b>{state}</b>.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
    except: bot.edit_message_text("❌ Invalid ID.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

def admin_broadcast_msg(message, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    bot.edit_message_text("📢 Broadcasting message... This might take a moment.", message.chat.id, menu_id)
    users = db.query("SELECT user_id FROM users")
    sent = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 <b>Admin Announcement:</b>\n\n{message.text}")
            sent += 1
            time.sleep(0.05)
        except: pass
    bot.edit_message_text(f"✅ Broadcast successfully sent to {sent} users.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

def admin_save_server(message, menu_id):
    if check_cancel(message, menu_id): return
    new_url = message.text.strip()
    bot.delete_message(message.chat.id, message.message_id)
    api_key = db.get_setting('api_key')
    try:
        r = requests.get(new_url, params={"api_key": api_key, "action": "getBalance"}, timeout=5)
        if r.status_code == 200:
            db.execute("UPDATE settings SET value = ? WHERE key = 'api_base_url'", (new_url,))
            bot.edit_message_text(f"✅ Server pinged successfully and updated to:\n<code>{new_url}</code>", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
        else: bot.edit_message_text(f"❌ Server check failed (HTTP {r.status_code}). Setup aborted.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
    except: bot.edit_message_text("❌ Connection failed. Ensure the URL format is correct. Update aborted.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

def admin_save_apikey(message, menu_id):
    if check_cancel(message, menu_id): return
    new_key = message.text.strip()
    bot.delete_message(message.chat.id, message.message_id)
    api_url = db.get_setting('api_base_url')
    try:
        r = requests.get(api_url, params={"api_key": new_key, "action": "getBalance"}, timeout=5)
        if "BAD_KEY" not in r.text and r.status_code == 200:
            db.execute("UPDATE settings SET value = ? WHERE key = 'api_key'", (new_key,))
            bot.edit_message_text(f"✅ API Key validated and updated successfully.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
        else: bot.edit_message_text(f"❌ API Key looks invalid according to server. Update aborted.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
    except: bot.edit_message_text("❌ Error checking API key. Update aborted.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

def admin_check_user_history(message, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    try:
        t_uid = int(message.text.strip())
        user_data = db.query("SELECT balance, joined_at, is_banned, task_balance FROM users WHERE user_id = ?", (t_uid,))
        if not user_data: return bot.edit_message_text(f"❌ User {t_uid} not found.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
        
        orders = db.query("SELECT order_id, service_code, status, cost, created_at, otp FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (t_uid,))
        total_spent = sum([float(o[3]) for o in orders if o[2] == "SUCCESS"]) if orders else 0.0
        ban_txt = "🚫 BANNED" if user_data[0][2] == 1 else "✅ ACTIVE"
        
        text = f"🕵️ <b>Dossier: <code>{t_uid}</code></b> ({ban_txt})\n"
        text += f"🗓 Joined: <i>{format_date(user_data[0][1])}</i>\n\n"
        text += f"💰 Deposit Balance: <b>₹{user_data[0][0]:.2f}</b>\n"
        text += f"💼 Task Balance: <b>₹{user_data[0][3]:.2f}</b>\n"
        text += f"💸 Spent (Last 10): <b>₹{total_spent:.2f}</b>\n\n"
        text += "📝 <b>Last 10 Transactions:</b>\n"
        if not orders: text += "No purchases yet."
        for o_id, code, status, cost, date, otp_code in orders:
            app_name = "Legacy Service"
            if code:
                name_data = db.query("SELECT name FROM api_services WHERE code = ?", (code,))
                app_name = name_data[0][0] if name_data else str(code).capitalize()
            
            safe_app_name = str(app_name).replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
            safe_otp = str(otp_code).replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;') if otp_code else ""
                
            status_icon = "✅" if status == "SUCCESS" else "❌" if status in ["CANCELLED", "TIMEOUT"] else "⏳"
            f_date = format_date(date)
            otp_str = f" [OTP: {safe_otp}]" if status == "SUCCESS" else ""
            text += f"{status_icon} <b>{safe_app_name}</b> (₹{cost}){otp_str} - <i>{f_date}</i>\n"
        bot.edit_message_text(text, message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
    except: bot.edit_message_text("❌ Invalid User ID.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

def admin_check_order_id(message, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    o_id = message.text.strip()
    order_data = db.query("SELECT user_id, phone, cost, status, otp, created_at, service_code FROM orders WHERE order_id = ?", (o_id,))
    if not order_data: return bot.edit_message_text(f"❌ Order ID <code>{o_id}</code> not found in database.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
    u_id, phone, cost, status, otp, date, code = order_data[0]
    app_name = "Legacy Service"
    if code:
        name_data = db.query("SELECT name FROM api_services WHERE code = ?", (code,))
        app_name = name_data[0][0] if name_data else str(code).capitalize()
    f_date = format_date(date)
    status_icon = "✅" if status == "SUCCESS" else "❌" if status in ["CANCELLED", "TIMEOUT"] else "⏳"
    text = f"🔍 <b>Order Details</b>\n\n🛒 <b>App:</b> {app_name} (<code>{code}</code>)\n🔖 <b>Order ID:</b> <code>{o_id}</code>\n👤 <b>User ID:</b> <code>{u_id}</code>\n📱 <b>Phone:</b> <code>+{phone}</code>\n💰 <b>Cost:</b> ₹{cost:.2f}\n📊 <b>Status:</b> {status_icon} {status}\n"
    
    safe_otp = str(otp).replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;') if otp else ""
    if safe_otp: text += f"✉️ <b>OTP:</b> <code>{safe_otp}</code>\n"
        
    text += f"\n📅 <b>Date:</b> <i>{f_date}</i>"
    bot.edit_message_text(text, message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

def admin_save_global_margin(message, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    try:
        db.execute("UPDATE settings SET value = ? WHERE key = 'global_margin'", (str(float(message.text)),))
        bot.edit_message_text(f"✅ Global margin updated to +₹{float(message.text)}.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
    except: bot.edit_message_text("❌ Invalid.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

def admin_search_override_app(message, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    res = db.query("SELECT code, name, custom_price FROM api_services WHERE LOWER(name) LIKE ? LIMIT 5", (f"%{message.text.lower()[:30]}%",))
    if not res: return bot.edit_message_text("❌ App not found.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
    markup = InlineKeyboardMarkup(row_width=1)
    for code, name, c_price in res: markup.add(InlineKeyboardButton(f"{name} (₹{c_price if c_price else 'Auto'})", callback_data=f"set_over_{code}_{menu_id}"))
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="adm_back_main"))
    bot.edit_message_text("Select app to configure:", message.chat.id, menu_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_over_"))
def admin_ask_override_amount(call):
    _, _, code, menu_id = call.data.split("_")
    bot.edit_message_text(f"Enter fixed price for app (or 'AUTO' to reset).\n\n<i>Type 'cancel' to abort.</i>", call.message.chat.id, menu_id)
    bot.register_next_step_handler(call.message, admin_save_override, code, menu_id)

def admin_save_override(message, code, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    if message.text and message.text.upper() == 'AUTO':
        db.execute("UPDATE api_services SET custom_price = NULL WHERE code = ?", (code,))
        bot.edit_message_text("✅ Reset to global margin.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
    else:
        try:
            db.execute("UPDATE api_services SET custom_price = ? WHERE code = ?", (float(message.text), code))
            bot.edit_message_text(f"✅ Fixed price set to ₹{float(message.text)}.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
        except: bot.edit_message_text("❌ Invalid.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

def admin_save_upi(message, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    if len(message.text) > 50: return bot.edit_message_text("❌ UPI ID too long.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
    db.execute("UPDATE settings SET value = ? WHERE key = 'upi_id'", (message.text,))
    bot.edit_message_text("✅ UPI updated.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

@bot.callback_query_handler(func=lambda call: call.data.startswith("fsub_"))
def manage_fsub_clicks(call):
    if call.data == "fsub_add":
        bot.edit_message_text("Enter Channel ID and Link separated by space.\nExample: <code>-100456 https://t.me/c</code>\nType 'cancel' to abort.", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, fsub_save_db, call.message.message_id)
    elif call.data == "fsub_del":
        bot.edit_message_text("Enter the exact Channel ID to remove (or 'cancel'):", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(call.message, fsub_del_db, call.message.message_id)

def fsub_save_db(message, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    try:
        c, u = message.text.split(" ", 1)
        db.execute("INSERT OR REPLACE INTO force_sub VALUES (?, ?)", (c.strip(), u.strip()))
        bot.edit_message_text("✅ Added. Make sure bot is admin!", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_manage_fsub"))
    except: bot.edit_message_text("❌ Invalid format.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_manage_fsub"))

def fsub_del_db(message, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    db.execute("DELETE FROM force_sub WHERE channel_id = ?", (message.text.strip(),))
    bot.edit_message_text("✅ Removed.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_manage_fsub"))

def admin_ask_manual_amount(message, action, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    try:
        t_uid = int(message.text.strip())
        bot.edit_message_text(f"💰 Enter AMOUNT for User <code>{t_uid}</code> (or 'cancel'):", message.chat.id, menu_id)
        bot.register_next_step_handler(message, admin_execute_manual_bal, t_uid, action, menu_id)
    except: bot.edit_message_text("❌ Invalid ID.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

def admin_execute_manual_bal(message, target_uid, action, menu_id):
    if check_cancel(message, menu_id): return
    bot.delete_message(message.chat.id, message.message_id)
    try:
        amt = float(message.text.strip())
        if action == "adm_sub_bal": amt = -amt
        if not db.query("SELECT balance FROM users WHERE user_id = ?", (target_uid,)): return bot.edit_message_text("❌ User not found.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
        db.update_balance(target_uid, amt, "main")
        bot.edit_message_text(f"✅ Success. Adjusted ₹{abs(amt)} for {target_uid}.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))
        try: bot.send_message(target_uid, f"🎉 <b>Admin Update:</b> ₹{amt} applied to wallet.")
        except: pass
    except: bot.edit_message_text("❌ Invalid amount.", message.chat.id, menu_id, reply_markup=UIFactory.back_button("adm_back_main"))

# =================================================================
# 13. AUTO-DEPOSIT & MANUAL FALLBACK (BHARATPE SYSTEM)
# =================================================================
def verify_bharatpe_transaction(utr, merchant_id, token):
    try:
        now = int(time.time())
        seven_days_ago = now - (7 * 24 * 60 * 60)
        
        url = f"https://payments-tesseract.bharatpe.in/api/v1/merchant/transactions"
        params = {"module": "PAYMENT_QR", "merchantId": merchant_id, "startTime": seven_days_ago, "endTime": now}
        headers = {"token": token, "Accept": "application/json", "Content-Type": "application/json"}
        
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            status = data.get("status", False)
            if status is True or status == "SUCCESS" or status == "OK":
                transactions = data.get("data", {}).get("transactions", [])
                for tx in transactions:
                    b_ref = str(tx.get("bankReferenceNo", "")).strip()
                    i_utr = str(tx.get("internalUtr", "")).strip()
                    
                    if utr == b_ref or utr == i_utr:
                        if tx.get("status") == "SUCCESS" and tx.get("type") == "PAYMENT_RECV":
                            amt_raw = tx.get("amount", 0)
                            amount = float(amt_raw) if amt_raw else 0.0
                            return {"success": True, "amount": amount, "debug": f"HTTP 200: Found {utr}!"}
                        else:
                            return {"success": False, "error": "TRANSACTION_NOT_SUCCESS"}
            return {"success": False, "error": f"NOT_FOUND_IN_LIST. First 50 chars: {r.text[:50]}"}
        return {"success": False, "error": f"HTTP_ERROR_{r.status_code}. First 50 chars: {r.text[:50]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@bot.message_handler(func=lambda message: message.text == "💰 Deposit Funds")
def handle_deposit_text(message):
    bot.clear_step_handler_by_chat_id(message.chat.id) 
    safe_delete_user_command(message) 
    u_id = message.from_user.id
    if check_spam(u_id) == "BANNED": return bot.send_message(u_id, "🚫 <b>Access Denied:</b> You have been banned.")
    if check_spam(u_id): return
    if db.get_setting("maintenance_mode", "0") == "1": return bot.send_message(message.chat.id, "🚧 <b>Bot is under maintenance.</b>\nDeposits are temporarily paused. Please try again later.")
    fsub = check_fsub(u_id)
    if fsub is not True: return bot.send_message(u_id, "🛑 <b>Access Denied:</b> Join channels first.", reply_markup=fsub)
        
    upi = db.get_setting('upi_id', 'admin@ybl')
    text = (
        "💳 <b>Deposit via UPI (Auto-Approve)</b>\n\n"
        f"UPI ID: <code>{upi}</code>\n\n"
        "1. Make payment using the UPI ID above.\n"
        "2. Send your <b>12-digit UTR</b> below for instant verification.\n\n"
        "⚠️ <b>STRICT POLICIES:</b>\n"
        "• <b>Minimum Deposit is ₹20.</b> Any deposit below ₹20 will be permanently canceled and no funds will be given.\n"
        "• <b>No Withdrawals.</b> Funds added to the bot must be used for services and cannot be transferred back to your bank account.\n\n"
        "<i>(Type 'cancel' to exit)</i>"
    )
    msg = bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(msg, user_submit_trx, msg.message_id)
    track_and_delete_old(message.chat.id, msg.message_id, 'user_deposit')

def user_submit_trx(message, menu_id):
    safe_delete_user_command(message)
    if not message.text: return bot.send_message(message.chat.id, "❌ Please send text only.")
    
    trx_id = message.text.strip().replace(" ", "")
    if len(trx_id) > 30: return bot.send_message(message.chat.id, "❌ Invalid Transaction ID (Too long).")
    if trx_id.lower() == 'cancel': return bot.send_message(message.chat.id, "✅ Deposit cancelled.")
    if trx_id in ["🛒 Buy Number", "👤 My Wallet", "💰 Deposit Funds", "📜 Order History", "💼 Earn Money"]: return bot.send_message(message.chat.id, "❌ Deposit cancelled (Menu clicked).")
    if len(trx_id) < 8: return bot.send_message(message.chat.id, "❌ Invalid Transaction ID.")
    
    existing = db.query("SELECT status FROM transactions WHERE trx_id = ?", (trx_id,))
    if existing:
        return bot.send_message(message.chat.id, f"❌ <b>Duplicate UTR:</b> This transaction has already been submitted.")

    wait_msg = bot.send_message(message.chat.id, "⏳ <b>Verifying payment...</b> please wait.")

    bp_mid = db.get_setting('bp_merchant_id', '')
    bp_token = db.get_setting('bp_token', '')
    
    if bp_mid and bp_token:
        verify_result = verify_bharatpe_transaction(trx_id, bp_mid, bp_token)
        if verify_result.get("success"):
            amt = verify_result["amount"]
            
            if amt < 20:
                 db.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?)", (trx_id, message.from_user.id, amt, "REJECTED_UNDERPAID", datetime.now()))
                 try: bot.delete_message(wait_msg.chat.id, wait_msg.message_id)
                 except: pass
                 return bot.send_message(message.chat.id, f"❌ <b>Deposit Rejected:</b> You paid ₹{amt}. The minimum deposit is ₹20.")

            db.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?)", (trx_id, message.from_user.id, amt, "APPROVED", datetime.now()))
            db.update_balance(message.from_user.id, amt, "main")
            
            try: bot.delete_message(wait_msg.chat.id, wait_msg.message_id)
            except: pass
            
            return bot.send_message(message.chat.id, f"✅ <b>Auto-Deposit Successful!</b>\n₹{amt} has been instantly added to your wallet.")

    db.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?)", (trx_id, message.from_user.id, 0.0, "PENDING", datetime.now()))
    
    try: bot.delete_message(wait_msg.chat.id, wait_msg.message_id)
    except: pass
    bot.send_message(message.chat.id, "✅ <b>Submitted for Manual Review!</b>\n\n(Auto-verify was unavailable or the UTR was delayed). An admin will verify this shortly.\n<i>(Reminder: Minimum ₹20)</i>")
    
    admin_str = db.get_setting("admin_ids", str(ADMIN_IDS[0]))
    admin_list = [int(x.strip()) for x in admin_str.split(",") if x.strip()]
    for adm in admin_list: 
        try: bot.send_message(adm, f"🔔 <b>New Manual Deposit</b>\nUser: {message.from_user.id}\nTRX: <code>{trx_id}</code>", reply_markup=UIFactory.trx_approval(trx_id))
        except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_pay_", "reject_pay_")))
def handle_payment_decision(call):
    if not is_admin(call.from_user.id): return
    action, t_id = "APPROVED" if "approve" in call.data else "REJECTED", call.data.split("_")[2]
    t_data = db.query("SELECT user_id, status FROM transactions WHERE trx_id = ?", (t_id,))
    if not t_data or t_data[0][1] != "PENDING": return bot.answer_callback_query(call.id, "Already processed!", show_alert=True)

    if action == "REJECTED":
        db.execute("UPDATE transactions SET status = 'REJECTED' WHERE trx_id = ?", (t_id,))
        bot.edit_message_text(f"❌ Payment {t_id} Rejected.", call.message.chat.id, call.message.message_id)
        try: bot.send_message(t_data[0][0], f"❌ <b>Deposit Declined:</b> TRX <code>{t_id}</code> was rejected by Admin. (Remember minimum deposit is ₹20).")
        except: pass
    else:
        msg = bot.send_message(call.message.chat.id, f"Enter amount to credit for TRX {t_id} (or 'cancel'):")
        bot.register_next_step_handler(msg, finalize_approval, t_id, t_data[0][0])

def finalize_approval(message, t_id, u_id):
    if not message.text: return bot.send_message(message.chat.id, "❌ Please send text only.")
    if message.text.lower() == 'cancel': return bot.send_message(message.chat.id, "✅ Cancelled approval flow.")
    try:
        amt = float(message.text)
        if db.query("SELECT status FROM transactions WHERE trx_id = ?", (t_id,))[0][0] != "PENDING": return bot.send_message(message.chat.id, "❌ Blocked: No longer pending.")
        db.execute("UPDATE transactions SET status = 'APPROVED', amount = ? WHERE trx_id = ?", (amt, t_id))
        db.update_balance(u_id, amt, "main")
        bot.send_message(message.chat.id, f"✅ Payment of ₹{amt} Credited to user {u_id}.")
        try: bot.send_message(u_id, f"🎉 <b>Success!</b> ₹{amt} added to your wallet.")
        except: pass
    except: bot.send_message(message.chat.id, "❌ Invalid amount entered.")

# =================================================================
# 14. ADVANCED AUTO-MODERATION (THE BLACK HOLE)
# =================================================================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'sticker', 'voice'])
def catch_random_messages(message):
    spam_status = check_spam(message.from_user.id)
    if spam_status == "BANNED": return
    if spam_status: return
    
    bot.clear_step_handler_by_chat_id(message.chat.id)
    
    if message.text and any(domain in message.text.lower() for domain in ["http://", "https://", "t.me/", "www."]):
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        warning = bot.send_message(message.chat.id, "🚫 <b>Auto-Moderation:</b> Links and unauthorized promotions are immediately removed.")
        threading.Timer(5.0, lambda: bot.delete_message(message.chat.id, warning.message_id)).start()
        return

    if message.text:
        bot.reply_to(message, "🤖 <b>Unrecognized Input.</b>\nPlease use the menu buttons below to interact with the bot.", reply_markup=UIFactory.reply_main_menu())

if __name__ == "__main__":
    logger.info("Enterprise Monolith V19 (AutoPay + Diagnostics) Spinning Up...")
    bot.infinity_polling(timeout=60, long_polling_timeout=45, logger_level=logging.ERROR)