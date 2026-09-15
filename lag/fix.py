# ============================================================
# ============ FIX.PY - CVIP JSON ===========================
# ============================================================

import threading
import json
import os
import requests
import time
import logging
import socket
import sys
import base64
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from main import (
    FFClient, get_available_account,
    get_remaining_count, stop_current, thread_lock,
    load_accounts
)
import main as _main
from reg import create_account, save_account

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

acc_file_lock = threading.Lock()
ghost_file_lock = threading.Lock()

# ============================================================
# ============ TELEGRAM BOT =================================
# ============================================================

TELEGRAM_TOKEN = "8628120697:AAHr4jQqFVltvh1_3QX6HcBG9gbzb8jmVUQ"

try:
    bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode='HTML')
    logger.info("Telegram bot initialized")
except Exception as e:
    logger.error(f"Failed to init bot: {e}")
    bot = None

auto_stop_timer = None
active_threads = []

pending_replacement_uids = []
replacement_lock = threading.Lock()

# ============================================================
# ============ CHECK JOIN GROUP ==============================
# ============================================================

# 2 nhóm bắt buộc join
REQUIRED_GROUPS = [
    {"id": "@zancommunity", "name": "Nhóm Cộng Đồng", "link": "https://t.me/zancommunity"},
    {"id": "@zanxchannel", "name": "Kênh Thông Báo", "link": "https://t.me/zanxchannel"},
]

def check_join_groups(user_id):
    """Check user đã join đủ 2 nhóm chưa"""
    if is_admin(user_id):
        return True   # Admin không cần check
    
    for group in REQUIRED_GROUPS:
        try:
            member = bot.get_chat_member(group["id"], user_id)
            if member.status not in ['member', 'creator', 'administrator']:
                return False
        except Exception as e:
            logger.error(f"Check group error: {e}")
            return False
    
    return True

def get_join_keyboard():
    """Tạo nút join nhóm"""
    markup = InlineKeyboardMarkup()
    for group in REQUIRED_GROUPS:
        btn = InlineKeyboardButton(
            text=f"📌 {group['name']}",
            url=group["link"]
        )
        markup.add(btn)
    btn_check = InlineKeyboardButton(
        text="✅ TÔI ĐÃ THAM GIA",
        callback_data="check_joined"
    )
    markup.add(btn_check)
    return markup

def send_join_warning(message):
    """Gửi cảnh báo phải join nhóm"""
    text = """<blockquote>⚠️ YÊU CẦU THAM GIA NHÓM

Bạn cần tham gia 2 nhóm dưới đây để sử dụng bot:

1️⃣ Nhóm Cộng Đồng
2️⃣ Kênh Thông Báo

Sau khi tham gia, bấm TÔI ĐÃ THAM GIA để xác nhận.</blockquote>"""
    bot.reply_to(
        message,
        text,
        parse_mode="HTML",
        reply_markup=get_join_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def callback_check_joined(call):
    try:
        user_id = call.from_user.id
        
        if check_join_groups(user_id):
            # Xoá tin nhắn cũ
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except: pass
            
            # Gửi tin xác nhận mới
            bot.send_message(
                call.message.chat.id,
                "<blockquote>VERIFY SUCCESS</blockquote>",
                parse_mode="HTML"
            )
            
            bot.answer_callback_query(
                call.id,
                "VERIFY SUCCESS"
            )
        else:
            bot.answer_callback_query(
                call.id,
                "NOT JOINED YET",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Callback error: {e}")

# ============================================================
# ============ HÀM REPLY JSON ===============================
# ============================================================

def reply_json(message, data):
    """Reply dạng json"""
    try:
        json_text = json.dumps(data, indent=2, ensure_ascii=False)
        bot.reply_to(
            message,
            f"```json\n{json_text}\n```",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Reply JSON error: {e}")

# ============================================================
# ============ REPLENISH ====================================
# ============================================================

def check_and_replenish_acc_json(filename="acc.json"):
    with acc_file_lock:
        data = load_accounts(filename)
        if len(data) < 10:
            num_to_create = random.randint(10, 15)
            logger.info(f"{filename} under 10 acc ({len(data)}). Creating {num_to_create}...")
            for _ in range(num_to_create):
                acc = create_account(name_prefix="zanxlag", region="VN")
                if acc:
                    uid = str(acc.get("uid"))
                    pwd = str(acc.get("password", acc.get("raw_password", "")))
                    data[uid] = pwd
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"Total: {len(data)}")

def check_and_replenish_lag_json(filename="lag.json"):
    with ghost_file_lock:
        data = {}
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        if not isinstance(data, dict):
            data = {}
            
        if len(data) < 10:
            num_to_create = 30
            logger.info(f"{filename} under 10 acc ({len(data)}). Creating {num_to_create}...")
            for _ in range(num_to_create):
                acc = create_account(name_prefix="zanxlag", region="VN")
                if acc:
                    uid = str(acc.get("uid"))
                    pwd = str(acc.get("password", acc.get("raw_password", "")))
                    data[uid] = pwd
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"Total: {len(data)}")

# ============================================================
# ============ LAUNCH BOT ===================================
# ============================================================

def queue_uid_for_replacement(old_uid):
    global pending_replacement_uids
    with replacement_lock:
        pending_replacement_uids.append(str(old_uid))
        if len(pending_replacement_uids) >= 2:
            uids_to_remove = pending_replacement_uids[:2]
            pending_replacement_uids = pending_replacement_uids[2:]
            _execute_batch_replacement(uids_to_remove)

def _execute_batch_replacement(old_uids):
    def _worker():
        filename = "acc.json"
        try:
            with acc_file_lock:
                data = {}
                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    with open(filename, "r", encoding="utf-8") as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            data = {}
                if not isinstance(data, dict):
                    data = {}
                for old_uid in old_uids:
                    data.pop(str(old_uid), None)
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            check_and_replenish_acc_json(filename)
        except Exception as e:
            logger.error(f"Replace error: {e}")
    threading.Thread(target=_worker, daemon=True).start()

def auto_reg_replacement(old_uid=None):
    if old_uid:
        queue_uid_for_replacement(old_uid)

def _launch_bot(team_code, uid, pwd, stop_event):
    try:
        client = FFClient(uid, pwd, team_code)
        client._stop_event = stop_event
        client.is_running = True
        client.start()
        client.join()
    except Exception as e:
        logger.error(f"Bot error [{uid} - {team_code}]: {e}")
    finally:
        with thread_lock:
            _main.current_stop_event = None
            _main.current_thread = None
        auto_reg_replacement(old_uid=uid)

def start_all_bots(tc, delay=5):
    filename = "lag.json"
    check_and_replenish_lag_json(filename)
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            accounts = json.load(f)
    except Exception:
        accounts = {}

    if not accounts:
        return False, f"No account in {filename}", 0, 0

    items = list(accounts.items())
    selected_items = items[:6]
    remaining_items = items[6:]
    selected_accounts = dict(selected_items)
    
    with ghost_file_lock:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(dict(remaining_items), f, indent=4, ensure_ascii=False)

    stop_current()
    old = _main.current_thread
    if old and old.is_alive():
        old.join(timeout=10)
        if old.is_alive() and hasattr(_main, 'current_stop_event') and _main.current_stop_event:
            _main.current_stop_event.set()

    global active_threads
    active_threads = [t for t in active_threads if t.is_alive()]

    stop_event = threading.Event()
    started_count = 0

    for uid, pwd in selected_accounts.items():
        t = threading.Thread(target=_launch_bot, args=(tc, uid, pwd, stop_event), daemon=True)
        t._teamcode = tc
        active_threads.append(t)
        t.start()
        started_count += 1

    with thread_lock:
        _main.current_stop_event = stop_event
        if active_threads:
            _main.current_thread = active_threads[-1]

    _auto_stop_bot(delay)
    return True, None, started_count, len(remaining_items)

def _auto_stop_bot(delay_seconds=5):
    global auto_stop_timer
    def stop_after_delay():
        time.sleep(delay_seconds)
        stopped = stop_current()
        logger.info(f"Auto-stopped after {delay_seconds}s: {stopped}")
    if auto_stop_timer:
        auto_stop_timer.cancel()
    auto_stop_timer = threading.Timer(delay_seconds, stop_after_delay)
    auto_stop_timer.daemon = True
    auto_stop_timer.start()

# ============================================================
# ============ ADMIN ========================================
# ============================================================

ADMIN_IDS = [8722607800]
bot_enabled = True
last_attack_time = 0

def is_admin(user_id):
    return user_id in ADMIN_IDS

def check_box_chat(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "ERROR: This command only works in group chat!")
        return False
    return True

# ============================================================
# ============ LỆNH /start /help /menu (TEXT THƯỜNG) ========
# ============================================================

if bot:
    @bot.message_handler(commands=['start', 'help', 'menu'])
    def help_command(message):
        if not check_box_chat(message): return
        
        # CHECK JOIN NHÓM
        if not check_join_groups(message.from_user.id):
            send_join_warning(message)
            return
        
        menu_text = """<blockquote>⚡FREE FIRE BOT SYSTEM</blockquote>

🚀 /c &lt;teamcode&gt;
Run max 6 bots from lag.json

📌 Example: /c 1234567

🟢 Status: Online
"""
        bot.reply_to(message, menu_text, parse_mode="HTML")  
              
    @bot.message_handler(commands=['bat'])
    def bat_command(message):
        if not check_box_chat(message): return
        if not is_admin(message.from_user.id): return
        global bot_enabled
        bot_enabled = True
        reply_json(message, {
            "status": "success",
            "message": "SYSTEM ENABLED",
            "bot_enabled": True
        })

    @bot.message_handler(commands=['tat'])
    def tat_command(message):
        if not check_box_chat(message): return
        if not is_admin(message.from_user.id): return
        global bot_enabled
        bot_enabled = False
        reply_json(message, {
            "status": "success",
            "message": "SYSTEM DISABLED",
            "bot_enabled": False
        })

# ============================================================
# ============ LỆNH /reg ====================================
# ============================================================

if bot:
    def add_account_to_file(uid, password, filename):
        try:
            data = {}
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                with open(filename, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        data = {}
            if not isinstance(data, dict):
                data = {}
            data[uid] = password
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error add to {filename}: {e}")
            return False

    @bot.message_handler(commands=['reg'])
    def reg_command(message):
        if not check_box_chat(message): return
        if not is_admin(message.from_user.id): return
        try:
            args = message.text.split(maxsplit=3)
            if len(args) < 3:
                reply_json(message, {
                    "status": "error",
                    "message": "Missing arguments",
                    "usage": "/reg <count> <name> [lag/acc/all]",
                    "example": "/reg 10 zan lag"
                })
                return
            
            try:
                count = int(args[1])
                if count <= 0:
                    reply_json(message, {
                        "status": "error",
                        "message": "Count must be > 0"
                    })
                    return
            except ValueError:
                reply_json(message, {
                    "status": "error",
                    "message": "Count must be number"
                })
                return
            
            bot_name = args[2].strip()
            target_file = args[3].strip().lower() if len(args) > 3 else "lag"
            
            files_to_save = []
            if target_file == "lag":
                files_to_save = ["lag.json"]
            elif target_file == "acc":
                files_to_save = ["acc.json"]
            elif target_file == "all":
                files_to_save = ["acc.json", "lag.json"]
            else:
                files_to_save = ["lag.json"]
            
            msg = bot.reply_to(
                message,
                f"```json\n{json.dumps({'status': 'processing', 'count': count, 'files': files_to_save}, indent=2, ensure_ascii=False)}\n```",
                parse_mode="Markdown"
            )
            
            success_count = 0
            for i in range(count):
                try:
                    acc = create_account(name_prefix=bot_name, region="VN")
                    if not acc:
                        continue
                    uid = str(acc.get("uid"))
                    pwd = str(acc.get("password", acc.get("raw_password", "")))
                    if not uid or not pwd:
                        continue
                    
                    for fname in files_to_save:
                        lock = ghost_file_lock if fname != "acc.json" else acc_file_lock
                        with lock:
                            add_account_to_file(uid, pwd, fname)
                    success_count += 1
                except Exception:
                    pass
            
            try:
                bot.delete_message(message.chat.id, msg.message_id)
            except: pass
            
            reply_json(message, {
                "status": "completed",
                "total": count,
                "success": success_count,
                "failed": count - success_count,
                "files": files_to_save
            })
        except Exception as e:
            reply_json(message, {
                "status": "error",
                "message": str(e)
            })

# ============================================================
# ============ LỆNH /cvip (AI CŨNG DÙNG ĐƯỢC) ===============
# ============================================================
if bot:
    @bot.message_handler(commands=['c'])
    def attack_command(message):
        if not check_box_chat(message): return
        
        # CHECK JOIN NHÓM
        if not check_join_groups(message.from_user.id):
            send_join_warning(message)
            return
        
        args = message.text.split()
        
        if len(args) < 2:
            bot.reply_to(
                message,
                "<blockquote>/c &lt;teamcode&gt;</blockquote>",
                parse_mode="HTML"
            )
            return
        
        global last_attack_time
        try:
            if time.time() - last_attack_time < 7:
                wait = int(7 - (time.time() - last_attack_time))
                reply_json(message, {
                    "status": "cooldown",
                    "message": "Vui lòng đợi",
                    "wait_seconds": wait
                })
                return
            
            tc = args[1].strip()
            delay = 20
            if len(args) >= 3 and is_admin(message.from_user.id):
                try: delay = int(args[2])
                except: delay = 20

            if not tc.isdigit() or len(tc) != 7:
                stop_current()
                reply_json(message, {
                    "status": "error",
                    "message": "Teamcode không hợp lệ",
                    "teamcode": tc,
                    "required": "7 chữ số",
                    "action": "Đã dừng lag"
                })
                return

            success, err_msg, total_started, remaining = start_all_bots(tc, delay)
            if not success:
                reply_json(message, {
                    "status": "error",
                    "message": err_msg
                })
                return

            last_attack_time = time.time()
            reply_json(message, {
                "status": "success",
                "message": "CVIP STARTED",
                "teamcode": tc,
                "bots_started": total_started,
                "accounts_left": remaining,
                "delay": delay,    
            })
        except Exception as e:
            logger.error(f"/c error: {e}")
            reply_json(message, {
                "status": "error",
                "message": str(e)
            })      
                          
# ============================================================
# ============ LỆNH /stop /status ===========================
# ============================================================

if bot:
    @bot.message_handler(commands=['stop'])
    def stop_command(message):
        if not check_box_chat(message): return
        if not is_admin(message.from_user.id): return
        global auto_stop_timer
        if auto_stop_timer:
            auto_stop_timer.cancel()
            auto_stop_timer = None
        stopped = stop_current()
        reply_json(message, {
            "status": "success" if stopped else "info",
            "message": "Stopped all bots" if stopped else "No bots running",
            "stopped": stopped
        })

    @bot.message_handler(commands=['status'])
    def status_command(message):
        if not check_box_chat(message): return
        if not is_admin(message.from_user.id): return
        active_count = sum(1 for th in active_threads if th.is_alive())
        remaining = get_remaining_count()
        reply_json(message, {
            "status": "online",
            "bots_running": active_count,
            "accounts_left": remaining,
            "system_enabled": bot_enabled,
            "time": time.strftime("%H:%M:%S %d/%m/%Y")
        })

# ============================================================
# ============ FLASK API ====================================
# ============================================================

@app.route("/attack", methods=["GET"])
def attack_all():
    tc = request.args.get("tc", "").strip()
    delay = request.args.get("delay", "10", type=int)
    if not tc.isdigit() or len(tc) != 7:
        stop_current()
        return jsonify({"ok": False, "error": "tc must be 7 digits"}), 400
    check_and_replenish_lag_json("lag.json")
    success, err_msg, total_started, remaining = start_all_bots(tc, delay)
    if not success: return jsonify({"ok": False, "error": err_msg}), 503
    return jsonify({"ok": True, "tc": tc, "total_bots": total_started, "delay": delay, "left": remaining})

@app.route("/stop", methods=["GET"])
def stop():
    global auto_stop_timer
    if auto_stop_timer:
        auto_stop_timer.cancel()
        auto_stop_timer = None
    stopped = stop_current()
    return jsonify({"ok": stopped, "msg": "stopped" if stopped else "no bot running"})

@app.route("/status", methods=["GET"])
def status():
    active_count = sum(1 for th in active_threads if th.is_alive())
    return jsonify({"active": active_count > 0, "active_count": active_count, "accounts": get_remaining_count()})

# ============================================================
# ============ POLLING RECONNECT ============================
# ============================================================

bot_polling_thread = None
bot_should_stop = False

def run_telegram_bot_with_reconnect(max_retries=10, base_delay=2):
    global bot_should_stop
    if not bot:
        return
    retry_count = 0
    delay = base_delay
    while not bot_should_stop and retry_count < max_retries:
        try:
            logger.info(f"Telegram polling started... (Attempt {retry_count + 1})")
            bot.polling(non_stop=True, interval=0, timeout=30, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"Telegram polling error: {e}")
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(delay)
                delay = min(delay * 2, 60)

def start_telegram_polling():
    global bot_polling_thread, bot_should_stop
    if not bot:
        return
    bot_should_stop = False
    bot_polling_thread = threading.Thread(
        target=run_telegram_bot_with_reconnect,
        kwargs={"max_retries": 10, "base_delay": 2},
        daemon=True,
        name="TelegramBotPolling"
    )
    bot_polling_thread.start()

def stop_telegram_polling():
    global bot_should_stop, bot_polling_thread
    bot_should_stop = True
    if bot:
        try:
            bot.stop_polling()
        except Exception:
            pass
    if bot_polling_thread and bot_polling_thread.is_alive():
        bot_polling_thread.join(timeout=5)

def ping_api_keep_alive():
    url = "http://zanlagx.onrender.com/status"
    
    while True:
        try:
            resp = requests.get(url, timeout=10)
            print(f"[PING] ✅ {url} - Status: {resp.status_code}")
        except Exception as e:
            print(f"[PING] ❌ Lỗi: {e}")
        
        time.sleep(600) 

def start_ping_thread():
    thread = threading.Thread(target=ping_api_keep_alive, daemon=True)
    thread.start()
    print("[PING] ✅ Đã khởi động thread ping API mỗi 10 phút!")


# ============================================================
# ============ START ========================================
# ============================================================

if __name__ == "__main__":
    start_ping_thread() 
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Remaining accounts: {get_remaining_count()}")
    if bot:
        start_telegram_polling()
    try:
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    finally:
        stop_telegram_polling()
