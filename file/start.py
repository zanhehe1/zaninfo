import threading, json, socket, time, random, datetime, aiohttp, asyncio, os, struct
import datetime as dt
from lib import *
from GPackGEN import *
from ReQAPI import *
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, jsonify, request 
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import time
import requests
from functools import wraps
import threading
import telebot
import socket
import traceback
import string
team_cooldown = {}  
lag_cooldown = {}  
user_msg_map = {}
temp_tokens = {}  
import telebot
import time
import sys
import socket
import traceback

# ====== BOT TOKEN ======
TELEGRAM_BOT_TOKEN = "8895100931:AAFw7LlRXlHRI3lvPbGl7Gj_gXdac7ZVtEs"
telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

# ====== HÀM IN ĐẬM ======
def p(text):
    print(f"📌 {text}")

def p_ok(text):
    print(f"✅ {text}")

def p_err(text):
    print(f"❌ {text}")

def p_warn(text):
    print(f"⚠️ {text}")

def p_info(text):
    print(f"ℹ️ {text}")

def line():
    print("─" * 50)

def test_step_by_step():
    print()
    line()
    p("🔍 BẮT ĐẦU KIỂM TRA TELEGRAM BOT")
    line()
    
    print()
    p("[1/6] KIỂM TRA INTERNET")
    line()
    
    try:
        socket.gethostbyname('1.1.1.1')
        p_ok("Kết nối Internet: OK")
    except Exception as e:
        p_err(f"Kết nối Internet: FAIL - {e}")
        p_warn("💡 Kiểm tra WiFi/4G, bật tắt máy bay")
    
    # ====== BƯỚC 2: TEST DNS ======
    print()
    p("[2/6] KIỂM TRA DNS")
    line()
    
    try:
        ip = socket.gethostbyname('api.telegram.org')
        p_ok(f"DNS api.telegram.org -> {ip}")
    except socket.gaierror as e:
        p_err(f"DNS FAIL: {e}")
        p_warn("💡 DNS bị lỗi, chạy lệnh: echo 'nameserver 8.8.8.8' > /etc/resolv.conf")
    except Exception as e:
        p_err(f"DNS ERROR: {e}")
    
    print()
    p("[3/6] KIỂM TRA CỔNG 443")
    line()
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('api.telegram.org', 443))
        sock.close()
        
        if result == 0:
            p_ok("Cổng 443: MỞ")
        else:
            p_err(f"Cổng 443: ĐÓNG - Lỗi {result}")
            p_warn("💡 Có thể bị tường lửa chặn hoặc Telegram bị block")
    except Exception as e:
        p_err(f"Lỗi test port: {e}")
   
    print()
    p("[4/6] KIỂM TRA TOKEN")
    line()
    
    try:
        me = telegram_bot.get_me()
        p_ok(f"Token hợp lệ!")
        p_info(f"Bot: @{me.username}")
        p_info(f"Name: {me.first_name}")
        p_info(f"ID: {me.id}")
    except telebot.apihelper.ApiException as e:
        if "401" in str(e):
            p_err("Token KHÔNG HỢP LỆ (401 Unauthorized)")
            p_warn("💡 Kiểm tra lại token bot!")
        elif "404" in str(e):
            p_err("Token KHÔNG TỒN TẠI (404 Not Found)")
            p_warn("💡 Token sai hoặc bot đã bị xóa!")
        else:
            p_err(f"Token lỗi: {e}")
    except Exception as e:
        p_err(f"Lỗi token: {e}")
    
    print()
    p("[5/6] KIỂM TRA WEBHOOK")
    line()
    
    try:
        info = telegram_bot.get_webhook_info()
        if info.url:
            p_warn(f"Webhook đang set: {info.url}")
            p_warn("💡 Xóa webhook trước khi polling!")
            try:
                telegram_bot.delete_webhook()
                p_ok("Đã xóa webhook!")
            except Exception as e:
                p_err(f"Không xóa được webhook: {e}")
        else:
            p_ok("Không có webhook - OK!")
    except Exception as e:
        p_err(f"Lỗi webhook: {e}")
    print()
    p("[6/6] TEST GỬI TIN NHẮN")
    line()
    
    try:       
        test_chat_id = 8722607800 
        telegram_bot.send_message(test_chat_id, "🔬 Test kết nối thành công!")
        p_ok("Gửi tin nhắn thành công!")
    except Exception as e:
        p_warn(f"Gửi tin nhắn thất bại: {e}")
        p_info("💡 Bot chưa có quyền gửi tin nhắn hoặc chat_id sai")
    
    print()
    line()
    p("🏁 KẾT THÚC KIỂM TRA")
    line()
    print()

def run_bot_with_log():
    print()
    line()
    p("🚀 BẮT ĐẦU CHẠY BOT")
    line()
    print()
    
    attempt = 0
    while True:
        attempt += 1
        
        print()
        p(f"🔄 Lần thử {attempt}")
        line()
        
        try:
            p("📡 Đang kết nối Telegram API...")
            
            # Xóa webhook
            try:
                telegram_bot.delete_webhook()
                p_ok("Đã xóa webhook")
            except Exception as e:
                p_warn(f"Không xóa được webhook: {e}")
            
            p("⏳ Bắt đầu polling...")
            print()
            
            # Bắt đầu polling
            telegram_bot.infinity_polling(
                timeout=60,
                long_polling_timeout=30,
                allowed_updates=['message', 'callback_query']
            )
            
        except Exception as e:
            print()
            line()
            p_err("🔥 LỖI XẢY RA:")
            line()
            
            error_str = str(e)
            
            # Phân tích lỗi
            if "No address associated with hostname" in error_str:
                p_err("📛 DNS LỖI: Không tìm thấy api.telegram.org")
                p_info("💡 Chạy lệnh: echo 'nameserver 8.8.8.8' > /etc/resolv.conf")
                p_info("💡 Hoặc dùng: echo 'nameserver 1.1.1.1' >> /etc/resolv.conf")
                
            elif "Network is unreachable" in error_str:
                p_err("📛 MẠNG LỖI: Không có kết nối Internet")
                p_info("💡 Kiểm tra WiFi/4G")
                p_info("💡 Chạy: ping 1.1.1.1")
                
            elif "Connection timed out" in error_str or "Read timed out" in error_str:
                p_err("📛 TIMEOUT: Kết nối quá chậm")
                p_info("💡 Mạng yếu hoặc đang bị nghẽn")
                p_info("💡 Thử dùng VPN hoặc proxy")
                
            elif "Software caused connection abort" in error_str:
                p_err("📛 KẾT NỐI BỊ NGẮT: Connection abort")
                p_info("💡 Thử restart bot hoặc kiểm tra tường lửa")
                
            elif "401" in error_str:
                p_err("📛 TOKEN SAI: 401 Unauthorized")
                p_info("💡 Kiểm tra lại BOT_TOKEN")
                
            elif "404" in error_str:
                p_err("📛 TOKEN KHÔNG TỒN TẠI: 404 Not Found")
                p_info("💡 Bot đã bị xóa hoặc token sai")
                
            else:
                p_err(f"📛 LỖI KHÔNG XÁC ĐỊNH:")
                p_err(error_str[:300])
            
            print()
            p_info("📦 Stack trace chi tiết:")
            line()
            traceback.print_exc()
            line()
            
            # Đợi rồi thử lại
            wait_time = 10
            p_info(f"⏳ Đợi {wait_time} giây rồi thử lại...")
            time.sleep(wait_time)

TELEGRAM_ADMINS = [8722607800]

class FreeFireTCP:
 def __init__(self, bot_config, manager):
  self.running = True
  self.bot_config = bot_config
  self.manager = manager
  self.running_event = threading.Event()
  self.running_event.set()
  self.stop_actions = threading.Event()
  self.stop_emote = threading.Event()
  self.rstatus = (0, 0)
  self.ids = []
  self.status = True
  self.started = False
  self.base_url = "https://clientbp.ggblueshark.com"
  self.reconnect_lock = threading.Lock()
  self.last_spam_time = {}
  self.roomcode = self.packetAuth = self.playerstatus = None
  self.AuthenCode = self.sock39699 = self.sock39801 = None
  self.ChatIP = self.OnlineIP = self.OnlinePort = self.ChatPort = None
  self.roomid = self.GuildIds = self.DesId = self.botid = None
  self.key = self.iv = self.token = b''
  self.login_session = self._data = None
  self.botid = self.nickname = self.region = None
  self.emoting = False
  self.reset_count = 0  # THÊM DÒNG NÀY
  self.Emotes = {
    'MP40V2': 909040010,
    'MP40': 909000075,
    'AK47': 909000063,
    'M1887': 909035007,
    'XM8': 909000085,
    'FAMAS': 909000090,
    'UMP': 909000098,
    'PARAFAL': 909045001,
    'M1014': 909000081,
    'M1014V2': 909039011,
    'P90': 909049010,
    'SCAR': 909000068,
    'M4A1': 909039011,
    'THOMPSON': 909038010,
    'GROZA': 909041005,
    'MP5': 909033002,
    'G18': 909038012
   }

  self.FULL_GUNS = [ 909049010, 909051003, 909033002, 909041005, 
909038010, 909039011, 909040010, 909000081, 909000085, 909000063,
 909000075, 909033001, 909000090, 909000068, 909000098, 909035007,
 909037011, 909038012, 909035012, 909042008, 909035007
  ]
  
 def _IIl(self, logindata, jsdata):
  self.cleanup()
  time.sleep(0.5)
  self._gen = TAO_PACKET(logindata, jsdata)
  self._bot = self.bot_session(self)
  self.running_event.set()
  time.sleep(1)
  threading.Thread(target=self.connect39801, daemon=True).start()
  threading.Thread(target=self.connect39699, daemon=True).start()

 def _save_history(self, action, data):
    """Lưu lịch sử redeem vào file"""
    try:
        history_file = "redeem_history.json"
        history = []
        
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    if not isinstance(history, list):
                        history = []
            except:
                history = []
        
        history.append({
            "action": action,
            "data": data,
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
            
    except Exception as e:
        print(f"[_save_history] Error: {e}")

 def visit_thread(bot, cid, type, uid):
  result = send_visit(uid)
  bot.reply(cid, type, result) 
 
 def cleanup(self):
  self.running_event.clear()
  sockets = [self.sock39699, self.sock39801]
  for sock in sockets:
   try:
    if sock:
     sock.shutdown(2)
     sock.close()
   except Exception as e: pass
  self.sock39699 = self.sock39801 = None

 def _keep_alive(self, sock):
    while self.running_event.is_set() and sock:
        try:
            sock.send(bytes([0, 2, 0, 1]))
            time.sleep(20)  
        except:          
            self.cleanup()
            time.sleep(2)
            self.start()
            break
             
 def restart_bot(self):
  self.cleanup()
  time.sleep(2)
  self.running_event.set()
  self.started = False
  self.start()

 def start(self):
    if self.started: return 
    self.started = True
    self.running_event.set()
    threading.Thread(target=self.rstart, daemon=True).start()
    
 def AntiDisconnect(self, sock):
  while True:
   sock.send(bytes([0, 2, 0, 1]))
   time.sleep(25)
                   
 def connect39801(self):
  with self.reconnect_lock:
   if not self.running_event.is_set(): return
   client = None
   try:
    client = socket.create_connection((self.ChatIP, int(self.ChatPort)))
    client.sendall(self.packetAuth)
    guild_active = self.bot_config.get("active-clan", True)
    if self.GuildIds and guild_active:
     client.send(self._bot.join_channel(self.GuildIds, self.AuthenCode, 1))
    client.send(self._bot.join_channel(None, None, 5))
    self.sock39801 = client
    while self.running_event.is_set():
     try:
      data = client.recv(3300)
      if len(data) == 0: break
      if data.hex()[:4] == "1200" and len(data) > 50:
       threading.Thread(target=self.C1200, args=(data, client,)).start()
     except Exception as e: break
   except Exception as e: pass
   finally:
    if client:
     try: client.close()
     except Exception as e: pass
    self.sock39801 = None
    if self.running_event.is_set():
     time.sleep(5)
     threading.Thread(target=self.connect39801, daemon=True).start()
 def connect39699(self):
  if not self.running_event.is_set(): return
  client = None
  try:
   client = socket.create_connection((self.OnlineIP,  int(self.OnlinePort)))
   client.sendall(self.packetAuth)
   self.sock39699 = client
   while self.running_event.is_set():
    try:
     data = client.recv(3300)
     if len(data) == 0: break
     if data.hex()[:4] == "0f00":
      decdata = json.loads(protobuf_dec(data.hex()[10:]))
      self.playerstatus = decdata
      rid = decdata.get("5").get("1").get("15", None)
      if rid: self.roomid = rid
      else: self.roomid = None

     if data.hex()[:4] == "0600" and len(data) <= 55:
      res = json.loads(protobuf_dec(data.hex()[10:]))
      uid = res.get("5").get("1")
      # ConfirmFriendRequest(uid, self.token, self.base_url)
      messages = """[c][b][C678DD]const [61AFEF]Response [E5C07B]= [C678DD]() [ABB2BF]=> [ABB2BF]{{
  [C678DD]return [ABB2BF]{{
    [E5C07B]uid[E5C07B]: [E5C07B]{}[ABB2BF],
    [E5C07B]tittle[ABB2BF]: [98C379]"Request accepted"[ABB2BF],
    [E5C07B]message[ABB2BF]: [98C379]"type /nofree"[ABB2BF],
    [E5C07B]telegram[ABB2BF]: [98C379]"@zanbackj"[ABB2BF]
  [ABB2BF]}}
[ABB2BF]}}""".format(uid)
      self._bot.reply(uid, 2, messages)
     if self.status: threading.Thread(target=self.gringay, args=(data,)).start()
    except Exception as e: 
     if not self.running_event.is_set(): break
  except Exception as e: pass
  finally:
   if client:
    try: client.close()
    except Exception as e: pass
   self.sock39699 = None
   if self.running_event.is_set():
    time.sleep(3)
    threading.Thread(target=self.connect39699, daemon=True).start()
                                                  
 def C1200(self, data, client):
    try:
        data = data1200(data)
        if not data.valid:
            return False
        uid, cid, type = data.uid, data.cid, data.type
        if int(self.botid) in [cid, uid]:
            return False
        message, name = data.message, data.name
        idlist = self.get_user_status(1)
        is_admin = AdminManager.is_admin(self.bot_config["bot_id"], uid)

        # ... phần code xử lý lệnh ở giữa ...

    except Exception as e:
        self.rstatus, self.ids = (0, 0), []
        print(f"[C1200] Error: {e}")
        return False
         
 def leave(self, uid, delay):
  try:
   time.sleep(int(delay))
   self.rstatus = (0, 0)
   self.ids = []
   self.sock39801.send(self._bot.leave_channel(uid, None))
   self.sock39699.send(self._bot.leave_squad(uid))
  except: self.rstatus, self.ids = (0, 0), []


 def gringay(self, data):
  if data.hex()[:4] == "0500" and len(data) >= 80:
   data = json.loads(protobuf_dec(data.hex()[10:]))
   if not isinstance(data.get("4"), (str, int)): return
   if int(data["4"]) in [3, 6, 8, 44, 56] and self.rstatus[0] == 10:
    self.ids.extend(extract_uid_fields(data))
   
   if int(data["4"]) == 3:
    print(data)
    uid = data.get("5").get("1")
    rc = data.get("5").get("8")
    
    self.sock39801.send(self._bot.join_channel(uid, rc, None))
    g01 = "[B][c]\n[%s]Dịch vụ: [U]LIKE - BOT - API.[/U][%s]\n\nTelegram: [00FFFF]@zanbackj& [00FF00]TikTok: [00FFFF]zanbackjq\n[000000]"%(grcolor(), grcolor())
    g02 = "\n".join([f"[{grcolor()}]BinhAn  " * 8 for _ in range(55)])
    self.sock39699.send(self._bot.reject_invite(random.choice([g01, g02]), uid, uid))
    
   if int(data["4"]) == 6:
    if isinstance(self.rstatus, tuple) and self.rstatus[0] == 1:
        try:
            self.sock39699.send(self._bot.leave_squad(000))
            uid = data.get("5", {}).get("1")
            recruit_code = data.get("5", {}).get("17")
            self.sock39801.send(self._bot.join_channel(uid, recruit_code, None))
            
            for _ in range(10):
                self._bot.reply(uid, None, self.rstatus[1])
                time.sleep(0.5)
            self.rstatus = (0, 0)
        except Exception as e:
            self.rstatus, self.ids = (0, 0), []

    if isinstance(self.rstatus, tuple) and self.rstatus[0] == 2:
        try:
            uid = data.get("5", {}).get("1")
            secret_code = data.get("5", {}).get("31")
            custom_name = self.rstatus[2] if len(self.rstatus) > 2 else None
            
            self.rstatus = (0, 0)
            if not uid or not secret_code:
                return False
            
            current_code = self.rstatus[1]
            self.sock39699.send(self._bot.leave_squad(00000))
            
            if custom_name:
                # Ghost với tên custom
                colors = ["[FF0000]", "[00FF00]", "[0000FF]", "[FFFF00]", "[FF00FF]", "[00FFFF]"]
                color = random.choice(colors)
                
                fields = {}
                fields[0] = 5
                fields[1] = 61
                fields[2] = {}
                fields[2][1] = int(uid)
                fields[2][2] = {}
                fields[2][2][1] = int(uid)
                fields[2][2][3] = f"[b][c]{color}{custom_name}"
                fields[2][2][6] = int(time.time())
                fields[2][2][7] = 0x01
                fields[2][2][9] = 0x01
                fields[2][3] = str(secret_code)
                
                ghost_packet = self._gen._builder(fields=list(fields.items()))
                self.sock39699.sendall(ghost_packet)
                
                self._bot.reply(uid, None, f"[B][c][00FF00]✅ Ghost thành công với tên: {custom_name}")
            else:
                # Ghost mặc định (multi bot)
                packetjs = self._bot.join_squad(current_code)
                bots = []
                for bot in self.manager.bots.values():
                    if bot is not self and bot.sock39699 and bot._bot:
                        bots.append(bot)
                    if len(bots) == 3:
                        break
                for bot in bots:
                    bot.sock39699.send(bot._bot.ghost(uid, secret_code))
                
                for _ in range(555):
                    self.sock39699.sendall(packetjs)
                    self.sock39699.sendall(self._bot.leave_squad(0x00))
                    time.sleep(0.005)
                    self.sock39699.sendall(self._bot.ghost(uid, secret_code))
                
                time.sleep(0.5)
                self.sock39699.sendall(self._bot.leave_squad(0x00))
                self.sock39699.sendall(self._bot.ghost(uid, secret_code))
            
            return True
            
        except Exception as e:
            self.rstatus, self.ids = (0, 0), []
            print(f"[GHOST ERROR] {e}")

    if isinstance(self.rstatus, tuple) and self.rstatus[0] == 3:
        try:
            uid = data.get("5", {}).get("1")
            secret_code = data.get("5", {}).get("31")
            self.sock39699.send(self._bot.leave_squad(1))
            if not uid or not secret_code:
                return False
            current_code = self.rstatus[1]
            self.rstatus = (0, 0)
            self.send_ghost(uid, secret_code)
        except Exception as e:
            self.rstatus, self.ids = (0, 0), []
                    
  if isinstance(self.rstatus, tuple) and self.rstatus[0] == 4:
    try:
        import pprint
        pprint.pprint(data)
        uid = data.get("5", {}).get("1")
        recruit_code = data.get("5", {}).get("17")
        self.sock39801.send(self._bot.join_channel(uid, recruit_code, None))
        time.sleep(1.2)
        self._bot.reply(uid, None, "[B][C][00FF00]Bo[c]t Em[b]ote By Zan\n[00FF00]TikTok: [FF69B4]zanbackj\n[00FF00]Tele[c]gr[c]am: [87CEEB]@zanbackj\n[00FF00]Group: [FFD700]ht[c]tps://t.[b]me/zancommunity")
        self.rstatus = (10, '')
        self.ids.extend(extract_uid_fields(data))
    except Exception as e:
        self.rstatus, self.ids = (0, 0), []
        
 def playcd(self):
     self.sock39699.send(self._bot.play_animation(914000002))
     time.sleep(3)
     self.sock39699.send(self._bot.play_animation(914000002))
     time.sleep(3.5)
     self.sock39699.send(self._bot.play_animation(914000002))

 def send_ghost(self, uid, secret):
  bots = []
  for i in self.manager.bots.values():
   if i is not self and i.running_event.is_set() and i.sock39699 and i._bot:
    bots.append(i)
   if len(bots) == 3: break
  for bot in bots: bot.sock39699.send(bot._bot.ghost(uid, secret))

 def spam_to_squads(self, uid):
  for i in range(123):
   self.sock39699.send(self._bot.request_join_squad(uid))
   time.sleep(0.35)

 def GenSpamRoom(self, cid):
  self.sock39699.send(self._bot.get_history(cid))
  time.sleep(1.5)
  rid = self.roomid
  if rid:
   packetjr = self._bot.request_join_room(rid, cid)
   for i in range(123):
    if not self.sock39699: return
    self.sock39699.send(packetjr)
    time.sleep(0.35)
   
 def GenSquads(self, team, cid, uid, Type, name):
        if not self.sock39699:
            self._bot.reply(cid, Type, "Thử lại!")
            return

        self.status = False
        self.sock39699.sendall(self._bot.open_squad(team))
        time.sleep(0.3)
        self.sock39699.send(self._bot.invite_squad(uid, 1))
        self.sock39699.send(self._bot.invite_squad(uid, 2))

        self._bot.reply(cid, Type, f"""[B][C][FFFFFF]Xin Chào! {name}
[FFFFFF]Đã tạo team {team} thành công!
[C0C0C0]Vui lòng chấp nhận lời mời từ bot!""")

        threading.Thread(target=self.playcd).start()
        threading.Thread(target=self.closesquads).start()

 def closesquads(self):
  time.sleep(10)
  self.rstatus, self.ids = (0, 0), []
  try: self.sock39699.send(self._bot.leave_squad(0x000000))
  except Exception as e: pass
  self.status = True
 
 def get_user_status(self, type, uid=None):
    if type == 1:
        return [u["uid"] for u in self.bot_config.get("access_bot", [])] + [self.botid] + [self.GuildIds]
    
    if type in [2, 3] and uid is not None:
        for u in self.bot_config.get("access_bot", []):
            if u["uid"] == int(uid):
                exp = u["expire"]
                try:
                    exp_time = datetime.datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")
                    now = datetime.datetime.now()
                    if exp_time < now:
                        self.manager.deleteId(self.bot_config["bot_id"], uid)
                        return "Hết hạn" if type == 3 else False  # SỬA
                    if type == 2:
                        return True
                    if type == 3:
                        delta = exp_time - now
                        days = delta.days
                        hours, remainder = divmod(delta.seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        parts = []
                        if days: parts.append(f"{days} ngày")
                        if hours: parts.append(f"{hours} giờ")
                        if minutes: parts.append(f"{minutes} phút")
                        time_left = ", ".join(parts) if parts else "0 phút"
                        return time_left
                except Exception as e:
                    return "Hết hạn" if type == 3 else False  # SỬA
        
        # KHÔNG TÌM THẤY UID -> TRẢ VỀ "Chưa kích hoạt"
        return "Chưa kích hoạt"  # SỬA DÒNG NÀY
    
    return "Chưa kích hoạt"  # SỬA DÒNG NÀY
           
 def format_status_message(self, info, uid):
  status = info.get("status", "") 
  uid = info.get("uid", uid)
  group = info.get("group")
  roomid = info.get("roomid")
  extra = ""
  if "Squads" in status and group:
   extra = "group: []{}\n".format(group)
  elif "Rooms" in status and roomid:
   extra = "Room ID: []{}\n".format(roomid)
  return """Player Status Info:
status: {}
uid: {}""".format(status, extra, uid) 

 def auto_send_likes(self):
  ds_ids = GetClanInfo(self.token, self.GuildIds).IdList()
  for id in ds_ids:
   message = send_likes(int(id), "∞")
   if "Bảo Trì!" in message: self._bot.reply(self.GuildIds, 1, message)
   else: self._bot.reply(self.GuildIds, 1, message)
   time.sleep(1.5)

 class bot_session:
  def __init__(self, parent):
   self.par = parent
  def __getattr__(self, name):
   return getattr(self.par._gen, name)
  def reply(self, Id, Tp, Ms):
   try:
    if self.par.running_event.is_set() and self.par.sock39801:
     self.par.sock39801.sendall(self.par._gen.send_message(Ms, Tp, Id))
   except Exception as e: pass
   
 def rstart(self):
    access_token = self.bot_config['auth_bot_login']['access_token']
    while self.running_event.is_set():
        try:
            data = FreeFireAPI().get(access_token, is_emulator=False)
            print(data)
            if "account not found" in data:
                self.running_event.clear()
                break
            if data.get("GuildData"):
                self.AuthenCode = data.get("GuildData").get("secret_code")
                self.GuildIds = data.get("GuildData").get("id")
            self.packetAuth = bytes(data["UserAuthPacket"])
            self.botid = int(data["UserAccountUID"])
            try:
                self.nickname = data.get("logindata", {}).get("4")
                if not self.nickname:
                    raise Exception("Empty nickname")
            except:
                import base64
                try:
                    raw = data.get("UserNickName", "")
                    self.nickname = base64.b64decode(raw).decode("utf-8", errors="ignore")
                except:
                    self.nickname = "Unknown"
            self.manager.save_config()
            self.region = str(data["LockRegion"])
            self.token = data["UserAuthToken"]
            self.ChatIP = data["GameServerAddress"]["chatip"]
            self.OnlineIP = data["GameServerAddress"]["onlineip"]
            self.OnlinePort = data["GameServerAddress"]["onlineport"]
            self.ChatPort = data["GameServerAddress"]["chatport"]
            self.key, self.iv = bytes(data["key"]), bytes(data["iv"])             
            self.base_url = data["BaseUrl"]
            ChooseEmote(self.token, self.base_url)
            self.online_time = time.time()
            self._IIl(data["logindata"], data)
            if not self.running_event.is_set():
                break
            time.sleep(14555)
        except Exception as e:
            import traceback
            traceback.print_exc()
            if self.running_event.is_set():
                time.sleep(1111)
 def start(self):
  if self.started: return 
  self.started = True
  self.running_event.set()
  threading.Thread(target=self.rstart, daemon=True).start() 

class BOTMNG:

 def __init__(self):
  self.bots = {}
  self.config_lock = threading.RLock()
  self.filename = "bot.json"
  self.config = {"bots": []}
  self.load_config()
  threading.Thread(
   target=self.auto_cleanup_expired_users,
   daemon=True
  ).start()

 def load_config(self):
  try:
   if not os.path.exists(self.filename):
    with open(self.filename, "w", encoding="utf-8") as f:
     json.dump({"bots": []}, f, indent=4, ensure_ascii=False)
   with open(self.filename, "r", encoding="utf-8") as f:
    content = f.read().strip()
   if not content:
    self.config = {"bots": []}
    return
   self.config = json.loads(content)
   if "bots" not in self.config:
    self.config["bots"] = []
   self.bots.clear()
   for bot_data in self.config["bots"]:

    try:
     bot_id = bot_data.get("bot_id")
     if not bot_id:
      continue
     if "auth_bot_login" not in bot_data:
      continue

     if "access_token" not in bot_data["auth_bot_login"]:
      continue
     bot_instance = FreeFireTCP(bot_data, self)
     bot_instance.bot_config = bot_data
     bot_instance.botid = bot_data.get("botid")
     bot_instance.nickname = bot_data.get("nickname")
     self.bots[bot_id] = bot_instance
    except Exception as e:
     print("Bot load error:", e)
   print(f"Loaded {len(self.bots)} bots from bot.json")
  except Exception as e:
   print("load_config error:", e)
   self.config = {"bots": []}

 def save_config(self):
  try:
   with self.config_lock:
    new_list = []
    for bot_id, bot_instance in self.bots.items():
     bot_config = bot_instance.bot_config.copy()
     bot_config["bot_id"] = bot_id
     if getattr(bot_instance, "botid", None):
      bot_config["botid"] = bot_instance.botid
     if getattr(bot_instance, "nickname", None):
      bot_config["nickname"] = bot_instance.nickname
     if "access_bot" not in bot_config:
      bot_config["access_bot"] = []
     new_list.append(bot_config)
    self.config["bots"] = new_list
    with open(self.filename, "w", encoding="utf-8") as f:
     json.dump(
      self.config,
      f,
      indent=4,
      ensure_ascii=False
     )
    print(f"Saved {len(new_list)} bots to bot.json")
  except Exception as e:
   print("save_config error:", e)

 def get_next_bot_id(self):
  with self.config_lock:
   if not self.bots:
    return 1
   return max(self.bots.keys()) + 1

 def check_token_exists(self, access_token):
  for bot in self.bots.values():
   if bot.bot_config["auth_bot_login"]["access_token"] == access_token:
    return True, bot.bot_config["bot_id"]
  return False, None

 def add_bot(self, access_token, bot_cmd_data=None):
  with self.config_lock:
   exists, existing_id = self.check_token_exists(access_token)
   if exists:
    return {
     "status": False,
     "message": "access token already exists"
    }
   bot_id = self.get_next_bot_id()
   new_bot = {
    "bot_id": bot_id,
    "auth_bot_login": {
        "access_token": access_token
    },
    "access_bot": [],
    "active-clan": True
   }
   bot_instance = FreeFireTCP(new_bot, self)
   bot_instance.bot_config = new_bot
   self.bots[bot_id] = bot_instance
   self.save_config()
   return {
    "status": True,
    "bot_id": bot_id
   }

 def delete_bot(self, bot_id):
  with self.config_lock:
   if bot_id not in self.bots:
    return False
   try:
    self.bots[bot_id].cleanup()
   except:
    pass
   del self.bots[bot_id]
   self.save_config()
   return True

 def add_uid_to_access(self, bot_id, uid, time_str):
    """Thêm UID vào danh sách truy cập"""
    try:
        # Parse time
        import re
        if not re.match(r'^\d+[hdwmy]$', time_str.lower()):
            return "invalid_time"
        
        # Lấy bot
        bot = self.bots.get(bot_id)
        if not bot:
            return "bot_not_found"
        
        # Tính timestamp
        now = datetime.now()
        num = int(time_str[:-1])
        unit = time_str[-1].lower()
        
        if unit == 'h':
            delta = timedelta(hours=num)
        elif unit == 'd':
            delta = timedelta(days=num)
        elif unit == 'w':
            delta = timedelta(weeks=num)
        elif unit == 'm':
            delta = timedelta(days=num * 30)
        elif unit == 'y':
            delta = timedelta(days=num * 365)
        else:
            return "invalid_time"
        
        expire_time = now + delta
        timestamp = int(expire_time.timestamp())
        
        # Thêm vào database
        if hasattr(bot, 'manager') and bot.manager:
            return bot.manager.add_uid_to_access(bot_id, uid, timestamp)
        else:
            return False
            
    except Exception as e:
        print(f"Add UID Error: {e}")
        return str(e)
        
 def deleteId(self, bot_id, uid):
  with self.config_lock:
   if bot_id not in self.bots:
    return False
   bot = self.bots[bot_id].bot_config
   try:
    uid = int(uid)
   except:
    return False
   bot["access_bot"] = [
    u for u in bot.get("access_bot", [])
    if u["uid"] != uid
   ]
   self.save_config()
   return True

 def parse_expire_time(self, time_str):
  try:
   unit = time_str[-1]
   value = int(time_str[:-1])
   now = datetime.datetime.now()
   if unit == "h":
    expire = now + datetime.timedelta(hours=value)
   elif unit == "d":
    expire = now + datetime.timedelta(days=value)
   elif unit == "w":
    expire = now + datetime.timedelta(weeks=value)
   elif unit == "y":
    expire = now + datetime.timedelta(days=365*value)
   else:
    return None
   return expire.strftime("%Y-%m-%d %H:%M:%S")
  except:
   return None

 def auto_cleanup_expired_users(self):      
  while True: 
   try:
    now = dt.datetime.now()
    changed = False
    for bot in self.bots.values():
     access = bot.bot_config.get("access_bot", [])
     new_access = []
     for user in access:
      try:
       expire = datetime.datetime.strptime(user["expire"], "%Y-%m-%d %H:%M:%S")
       if expire > now:
        new_access.append(user)
       else:
        changed = True
      except:
       changed = True
     bot.bot_config["access_bot"] = new_access
    if changed:
     self.save_config()
   except Exception as e:
    print(traceback.format_exc())
   time.sleep(3600)
 
 def laybanbe(tk):
    h = {
        "Authorization": f"Bearer {tk}",
        "User-Agent": "UnityPlayer/2022.3.47f1",
        "ReleaseVersion": "OB54"
    }
    payload = b'\x59\x8F\xCA\xF0\x78\x39\x30\x8F\xF2\x87\xAC\xA3\xAE\x0A\x06\x17'
    try:
        r = requests.post("https://clientbp.ggpolarbear.com/GetFriend", headers=h, data=payload, timeout=10)
        if r.status_code != 200:
            return []
        p = parse(r.content)
        if 1 in p and isinstance(p[1], list):
            return p[1]
        return []
    except:
        return []

CHAT_GROUP_ID_1 = "@zancommunity"
CHAT_GROUP_ID_2 = "@zanxchannel"

def is_telegram_admin(user_id):
    try: 
        return user_id in TELEGRAM_ADMINS
    except: 
        return False

def check_user_in_group(user_id):
    if is_telegram_admin(user_id):
        return True
    
    in_group1 = False
    try:
        member1 = telegram_bot.get_chat_member(CHAT_GROUP_ID_1, user_id)
        if member1.status in ['member', 'creator', 'administrator']:
            in_group1 = True
    except Exception as e:
        print("CHECK GROUP 1 ERROR:", e)
    
    in_group2 = False
    try:
        member2 = telegram_bot.get_chat_member(CHAT_GROUP_ID_2, user_id)
        if member2.status in ['member', 'creator', 'administrator']:
            in_group2 = True
    except Exception as e:
        print("CHECK GROUP 2 ERROR:", e)
    
    return in_group1 and in_group2

def get_join_keyboard():
    markup = InlineKeyboardMarkup()
    btn_group1 = InlineKeyboardButton(text="👥 Nhóm Cộng Đồng", url="https://t.me/zancommunity")
    btn_group2 = InlineKeyboardButton(text="📢 Kênh Thông Báo", url="https://t.me/zanxchannel")
    btn_joined = InlineKeyboardButton(text="✅ Tôi đã tham gia", callback_data="check_joined")
    markup.row(btn_group1)
    markup.row(btn_group2)
    markup.row(btn_joined)
    return markup

from functools import wraps

def is_admin_user(user_id):
    return user_id in TELEGRAM_ADMINS

def is_private_chat(message):    
    return message.chat.type == 'private'

def is_group_chat(message):
    return message.chat.type in ['group', 'supergroup']

def check_group_only(func):   
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id        
        
        if is_admin_user(user_id):
            return func(message, *args, **kwargs)
             
        if is_private_chat(message):
            telegram_bot.reply_to(
                message,
                f"""⛔️ <b>Bạn không có quyền sử dụng bot này.</b>
Chỉ admin và người quản lý mới có thể sử dụng bot qua tin nhắn riêng!
Vui lòng sử dụng bot trong nhóm <b>@zancommunity</b> để thực hiện lệnh.

━━━━━━━━━━━━━━━━━━━━
📩 Liên hệ: <b>@zanbackj</b>""",
                parse_mode="HTML"
            )
            return
        
        return func(message, *args, **kwargs)
    return wrapper
            
ADMIN_ID = [8722607800]
TELE_USERS_FILE = "tele_users.json"
TELE_GROUPS_FILE = "tele_groups.json"

def save_telegram_chat(chat_id, filename):
    chats = []
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                chats = json.load(f)
        except:
            pass
            
    if chat_id not in chats:
        chats.append(chat_id)
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(chats, f, indent=4)
        except:
            pass

from functools import wraps

def async_telegram(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        threading.Thread(target=func, args=(message, *args), kwargs=kwargs, daemon=True).start()
    return wrapper
 
@telegram_bot.message_handler(commands=['start', 'help', 'menu'])
@check_group_only
@async_telegram
def telegram_start_help_menu(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    menu_text = """
<blockquote>📌 MENU ĐIỀU KHIỂN HỆ THỐNG

[ LỆNH TẠO ĐỘI ]
├ /2 {uid} ➜ Lập team 2 người
├ /3 {uid} ➜ Lập team 3 người
├ /4 {uid} ➜ Lập team 4 người
├ /5 {uid} ➜ Lập team 5 người
├ /6 {uid} ➜ Lập team 6 người

[ LỆNH HÀNH ĐỘNG ]
├ /s7 {teamcode} {uid1} {uid2} ➜ Múa all hành động s7
├ /rd {teamcode} {uid1} {uid2} ➜ Múa random all s7
├ /hdco {teamcode} {uid1} {uid2} ➜ Múa all hành động cổ
└ /rngau {teamcode} {uid1} {uid2} ➜ Múa all hành động ngầu

[ LỆNH SPAM & LAG ]
├ /lag {teamcode} ➜ Gửi request lag đến đội
├ /ghost {teamcode} {tên} ➜ Ghost đội với tên tùy chỉnh
├ /spamall {uid} ➜ Spam lời mời vô đội
├ /rinv {uid} ➜ Spam vô phòng
└ /msg {teamcode} {message} ➜ Spam tin nhắn vô đội

[ TRA CỨU INFO ]
├ /isbanned {uid} ➜ Kiểm tra tình trạng ban
├ /info {uid} ➜ Xem thông tin người chơi
├ /status {uid} ➜ Kiểm tra trạng thái người chơi

[ LỆNH BUFF LIKE ]
├ /like {uid} ➜ Buff like ( nhận khoảng 110 like )
├ /autolike {uid} {số ngày} ➜ Auto like hàng ngày (Admin)
├ /autolist ➜ Xem danh sách auto like (Admin)
└ /delauto {uid} ➜ Xóa khỏi danh sách auto like (Admin)

[ QUYỀN HẠN QUẢN TRỊ ]
├ /addbot {token} ➜ Thêm bot mới
├ /kb {botid} {id} ➜ Gửi yêu cầu kết bạn
├ /xkb {botid} {id} ➜ Hủy yêu cầu kết bạn
├ /delbot {botid} ➜ Xóa bot khỏi hệ thống
└ /checkbot ➜ Kiểm tra danh sách bot online

⚠️ LƯU Ý QUAN TRỌNG:
• Chỉ quản trị viên mới có thể nhắn tin riêng với bot
• Người dùng thường vui lòng sử dụng lệnh trong nhóm
• Mọi thắc mắc liên hệ: @zanbackj</blockquote>
"""
    
    telegram_bot.reply_to(message, menu_text, parse_mode="HTML")
                                       
@telegram_bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def callback_check_joined(call):
    try:
        user_id = call.from_user.id
        message_id = call.message.message_id
        
        original_user_id = user_msg_map.get(message_id)
        if original_user_id and user_id != original_user_id:
            try:
                telegram_bot.answer_callback_query(
                    call.id,
                    text="❌ Bạn không phải là người thực hiện yêu cầu này!",
                    show_alert=True
                )
            except:
                pass
            return
        
        if check_user_in_group(user_id):
            try:
                telegram_bot.edit_message_text(
                    "🎉 Xác thực thành công! Hãy sử dụng lệnh /menu để xem danh sách lệnh.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id
                )
            except:
                pass
            
            try:
                telegram_bot.answer_callback_query(
                    call.id, 
                    text="✅ Xác thực thành công!", 
                    show_alert=False
                )
            except:
                pass
        else:
            in_group1 = False
            in_group2 = False
            
            try:
                member1 = telegram_bot.get_chat_member(CHAT_GROUP_ID_1, user_id)
                if member1.status in ['member', 'creator', 'administrator']:
                    in_group1 = True
            except:
                pass
            
            try:
                member2 = telegram_bot.get_chat_member(CHAT_GROUP_ID_2, user_id)
                if member2.status in ['member', 'creator', 'administrator']:
                    in_group2 = True
            except:
                pass
            
            missing = []
            if not in_group1:
                missing.append("Nhóm Cộng Đồng (@zancommunity)")
            if not in_group2:
                missing.append("Kênh Thông Báo (@zanxchannel)")
            
            msg = "❌ Bạn chưa tham gia:\n" + "\n".join(f"• {m}" for m in missing)
            try:
                telegram_bot.answer_callback_query(
                    call.id, 
                    text=msg, 
                    show_alert=True
                )
            except:
                pass
    except Exception as e:
        print(f"Callback error: {e}")         
                               
def get_available_bots(count=1):
    available = []
    for b in TCPbot.bots.values():
        if (b.running_event.is_set() and 
            getattr(b, "sock39699", None) and 
            not getattr(b, "is_busy", False)):
            available.append(b)
            if len(available) == count:
                break
    return available

def send_warn_join_group(message):
    user_id = message.from_user.id
    
    # Kiểm tra từng nhóm
    in_group1 = False
    in_group2 = False
    
    try:
        member1 = telegram_bot.get_chat_member(CHAT_GROUP_ID_1, user_id)
        if member1.status in ['member', 'creator', 'administrator']:
            in_group1 = True
    except:
        pass
    
    try:
        member2 = telegram_bot.get_chat_member(CHAT_GROUP_ID_2, user_id)
        if member2.status in ['member', 'creator', 'administrator']:
            in_group2 = True
    except:
        pass
    
    status_msg = ""
    if not in_group1:
        status_msg += "❌ Nhóm Cộng Đồng (@zancommunity)\n"
    else:
        status_msg += "✅ Nhóm Cộng Đồng (@zancommunity)\n"
    
    if not in_group2:
        status_msg += "❌ Kênh Thông Báo (@zanxchannel)\n"
    else:
        status_msg += "✅ Kênh Thông Báo (@zanxchannel)\n"
    
    warn_msg = (
        f"<blockquote>"
        f"<b>⚠️ BẠN CHƯA THAM GIA ĐỦ NHÓM</b>\n"
        f"───────────────────────\n"
        f"👋 Xin chào <code>{message.from_user.first_name}</code>,\n\n"
        f"Bạn cần tham gia 2 kênh sau để sử dụng bot:\n\n"
        f"{status_msg}\n"
        f"👉 Vui lòng bấm vào các nút bên dưới để tham gia đủ!"
        f"</blockquote>"
    )
    telegram_bot.reply_to(message, warn_msg, parse_mode="HTML", reply_markup=get_join_keyboard())

import telebot
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# ====== CẤU HÌNH ======
ACCOUNTS_FILE = "accounts.json"

# ====== LOG ======
def log_print(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# ====== HÀM MÃ HÓA UID ======
def encrypt_uid(uid):
    dec = ['80','81','82','83','84','85','86','87','88','89','8a','8b','8c','8d','8e','8f','90','91','92','93','94','95','96','97','98','99','9a','9b','9c','9d','9e','9f','a0','a1','a2','a3','a4','a5','a6','a7','a8','a9','aa','ab','ac','ad','ae','af','b0','b1','b2','b3','b4','b5','b6','b7','b8','b9','ba','bb','bc','bd','be','bf','c0','c1','c2','c3','c4','c5','c6','c7','c8','c9','ca','cb','cc','cd','ce','cf','d0','d1','d2','d3','d4','d5','d6','d7','d8','d9','da','db','dc','dd','de','df','e0','e1','e2','e3','e4','e5','e6','e7','e8','e9','ea','eb','ec','ed','ee','ef','f0','f1','f2','f3','f4','f5','f6','f7','f8','f9','fa','fb','fc','fd','fe','ff']
    xxx = ['1','01','02','03','04','05','06','07','08','09','0a','0b','0c','0d','0e','0f','10','11','12','13','14','15','16','17','18','19','1a','1b','1c','1d','1e','1f','20','21','22','23','24','25','26','27','28','29','2a','2b','2c','2d','2e','2f','30','31','32','33','34','35','36','37','38','39','3a','3b','3c','3d','3e','3f','40','41','42','43','44','45','46','47','48','49','4a','4b','4c','4d','4e','4f','50','51','52','53','54','55','56','57','58','59','5a','5b','5c','5d','5e','5f','60','61','62','63','64','65','66','67','68','69','6a','6b','6c','6d','6e','6f','70','71','72','73','74','75','76','77','78','79','7a','7b','7c','7d','7e','7f']
    try:
        x = int(uid)
        x_float = float(x) / 128
        if x_float > 128:
            x_float /= 128
            if x_float > 128:
                x_float /= 128
                if x_float > 128:
                    x_float /= 128
                    strx = int(x_float)
                    y = (x_float - strx) * 128
                    z = (y - int(y)) * 128
                    n = (z - int(z)) * 128
                    m = (n - int(n)) * 128
                    return dec[int(m)] + dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
                else:
                    strx = int(x_float)
                    y = (x_float - strx) * 128
                    z = (y - int(y)) * 128
                    n = (z - int(z)) * 128
                    return dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
        return None 
    except: 
        return None

# ====== HÀM LOGIN LẤY JWT ======
def G_AccEss(U, P):
    log_print(f"🔐 Đang login UID: {U[:6]}...")
    UrL = "https://100067.connect.garena.com/oauth/guest/token/grant"
    HE = {
        "Host": "100067.connect.garena.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close",
    }
    dT = {
        "uid": f"{U}",
        "password": f"{P}",
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067",
    }
    try:
        R = requests.post(UrL, headers=HE, data=dT)
        log_print(f"📡 Login response: {R.status_code}")
        if R.status_code == 200:
            data = R.json()
            log_print(f"✅ Login thành công UID: {U[:6]}...")
            return data.get("access_token"), data.get("open_id")
        else:
            log_print(f"❌ Login thất bại: {R.text[:100]}")
    except Exception as e:
        log_print(f"❌ Lỗi G_AccEss: {e}")
    return None, None

# ====== HÀM LẤY JWT TỪ ACCOUNTS.JSON ======
def get_jwt_from_file(uid):
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            accounts = json.load(f)
        for acc in accounts:
            if str(acc.get("uid")) == str(uid):
                return acc.get("jwt")
    except:
        pass
    return None

# ====== HÀM GỬI KẾT BẠN DÙNG JWT ======
def SendFriendRequest(target_uid, jwt_token, bot_uid):
    try:
        log_print(f"📤 Bot {bot_uid} -> Target {target_uid}")
        
        Key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
        Iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
        
        encrypted_id = encrypt_uid(target_uid)
        if not encrypted_id:
            return False, "Mã hóa UID thất bại"
        
        plain_text_payload = f'08a7c4839f1e10{encrypted_id}1801'
        cipher = AES.new(Key, AES.MODE_CBC, Iv)
        data = cipher.encrypt(pad(bytes.fromhex(plain_text_payload), AES.block_size))
        
        headers = {
            'X-Unity-Version': '2018.4.11f1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-GA': 'v1 1',
            'Authorization': f'Bearer {jwt_token}',
            'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }
        
        url = 'https://clientbp.ggpolarbear.com/RequestAddingFriend'
        response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
        
        log_print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            return True, "✅ Gửi kết bạn thành công!"
        else:
            text = response.text
            log_print(f"📄 Response: {text[:200]}")
            if 'BR_FRIEND_NOT_SAME_REGION' in text:
                return False, "❌ Khác khu vực!"
            elif 'BR_FRIEND_MAX_REQUEST' in text:
                return False, "❌ Đã đạt giới hạn!"
            elif 'BR_FRIEND_ALREADY_SENT_REQUEST' in text:
                return False, "❌ Đã gửi trước đó!"
            elif 'BR_FRIEND_ALREADY_FRIEND' in text:
                return False, "❌ Đã là bạn bè!"
            else:
                return False, f"❌ Lỗi: {text[:50]}"
            
    except Exception as e:
        return False, f"❌ Lỗi: {str(e)}"

# ====== LỆNH /spamkb ======
@telegram_bot.message_handler(commands=['spamkb'])
@check_group_only
def telegram_spam_kb(message):
    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote>❌ SAI CÚ PHÁP\n💡 Dùng: /spamkb [uid_target]\n📌 Ví dụ: /spamkb 123456789</blockquote>",
                parse_mode="HTML"
            )
            return
        
        target_uid = parts[1].strip()
        if not target_uid.isdigit():
            telegram_bot.reply_to(message, "<blockquote>❌ UID phải là số!</blockquote>", parse_mode="HTML")
            return
        
        log_print(f"🎯 Spam tới UID: {target_uid}")
        
        if not os.path.exists(ACCOUNTS_FILE):
            telegram_bot.reply_to(message, f"<blockquote>❌ Không tìm thấy file {ACCOUNTS_FILE}!</blockquote>", parse_mode="HTML")
            return
        
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            accounts = json.load(f)
        
        if not accounts:
            telegram_bot.reply_to(message, "<blockquote>❌ Không có account nào!</blockquote>", parse_mode="HTML")
            return
        
        # Lọc accounts có jwt
        valid_accounts = []
        for acc in accounts:
            if acc.get("jwt") and acc.get("status") == "success":
                valid_accounts.append({
                    "uid": acc.get("uid"),
                    "jwt": acc.get("jwt")
                })
        
        if not valid_accounts:
            telegram_bot.reply_to(message, "<blockquote>❌ Không có account nào có JWT hợp lệ!</blockquote>", parse_mode="HTML")
            return
        
        log_print(f"📦 Load {len(valid_accounts)} accounts có JWT")
        
        msg = telegram_bot.reply_to(
            message,
            f"<blockquote>🚀 ĐANG SPAM KẾT BẠN\n━━━━━━━━━━━━━━━━━━━━\n🎯 Target: <code>{target_uid}</code>\n👥 Tổng bots: <b>{len(valid_accounts)}</b>\n✅ Thành công: <b>0</b>\n❌ Thất bại: <b>0</b>\n⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        def run_spam():
            success_count = 0
            fail_count = 0
            
            for i, acc in enumerate(valid_accounts, 1):
                uid = acc["uid"]
                jwt_token = acc["jwt"]
                
                try:
                    success, msg_result = SendFriendRequest(target_uid, jwt_token, uid)
                    
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                    
                    # Cập nhật mỗi 5 acc
                    if i % 5 == 0 or i == len(valid_accounts):
                        try:
                            telegram_bot.edit_message_text(
                                f"<blockquote>🚀 ĐANG SPAM KẾT BẠN\n━━━━━━━━━━━━━━━━━━━━\n🎯 Target: <code>{target_uid}</code>\n👥 Tổng bots: <b>{len(valid_accounts)}</b>\n🔄 Tiến độ: <b>{i}/{len(valid_accounts)}</b>\n✅ Thành công: <b>{success_count}</b>\n❌ Thất bại: <b>{fail_count}</b>\n⏳ Đang xử lý...</blockquote>",
                                chat_id=message.chat.id,
                                message_id=msg.message_id,
                                parse_mode="HTML"
                            )
                        except:
                            pass
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    fail_count += 1
            
            # Kết quả cuối cùng
            summary = (
                f"<blockquote>📊 KẾT QUẢ SPAM KẾT BẠN\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 Target: <code>{target_uid}</code>\n"
                f"👥 Tổng bots: <b>{len(valid_accounts)}</b>\n"
                f"✅ Thành công: <b>{success_count}</b>\n"
                f"❌ Thất bại: <b>{fail_count}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Hoàn thành!</blockquote>"
            )
            
            try:
                telegram_bot.edit_message_text(
                    summary,
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
            except:
                telegram_bot.send_message(
                    message.chat.id,
                    summary,
                    parse_mode="HTML"
                )
        
        threading.Thread(target=run_spam, daemon=True).start()
        
    except Exception as e:
        log_print(f"❌ Lỗi: {e}")
        telegram_bot.reply_to(message, f"<blockquote>❌ Lỗi: {str(e)}</blockquote>", parse_mode="HTML")
                                                                
from telebot import types

@telegram_bot.message_handler(commands=['2', '3', '4', '5', '6'])
@async_telegram
@check_group_only
def handle_team_creation(message):   
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return   
    user_id = message.from_user.id
    current_time = time.time()
    
    # ====== KIỂM TRA COOLDOWN ======
    if user_id in team_cooldown:
        remaining = int(team_cooldown[user_id] - current_time)
        if remaining > 0:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>⏳ vui lòng đợi {remaining} giây và sử dụng lại</b></blockquote>",
                parse_mode="HTML"
            )
            return
    
    cmd = message.text.split()[0][1:]
    parts = message.text.split()
    
    if len(parts) < 2 or not parts[1].isdigit():
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
            f"💡 Vui lòng nhập theo định dạng:\n"
            f"<code>/{cmd} [UID]</code>\n\n"
            f"📌 Ví dụ: <code>/{cmd} 123456789</code></blockquote>",
            parse_mode="HTML"
        )
        return
    
    uid_str = parts[1].strip()
    if len(uid_str) < 8 or len(uid_str) > 11:
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>❌ UID KHÔNG HỢP LỆ</b>\n"
            f"UID phải từ 8-10 chữ số.</blockquote>",
            parse_mode="HTML"
        )
        return
    
    uid = int(uid_str)
    team_size = int(cmd)
    bots = get_available_bots(1)
    
    if not bots:
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>⚠️ HỆ THỐNG QUÁ TẢI</b>\n\n"
            f"🔴 Không thể khởi tạo <b>Team {team_size}</b> cho UID <code>{uid}</code>.\n"
            f"Hiện tại tất cả các Bot đều đang bận hoặc offline. Vui lòng thử lại sau giây lát!</blockquote>",
            parse_mode="HTML"
        )
        return
    
    bot = bots[0]
    bot.is_busy = True 
    
    # ====== SET COOLDOWN ======
    team_cooldown[user_id] = current_time + 15
    
    def safe_send(data):
        try:
            if bot.sock39699:
                bot.sock39699.send(data)
        except Exception as e:
            print("SEND ERROR:", e)
    
    def run():
        try:
            if not bot.sock39699:
                print("❌ SOCKET NULL")
                return
            safe_send(bot._bot.open_squad(team_size))
            time.sleep(0.5)
            safe_send(bot._bot.invite_squad(uid, 1))
            safe_send(bot._bot.invite_squad(uid, 2))
            time.sleep(9)
            safe_send(bot._bot.leave_squad(0))
        except Exception as e:
            print("TEAM CREATION ERROR:", e)
        finally:
            bot.is_busy = False 
    
    threading.Thread(target=run, daemon=True).start()
    bot_name = getattr(bot, 'nickname', f"Bot #{bot.botid}")
    
    telegram_bot.reply_to(
        message,
        f"<blockquote><b>✅ ĐÃ GỬI LỜI MỜI TEAM {team_size}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Bot: {bot_name}\n"
        f"🆔 UID: {uid}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Vào game nhận lời mời nhé!</blockquote>",
        parse_mode="HTML"
    )

# ====== LỆNH /web ======
@telegram_bot.message_handler(commands=['web'])
@async_telegram
def telegram_web(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    try:
        parts = message.text.split(maxsplit=1)
        
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<b>❌ SAI CÚ PHÁP</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💡 <code>/web [url]</code>\n"
                "📌 Ví dụ: <code>/web example.com</code>",
                parse_mode="HTML"
            )
            return
        
        url = parts[1].strip()
        
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        
        msg = telegram_bot.reply_to(
            message,
            f"<b>🔄 ĐANG LẤY NỘI DUNG...</b>\n"
            f"🔗 <code>{url}</code>",
            parse_mode="HTML"
        )
        
        def run_web():
            try:
                import requests
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    # Lấy title
                    title = "Không có title"
                    try:
                        import re
                        match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
                        if match:
                            title = match.group(1).strip()
                    except:
                        pass
                    
                    # Lấy text
                    text = response.text
                    text = re.sub(r'<[^>]+>', ' ', text)
                    text = ' '.join(text.split())[:500]
                    
                    text_response = f"<b>📄 NỘI DUNG WEB</b>\n"
                    text_response += f"━━━━━━━━━━━━━━━━━━━━\n"
                    text_response += f"🔗 <b>URL:</b> <code>{url}</code>\n"
                    text_response += f"📌 <b>Status:</b> {response.status_code}\n"
                    text_response += f"━━━━━━━━━━━━━━━━━━━━\n"
                    text_response += f"📝 <b>Title:</b> {title}\n"
                    text_response += f"━━━━━━━━━━━━━━━━━━━━\n"
                    text_response += f"📄 <b>Nội dung:</b>\n"
                    text_response += f"<i>{text[:300]}{'...' if len(text) > 300 else ''}</i>\n"
                    text_response += f"━━━━━━━━━━━━━━━━━━━━\n"
                    text_response += f"📊 <b>Kích thước:</b> {len(response.content)} bytes"
                    
                    telegram_bot.edit_message_text(
                        text_response,
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                else:
                    telegram_bot.edit_message_text(
                        f"<b>❌ LỖI</b>\n"
                        f"🔴 Status: {response.status_code}",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                
            except Exception as e:
                telegram_bot.edit_message_text(
                    f"<b>❌ LỖI</b>\n🔴 {str(e)}",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
        
        threading.Thread(target=run_web, daemon=True).start()
        
    except Exception as e:
        telegram_bot.reply_to(message, f"<b>❌ LỖI</b>\n🔴 {str(e)}", parse_mode="HTML")

# ====== LỆNH /gettoken ======
@telegram_bot.message_handler(commands=['gettoken'])
@async_telegram
def telegram_gettoken(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    try:
        parts = message.text.split()
        
        if len(parts) < 3:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💡 <code>/gettoken [uid] [password]</code>\n"
                "📌 Ví dụ: <code>/gettoken 123456789 matkhau123</code>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🔑 Lấy Access Token từ UID và Password</blockquote>",
                parse_mode="HTML"
            )
            return
        
        uid = parts[1].strip()
        password = parts[2].strip()
        
        if not uid.isdigit():
            telegram_bot.reply_to(message, "<blockquote>❌ UID phải là số!</blockquote>", parse_mode="HTML")
            return
        
        msg = telegram_bot.reply_to(
            message,
            f"<blockquote><b>🔄 ĐANG LẤY TOKEN...</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 UID: <code>{uid}</code>\n"
            f"⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        def run_gettoken():
            try:
                import requests
                import json
                
                # ====== GỌI API LẤY TOKEN ======
                url = "https://100067.connect.garena.com/oauth/guest/token/grant"
                headers = {
                    "Host": "100067.connect.garena.com",
                    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 7.1.2)",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "close",
                }
                data = {
                    "uid": f"{uid}",
                    "password": f"{password}",
                    "response_type": "token",
                    "client_type": "2",
                    "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
                    "client_id": "100067",
                }
                
                response = requests.post(url, headers=headers, data=data, timeout=15)
                
                if response.status_code == 200:
                    result = response.json()
                    access_token = result.get("access_token")
                    open_id = result.get("open_id")
                    uid_return = result.get("uid")
                    
                    if access_token:
                        # Lấy thông tin từ token (decode JWT)
                        try:
                            import base64
                            import json as json_decode
                            parts_token = access_token.split('.')
                            if len(parts_token) >= 2:
                                payload = parts_token[1]
                                payload += '=' * (4 - len(payload) % 4)
                                decoded = json_decode.loads(base64.urlsafe_b64decode(payload))
                                nickname = decoded.get('nickname', 'N/A')
                                if nickname:
                                    try:
                                        nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                                    except:
                                        pass
                            else:
                                nickname = "N/A"
                        except:
                            nickname = "N/A"
                        
                        telegram_bot.edit_message_text(
                            f"<blockquote><b>✅ LẤY TOKEN THÀNH CÔNG</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🆔 UID: <code>{uid_return or uid}</code>\n"
                            f"👤 Name: {nickname}\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔑 <b>Access Token:</b>\n"
                            f"<code>{access_token}</code>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"📋 Open ID: <code>{open_id}</code></blockquote>",
                            chat_id=message.chat.id,
                            message_id=msg.message_id,
                            parse_mode="HTML"
                        )
                    else:
                        telegram_bot.edit_message_text(
                            f"<blockquote><b>❌ LẤY TOKEN THẤT BẠI</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🔴 Sai UID hoặc Password!</blockquote>",
                            chat_id=message.chat.id,
                            message_id=msg.message_id,
                            parse_mode="HTML"
                        )
                else:
                    telegram_bot.edit_message_text(
                        f"<blockquote><b>❌ LẤY TOKEN THẤT BẠI</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🔴 Lỗi: {response.status_code}</blockquote>",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                    
            except Exception as e:
                telegram_bot.edit_message_text(
                    f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
        
        threading.Thread(target=run_gettoken, daemon=True).start()
        
    except Exception as e:
        telegram_bot.reply_to(message, f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>", parse_mode="HTML")
        
# ====== BUFF LIKE COMMAND (FAST) ======
LIKE_API_URL = "https://cds-gilt.vercel.app/like"

@telegram_bot.message_handler(commands=['like'])
@check_group_only
@async_telegram
def telegram_like(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    try:
        parts = message.text.split()
        
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💡 <code>/like [uid]</code>\n"
                "📌 Ví dụ: <code>/like 16890930508</code>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🌍 Default server: <code>BD</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        uid = parts[1].strip()
        
        if not uid.isdigit():
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ ERROR</b>\n🔴 UID must be a number!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        if len(uid) < 8 or len(uid) > 11:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ INVALID UID</b>\n🔴 UID must be 8-11 digits!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        msg = telegram_bot.reply_to(
            message,
            f"<blockquote><b>🔄 BUFFING LIKES...</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 UID: <code>{uid}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Processing...</blockquote>",
            parse_mode="HTML"
        )
        
        def run_like():
            try:
                import requests
                
                # ====== GIẢM TIMEOUT XUỐNG 3s ======
                url = f"https://cds-gilt.vercel.app/like?uid={uid}&server_name=BD"
                response = requests.get(url, timeout=3)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    added = data.get('added', 0)
                    before = data.get('before', 0)
                    after = data.get('after', 0)
                    nickname = data.get('nickname', 'Unknown')
                    status = data.get('status', 'unknown')
                    
                    if status == "max_like":
                        status_text = "✅ Max like reached!"
                    elif added > 0:
                        status_text = "✅ Buff like successful!"
                    else:
                        status_text = "ℹ️ No changes."
                    
                    message_text = (
                        f"<blockquote>\n"
                        f"{status_text}\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"👤 Nickname: <code>{nickname}</code>\n"
                        f"🎯 UID: <code>{uid}</code>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"❤️ Before: <code>{before}</code>\n"
                        f"❤️ After: <code>{after}</code>\n"
                        f"➕ Added: <code>+{added}</code>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚡ Done!</blockquote>"
                    )
                    
                    telegram_bot.edit_message_text(
                        message_text,
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                else:
                    telegram_bot.edit_message_text(
                        f"<blockquote><b>❌ API ERROR</b>\n🔴 HTTP {response.status_code}</blockquote>",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                    
            except requests.exceptions.Timeout:
                telegram_bot.edit_message_text(
                    "<blockquote><b>❌ TIMEOUT</b>\n🔴 API response slow!</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
            except Exception as e:
                telegram_bot.edit_message_text(
                    f"<blockquote><b>❌ ERROR</b>\n🔴 {str(e)}</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
        
        threading.Thread(target=run_like, daemon=True).start()
        
    except Exception as e:
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>❌ ERROR</b>\n🔴 {str(e)}</blockquote>",
            parse_mode="HTML"
        )
                                            
@telegram_bot.message_handler(commands=['status'])
@check_group_only
@async_telegram
def handle_telegram_status(message):
    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/status [uid]</code>\n📌 Ví dụ: <code>/status 123456789</code></blockquote>"
            )
            return

        uid = parts[1].strip()
        if not uid.isdigit():
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ LỖI</b>\n🔴 UID phải là số!</blockquote>"
            )
            return

        bots = get_available_bots(1)
        if not bots:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>⚠️ BOT BẬN</b>\n🔴 Không có bot nào rảnh!</blockquote>"
            )
            return

        bot = bots[0]
        bot.is_busy = True
        bot_name = getattr(bot, 'nickname', f'Bot #{bot.botid}')

        msg = telegram_bot.reply_to(
            message,
            f"<blockquote><b>📡 ĐANG LẤY THÔNG TIN</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>UID:</b> <code>{uid}</code>\n🤖 <b>Bot:</b> <code>{bot_name}</code>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )

        def run_status():
            try:
                bot.sock39699.send(bot._bot.get_history(uid))
                
                wait_time = 0
                while not bot.playerstatus and wait_time < 5:
                    time.sleep(0.5)
                    wait_time += 0.5

                if bot.playerstatus:
                    try:
                        # ====== DÙNG HÀM get_player_status ======
                        data = get_player_status(bot.playerstatus)
                        
                        if data:
                            status_text = data.get("status", "Không xác định")
                            player_uid = data.get("uid", uid)
                            group = data.get("group", "")
                            roomid = data.get("roomid", "")
                            
                            extra = ""
                            if group:
                                extra = f"\n🏠 <b>Nhóm:</b> <code>{group}</code>"
                            if roomid:
                                extra = f"\n🏠 <b>Room ID:</b> <code>{roomid}</code>"
                            
                            telegram_bot.edit_message_text(
                                f"<blockquote><b>✅ THÔNG TIN NGƯỜI CHƠI</b>\n━━━━━━━━━━━━━━━━━━━━\n🆔 <b>UID:</b> <code>{player_uid}</code>\n📌 <b>Trạng thái:</b> <code>{status_text}</code>{extra}\n🤖 <b>Bot:</b> <code>{bot_name}</code>\n━━━━━━━━━━━━━━━━━━━━\n⚡ Lấy thông tin thành công!</blockquote>",
                                chat_id=message.chat.id,
                                message_id=msg.message_id,
                                parse_mode="HTML"
                            )
                        else:
                            telegram_bot.edit_message_text(
                                f"<blockquote><b>⚠️ KHÔNG TÌM THẤY</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>UID:</b> <code>{uid}</code>\n🔴 <b>Trạng thái:</b> <code>Không có dữ liệu</code>\n━━━━━━━━━━━━━━━━━━━━\n💡 Vui lòng thử lại!</blockquote>",
                                chat_id=message.chat.id,
                                message_id=msg.message_id,
                                parse_mode="HTML"
                            )
                    except Exception as e:
                        telegram_bot.edit_message_text(
                            f"<blockquote><b>⚠️ LỖI PARSE</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>UID:</b> <code>{uid}</code>\n🔴 <b>Lỗi:</b> <code>{str(e)[:30]}</code>\n━━━━━━━━━━━━━━━━━━━━\n⚡ Vui lòng thử lại!</blockquote>",
                            chat_id=message.chat.id,
                            message_id=msg.message_id,
                            parse_mode="HTML"
                        )
                else:
                    telegram_bot.edit_message_text(
                        f"<blockquote><b>⚠️ KHÔNG TÌM THẤY</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>UID:</b> <code>{uid}</code>\n🔴 <b>Trạng thái:</b> <code>Không có dữ liệu</code>\n━━━━━━━━━━━━━━━━━━━━\n💡 Lỗi API hoặc disconnect, thử lại!</blockquote>",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )

            except Exception as e:
                try:
                    telegram_bot.edit_message_text(
                        f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)[:50]}</blockquote>",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                except:
                    pass
            finally:
                bot.is_busy = False

        threading.Thread(target=run_status, daemon=True).start()

    except Exception as e:
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>"
        )
@telegram_bot.message_handler(commands=['lag'])
@check_group_only
@async_telegram
def handle_telegram_lag(message):
    user_id = message.from_user.id
    current_time = time.time()
    
    # ====== KIỂM TRA COOLDOWN ======
    if user_id in lag_cooldown:
        remaining = int(lag_cooldown[user_id] - current_time)
        if remaining > 0:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>⏳ vui lòng đợi {remaining} giây và sử dụng lại</b></blockquote>",
                parse_mode='HTML'
            )
            return
    
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        telegram_bot.reply_to(
            message, 
            "<blockquote><b>❌ SAI CÚ PHÁP</b>\n━━━━━━━━━━━━━━━━━━━━\n💡 Dùng: <code>/lag [teamcode]</code>\n📌 Ví dụ: <code>/lag 1234567</code>\n━━━━━━━━━━━━━━━━━━━━\n⛔ Teamcode phải là <b>7 CHỮ SỐ</b>!</blockquote>", 
            parse_mode='HTML'
        )
        return
    
    team_code = parts[1].strip()
    
    # ====== KIỂM TRA ĐỘ DÀI 7 CHỮ SỐ ======
    if len(team_code) != 7:
        telegram_bot.reply_to(
            message, 
            f"<blockquote><b>❌ TEAMCODE PHẢI 7 CHỮ SỐ</b>\n━━━━━━━━━━━━━━━━━━━━\n🔴 Teamcode bạn nhập: <code>{team_code}</code> ({len(team_code)} số)\n💡 Vui lòng nhập đúng <b>7 chữ số</b>!\n📌 Ví dụ: <code>/lag 1234567</code></blockquote>", 
            parse_mode='HTML'
        )
        return
    
    team_code_int = int(team_code)
    
    bots = get_available_bots(2)
    if len(bots) < 2:
        telegram_bot.reply_to(
            message, 
            "<blockquote><b>⚠️ KHÔNG ĐỦ BOT</b>\n━━━━━━━━━━━━━━━━━━━━\n🔴 Cần 2 bot rảnh. Vui lòng đợi!</blockquote>", 
            parse_mode='HTML'
        )
        return
    
    bot1, bot2 = bots[0], bots[1]
    bot1.is_busy = True
    bot2.is_busy = True
    
    bot1_name = getattr(bot1, 'nickname', f"Bot #{bot1.botid}")
    bot2_name = getattr(bot2, 'nickname', f"Bot #{bot2.botid}")
    
    # ====== SET COOLDOWN ======
    lag_cooldown[user_id] = current_time + 15
    
    status_msg = telegram_bot.reply_to(
        message, 
        f"<blockquote><b>✅ KÍCH HOẠT LAG TEAMCODE {team_code_int} THÀNH CÔNG!</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 <b>Bot:</b> <code>{bot1_name}</code> & <code>{bot2_name}</code>\n📩 <b>Trạng thái:</b> Đang thực thi gửi gói tin lag vào phòng...</blockquote>", 
        parse_mode='HTML'
    )

    def run_lag(bot):
        try:
            bot.sock39699.sendall(bot._bot.join_squad(team_code_int))
            time.sleep(1)
            
            for _ in range(1111):
                try:
                    bot.sock39699.sendall(bot._gen.lag_zan())
                    time.sleep(0.0001)
                except:
                    pass
            
            bot.sock39699.sendall(bot._bot.leave_squad(0))
            bot.is_busy = False
            
        except Exception as e:
            print(f"[LAG ERROR] {e}")
            bot.is_busy = False
    
    def run():
        t1 = threading.Thread(target=run_lag, args=(bot1,), daemon=True)
        t2 = threading.Thread(target=run_lag, args=(bot2,), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    
    threading.Thread(target=run, daemon=True).start()
                      
@telegram_bot.message_handler(commands=['addbot'])
@async_telegram
def telegram_add_bot(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
          
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(message, "❌ Sai cú pháp!\nSử dụng: /addbot <token>")
            return
        
        token = parts[1]
        result = TCPbot.add_bot(token)
        
        if result["status"]:
            bot_id = result["bot_id"]
            TCPbot.bots[bot_id].start()
            response = f"✅ Thêm bot thành công!\nBot ID: {bot_id}\nToken: {token[:20]}..."
        else:
            response = f"❌ Thêm bot thất bại!\nLý do: {result['message']}"
        
        telegram_bot.reply_to(message, response)
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")
        
@telegram_bot.message_handler(commands=['msg'])
@check_group_only
@async_telegram
def handle_msg(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    try:
        parts = message.text.strip().split(maxsplit=2)
        if len(parts) < 3:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/msg [teamcode] [nội dung]</code></blockquote>",
                parse_mode="HTML"
            )
            return
        try:
            tcode = int(parts[1])
        except:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ LỖI</b>\n🔴 Teamcode phải là số!</blockquote>",
                parse_mode="HTML"
            )
            return
        msg_content = parts[2]
        bots = get_available_bots(1)
        if not bots:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>⚠️ HỆ THỐNG QUÁ TẢI</b>\n🔴 Không có bot nào rảnh! Vui lòng đợi...</blockquote>",
                parse_mode="HTML"
            )
            return
        bot = bots[0]
        bot.is_busy = True
        try:
            bot.rstatus = (1, msg_content)
            bot.sock39699.send(bot._bot.join_squad(tcode))
            payload = json.dumps({"StickerStr": "[1=1200000002-11]", "type": "Sticker"})
            bot.sock39801.send(bot._bot.send_object(payload, message.chat.id, None))
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>✅ GỬI TIN NHẮN THÀNH CÔNG</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Teamcode:</b> <code>{tcode}</code>\n💬 <b>Nội dung:</b> <i>{msg_content}</i>\n🤖 <b>Bot:</b> <code>{getattr(bot, 'nickname', f'Bot #{bot.botid}')}</code>\n━━━━━━━━━━━━━━━━━━━━\n⚡ Đã gửi tin nhắn tới đội !</blockquote>",
                parse_mode="HTML"
            )
        finally:
            bot.is_busy = False
    except Exception as e:
        if 'bot' in locals():
            bot.is_busy = False
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>✅ GỬI TIN NHẮN THÀNH CÔNG</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Teamcode:</b> <code>{tcode}</code>\n💬 <b>Nội dung:</b> <i>{msg_content}</i>\n🤖 <b>Bot:</b> <code>{getattr(bot, 'nickname', f'Bot #{bot.botid}')}</code>\n━━━━━━━━━━━━━━━━━━━━\n⚡ Đã gửi tin nhắn tới đội !</blockquote>",
                parse_mode="HTML"
            )
                
@telegram_bot.message_handler(commands=['rd'])
@check_group_only
@async_telegram
def handle_telegram_rd(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) < 3:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ SAI CÚ PHÁP LỆNH</b>\n"
                f"💡 <i>Vui lòng nhập theo định dạng:</i>\n"
                f"<code>/rd [mã phòng] [uid1 uid2]</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        if not parts[1].isdigit():
            telegram_bot.reply_to(
                message, 
                "<blockquote>❌ LỖI: Mã phòng bắt buộc phải là ký tự số!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        team_code = int(parts[1])
        target_uids = []
        for uid_str in parts[2:]:
            try: 
                target_uids.append(int(uid_str))
            except: 
                pass
        
        if not target_uids:
            telegram_bot.reply_to(
                message, 
                "<blockquote>❌ LỖI: Danh sách UID mục tiêu không hợp lệ!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        bots = get_available_bots(1)
        if not bots:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>⚠️ HỆ THỐNG QUÁ TẢI</b>\n"
                f"🔴 Không thể kích hoạt múa S7 cho phòng <code>{team_code}</code>.\n"
                f"🤖 Hiện tại không có Bot nào rảnh. Vui lòng đợi trong giây lát!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        bot = bots[0]
        bot.is_busy = True  
        skin_ids = [914051001, 914053001, 914044001, 914047001, 914047002, 914048001, 914053001]
        skin_id = random.choice(skin_ids)
        emotes = [
            909049010, 909051003, 909033002, 909041005, 909038010,
            909039011, 909040010, 909000081, 909000085, 909000063,
            909000075, 909033001, 909000090, 909000068, 909000098,
            909035007, 909037011, 909038012, 909035012, 909042008,
            909045001
        ]
        
        cfg = getattr(bot, "bot_config", {}) or {}
        botid = cfg.get('auth_bot_login', {}).get('uid')
        if not botid:
            botid = getattr(bot, 'botid', None)
        
        all_dancers = []
        if botid:
            try: 
                all_dancers.append(int(botid))
            except: 
                pass
        all_dancers.extend(target_uids)
        unique_dancers = list(dict.fromkeys(all_dancers))
        bot_name = getattr(bot, 'nickname', f"Bot #{bot.botid}")
        
        uid_list_str = ', '.join([f"<code>{uid}</code>" for uid in target_uids])
        
        msg = telegram_bot.reply_to(
            message,
            f"<blockquote><b>⚡ BOT ĐANG TIẾN HÀNH MÚA RANDOM</b>\n━━━━━━━━━━━━━━━━\n🎯 Team: <code>{team_code}</code>\n🤖 Bot: <code>{bot_name}</code>\n👥 Mục tiêu: {uid_list_str}\n━━━━━━━━━━━━━━━━\n⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        def auto_rd():
            try:
                sock = bot.sock39699
                if not sock: 
                    return
                sock.sendall(bot._bot.join_squad(team_code))
                time.sleep(1)
                sock.sendall(bot._bot.play_animation(skin_id))
                time.sleep(2.5)
                sock.sendall(bot._bot.showskin(skin_id))
                time.sleep(1)
                used = []
                for _ in range(18):
                    for uid in unique_dancers:
                        available = [e for e in emotes if e not in used]
                        if not available:
                            used.clear()
                            available = emotes[:]
                        emo = random.choice(available)
                        used.append(emo)
                        sock.sendall(bot._bot.play_emote(emo, [uid]))
                        if len(used) == len(emotes):
                            used.clear()
                    time.sleep(5)
                try: 
                    sock.sendall(bot._bot.leave_squad(0))
                except: 
                    pass
                try:
                    telegram_bot.edit_message_text(
                        f"<blockquote><b>✅ HOÀN TẤT</b>\n━━━━━━━━━━━━━━━━\n🎯 Team: <code>{team_code}</code>\n🤖 Bot: <code>{bot_name}</code>\n👥 Mục tiêu: {uid_list_str}\n━━━━━━━━━━━━━━━━\n⚡ Đã thực hiện xong tiến trình múa random!</blockquote>",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                except: 
                    pass
            except Exception as e:
                print("RD ERROR:", e)
                try: 
                    sock.sendall(bot._bot.leave_squad(0))
                except: 
                    pass
                try:
                    telegram_bot.edit_message_text(
                        f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                except: 
                    pass
            finally:
                bot.is_busy = False  
        
        threading.Thread(target=auto_rd, daemon=True).start()
        
    except Exception as e:
        telegram_bot.reply_to(
            message,
            f"<blockquote>❌ LỖI HỆ THỐNG: {str(e)[:50]}</blockquote>",
            parse_mode="HTML"
        )
                
@telegram_bot.message_handler(commands=['hdco'])
@check_group_only
@async_telegram
def handle_telegram_hdco_cmd(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/hdco [teamcode] [uid1 uid2]</code></blockquote>",
            parse_mode="HTML"
        )
        return
    
    try: 
        tc = int(parts[1])
    except:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ LỖI</b>\n🔴 Teamcode phải là số!</blockquote>",
            parse_mode="HTML"
        )
        return
    
    custom_uids = []
    for x in parts[2:]:
        try: 
            custom_uids.append(int(x))
        except: 
            pass
    
    if not custom_uids:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ LỖI</b>\n🔴 Cần ít nhất 1 UID!</blockquote>",
            parse_mode="HTML"
        )
        return
    
    bots = get_available_bots(1)
    if not bots:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>⚠️ QUÁ TẢI</b>\n🔴 Không có bot rảnh!</blockquote>",
            parse_mode="HTML"
        )
        return
    
    bot = bots[0]
    bot.is_busy = True
    bot_name = getattr(bot, 'nickname', f'Bot #{bot.botid}')
    
    uid_list_str = ', '.join([f"<code>{uid}</code>" for uid in custom_uids])
    
    msg = telegram_bot.reply_to(
        message,
        f"<blockquote><b>⚡ BOT ĐANG TIẾN HÀNH MÚA HÀNH ĐỘNG CỔ</b>\n━━━━━━━━━━━━━━━━\n🎯 Team: <code>{tc}</code>\n🤖 Bot: <code>{bot_name}</code>\n👥 Mục tiêu: {uid_list_str}\n━━━━━━━━━━━━━━━━\n⏳ Đang xử lý...</blockquote>",
        parse_mode="HTML"
    )
    
    def safe_send(data):
        try:
            if bot.sock39699: 
                bot.sock39699.send(data)
        except: 
            pass
    
    def run_hdco():
        try:
            if not bot.sock39699: 
                return
            bot.rstatus = (4, '')
            safe_send(bot._bot.join_squad(tc))
            time.sleep(2.5)
            ids = list(custom_uids)
            if bot.botid and int(bot.botid) not in ids:
                ids.append(int(bot.botid))
            skin_ids = [914051001, 914053001, 914044001, 914047001, 914047002, 914048001]
            skin_id = random.choice(skin_ids)
            safe_send(bot._bot.play_animation(skin_id))
            time.sleep(3)
            safe_send(bot._bot.showskin(skin_id))
            time.sleep(1.5)
            vip_emotes = [909000020, 909000021, 909000027, 909000008, 909000011, 909000012, 909042007, 909000040, 909000016, 909000029, 909000037, 909000022, 909000043, 909000061, 909000066]
            for _ in range(1):
                for emo in vip_emotes:
                    if not bot.sock39699: 
                        break
                    safe_send(bot._bot.play_emote(emo, ids))
                    time.sleep(4.5)
                time.sleep(3)
            try: 
                safe_send(bot._bot.leave_squad(tc))
            except: 
                pass
            try:
                telegram_bot.edit_message_text(
                    f"<blockquote><b>✅ HOÀN TẤT</b>\n━━━━━━━━━━━━━━━━\n🎯 Team: <code>{tc}</code>\n🤖 Bot: <code>{bot_name}</code>\n👥 Mục tiêu: {uid_list_str}\n━━━━━━━━━━━━━━━━\n⚡ Đã thực hiện xong tiến trình múa hành động cổ!</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
            except: 
                pass
        except Exception as e:
            print("HDCO ERROR:", e)
            try:
                telegram_bot.edit_message_text(
                    f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
            except: 
                pass
        finally:
            bot.is_busy = False
    
    threading.Thread(target=run_hdco, daemon=True).start()
        
@telegram_bot.message_handler(commands=['rngau'])
@check_group_only
@async_telegram
def handle_telegram_rngau_cmd(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/rngau [teamcode] [uid1 uid2]</code></blockquote>",
            parse_mode="HTML"
        )
        return
    
    try: 
        tc = int(parts[1])
    except:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ LỖI</b>\n🔴 Teamcode phải là số!</blockquote>",
            parse_mode="HTML"
        )
        return
    
    custom_uids = []
    for x in parts[2:]:
        try: 
            custom_uids.append(int(x))
        except: 
            pass
    
    if not custom_uids:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ LỖI</b>\n🔴 Cần ít nhất 1 UID!</blockquote>",
            parse_mode="HTML"
        )
        return
    
    bots = get_available_bots(1)
    if not bots:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>⚠️ QUÁ TẢI</b>\n🔴 Không có bot rảnh!</blockquote>",
            parse_mode="HTML"
        )
        return
    
    bot = bots[0]
    bot.is_busy = True
    bot_name = getattr(bot, 'nickname', f'Bot #{bot.botid}')
    
    uid_list_str = ', '.join([f"<code>{uid}</code>" for uid in custom_uids])
    
    msg = telegram_bot.reply_to(
        message,
        f"<blockquote><b>⚡ BOT ĐANG TIẾN HÀNH BẬT HÀNH ĐỘNG NGẦU </b>\n━━━━━━━━━━━━━━━━\n🎯 Team: <code>{tc}</code>\n🤖 Bot: <code>{bot_name}</code>\n👥 Mục tiêu: {uid_list_str}\n━━━━━━━━━━━━━━━━\n⏳ Đang xử lý...</blockquote>",
        parse_mode="HTML"
    )
    
    def safe_send(data):
        try:
            if bot.sock39699: 
                bot.sock39699.send(data)
        except: 
            pass
    
    def run_rngau():
        try:
            if not bot.sock39699: 
                return
            bot.rstatus = (4, '')
            safe_send(bot._bot.join_squad(tc))
            time.sleep(2.5)
            ids = list(custom_uids)
            if bot.botid and int(bot.botid) not in ids:
                ids.append(int(bot.botid))
            skin_ids = [914051001, 914053001, 914044001, 914047001, 914047002, 914048001]
            skin_id = random.choice(skin_ids)
            safe_send(bot._bot.play_animation(skin_id))
            time.sleep(3)
            safe_send(bot._bot.showskin(skin_id))
            time.sleep(1.5)
            rngau_emotes = [909000034, 909000036, 909000014, 909000089, 909000088, 909040008, 909051010, 909052004, 909052002]
            for _ in range(1):
                for emo in rngau_emotes:
                    if not bot.sock39699: 
                        break
                    safe_send(bot._bot.play_emote(emo, ids))
                    time.sleep(4.5)
                time.sleep(3)
            try: 
                safe_send(bot._bot.leave_squad(tc))
            except: 
                pass
            try:
                telegram_bot.edit_message_text(
                    f"<blockquote><b>✅ HOÀN TẤT</b>\n━━━━━━━━━━━━━━━━\n🎯 Team: <code>{tc}</code>\n🤖 Bot: <code>{bot_name}</code>\n👥 Mục tiêu: {uid_list_str}\n━━━━━━━━━━━━━━━━\n⚡ Đã thực hiện xong tiến trình múa hành động ngầu!</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
            except: 
                pass
        except Exception as e:
            print("RNGAU ERROR:", e)
            try:
                telegram_bot.edit_message_text(
                    f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
            except: 
                pass
        finally:
            bot.is_busy = False
    
    threading.Thread(target=run_rngau, daemon=True).start()
 
@telegram_bot.message_handler(commands=['resetall'])
@check_group_only
@async_telegram
def reset_all_bots(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Không có quyền!")
        return
    
    count = 0
    for bot in TCPbot.bots.values():
        bot.is_busy = False
        bot.cleanup()
        time.sleep(1)
        bot.start()
        count += 1
    
    telegram_bot.reply_to(message, f"✅ Đã reset {count} bot!")
        
@telegram_bot.message_handler(commands=['s7'])
@check_group_only
@async_telegram
def handle_telegram_s7_cmd(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
            "💡 Dùng: <code>/s7 [teamcode] [uid1 uid2]</code>\n"
            "📌 Ví dụ: <code>/s7 1234567 16104663154 123456789</code></blockquote>",
            parse_mode="HTML"
        )
        return
    
    try: 
        tc = int(parts[1])
    except:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ LỖI</b>\n🔴 Teamcode phải là số!</blockquote>",
            parse_mode="HTML"
        )
        return
    
    custom_uids = []
    for x in parts[2:]:
        try: 
            custom_uids.append(int(x))
        except: 
            pass
    
    if not custom_uids:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ LỖI</b>\n🔴 Cần ít nhất 1 UID!</blockquote>",
            parse_mode="HTML"
        )
        return
    
    bots = get_available_bots(1)
    if not bots:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>⚠️ QUÁ TẢI</b>\n🔴 Không có bot rảnh!</blockquote>",
            parse_mode="HTML"
        )
        return
    
    bot = bots[0]
    bot.is_busy = True
    bot_name = getattr(bot, 'nickname', f'Bot #{bot.botid}')
    
    uid_list_str = ', '.join([f"<code>{uid}</code>" for uid in custom_uids])
    
    msg = telegram_bot.reply_to(
        message,
        f"<blockquote><b>⚡ BOT ĐANG TIẾN HÀNH MÚA S7</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🎯 Team: <code>{tc}</code>\n"
        f"🤖 Bot: <code>{bot_name}</code>\n"
        f"👥 Mục tiêu: {uid_list_str}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⏳ Đang xử lý...</blockquote>",
        parse_mode="HTML"
    )
    
    def safe_send(data):
        try:
            if bot.sock39699: 
                bot.sock39699.send(data)
        except: 
            pass
    
    def run_s7():
        try:
            if not bot.sock39699: 
                return
            bot.rstatus = (4, '')
            safe_send(bot._bot.join_squad(tc))
            time.sleep(2.5)
            ids = list(custom_uids)
            if bot.botid and int(bot.botid) not in ids:
                ids.append(int(bot.botid))
            skin_ids = [914051001, 914053001, 914044001, 914047001, 914047002, 914048001]
            skin_id = random.choice(skin_ids)
            safe_send(bot._bot.play_animation(skin_id))
            time.sleep(3)
            safe_send(bot._bot.showskin(skin_id))
            time.sleep(1)
            vip_emotes = [909040010, 909000090, 909035012, 909038010, 909035007, 909039011, 909000063, 909000098, 909000081, 909000075, 909042008, 909000068, 909049010, 909041005, 909033002, 909045001, 909000085, 909051003]
            for _ in range(1):
                for emo in vip_emotes:
                    if not bot.sock39699: 
                        break
                    safe_send(bot._bot.play_emote(emo, ids))
                    time.sleep(5)
                time.sleep(3)
            try: 
                safe_send(bot._bot.leave_squad(tc))
            except: 
                pass
            try:
                telegram_bot.edit_message_text(
                    f"<blockquote><b>✅ HOÀN TẤT</b>\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"🎯 Team: <code>{tc}</code>\n"
                    f"🤖 Bot: <code>{bot_name}</code>\n"
                    f"👥 Mục tiêu: {uid_list_str}\n"
                    f"━━━━━━━━━━━━━━━━\n"
                    f"⚡ Đã thực hiện xong tiến trình múa s7!</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
            except: 
                pass
        except Exception as e:
            try:
                telegram_bot.edit_message_text(
                    f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
            except: 
                pass
        finally:
            bot.is_busy = False
    
    threading.Thread(target=run_s7, daemon=True).start()
            
def safe_edit(chat_id, msg_id, text):
    try:
        telegram_bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_id,
            text=text,
            parse_mode='HTML'
        )
    except Exception as e:
        print("EDIT FAIL:", e)
  
@telegram_bot.message_handler(commands=['checkbot'])
@check_group_only
@async_telegram
def tele_check(message):
    try:
        ADMIN_IDS = [8722607800]
        user_id = int(message.from_user.id)
        
        if user_id not in ADMIN_IDS:
            telegram_bot.reply_to(message, "❌ Không có quyền sử dụng lệnh này")
            return
        
        if not TCPbot.bots:
            telegram_bot.reply_to(message, "❌ Không có bot nào trong hệ thống")
            return
        
        online_count = 0
        offline_count = 0
        busy_count = 0
        free_count = 0
        total_count = len(TCPbot.bots)
        
        for bot in TCPbot.bots.values():
            running = bot.running_event.is_set() if bot.running_event else False
            is_busy = getattr(bot, 'is_busy', False)
            
            if not running:
                offline_count += 1
            else:
                online_count += 1
                if is_busy:
                    busy_count += 1
                else:
                    free_count += 1
        
        text = "<blockquote><b>📊 BẢNG TRẠNG THÁI BOT</b>\n"
        text += f"📌 Tổng bot: <b>{total_count}</b>\n"
        text += f"🟢 Online: <b>{online_count}</b>\n"
        text += f"🔴 Offline: <b>{offline_count}</b>\n"
        text += f"🟢 Rảnh: <b>{free_count}</b>\n"
        text += f"🟡 Bận: <b>{busy_count}</b>\n"
        text += f"</blockquote>\n\n"
        
        for bid, bot in TCPbot.bots.items():
            running = bot.running_event.is_set() if bot.running_event else False
            nickname = getattr(bot, 'nickname', 'Chưa đồng bộ')
            uid_bot = getattr(bot, 'botid', 'Trống')
            is_busy = getattr(bot, 'is_busy', False)
            
            if not running:
                status = "🔴 Offline"
                activity = "❌ Tắt"
            else:
                status = "🟢 Online"
                activity = "🟡 Bận" if is_busy else "✅ Rảnh"
            
            text += f"<blockquote><b>🤖 Bot {bid}</b>\n"
            text += f"├ Tên: {nickname}\n"
            text += f"├ UID: <code>{uid_bot}</code>\n"
            text += f"├ Trạng thái: {status}\n"
            text += f"└ Hoạt động: {activity}</blockquote>\n"
        
        telegram_bot.reply_to(message, text, parse_mode="HTML")
        
    except Exception as e:
        telegram_bot.reply_to(message, f"ERROR: {e}")
        print("CHECKBOTS ERROR:", e)
                        
@telegram_bot.message_handler(commands=['rinv'])
@check_group_only
@async_telegram
def handle_telegram_rinv(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return

    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/rinv [uid]</code>\n📌 Ví dụ: <code>/rinv 123456789</code></blockquote>",
                parse_mode="HTML"
            )
            return

        target_uid = parts[1].strip()
        if not target_uid.isdigit():
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ LỖI</b>\n🔴 UID phải là số!</blockquote>",
                parse_mode="HTML"
            )
            return

        bots = get_available_bots(1)
        if not bots:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>⚠️ BOT BẬN</b>\n🔴 Không có bot nào rảnh để xử lý!</blockquote>",
                parse_mode="HTML"
            )
            return

        bot = bots[0]
        bot.is_busy = True
        bot_name = getattr(bot, 'nickname', f'Bot #{bot.botid}')

        msg = telegram_bot.reply_to(
            message,
            f"<blockquote><b>⚡ ĐANG SPAM ROOM</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>UID:</b> <code>{target_uid}</code>\n🤖 <b>Bot:</b> <code>{bot_name}</code>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )

        def run_rinv():
            try:
                bot.sock39699.send(bot._bot.get_history(target_uid))
                time.sleep(1.5)
                
                room_id = bot.roomid
                if not room_id:
                    try:
                        telegram_bot.edit_message_text(
                            "<blockquote><b>⚠️ KHÔNG TÌM THẤY PHÒNG</b>\n🔴 UID không có trong phòng!</blockquote>",
                            chat_id=message.chat.id,
                            message_id=msg.message_id,
                            parse_mode="HTML"
                        )
                    except:
                        pass
                    return

                success_count = 0
                fail_count = 0

                for i in range(123):
                    try:
                        packet = bot._bot.request_join_room(room_id, target_uid)
                        bot.sock39699.send(packet)
                        success_count += 1
                        time.sleep(0.35)
                    except:
                        fail_count += 1

                    if (i + 1) % 20 == 0 or i == 122:
                        try:
                            telegram_bot.edit_message_text(
                                f"<blockquote><b>⚡ ĐANG SPAM ROOM</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>UID:</b> <code>{target_uid}</code>\n🏠 <b>Room ID:</b> <code>{room_id}</code>\n🤖 <b>Bot:</b> <code>{bot_name}</code>\n🔄 <b>Tiến độ:</b> <code>{i+1}/123</code>\n✅ <b>Thành công:</b> <code>{success_count}</code>\n❌ <b>Thất bại:</b> <code>{fail_count}</code>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Đang xử lý...</blockquote>",
                                chat_id=message.chat.id,
                                message_id=msg.message_id,
                                parse_mode="HTML"
                            )
                        except:
                            pass

                try:
                    telegram_bot.edit_message_text(
                        f"<blockquote><b>✅ SPAM ROOM HOÀN TẤT</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>UID:</b> <code>{target_uid}</code>\n🏠 <b>Room ID:</b> <code>{room_id}</code>\n🤖 <b>Bot:</b> <code>{bot_name}</code>\n🔄 <b>Tổng:</b> <code>123</code>\n✅ <b>Thành công:</b> <code>{success_count}</code>\n❌ <b>Thất bại:</b> <code>{fail_count}</code>\n━━━━━━━━━━━━━━━━━━━━\n⚡ Đã spam xong!</blockquote>",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                except:
                    pass

            except Exception as e:
                try:
                    telegram_bot.edit_message_text(
                        f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                except:
                    pass
            finally:
                bot.is_busy = False

        threading.Thread(target=run_rinv, daemon=True).start()

    except Exception as e:
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>",
            parse_mode="HTML"
        )
                
def random_colored_text(text):
    colors = [
        "FF0000",  # đỏ
        "00FF00",  # xanh lá
        "FFFF00",
  "00FFFF",
  "0000FF",
  "FF00FF",
  "FF66FF"   # vàng
    ]

    color = random.choice(colors)
    return f"[{color}]{text}"


def random_telegram_name():
    return f"[c][b][FFFFFF]Telegram: {random_colored_text('@zanbackj')}"


def random_tiktok_name():
    return f"[c][b][FFFF00]TikTok: {random_colored_text('@zanbackj')}"
                
@telegram_bot.message_handler(commands=['dc'])
@check_group_only
@async_telegram
def handle_telegram_hc(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/dc [teamcode]</code>\n📌 Ví dụ: <code>/dc 1234567</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        team_code = parts[1].strip()
        if not team_code.isdigit():
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ LỖI</b>\n🔴 Teamcode phải là số!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        team_code = int(team_code)
        
        bots = get_available_bots(1)
        if not bots:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>⚠️ HỆ THỐNG QUÁ TẢI</b>\n🔴 Không có bot rảnh!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        bot = bots[0]
        bot.is_busy = True
        bot_name = getattr(bot, 'nickname', f'Bot #{bot.botid}')
        
        msg = telegram_bot.reply_to(
            message,
            f"<blockquote><b>⚡ ĐANG MÚA S7</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Teamcode:</b> <code>{team_code}</code>\n🤖 <b>Bot:</b> <code>{bot_name}</code>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        def run_dc():
            try:
                sock = bot.sock39699
                
                bot.ids = []
                bot.rstatus = (10, team_code)
                sock.sendall(bot._bot.join_squad(team_code))
                time.sleep(3)
                
                sock.sendall(bot._bot.play_animation(914053001))
                time.sleep(4)
                sock.sendall(bot._bot.showskin(914053001))
                time.sleep(1)
                
                ids = list(set(bot.ids)) if bot.ids else []
                bot.rstatus = (0, 0)
                
                if not ids:
                    ids = [bot.botid]
                
                s7_emotes = [
                    909040010, 909000090, 909035012,
                    909038010, 909035007, 909039011,
                    909000063, 909000098,
                    909000081, 909000075,
                    909042008, 909000068,
                    909049010, 909041005,
                    909033002, 909045001,
                    909000085, 909051003
                ]
                
                for emote in s7_emotes:
                    try:
                        sock.sendall(bot._bot.play_emote(emote, ids))
                        time.sleep(4.5)
                    except:
                        pass
                
                sock.sendall(bot._bot.leave_squad(0))
                
                telegram_bot.edit_message_text(
                    f"<blockquote><b>✅ MÚA S7 THÀNH CÔNG</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Teamcode:</b> <code>{team_code}</code>\n🤖 <b>Bot:</b> <code>{bot_name}</code>\n👥 <b>Số UID:</b> <code>{len(ids)}</code>\n━━━━━━━━━━━━━━━━━━━━\n⚡ Đã múa xong!</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
                
            except Exception as e:
                try:
                    sock.sendall(bot._bot.leave_squad(0))
                except:
                    pass
                    
                telegram_bot.edit_message_text(
                    f"<blockquote><b>❌ MÚA S7 THẤT BẠI</b>\n━━━━━━━━━━━━━━━━━━━━\n🔴 <b>Lỗi:</b> {str(e)}\n━━━━━━━━━━━━━━━━━━━━\n💡 Kiểm tra lại teamcode!</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
            finally:
                bot.is_busy = False
        
        threading.Thread(target=run_dc, daemon=True).start()
        
    except Exception as e:
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>",
            parse_mode="HTML"
        )

@telegram_bot.message_handler(commands=['ghost'])
def handle_telegram_ghost(message):
    parts = message.text.split(maxsplit=2)
    
    if len(parts) < 2 or not parts[1].isdigit():
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
            "💡 <code>/ghost [teamcode] [tên]</code>\n"
            "📌 Ví dụ: <code>/ghost 1234567 zan</code></blockquote>",
            parse_mode='HTML'
        )
        return
    
    team_code = parts[1]
    custom_name = parts[2] if len(parts) > 2 else "Tiktok: @nqbinhan_"
    
    if not team_code.isdigit():
        telegram_bot.reply_to(message, "<blockquote><b>❌ LỖI</b>\nTeamcode phải là số!</blockquote>", parse_mode='HTML')
        return
    
    team_code_int = int(team_code)
    clean_name = custom_name  # Không lọc gì hết
    
    # Lấy bot rảnh
    bot = None
    for b in TCPbot.bots.values():
        if b.running_event.is_set() and b.sock39699:
            if b.rstatus[0] == 0 or b.rstatus[0] is None:
                if not getattr(b, 'is_busy', False):
                    bot = b
                    break
    
    if not bot:
        telegram_bot.reply_to(message, "<blockquote><b>⚠️ KHÔNG CÓ BOT RẢNH</b></blockquote>", parse_mode='HTML')
        return
    
    bot.is_busy = True
    
    status_msg = telegram_bot.reply_to(
        message,
        f"<blockquote><b>✅ GHOST THÀNH CÔNG TEAMCODE {team_code_int} !</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 Teamcode: <code>{team_code_int}</code>\n"
        f"📛 Tên hiển thị: <code>{clean_name}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Đã ghost thành công!</blockquote>",
        parse_mode='HTML'
    )
    
    def run_ghost():
        try:
            bot.rstatus = (2, team_code_int, clean_name)
            
            bot.sock39699.sendall(bot._bot.join_squad(team_code_int))
            time.sleep(1.5)
            
            # ====== Ghost trực tiếp ======
            colors = ["[FF0000]", "[00FF00]", "[0000FF]", "[FFFF00]", "[FF00FF]", "[00FFFF]"]
            color = random.choice(colors)
            
            fields = {}
            fields[0] = 5
            fields[1] = 61
            fields[2] = {}
            fields[2][1] = int(team_code_int)
            fields[2][2] = {}
            fields[2][2][1] = int(team_code_int)
            fields[2][2][3] = f"[b][c]{color}{clean_name}"
            fields[2][2][6] = int(time.time())
            fields[2][2][7] = 0x01
            fields[2][2][9] = 0x01
            fields[2][3] = "1"
            
            ghost_packet = bot._gen._builder(fields=list(fields.items()))
            bot.sock39699.sendall(ghost_packet)
            time.sleep(1)
            
            # Rời team
            bot.sock39699.sendall(bot._bot.leave_squad(0))
            
            bot.is_busy = False
            bot.rstatus = (0, 0)
            
        except Exception as e:
            bot.is_busy = False
            bot.rstatus = (0, 0)
            print(f"[GHOST ERROR] {e}")
    
    threading.Thread(target=run_ghost, daemon=True).start()
                            
@telegram_bot.message_handler(commands=['spamall'])
@check_group_only
@async_telegram
def handle_telegram_spamall(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return

    try:
        parts = message.text.strip().split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/spamall [uid]</code>\n📌 Ví dụ: <code>/spamall 123456789</code></blockquote>",
                parse_mode="HTML"
            )
            return

        target_uid = parts[1].strip()
        if not target_uid.isdigit():
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ LỖI</b>\n🔴 UID phải là số!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        # ====== KIỂM TRA UID TỪ 8-11 SỐ ======
        if len(target_uid) < 8 or len(target_uid) > 11:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ UID KHÔNG HỢP LỆ</b>\n🔴 UID phải có từ 8-11 chữ số!</blockquote>",
                parse_mode="HTML"
            )
            return

        bots = get_available_bots(1)
        if not bots:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>⚠️ BOT BẬN</b>\n🔴 Không có bot nào rảnh để xử lý!</blockquote>",
                parse_mode="HTML"
            )
            return

        bot = bots[0]
        bot.is_busy = True
        bot_name = getattr(bot, 'nickname', f'Bot #{bot.botid}')

        badge_values = [1048576, 1048577, 1048578, 1048579, 1048580]

        msg = telegram_bot.reply_to(
            message,
            f"<blockquote><b>⚡ ĐANG SPAM ALL BADGE</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>UID:</b> <code>{target_uid}</code>\n📛 <b>Loại:</b> <code>5 TÍCH</code>\n🤖 <b>Bot:</b> <code>{bot_name}</code>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )

        def run_spamall():
            try:
                total_success = 0
                total_fail = 0

                # 5 badge, mỗi badge spam 10 lần
                for badge_idx, badge_value in enumerate(badge_values, 1):
                    for i in range(10):
                        try:
                            # Tạo packet join squad
                            join_packet = bot._bot.request_join_squad(int(target_uid))
                            bot.sock39699.sendall(join_packet)
                            total_success += 1
                            time.sleep(0.3)
                            
                        except Exception as e:
                            total_fail += 1
                            print(f"[SPAMALL] Lỗi: {e}")
                        
                        # Cập nhật mỗi 5 lần
                        if (badge_idx * 10 + i) % 5 == 0:
                            try:
                                done = (badge_idx - 1) * 10 + i + 1
                                telegram_bot.edit_message_text(
                                    f"<blockquote><b>⚡ ĐANG SPAM ALL BADGE</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>UID:</b> <code>{target_uid}</code>\n📛 <b>tích:</b> <code>{badge_idx}/5</code>\n🔄 <b>Đã spam:</b> <code>{done}/50</code>\n✅ <b>Thành công:</b> <code>{total_success}</code>\n❌ <b>Thất bại:</b> <code>{total_fail}</code>\n🤖 <b>Bot:</b> <code>{bot_name}</code>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Đang xử lý...</blockquote>",
                                    chat_id=message.chat.id,
                                    message_id=msg.message_id,
                                    parse_mode="HTML"
                                )
                            except:
                                pass
                    
                    time.sleep(0.5)

                try:
                    bot.sock39699.sendall(bot._bot.leave_squad(0))
                except:
                    pass

                try:
                    telegram_bot.edit_message_text(
                        f"<blockquote><b>✅ SPAM ALL BADGE HOÀN TẤT</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>UID:</b> <code>{target_uid}</code>\n📛 <b>Loại:</b> <code>5 TÍCH</code>\n🔄 <b>Tổng:</b> <code>50</code>\n✅ <b>Thành công:</b> <code>{total_success}</code>\n❌ <b>Thất bại:</b> <code>{total_fail}</code>\n🤖 <b>Bot:</b> <code>{bot_name}</code>\n━━━━━━━━━━━━━━━━━━━━\n⚡ Đã spam xong!</blockquote>",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                except:
                    pass

            except Exception as e:
                try:
                    telegram_bot.edit_message_text(
                        f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>",
                        chat_id=message.chat.id,
                        message_id=msg.message_id,
                        parse_mode="HTML"
                    )
                except:
                    pass
            finally:
                bot.is_busy = False

        threading.Thread(target=run_spamall, daemon=True).start()

    except Exception as e:
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>",
            parse_mode="HTML"
        )
                      
@telegram_bot.message_handler(commands=['service'])
@check_group_only
@async_telegram
def telegram_service(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    msg = f"""
📦 BẢNG GIÁ DỊCH VỤ
━━━━━━━━━━━━━━━━━━━━━━━━

1. BOT THƯỜNG:
├ 1 ngày: 10k
├ 1 tuần: 50k
└ 1 tháng: 120k

5. BOT TÊN RIÊNG:
├ 1 ngày: 15k
├ 1 tuần: 60k
└ 1 tháng: 150k

2. BOT QUÂN ĐOÀN (nhiều người sử dụng được):
├ 1 ngày: 15k
├ 1 tuần: 65k
└ 1 tháng: 170k

3. CAPCUT PRO:
└ 50/1 tháng

4. WINK:
├ 1 tuần: 60k
├ 2 tuần: 100k
└ 3 tuần: 130k

━━━━━━━━━━━━━━━━━━━━━━━━
📩 có nhu cầu liên hệ admin: @zanbackj
"""
    telegram_bot.reply_to(message, msg)
                                 
@telegram_bot.message_handler(commands=['getlink'])
@check_group_only
@async_telegram
def get_group_link(message):
    if message.from_user.id != ADMIN_ID:
        telegram_bot.reply_to(message, "❌ Không có quyền!")
        return
    
    group_ids = []
    if os.path.exists(TELE_GROUPS_FILE):
        try:
            with open(TELE_GROUPS_FILE, "r", encoding="utf-8") as f:
                group_ids = json.load(f)
        except:
            pass
    
    if not group_ids:
        telegram_bot.reply_to(message, "📭 Chưa có group nào!")
        return
    
    result = "<b>📋 DANH SÁCH GROUP:</b>\n───────────────────────\n"
    
    for gid in group_ids:
        try:
            chat = telegram_bot.get_chat(gid)
            title = chat.title or "Unknown"
            
            try:
                if chat.username:
                    link = f"https://t.me/{chat.username}"
                else:
                    link = telegram_bot.export_chat_invite_link(gid)
            except:
                link = "Không thể tạo link (cần quyền admin)"
            
            result += f"📌 <b>{title}</b>\n"
            result += f"   ID: <code>{gid}</code>\n"
            result += f"   Link: {link}\n\n"
        except Exception as e:
            result += f"❌ <code>{gid}</code> - Lỗi: {str(e)[:30]}\n\n"
    
    telegram_bot.reply_to(message, result, parse_mode="HTML")
        
@telegram_bot.message_handler(commands=['info'])
@check_group_only
@async_telegram
def handle_info(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/info [UID]</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        uid = args[1].strip()
        if not uid.isdigit():
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ LỖI</b>\n🔴 UID phải là số!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        msg = telegram_bot.reply_to(
            message,
            "<blockquote>⏳ Đang tra cứu thông tin...</blockquote>",
            parse_mode="HTML"
        )
        
        url = f"http://localhost:2011/info1?uid={uid}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            telegram_bot.edit_message_text(
                f"<blockquote><b>❌ LỖI API</b>\n🔴 HTTP {response.status_code}</blockquote>",
                chat_id=message.chat.id,
                message_id=msg.message_id,
                parse_mode="HTML"
            )
            return
        
        data = response.json()
        
        if not data.get('success'):
            telegram_bot.edit_message_text(
                f"<blockquote><b>❌ LỖI</b>\n🔴 {data.get('error', 'Unknown error')}</blockquote>",
                chat_id=message.chat.id,
                message_id=msg.message_id,
                parse_mode="HTML"
            )
            return
        
        result = data.get('result', {})
        basic = result.get('basic_info', {})
        social = result.get('social_info', {})
        credit = result.get('credit_score_info', {})
        clan = result.get('clan_basic_info', {})
        pet = result.get('pet_info', {})
        profile = result.get('profile_info', {})
        
        def convert_time(timestamp):
            try:
                ts = int(timestamp)
                return datetime.datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
            except:
                return str(timestamp)
        
        reply = f"""
<blockquote><b>📊 THÔNG TIN NGƯỜI CHƠI</b>
━━━━━━━━━━━━━━━━━━━━
👤 <b>Tên:</b> <code>{basic.get('nickname', 'N/A')}</code>
🆔 <b>UID:</b> <code>{basic.get('account_id', 'N/A')}</code>
🌍 <b>Khu vực:</b> <code>{basic.get('region', 'N/A')}</code>
🎖 <b>Cấp độ:</b> <code>{basic.get('level', 'N/A')}</code>
❤️ <b>Lượt thích:</b> <code>{basic.get('liked', 'N/A')}</code>
🏆 <b>Hạng BR:</b> <code>{basic.get('rank', 'N/A')}</code>
🏆 <b>Hạng CS:</b> <code>{basic.get('cs_rank', 'N/A')}</code>
💯 <b>Điểm uy tín:</b> <code>{credit.get('credit_score', 'N/A')}</code>
✍️ <b>Tiểu sử:</b> <i>{social.get('signature', 'Không có')}</i>
━━━━━━━━━━━━━━━━━━━━
<b>🏠 CLAN:</b>
├ <b>Tên:</b> <code>{clan.get('clan_name', 'Không có')}</code>
├ <b>ID:</b> <code>{clan.get('clan_id', 'N/A')}</code>
├ <b>Level:</b> <code>{clan.get('clan_level', 'N/A')}</code>
└ <b>Thành viên:</b> <code>{clan.get('member_num', 0)}/{clan.get('capacity', 0)}</code>
━━━━━━━━━━━━━━━━━━━━
<b>🐾 PET:</b>
├ <b>Tên:</b> <code>{pet.get('name', 'Không có')}</code>
├ <b>Level:</b> <code>{pet.get('level', 'N/A')}</code>
└ <b>Skin ID:</b> <code>{pet.get('skin_id', 'N/A')}</code>
━━━━━━━━━━━━━━━━━━━━
</blockquote>
"""
        telegram_bot.edit_message_text(
            reply,
            chat_id=message.chat.id,
            message_id=msg.message_id,
            parse_mode="HTML"
        )
        
    except requests.exceptions.Timeout:
        telegram_bot.edit_message_text(
            "<blockquote><b>❌ LỖI</b>\n🔴 API không phản hồi, vui lòng thử lại sau.</blockquote>",
            chat_id=message.chat.id,
            message_id=msg.message_id,
            parse_mode="HTML"
        )
    except Exception as e:
        telegram_bot.edit_message_text(
            f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>",
            chat_id=message.chat.id,
            message_id=msg.message_id,
            parse_mode="HTML"
        )     
                                
@telegram_bot.message_handler(commands=['add'])
@check_group_only
@async_telegram
def handle_telegram_add_user(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "<pre>❌ TỪ CHỐI TRUY CẬP\n🔴 Bạn không có quyền hạn Admin để sử dụng lệnh này!</pre>")
        return
    
    try:
        cid = message.chat.id
        parts = message.text.strip().split()
        if len(parts) < 4:
            error_msg = (
                f"<pre>❌ SAI CÚ PHÁP LỆNH QUẢN TRỊ\n"
                f"💡 Định dạng lẻ: /add [bot id] [uid] [thời gian]\n"
                f"💡 Định dạng all: /add all [uid] [thời gian]\n\n"
                f"📌 Ví dụ:\n"
                f"➜ /add 1 12345678 30d\n"
                f"➜ /add all 12345678 30d</pre>"
            )
            telegram_bot.reply_to(message, error_msg)
            return
        
        is_add_all = (parts[1].lower() == "all")
        if not is_add_all and not parts[1].isdigit():
            telegram_bot.reply_to(message, "<pre>❌ Lỗi: Bot ID phải là số hoặc chữ 'all'!</pre>")
            return
        
        if not parts[2].isdigit():
            telegram_bot.reply_to(message, "<pre>❌ Lỗi: UID Game phải là ký tự số!</pre>")
            return
        
        add_uid = int(parts[2].strip())
        duration = parts[3].strip()
        bots_to_process = []
        
        if is_add_all:
            for b in TCPbot.bots.values():
                if b.running_event.is_set() and hasattr(b, "manager"):
                    bots_to_process.append(b)
        else:
            target_bot_id = int(parts[1].strip())
            for b in TCPbot.bots.values():
                bot_config_id = b.bot_config.get("bot_id") if hasattr(b, "bot_config") else None
                if (bot_config_id == target_bot_id or getattr(b, "botid", None) == target_bot_id) and hasattr(b, "manager"):
                    bots_to_process.append(b)
                    break
        
        if not bots_to_process:
            if is_add_all:
                fail_msg = "<pre>⚠️ THÔNG BÁO\n🔴 Hệ thống hiện tại không có Bot nào đang online!</pre>"
            else:
                fail_msg = f"<pre>⚠️ THÔNG BÁO\n🔴 Bot ID {target_bot_id} hiện offline hoặc không có kết nối Database.</pre>"
            telegram_bot.reply_to(message, fail_msg)
            return
        
        success_count = 0
        failed_bots = []
        
        for bot in bots_to_process:
            cfg = getattr(bot, "bot_config", {}) or {}
            current_bot_id = cfg.get("bot_id") or getattr(bot, "botid", None)
            if not current_bot_id:
                continue
            try:
                result = bot.manager.add_uid_to_access(current_bot_id, add_uid, duration)
                if result == True:
                    success_count += 1
                else:
                    bot_name = getattr(bot, 'nickname', f"Bot #{current_bot_id}")
                    failed_bots.append(bot_name)
            except Exception as ex:
                bot_name = getattr(bot, 'nickname', f"Bot #{current_bot_id}")
                failed_bots.append(f"{bot_name}")
        
        if is_add_all:
            done_msg = (
                f"<pre>✅ TIẾN TRÌNH ADD ALL HOÀN TẤT\n"
                f"───────────────────────\n"
                f"👤 UID Game: {add_uid}\n"
                f"⏳ Thời hạn: {duration}\n"
                f"📊 Thành công: {success_count}/{len(bots_to_process)} Bot</pre>"
            )
            if failed_bots:
                done_msg += f"\n⚠️ <i>Thất bại tại: {', '.join(failed_bots)}</i>"
        else:
            if success_count > 0:
                done_msg = (
                    f"<pre>✅ KÍCH HOẠT TÀI KHOẢN THÀNH CÔNG\n"
                    f"───────────────────────\n"
                    f"🤖 Hệ thống Bot: {target_bot_id}\n"
                    f"👤 UID Game: {add_uid}\n"
                    f"⏳ Thời hạn cấp: {duration}\n"
                    f"⚙️ Trạng thái: Đã thêm vào danh sách sử dụng bot thành công!</pre>"
                )
            else:
                done_msg = f"<pre>❌ THẤT BẠI\n🔴 Không thể thêm UID {add_uid} vào Database của Bot {target_bot_id}.</pre>"
        
        telegram_bot.reply_to(message, done_msg)
        
    except Exception as e:
        try:
            telegram_bot.reply_to(message, f"<pre>❌ LỖI HỆ THỐNG\n🔴 Chi tiết: {str(e)[:50]}</pre>")
        except:
            pass
        print("ADD USER ERROR:", e)

@telegram_bot.message_handler(commands=['kb'])
@check_group_only
@async_telegram
def telegram_kb(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Không có quyền!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/kb [botid] [uid]</code>\n📌 Ví dụ: <code>/kb 1 123456789</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        bot_id = parts[1]
        uid = parts[2]
        
        import requests
        url = f"http://127.0.0.1:2011/kb?uid={uid}&botid={bot_id}"
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if result.get('status') == 'success':
            data = result.get('data', {})
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>✅ GỬI KẾT BẠN THÀNH CÔNG</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 <b>Bot:</b> <code>{data.get('bot_name', '')}</code>\n🆔 <b>UID:</b> <code>{uid}</code>\n📩 <b>Trạng thái:</b> {result.get('message')}\n━━━━━━━━━━━━━━━━━━━━\n⚡ Đã gửi qua API!</blockquote>",
                parse_mode="HTML"
            )
        else:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ GỬI KẾT BẠN THẤT BẠI</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 <b>Bot ID:</b> <code>{bot_id}</code>\n🆔 <b>UID:</b> <code>{uid}</code>\n⚠️ <b>Lý do:</b> {result.get('message')}\n━━━━━━━━━━━━━━━━━━━━\n💡 Kiểm tra lại bot!</blockquote>",
                parse_mode="HTML"
            )
            
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")
        
MAX_REG_PER_DAY = 50
MAX_REG_ADMIN = 9999
REG_HISTORY_FILE = "reg_history.json"
LIMITS_FILE = "reg_limits.json"

# ====== LOG ======
def log_print(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# ====== IMPORT ======
from zan_fixed import (
    generate_accounts, REGION_LANG, CLIENT_VERSION, RELEASE_VERSION,
    LOGIN_SERVER_URL, guest_register, token_grant, major_register,
    major_login, choose_region, get_login_data, create_account,
    generate_nickname, generate_password, _build_major_login
)

# ====== REG HISTORY ======
def load_reg_history():
    if os.path.exists(REG_HISTORY_FILE):
        try:
            with open(REG_HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_reg_history(data):
    with open(REG_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_today():
    return time.strftime("%Y-%m-%d")

def get_user_reg_today(user_id):
    history = load_reg_history()
    today = get_today()
    user_key = str(user_id)
    
    if user_key in history:
        data = history[user_key]
        if isinstance(data, dict) and data.get("date") == today:
            return data.get("count", 0)
    return 0

def update_user_reg(user_id, count):
    history = load_reg_history()
    today = get_today()
    user_key = str(user_id)
    
    if user_key not in history or not isinstance(history[user_key], dict) or history[user_key].get("date") != today:
        history[user_key] = {"date": today, "count": 0}
    
    history[user_key]["count"] += count
    save_reg_history(history)

# ====== LẤY GIỚI HẠN REG CỦA USER ======
def get_user_reg_limit(user_id):
    """Lấy giới hạn reg của user từ file reg_limits.json"""
    if os.path.exists(LIMITS_FILE):
        try:
            with open(LIMITS_FILE, 'r', encoding='utf-8') as f:
                limits_data = json.load(f)
            return limits_data.get(str(user_id), {}).get("limit", MAX_REG_PER_DAY)
        except:
            return MAX_REG_PER_DAY
    return MAX_REG_PER_DAY

@telegram_bot.message_handler(commands=['reg'])
@async_telegram
def telegram_reg_account(message):
    user_id = message.from_user.id
    is_admin = is_telegram_admin(user_id)
    
    # ====== CHỈ ADMIN MỚI ĐƯỢC DÙNG ======
    if not is_admin:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ TỪ CHỐI TRUY CẬP</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔴 Chỉ Admin mới có quyền sử dụng lệnh này!\n"
            "📩 Liên hệ: @zanbackj</blockquote>",
            parse_mode="HTML"
        )
        return
    
    # ====== CHECK GROUP ======
    if not check_user_in_group(user_id):
        send_warn_join_group(message)
        return
    
    try:
        args = message.text.split()
        if len(args) < 4:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💡 <code>/reg [số_lượng] [region] [tên]</code>\n\n"
                "📌 <b>Ví dụ:</b>\n"
                "<code>/reg 10 VN zan</code>\n\n"
                "🌍 <b>Region hỗ trợ:</b>\n"
                "<code>VN, TH, ID, SG, MY, IN, PK, BD, RU, BR, EU, NA, ME, TW</code>\n\n"
                "📊 <b>Giới hạn Admin:</b> <code>{}</code> acc/lần</blockquote>".format(MAX_REG_ADMIN),
                parse_mode="HTML"
            )
            return
        
        count = int(args[1])
        region = args[2].upper()
        name = args[3]
        
        # ====== KIỂM TRA TÊN ======
        if len(name) < 1:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ TÊN QUÁ NGẮN</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔴 Tên phải có ít nhất <b>1</b> ký tự!\n"
                f"💡 Vui lòng nhập tên hợp lệ.</blockquote>",
                parse_mode="HTML"
            )
            return
        
        if len(name) > 8:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ TÊN QUÁ DÀI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔴 Tên chỉ được tối đa <b>8</b> ký tự!\n"
                f"📌 Tên hiện tại: <code>{name}</code> ({len(name)} ký tự)\n"
                f"💡 Vui lòng rút gọn tên (tối đa 8 ký tự).</blockquote>",
                parse_mode="HTML"
            )
            return
        
        if " " in name:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ TÊN CÓ KHOẢNG CÁCH</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔴 Tên <b>KHÔNG ĐƯỢC</b> có khoảng cách!\n"
                f"📌 Tên hiện tại: <code>{name}</code>\n"
                f"💡 Vui lòng nhập tên viết liền, không dấu cách.\n"
                f"📌 Ví dụ: <code>zan</code>, <code>vip</code>, <code>ff</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        if region not in REGION_LANG:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ REGION KHÔNG HỢP LỆ</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🌍 Hỗ trợ: <code>{', '.join(REGION_LANG.keys())}</code>\n"
                f"📌 Ví dụ: <code>/reg 10 VN zan</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        if count < 1:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ LỖI</b>\n"
                f"🔴 Số lượng phải lớn hơn 0!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        if count > MAX_REG_ADMIN:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ LỖI</b>\n"
                f"🔴 Admin chỉ được reg tối đa <code>{MAX_REG_ADMIN}</code> acc/lần!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        msg = telegram_bot.reply_to(
            message,
            f"<blockquote><b>⏳ ĐANG TẠO TÀI KHOẢN</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Số lượng: <code>{count}</code>\n"
            f"🌍 Region: <code>{region}</code>\n"
            f"👤 Prefix: <code>{name}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Vui lòng chờ...</blockquote>",
            parse_mode="HTML"
        )
        
        def run_reg():
            try:
                from telebot.types import InputFile
                import io
                
                results = generate_accounts(name, region, count, 60)
                
                if results:
                    file_content = f"========== FREE FIRE ACCOUNTS ==========\n"
                    file_content += f"Total: {len(results)} accounts\n"
                    file_content += f"Region: {region}\n"
                    file_content += f"Prefix: {name}\n"
                    file_content += f"Version: 1.126.1 (OB54)\n"
                    file_content += f"Server: {LOGIN_SERVER_URL}\n"
                    file_content += f"Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    file_content += f"========================================\n\n"
                    
                    tokens = []
                    for i, acc in enumerate(results, 1):
                        file_content += f"[{i}] UID: {acc.get('uid')}\n"
                        file_content += f"    Password: {acc.get('password')}\n"
                        file_content += f"    Name: {acc.get('name')}\n"
                        file_content += f"    Region: {acc.get('region')}\n"
                        file_content += f"    Account ID: {acc.get('account_id')}\n"
                        file_content += f"    Access Token: {acc.get('access_token')}\n"
                        file_content += f"    Open ID: {acc.get('open_id')}\n"
                        file_content += f"    Status: {acc.get('status')}\n"
                        file_content += f"    ------------------------------\n"
                        if acc.get('access_token'):
                            tokens.append(acc.get('access_token'))
                    
                    file_bytes = io.BytesIO(file_content.encode('utf-8'))
                    file_bytes.name = "accounts.json"
                    
                    caption = (
                        f"<blockquote><b>✅ ADMIN REG THÀNH CÔNG</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📦 Đã tạo: <code>{len(results)}/{count}</code> acc\n"
                        f"🌍 Region: <code>{region}</code>\n"
                        f"👤 Prefix: <code>{name}</code>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📥 File: <code>accounts.json</code></blockquote>"
                    )
                    
                    telegram_bot.send_document(
                        message.chat.id,
                        file_bytes,
                        caption=caption,
                        visible_file_name="accounts.json",
                        parse_mode="HTML"
                    )
                    
                    try:
                        telegram_bot.delete_message(message.chat.id, msg.message_id)
                    except:
                        pass
                    
                    if tokens:
                        temp_tokens[message.from_user.id] = tokens
                        
                        keyboard = InlineKeyboardMarkup()
                        keyboard.add(
                            InlineKeyboardButton("✅ Có (1 bot)", callback_data="addbot_yes"),
                            InlineKeyboardButton("✅ Có (ALL bot)", callback_data="addbot_all"),
                            InlineKeyboardButton("❌ Không", callback_data="addbot_no")
                        )
                        telegram_bot.send_message(
                            message.chat.id,
                            f"<blockquote><b>🔗 KẾT NỐI BOT TCP?</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🤖 Số lượng: <code>{len(tokens)}</code> acc\n"
                            f"📌 Chọn 'Có (1 bot)' để thêm 1 bot\n"
                            f"📌 Chọn 'Có (ALL bot)' để thêm tất cả\n"
                            f"📌 Chọn 'Không' để hủy</blockquote>",
                            parse_mode="HTML",
                            reply_markup=keyboard
                        )
                    
                else:
                    telegram_bot.send_message(
                        message.chat.id,
                        "<blockquote><b>❌ KHÔNG TẠO ĐƯỢC ACCOUNT</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🔴 Vui lòng thử lại sau!</blockquote>",
                        parse_mode="HTML"
                    )
                    
            except Exception as e:
                import traceback
                traceback.print_exc()
                telegram_bot.send_message(
                    message.chat.id,
                    f"<blockquote><b>❌ LỖI</b>\n"
                    f"🔴 {str(e)}</blockquote>",
                    parse_mode="HTML"
                )
        
        threading.Thread(target=run_reg, daemon=True).start()
        
    except ValueError:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ LỖI</b>\n"
            f"🔴 Số lượng phải là số nguyên!</blockquote>",
            parse_mode="HTML"
        )
    except Exception as e:
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>❌ LỖI</b>\n"
            f"🔴 {str(e)}</blockquote>",
            parse_mode="HTML"
        )
                            
# ====== CALLBACK CHO ADD BOT ======
@telegram_bot.callback_query_handler(func=lambda call: call.data in ["addbot_yes", "addbot_no", "addbot_all"])
def callback_addbot(call):
    try:
        user_id = call.from_user.id
        
        # ====== KIỂM TRA ADMIN ======
        if not is_telegram_admin(user_id):
            telegram_bot.answer_callback_query(
                call.id, 
                "❌ Bạn không phải admin để thực hiện yêu cầu này!",
                show_alert=True
            )
            return
        
        tokens = temp_tokens.get(user_id, [])
        
        if call.data == "addbot_no":
            telegram_bot.edit_message_text(
                "<blockquote><b>✅ ĐÃ HỦY KẾT NỐI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Không thêm bot TCP vào hệ thống.</blockquote>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )
            telegram_bot.answer_callback_query(call.id, "Đã hủy!")
            if user_id in temp_tokens:
                del temp_tokens[user_id]
            return
        
        if not tokens:
            telegram_bot.edit_message_text(
                "<blockquote><b>❌ LỖI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔴 Không lấy được access token!\n"
                f"💡 Vui lòng thử lại lệnh /reg</blockquote>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )
            telegram_bot.answer_callback_query(call.id, "Lỗi token!")
            return
        
        # ====== THÊM 1 BOT ======
        if call.data == "addbot_yes":
            token = tokens[0] if tokens else None
            if not token:
                telegram_bot.answer_callback_query(call.id, "Không có token!")
                return
            
            result = TCPbot.add_bot(token)
            
            if result["status"]:
                bot_id = result["bot_id"]
                TCPbot.bots[bot_id].start()
                
                telegram_bot.edit_message_text(
                    f"<blockquote><b>✅ THÊM 1 BOT THÀNH CÔNG</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🤖 Bot ID: <code>{bot_id}</code>\n"
                    f"🔑 Token: <code>{token[:20]}...</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⚡ Bot đã được thêm vào hệ thống!</blockquote>",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="HTML"
                )
                telegram_bot.answer_callback_query(call.id, "Thêm bot thành công!")
            else:
                telegram_bot.edit_message_text(
                    f"<blockquote><b>❌ THÊM BOT THẤT BẠI</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔴 Lý do: {result['message']}</blockquote>",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="HTML"
                )
                telegram_bot.answer_callback_query(call.id, "Thêm bot thất bại!")
        
        # ====== THÊM ALL BOT ======
        elif call.data == "addbot_all":
            success_count = 0
            fail_count = 0
            bot_ids = []
            
            for token in tokens:
                result = TCPbot.add_bot(token)
                if result["status"]:
                    bot_id = result["bot_id"]
                    TCPbot.bots[bot_id].start()
                    success_count += 1
                    bot_ids.append(bot_id)
                else:
                    fail_count += 1
            
            telegram_bot.edit_message_text(
                f"<blockquote><b>✅ THÊM ALL BOT THÀNH CÔNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Thành công: <code>{success_count}</code> bot\n"
                f"❌ Thất bại: <code>{fail_count}</code> bot\n"
                f"🤖 Bot IDs: <code>{', '.join(map(str, bot_ids))}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Tất cả bot đã được thêm vào hệ thống!</blockquote>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML"
            )
            telegram_bot.answer_callback_query(call.id, f"Thêm {success_count} bot thành công!")
        
        # Xóa token tạm
        if user_id in temp_tokens:
            del temp_tokens[user_id]
            
    except Exception as e:
        telegram_bot.answer_callback_query(call.id, f"Lỗi: {str(e)}")

# ====== LỆNH CHECKALLREG (BỎ HTML) ======
@telegram_bot.message_handler(commands=['checkallreg'])
@async_telegram
def telegram_checkallreg(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    try:
        if not is_telegram_admin(message.from_user.id):
            telegram_bot.reply_to(message, "❌ KHÔNG CÓ QUYỀN - Chỉ admin mới dùng được!")
            return
        
        history = load_reg_history()
        limits_data = {}
        if os.path.exists(LIMITS_FILE):
            with open(LIMITS_FILE, "r", encoding="utf-8") as f:
                limits_data = json.load(f)
        
        if not history:
            telegram_bot.reply_to(message, "📭 CHƯA CÓ DỮ LIỆU REG - Chưa có ai reg account!")
            return
        
        text = "📊 DANH SÁCH REG CỦA TẤT CẢ USER\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        today = get_today()
        total_reg = 0
        user_list = []
        
        for uid, data in history.items():
            if isinstance(data, dict):
                date = data.get("date", "N/A")
                count = data.get("count", 0)
                total_reg += count
                
                limit = limits_data.get(uid, {}).get("limit", MAX_REG_PER_DAY)
                
                try:
                    user = telegram_bot.get_chat(int(uid))
                    name = user.first_name or "Unknown"
                    username = f"@{user.username}" if user.username else ""
                except:
                    name = "Unknown"
                    username = ""
                
                if date == today:
                    user_list.append({
                        "uid": uid,
                        "name": name,
                        "username": username,
                        "count": count,
                        "limit": limit,
                        "date": date
                    })
        
        user_list.sort(key=lambda x: x["count"], reverse=True)
        
        if not user_list:
            text += "📭 Hôm nay chưa có ai reg!\n"
        else:
            for i, u in enumerate(user_list, 1):
                text += f"{i}. {u['name']} {u['username']}\n"
                text += f"   UID: {u['uid']}\n"
                text += f"   Reg: {u['count']}/{u['limit']}\n"
                text += f"   Ngày: {u['date']}\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📦 Tổng reg hôm nay: {total_reg} accounts\n"
        text += f"👥 Tổng user: {len(user_list)} người"
        
        if len(text) > 4000:
            import io
            file_bytes = io.BytesIO(text.encode('utf-8'))
            file_bytes.name = "reg_report.txt"
            telegram_bot.send_document(
                message.chat.id,
                file_bytes,
                caption=f"Báo cáo reg ngày {today}"
            )
        else:
            telegram_bot.reply_to(message, text)
        
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ LỖI: {str(e)}")


# ====== LỆNH CHECKREG (BỎ HTML) ======
@telegram_bot.message_handler(commands=['checkreg'])
@async_telegram
def telegram_checkreg(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    try:
        user_id = message.from_user.id
        is_admin = is_telegram_admin(user_id)
        
        target_id = user_id
        target_name = message.from_user.first_name or "Unknown"
        
        if is_admin and message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_name = message.reply_to_message.from_user.first_name or "Unknown"
        
        if is_admin and len(message.text.split()) > 1:
            try:
                target_id = int(message.text.split()[1])
            except:
                pass
        
        history = load_reg_history()
        today = get_today()
        user_key = str(target_id)
        user_limit = get_user_reg_limit(target_id)
        
        today_count = 0
        if user_key in history:
            data = history[user_key]
            if isinstance(data, dict):
                if data.get("date") == today:
                    today_count = data.get("count", 0)
        
        reg_details = {}
        if os.path.exists("reg_details.json"):
            with open("reg_details.json", "r", encoding="utf-8") as f:
                reg_details = json.load(f)
        
        user_regs = reg_details.get(user_key, [])
        
        try:
            user = telegram_bot.get_chat(target_id)
            user_name = user.first_name or target_name
            username = f"@{user.username}" if user.username else ""
        except:
            user_name = target_name
            username = ""
        
        text = f"📊 THÔNG TIN REG\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"User: {user_name} {username}\n"
        text += f"ID: {target_id}\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"Hôm nay: {today}\n"
        text += f"Đã reg: {today_count}/{user_limit}\n"
        text += f"Còn lại: {user_limit - today_count}\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        
        if user_regs:
            text += f"Lịch sử reg gần đây:\n"
            for reg in user_regs[-5:]:
                date = reg.get("date", "N/A")
                count = reg.get("count", 0)
                region = reg.get("region", "N/A")
                text += f"  - {date}: {count} acc ({region})\n"
        
        limits_data = {}
        if os.path.exists(LIMITS_FILE):
            with open(LIMITS_FILE, "r", encoding="utf-8") as f:
                limits_data = json.load(f)
        
        user_limit_info = limits_data.get(user_key, {})
        if user_limit_info:
            limit = user_limit_info.get("limit", MAX_REG_PER_DAY)
            updated_by = user_limit_info.get("updated_by", "N/A")
            updated_at = user_limit_info.get("updated_at", "N/A")
            text += f"━━━━━━━━━━━━━━━━━━━━\n"
            text += f"Giới hạn reg: {limit} acc/ngày\n"
            if updated_by != "N/A":
                text += f"Updated by: {updated_by}\n"
                text += f"Lúc: {updated_at}\n"
        
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"Reset vào 00:00 hàng ngày"
        
        telegram_bot.reply_to(message, text)
        
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ LỖI: {str(e)}")


# ====== LỆNH TOPREG (BỎ HTML) ======
@telegram_bot.message_handler(commands=['topreg'])
@async_telegram
def telegram_topreg(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    try:
        history = load_reg_history()
        
        if not history:
            telegram_bot.reply_to(message, "📭 Chưa có dữ liệu reg!")
            return
        
        user_stats = {}
        for uid, data in history.items():
            if isinstance(data, dict):
                count = data.get("count", 0)
                if uid in user_stats:
                    user_stats[uid] += count
                else:
                    user_stats[uid] = count
        
        sorted_users = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        
        text = "🏆 TOP 10 USER REG NHIỀU NHẤT\n"
        text += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, (uid, count) in enumerate(sorted_users, 1):
            try:
                user = telegram_bot.get_chat(int(uid))
                name = user.first_name or "Unknown"
                username = f"@{user.username}" if user.username else ""
            except:
                name = "Unknown"
                username = ""
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} {username}\n"
            text += f"   {count} accounts\n"
            text += f"   UID: {uid}\n\n"
        
        telegram_bot.reply_to(message, text)
        
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ LỖI: {str(e)}")
                
# ====== LỆNH /addreg ======
@telegram_bot.message_handler(commands=['addreg'])
def telegram_addreg(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(
            message,
            "<b>❌ KHÔNG CÓ QUYỀN</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔴 Bạn không có quyền sử dụng lệnh này!",
            parse_mode="HTML"
        )
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            telegram_bot.reply_to(
                message,
                "<b>❌ SAI CÚ PHÁP</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "💡 <code>/addreg @username [số_lượng]</code>\n"
                "💡 <code>/addreg user_id [số_lượng]</code>\n\n"
                "📌 <b>Ví dụ:</b>\n"
                "<code>/addreg @zanbackj 100</code>\n"
                "<code>/addreg 123456789 50</code>\n\n"
                "📊 <b>Mặc định:</b> 50 acc/ngày\n"
                "🔄 Reset vào 00:00 hàng ngày",
                parse_mode="HTML"
            )
            return
        
        target = args[1].strip()
        limit = 50
        
        if len(args) >= 3:
            try:
                limit = int(args[2])
                if limit < 1:
                    limit = 1
                if limit > 9999:
                    limit = 9999
            except:
                limit = 50
        
        # Xử lý target
        user_id = None
        user_name = target
        
        if target.startswith("@"):
            username = target[1:]
            try:
                user = telegram_bot.get_chat(f"@{username}")
                user_id = user.id
                user_name = user.first_name or username
            except Exception as e:
                telegram_bot.reply_to(
                    message,
                    f"<b>❌ KHÔNG TÌM THẤY USER</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔴 Username <code>{target}</code> không tồn tại!\n"
                    f"💡 User phải đã từng chat với bot.",
                    parse_mode="HTML"
                )
                return
        else:
            try:
                user_id = int(target)
                try:
                    user = telegram_bot.get_chat(user_id)
                    user_name = user.first_name or str(user_id)
                except:
                    user_name = str(user_id)
            except:
                telegram_bot.reply_to(
                    message,
                    f"<b>❌ ID KHÔNG HỢP LỆ</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔴 <code>{target}</code> không phải ID Telegram hợp lệ!",
                    parse_mode="HTML"
                )
                return
        
        if not user_id:
            telegram_bot.reply_to(
                message,
                "<b>❌ KHÔNG TÌM THẤY USER</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔴 Không xác định được user!\n"
                f"💡 Reply tin nhắn của user: <code>/addreg 100</code>",
                parse_mode="HTML"
            )
            return
        
        # Lưu giới hạn
        limits_data = {}
        if os.path.exists(LIMITS_FILE):
            try:
                with open(LIMITS_FILE, "r", encoding="utf-8") as f:
                    limits_data = json.load(f)
            except:
                limits_data = {}
        
        limits_data[str(user_id)] = {
            "limit": limit,
            "updated_by": message.from_user.id,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(LIMITS_FILE, "w", encoding="utf-8") as f:
            json.dump(limits_data, f, indent=2, ensure_ascii=False)
        
        # Thông báo cho user
        try:
            telegram_bot.send_message(
                user_id,
                f"<b>✅ ĐÃ CẬP NHẬT GIỚI HẠN REG</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 Bạn có thể tạo <code>{limit}</code> account mỗi ngày!\n"
                f"📊 Giới hạn mới: <code>{limit}</code> acc/ngày\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔄 Reset vào 00:00 hàng ngày\n"
                f"📌 Dùng /reg để tạo account",
                parse_mode="HTML"
            )
        except:
            pass
        
        telegram_bot.reply_to(
            message,
            f"<b>✅ ĐÃ CẬP NHẬT GIỚI HẠN REG</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 User: <code>{user_name}</code>\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📊 Giới hạn mới: <code>{limit}</code> acc/ngày\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📩 Đã gửi thông báo cho user!",
            parse_mode="HTML"
        )
        
    except Exception as e:
        telegram_bot.reply_to(
            message,
            f"<b>❌ LỖI</b>\n"
            f"🔴 {str(e)}",
            parse_mode="HTML"
        )
                     
ADMIN_ID = [8722607800]
TELE_USERS_FILE = "tele_users.json"

def save_telegram_user(chat_id):
    users = []
    if os.path.exists(TELE_USERS_FILE):
        try:
            with open(TELE_USERS_FILE, "r", encoding="utf-8") as f:
                users = json.load(f)
        except:
            pass
            
    if chat_id not in users:
        users.append(chat_id)
        try:
            with open(TELE_USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(users, f, indent=4)
        except:
            pass

@telegram_bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'])
def auto_save_group_id(message):
    save_telegram_chat(message.chat.id, TELE_GROUPS_FILE)

# ====== LỆNH /TB ======
@telegram_bot.message_handler(commands=['tb'])
def telegram_broadcast(message):
    if message.from_user.id not in ADMIN_ID:
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return

    msg_text = message.text.split(maxsplit=1)
    if len(msg_text) < 2:
        telegram_bot.reply_to(message, f"⚠️ THÔNG BÁO LỖI\nVui lòng nhập nội dung.\nVí dụ: /tb Thông báo bảo trì hệ thống")
        return
        
    broadcast_content = msg_text[1]
    
    user_ids = []
    if os.path.exists(TELE_USERS_FILE):
        try:
            with open(TELE_USERS_FILE, "r", encoding="utf-8") as f:
                user_ids = json.load(f)
        except:
            pass

    group_ids = []
    if os.path.exists(TELE_GROUPS_FILE):
        try:
            with open(TELE_GROUPS_FILE, "r", encoding="utf-8") as f:
                group_ids = json.load(f)
        except:
            pass

    if not user_ids and not group_ids:
        telegram_bot.reply_to(message, f"📭 DANH SÁCH TRỐNG\nKhông tìm thấy ID người dùng hoặc ID nhóm nào.")
        return

    telegram_bot.reply_to(message, f"⏳ ĐANG TIẾN HÀNH\nĐang gửi tới {len(user_ids)} người dùng và {len(group_ids)} nhóm...")

    user_success = 0
    group_success = 0
    fail_count = 0
    
    # ====== CHỈ GỬI NỘI DUNG, KHÔNG CÓ TÊN ADMIN ======
    formatted_msg = f"<b>{broadcast_content}</b>"

    for user_id in user_ids:
        try:
            telegram_bot.send_message(user_id, formatted_msg, parse_mode="HTML")
            user_success += 1
            time.sleep(0.05)
        except:
            fail_count += 1

    for group_id in group_ids:
        try:
            telegram_bot.send_message(group_id, formatted_msg, parse_mode="HTML")
            group_success += 1
            time.sleep(0.05)
        except:
            fail_count += 1

    report = (
        f"📊 KẾT QUẢ GỬI TIN (BROADCAST)\n"
        f"───────────────────────\n"
        f"👤 Thành công User: {user_success}\n"
        f"👥 Thành công Group: {group_success}\n"
        f"❌ Thất bại (Block/Kích): {fail_count}\n"
        f"🌐 Tổng số mục tiêu: {len(user_ids) + len(group_ids)}"
    )
    telegram_bot.send_message(ADMIN_ID[0], report)
                       
ADMIN_IDSK = [8722607800]

@telegram_bot.message_handler(commands=['cbrs', 'checkusers'])
def telegram_check_users(message):
    if message.from_user.id not in ADMIN_IDSK:
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    user_ids = []
    if os.path.exists(TELE_USERS_FILE):
        try:
            with open(TELE_USERS_FILE, "r", encoding="utf-8") as f:
                user_ids = json.load(f)
        except:
            pass
    
    group_ids = []
    if os.path.exists(TELE_GROUPS_FILE):
        try:
            with open(TELE_GROUPS_FILE, "r", encoding="utf-8") as f:
                group_ids = json.load(f)
        except:
            pass
    
    total_users = len(user_ids)
    total_groups = len(group_ids)
    
    report = f"""
<blockquote>
<b>📊 DANH SÁCH NGƯỜI DÙNG</b>
───────────────────────
👤 <b>Tổng User:</b> <code>{total_users}</code>
👥 <b>Tổng Group:</b> <code>{total_groups}</code>
───────────────────────
<b>📋 DANH SÁCH USER:</b>
"""
    
    if user_ids:
        for i, uid in enumerate(user_ids[:50], 1):
            try:
                user = telegram_bot.get_chat(uid)
                name = user.first_name or "Unknown"
                username = f"@{user.username}" if user.username else ""
                report += f"{i}. {name} {username} - <code>{uid}</code>\n"
            except:
                report += f"{i}. <code>{uid}</code> (Không truy cập được)\n"
    else:
        report += "📭 Chưa có user nào!\n"
    
    if len(user_ids) > 50:
        report += f"\n... và {len(user_ids) - 50} user khác"
    
    report += f"""
───────────────────────
📋 <b>DANH SÁCH GROUP:</b>
"""
    
    if group_ids:
        for i, gid in enumerate(group_ids[:20], 1):
            try:
                chat = telegram_bot.get_chat(gid)
                title = chat.title or "Unknown"
                report += f"{i}. {title} - <code>{gid}</code>\n"
            except:
                report += f"{i}. <code>{gid}</code> (Không truy cập được)\n"
    else:
        report += "📭 Chưa có group nào!\n"
    
    if len(group_ids) > 20:
        report += f"\n... và {len(group_ids) - 20} group khác"
    
    report += "</blockquote>"
    
    telegram_bot.reply_to(message, report, parse_mode="HTML")
    
# ====== LỆNH /price TRONG TELEGRAM ======
@telegram_bot.message_handler(commands=['price', 'gia', 'banggiao'])
def price_cmd(message):
    text = """
🔥 <b>BẢNG GIÁ DỊCH VỤ BOT FF</b>
━━━━━━━━━━━━━━━━━━━━

🤖 <b>BOT TEAM 5-6 (MÚA S7):</b>
├ 1 ngày: 10k
├ 1 tuần: 40k
└ 1 tháng: 100k

👑 <b>BOT TÊN RIÊNG THEO YÊU CẦU:</b>
├ 1 tuần: 60k
└ 1 tháng: 120k

🛡️ <b>BOT QUÂN ĐOÀN (NHIỀU NGƯỜI DÙNG):</b>
├ 1 tuần: 65k
├ 1 tháng: 120k
└ 3 tháng: 236k

━━━━━━━━━━━━━━━━━━━━
✅ <b>ƯU ĐÃI ĐẶC BIỆT:</b>
📌 Càng thuê lâu dài giá càng rẻ
🟢 Bot online 24/7, hoạt động liên tục
🔄 Hỗ trợ đổi tên bot theo yêu cầu

━━━━━━━━━━━━━━━━━━━━
📩 Liên hệ mua: @zanbackj
    """
    
    telegram_bot.reply_to(message, text, parse_mode="HTML")

@telegram_bot.message_handler(commands=['kick'])
@check_group_only
@async_telegram
def handle_telegram_kick(message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        telegram_bot.reply_to(
            message, 
            "<blockquote><b>❌ SAI CÚ PHÁP</b>\n━━━━━━━━━━━━━━━━━━━━\n💡 Dùng: <code>/kick [teamcode]</code>\n📌 Ví dụ: <code>/kick 1234567</code>\n━━━━━━━━━━━━━━━━━━━━\n⛔ Teamcode phải là 7 chữ số!</blockquote>", 
            parse_mode='HTML'
        )
        return
    
    team_code_int = int(parts[1])
    
    bots = get_available_bots(1)
    if not bots:
        telegram_bot.reply_to(
            message, 
            "<blockquote><b>⚠️ KHÔNG CÓ BOT RẢNH</b>\n━━━━━━━━━━━━━━━━━━━━\n🔴 Tất cả bot đang bận hoặc offline.\n💡 Vui lòng thử lại sau!\n</blockquote>", 
            parse_mode='HTML'
        )
        return
    
    bot = bots[0]
    bot.is_busy = True
        
    status_msg = telegram_bot.reply_to(
        message, 
        f"<blockquote><b>🔄 ĐANG KICK TEAM</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Teamcode:</b> <code>{team_code_int}</code>\n🤖 <b>Bot:</b> <code>{getattr(bot, 'nickname', f'Bot #{bot.botid}')}</code>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Đang xử lý!</blockquote>", 
        parse_mode='HTML'
    )

    try:
        bot.rstatus = (99, "lagging")
        bot.sock39699.sendall(bot._bot.join_squad(team_code_int))
        time.sleep(1.5)
        
        sms_text = "[b][c][ffffff]Telegram: @zanbackj\nTiktok: @zanbackj\nThuê Bot Liên hệ admin"
        bot.rstatus = (1, sms_text)
        time.sleep(0.5)
        
        for _ in range(2222):
            try:
                bot.sock39699.sendall(bot._gen.lag_zan())
                time.sleep(0.0001)
            except:
                pass
        
        bot.sock39699.sendall(bot._bot.leave_squad(0))                
        bot.rstatus = (0, 0)
        bot.is_busy = False
        
        telegram_bot.edit_message_text(
            f"<blockquote><b>✅ KICK TEAM THÀNH CÔNG</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Teamcode:</b> <code>{team_code_int}</code>\n🤖 <b>Bot:</b> <code>{getattr(bot, 'nickname', f'Bot #{bot.botid}')}</code>\n━━━━━━━━━━━━━━━━━━━━\n⚡ Đã kick xong team!</blockquote>",
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            parse_mode='HTML'
        )
        
    except Exception as e:      
        bot.rstatus = (0, 0)
        bot.is_busy = False
        telegram_bot.edit_message_text(
            f"<blockquote><b>❌ KICK TEAM THẤT BẠI</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>Teamcode:</b> <code>{team_code_int}</code>\n🔴 <b>Lỗi:</b> {str(e)}\n━━━━━━━━━━━━━━━━━━━━\n💡 Kiểm tra lại teamcode hoặc bot!</blockquote>",
            chat_id=message.chat.id,
            message_id=status_msg.message_id,
            parse_mode='HTML'
        )                               
@telegram_bot.message_handler(commands=['kball'])
def telegram_kb_all(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Không có quyền!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/kball [uid]</code>\n📌 Ví dụ: <code>/kball 123456789</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        uid = parts[1]
        
        import requests
        url = f"http://127.0.0.1:2011/kb/all?uid={uid}"
        response = requests.get(url, timeout=30)
        result = response.json()
        
        if result.get('status') == 'success':
            data = result.get('data', {})
            results = data.get('results', [])
            
            msg = f"<blockquote><b>✅ GỬI KẾT BẠN ALL THÀNH CÔNG</b>\n━━━━━━━━━━━━━━━━━━━━\n🆔 <b>UID:</b> <code>{uid}</code>\n✅ <b>Thành công:</b> {data.get('success', 0)}/{data.get('total_bots', 0)}\n━━━━━━━━━━━━━━━━━━━━\n"
            
            for r in results:
                status = "✅" if r.get('success') else "❌"
                msg += f"{status} <b>{r.get('bot_name')}</b>: {r.get('message')}\n"
            
            msg += "━━━━━━━━━━━━━━━━━━━━\n⚡ Đã gửi qua API!</blockquote>"
            
            telegram_bot.reply_to(message, msg, parse_mode="HTML")
        else:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ GỬI KẾT BẠN ALL THẤT BẠI</b>\n━━━━━━━━━━━━━━━━━━━━\n🆔 <b>UID:</b> <code>{uid}</code>\n⚠️ <b>Lý do:</b> {result.get('message')}\n━━━━━━━━━━━━━━━━━━━━\n💡 Kiểm tra lại!</blockquote>",
                parse_mode="HTML"
            )
            
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@telegram_bot.message_handler(commands=['xkb'])
def telegram_xkb(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/xkb [bot_id] [uid]</code>\n📌 Ví dụ: <code>/xkb 1 123456789</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        bot_id = parts[1]
        uid = parts[2]
        
        import requests
        url = f"http://127.0.0.1:2011/xkb?uid={uid}&botid={bot_id}"
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if result.get('status') == 'success':
            data = result.get('data', {})
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>✅ HỦY KẾT BẠN THÀNH CÔNG</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 <b>Bot:</b> <code>{data.get('bot_name', '')}</code>\n🆔 <b>UID:</b> <code>{uid}</code>\n📩 <b>Trạng thái:</b> {result.get('message')}\n━━━━━━━━━━━━━━━━━━━━\n⚡ Đã hủy qua API!</blockquote>",
                parse_mode="HTML"
            )
        else:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ HỦY KẾT BẠN THẤT BẠI</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 <b>Bot ID:</b> <code>{bot_id}</code>\n🆔 <b>UID:</b> <code>{uid}</code>\n⚠️ <b>Lý do:</b> {result.get('message')}\n━━━━━━━━━━━━━━━━━━━━\n💡 Kiểm tra lại bot!</blockquote>",
                parse_mode="HTML"
            )
            
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")
        
@telegram_bot.message_handler(commands=['xkball'])
def telegram_xkb_all(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Không có quyền!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/xkball [uid]</code>\n📌 Ví dụ: <code>/xkball 123456789</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        uid = parts[1]
        
        import requests
        url = f"http://127.0.0.1:2011/xkb/all?uid={uid}"
        response = requests.get(url, timeout=30)
        result = response.json()
        
        if result.get('status') == 'success':
            data = result.get('data', {})
            results = data.get('results', [])
            
            msg = f"<blockquote><b>✅ HỦY KẾT BẠN ALL THÀNH CÔNG</b>\n━━━━━━━━━━━━━━━━━━━━\n🆔 <b>UID:</b> <code>{uid}</code>\n✅ <b>Thành công:</b> {data.get('success', 0)}/{data.get('total_bots', 0)}\n━━━━━━━━━━━━━━━━━━━━\n"
            
            for r in results:
                status = "✅" if r.get('success') else "❌"
                msg += f"{status} <b>{r.get('bot_name')}</b>: {r.get('message')}\n"
            
            msg += "━━━━━━━━━━━━━━━━━━━━\n⚡ Đã hủy qua API!</blockquote>"
            
            telegram_bot.reply_to(message, msg, parse_mode="HTML")
        else:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ HỦY KẾT BẠN ALL THẤT BẠI</b>\n━━━━━━━━━━━━━━━━━━━━\n🆔 <b>UID:</b> <code>{uid}</code>\n⚠️ <b>Lý do:</b> {result.get('message')}\n━━━━━━━━━━━━━━━━━━━━\n💡 Kiểm tra lại!</blockquote>",
                parse_mode="HTML"
            )
            
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")
                
@telegram_bot.message_handler(commands=['isbanned'])
@check_group_only
@async_telegram
def telegram_isbanned(message):
    if not check_user_in_group(message.from_user.id):
        send_warn_join_group(message)
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ INVALID SYNTAX</b>\n💡 Use: <code>/isbanned [uid]</code>\n📌 Example: <code>/isbanned 123456789</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        uid = args[1].strip()
        if not uid.isdigit():
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ ERROR</b>\n🔴 UID must be a number!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        msg = telegram_bot.reply_to(
            message,
            f"<blockquote><b>📡 CHECKING BAN STATUS</b>\n━━━━━━━━━━━━━━━━━━━━\n🎯 <b>UID:</b> <code>{uid}</code>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Processing...</blockquote>",
            parse_mode="HTML"
        )
        
        def run_check():
            try:
                is_banned = check_banned(uid)
                
                if is_banned:
                    response = (
                        f"<blockquote><b>🆔 UID: {uid}</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 <b>Status:</b> 🚫 BANNED\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"⚠️ This account has been banned!</blockquote>"
                    )
                else:
                    response = (
                        f"<blockquote><b>🆔 UID: {uid}</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"📌 <b>Status:</b> ✅ NOT BANNED\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"✅ This account is active!</blockquote>"
                    )
                
                telegram_bot.edit_message_text(
                    response,
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
                
            except Exception as e:
                telegram_bot.edit_message_text(
                    f"<blockquote><b>❌ ERROR</b>\n🔴 {str(e)}</blockquote>",
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    parse_mode="HTML"
                )
        
        threading.Thread(target=run_check, daemon=True).start()
        
    except Exception as e:
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>❌ ERROR</b>\n🔴 {str(e)}</blockquote>",
            parse_mode="HTML"
        )
                                           
@telegram_bot.message_handler(commands=['addid'])
def telegram_addid(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Không có quyền!")
        return

    parts = message.text.split()
    if len(parts) < 4:
        telegram_bot.reply_to(
            message,
            "<blockquote><b>❌ SAI CÚ PHÁP</b>\n💡 Dùng: <code>/addid [botid] [uid] [time]</code>\n📌 Ví dụ: <code>/addid 1 123456 7d</code></blockquote>",
            parse_mode="HTML"
        )
        return

    try:
        bid = int(parts[1])
        uid = int(parts[2])
        timee = parts[3]

        if bid not in TCPbot.bots:
            telegram_bot.reply_to(message, "❌ Bot không tồn tại!")
            return

        import re
        if not re.match(r'^\d+[hdwmy]$', timee.lower()):
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI ĐỊNH DẠNG TIME</b>\n💡 Dùng: <code>1h</code> <code>1d</code> <code>7d</code> <code>1w</code> <code>1m</code></blockquote>",
                parse_mode="HTML"
            )
            return

        import sqlite3
        db_path = f"bot_{bid}.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS access (uid INTEGER PRIMARY KEY, expire_time TEXT)')
        cursor.execute('INSERT OR REPLACE INTO access (uid, expire_time) VALUES (?, ?)', (uid, timee))
        conn.commit()
        conn.close()

        bot = TCPbot.bots[bid]
        if hasattr(bot, 'bot_config'):
            if 'access_bot' not in bot.bot_config:
                bot.bot_config['access_bot'] = []
            
            found = False
            for u in bot.bot_config['access_bot']:
                if u.get('uid') == uid:
                    u['expire'] = timee
                    found = True
                    break
            
            if not found:
                bot.bot_config['access_bot'].append({
                    'uid': uid,
                    'expire': timee
                })
            
            TCPbot.save_config()
        
        if hasattr(bot, 'access_list'):
            bot.access_list[uid] = timee
        else:
            bot.access_list = {uid: timee}

        telegram_bot.reply_to(
            message,
            f"<blockquote><b>✅ THÊM QUYỀN THÀNH CÔNG</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 <b>Bot ID:</b> <code>{bid}</code>\n👤 <b>UID:</b> <code>{uid}</code>\n⏳ <b>Time:</b> <code>{timee}</code>\n━━━━━━━━━━━━━━━━━━━━\n⚡ Đã thêm thành công!</blockquote>",
            parse_mode="HTML"
        )

    except Exception as e:
        telegram_bot.reply_to(message, f"<blockquote><b>❌ LỖI</b>\n🔴 {str(e)}</blockquote>", parse_mode="HTML")
                           
@telegram_bot.message_handler(commands=['del'])
def telegram_delete_user(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            telegram_bot.reply_to(message, "❌ Sai cú pháp! Cú pháp chuẩn: /del <bot_id> <uid>")
            return
        
        bot_id = int(parts[1])
        uid = int(parts[2])
        
        if bot_id not in TCPbot.bots:
            telegram_bot.reply_to(message, f"❌ Không tìm thấy bot ID {bot_id} trong hệ thống!")
            return
        
        target_bot = TCPbot.bots[bot_id]
        bot_config = getattr(target_bot, "bot_config", {})
        bot_name = bot_config.get("bot_name") or getattr(target_bot, "nickname", "Không rõ tên")
        result = TCPbot.deleteId(bot_id, uid)
        
        if result:
            msg = (
                f"🗑️ Đã xóa quyền sử dụng thành công!\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot ID: {bot_id}\n"
                f"📛 Name bot: {bot_name}\n"
                f"👤 UID: {uid}"
            )
            telegram_bot.reply_to(message, msg)
        else:
            telegram_bot.reply_to(message, "❌ Xóa người dùng thất bại hoặc không tìm thấy dữ liệu trên bot này!")
            
    except ValueError:
        telegram_bot.reply_to(message, "❌ Bot ID và UID phải là số nguyên!")
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")
              
@telegram_bot.message_handler(commands=['delbot'])
def telegram_del_bot(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(message, "❌ Sai cú pháp!\nSử dụng: /delbot <bot_id> hoặc /delbot all")
            return
        
        target = parts[1]
        
        # ====== XÓA ALL BOT ======
        if target.lower() == "all":
            bot_list = list(TCPbot.bots.keys())
            if not bot_list:
                telegram_bot.reply_to(message, "📭 Không có bot nào để xóa!")
                return
            
            count = 0
            for bid in bot_list:
                try:
                    result = TCPbot.delete_bot(bid)
                    if result == "RES_OK":
                        count += 1
                except:
                    pass
            
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>🗑️ ĐÃ XÓA TẤT CẢ BOT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Đã xóa <code>{count}</code> bot\n"
                f"📦 Tổng: <code>{len(bot_list)}</code> bot\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Tất cả bot đã bị xóa!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        # ====== XÓA 1 BOT ======
        bid = int(target)
        result = TCPbot.delete_bot(bid) 
        
        if result == "RES_OK":
            response = f"🗑️ Xóa bot thành công!\nBot ID: {bid} đã được loại bỏ và dừng hoạt động."
        elif result == "RES_BOT_NOT_FOUND":
            response = f"❌ Xóa bot thất bại!\nLý do: Không tìm thấy Bot ID {bid} trong hệ thống."
        elif result == "RES_BOT_BUSY":
            response = f"⏳ Xóa bot thất bại!\nLý do: Bot {bid} đang bận xử lý tiến trình khác, không thể dừng."
        else:
            response = f"❌ Lỗi không xác định: {result}"
        
        telegram_bot.reply_to(message, response)
        
    except ValueError:
        telegram_bot.reply_to(message, "❌ Thất bại: Bot ID phải là một số hoặc 'all'!")
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi khi xóa bot: {str(e)}")
                
@telegram_bot.message_handler(commands=['addadmin'])
def telegram_add_admin(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            telegram_bot.reply_to(message, "❌ Sai cú pháp!\nSử dụng: /addadmin <bot_id|all> <uid>")
            return
        
        target = parts[1]
        uid = int(parts[2])
        
        if target.lower() == "all":
            count = 0
            for bot_id in TCPbot.bots:
                try:
                    if AdminManager.add_admin(bot_id, uid):
                        count += 1
                except:
                    pass
            telegram_bot.reply_to(message, f"✅ Đã thêm UID {uid} vào {count} bot")
            return         
        
        bot_id = int(target)
        if bot_id not in TCPbot.bots:
            telegram_bot.reply_to(message, f"❌ Không tìm thấy bot ID {bot_id}")
            return
        
        result = AdminManager.add_admin(bot_id, uid)
        if result:
            response = f"✅ Đã thêm admin UID {uid} cho bot ID {bot_id} thành công!"
        else:
            response = f"❌ Thêm admin thất bại! UID {uid} có thể đã là admin."
        
        telegram_bot.reply_to(message, response)
        
    except ValueError:
        telegram_bot.reply_to(message, "❌ Bot ID và UID phải là số!")
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")
        
TCPbot = BOTMNG()
app = Flask(__name__)
   
@app.route("/check", methods=["GET"])
def ktr_bot():
 data = []
 for bid, bot in TCPbot.bots.items():
  I={
   "id": bid,
   "access-token": bot.bot_config['auth_bot_login']['access_token'],
   "access-user": bot.bot_config.get('access_bot', []),
   "bot-id": bot.bot_config.get("botid", getattr(bot, "botid", None)),
   "nickname": bot.bot_config.get('nickname', getattr(bot, 'nickname', None)),
   "active-guild?": bot.bot_config.get("active-clan", True),
   "status": "online" if bot.running_event.is_set() else "Inactive"
  }
  data.append(I)
 return jsonify({"data": data, "total": len(data)})
                          
@app.route("/addid", methods=["GET"])
def add_uid():
    try:
        bid = request.args.get("id")
        uid = request.args.get("uid")
        timee = request.args.get("time")
        
        if not bid or not uid or not timee:
            return "RES_INVALID", 201
        
        if not bid.isdigit() or not uid.isdigit():
            return "RES_INVALID_ID", 201
        
        bid = int(bid)
        uid = int(uid)
        
        # Kiểm tra định dạng time
        import re
        if not re.match(r'^\d+[hdwmy]$', timee.lower()):
            return "RES_INVALID_TIME", 201
        
        # Thêm trực tiếp vào database bằng SQL
        import sqlite3
        db_path = f"bot_{bid}.db"
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Tạo bảng
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS access (
                    uid INTEGER PRIMARY KEY,
                    expire_time TEXT
                )
            ''')
            
            # Lưu timee dạng chuỗi
            cursor.execute(
                'INSERT OR REPLACE INTO access (uid, expire_time) VALUES (?, ?)',
                (uid, timee)
            )
            
            conn.commit()
            conn.close()
            
            # Reload lại access cho bot
            if bid in TCPbot.bots:
                bot = TCPbot.bots[bid]
                if hasattr(bot, 'load_access'):
                    bot.load_access()
                # Hoặc cập nhật trực tiếp vào bot_config
                if hasattr(bot, 'bot_config'):
                    if 'access_bot' not in bot.bot_config:
                        bot.bot_config['access_bot'] = []
                    
                    # Kiểm tra và cập nhật
                    found = False
                    for u in bot.bot_config['access_bot']:
                        if u.get('uid') == uid:
                            u['expire'] = timee
                            found = True
                            break
                    
                    if not found:
                        bot.bot_config['access_bot'].append({
                            'uid': uid,
                            'expire': timee
                        })
                    
                    TCPbot.save_config()
            
            return "RES_OK", 200
            
        except Exception as e:
            return f"RES_FAILED: {str(e)}", 201
            
    except Exception as e:
        return f"RES_ERROR: {str(e)}", 201
        
@app.route("/delid", methods=["GET"])
def delete_uid():
 bid = request.args.get("botid")
 uid = request.args.get("uid")
 if not bid or not uid:return "RES_INVALID", 201
 try:bid = int(bid)
 except:return "RES_INVALID_ID", 201
 I=TCPbot.deleteId(bid, uid)
 if I:return "RES_OK", 200
 else:return "RES_FAILED", 201

@app.route("/addbot", methods=["GET"])
def add_bot():
    token = request.args.get("token")
    if not token: 
        return "RES_INVALID", 201
    
    # Kiểm tra token trước khi thêm
        try:
            from ReQAPI import FreeFireAPI
        test = FreeFireAPI().get(token, is_emulator=False)
        if "account not found" in str(test):
            return "TOKEN_INVALID", 201
    except:
        pass
    
    I = TCPbot.add_bot(token)
    if I["status"]:
        TCPbot.bots[I["bot_id"]].start()
        return "RES_OK", 200
    else: 
        return str(I["message"]), 201

@app.route("/lag", methods=["GET"])
def api_lag():
    tc = request.args.get("tc")
    if not tc:
        return jsonify({"success": False, "message": "Missing tc"}), 400
    
    try:
        tc = int(tc)
    except:
        return jsonify({"success": False, "message": "Invalid tc"}), 400
    
    if len(str(tc)) != 7:
        return jsonify({"success": False, "message": "tc must be 7 digits"}), 400
    
    # Tìm bot rảnh
    bot = None
    for b in TCPbot.bots.values():
        if (b.running_event.is_set() and 
            getattr(b, "sock39699", None) and 
            not getattr(b, "is_busy", False)):
            bot = b
            break
    
    if not bot:
        return jsonify({"success": False, "message": "No bot available"}), 400
    
    bot.is_busy = True
    bot_name = getattr(bot, 'nickname', f'Bot #{bot.botid}')
    
    def run_lag():
        try:
            bot.rstatus = (99, "lagging")
            bot.sock39699.sendall(bot._bot.join_squad(tc))
            time.sleep(1.5)
            
            sms_text = "[b][c][ffffff]Telegram: @zanbackj\nTiktok: @zanbackj\nThuê Bot Liên hệ admin"
            bot.rstatus = (1, sms_text)
            time.sleep(0.5)
            
            for _ in range(1111):
                try:
                    bot.sock39699.sendall(bot._gen.lag_dev())
                    time.sleep(0.0001)
                except:
                    pass
            
            bot.sock39699.sendall(bot._bot.leave_squad(0))
            bot.rstatus = (0, 0)
            
        except Exception as e:
            print(f"LAG API ERROR: {e}")
        finally:
            bot.is_busy = False
    
    threading.Thread(target=run_lag, daemon=True).start()
    
    return jsonify({
        "success": True,
        "message": f"Lagging team {tc} with bot {bot_name}",
        "data": {
            "tc": tc,
            "bot": bot_name
        }
    }), 200
        
@app.route("/delbot", methods=["GET"])
def delete_bot():
    botid = request.args.get("botid")
    if not botid:
        return "RES_INVALID", 201
    try:
        bid = int(botid)
    except:
        return "RES_INVALID", 201
    I = TCPbot.delete_bot(bid)
    if I:
        return "RES_OK", 200
    else:
        return "RES_BOT_NOT_FOUND", 201

@app.route("/get", methods=["GET"])
def api_gettoken():
    account = request.args.get("token")
    emulator = request.args.get("emu", "false").lower() == "true"
    if not account:
        return jsonify({"success": False, "error": "Missing account"}), 400
    try:
        api = FreeFireAPI()
        data = api.get(account, emulator)
        result = {
            "uid": data.get("UserAccountUID"),
            "region": data.get("LockRegion"),
            "token": data.get("UserAuthToken")
        }
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/addadmin", methods=["GET"])
def add_admin():
 bid = request.args.get("botid")
 aid = request.args.get("uid")
 if not bid or not aid: return "RES_INVALID", 201
 try:
  bid = int(bid)
  aid = int(aid)
 except Exception as e: return str(e), 201
 I=AdminManager.add_admin(bid, aid)
 if I:return "RES_OK", 200
 else: return "RES_ADMIN_ALREADY_EXISTS", 201 

@app.route("/kb", methods=["GET"])
def api_kb_get():
    try:
        uid = request.args.get('uid')
        bot_id = request.args.get('botid')
        
        if not uid:
            return jsonify({'status': 'error', 'message': 'Missing uid'}), 400
        if not bot_id:
            return jsonify({'status': 'error', 'message': 'Missing botid'}), 400
        if not bot_id.isdigit():
            return jsonify({'status': 'error', 'message': 'botid must be number'}), 400
            
        bot_id = int(bot_id)
        
        if bot_id not in TCPbot.bots:
            return jsonify({'status': 'error', 'message': f'Bot {bot_id} not found'}), 404
            
        bot = TCPbot.bots[bot_id]
        
        if not bot.running_event.is_set():
            return jsonify({'status': 'error', 'message': 'Bot offline'}), 400
            
        token = getattr(bot, 'token', None)
        if not token:
            return jsonify({'status': 'error', 'message': 'No token'}), 400
            
        bot_uid = getattr(bot, 'botid', '')
        
        # Gửi kết bạn trực tiếp 
        try:
            def encrypt_uid(x):
                dec = ['80','81','82','83','84','85','86','87','88','89','8a','8b','8c','8d','8e','8f','90','91','92','93','94','95','96','97','98','99','9a','9b','9c','9d','9e','9f','a0','a1','a2','a3','a4','a5','a6','a7','a8','a9','aa','ab','ac','ad','ae','af','b0','b1','b2','b3','b4','b5','b6','b7','b8','b9','ba','bb','bc','bd','be','bf','c0','c1','c2','c3','c4','c5','c6','c7','c8','c9','ca','cb','cc','cd','ce','cf','d0','d1','d2','d3','d4','d5','d6','d7','d8','d9','da','db','dc','dd','de','df','e0','e1','e2','e3','e4','e5','e6','e7','e8','e9','ea','eb','ec','ed','ee','ef','f0','f1','f2','f3','f4','f5','f6','f7','f8','f9','fa','fb','fc','fd','fe','ff']
                xxx = ['1','01','02','03','04','05','06','07','08','09','0a','0b','0c','0d','0e','0f','10','11','12','13','14','15','16','17','18','19','1a','1b','1c','1d','1e','1f','20','21','22','23','24','25','26','27','28','29','2a','2b','2c','2d','2e','2f','30','31','32','33','34','35','36','37','38','39','3a','3b','3c','3d','3e','3f','40','41','42','43','44','45','46','47','48','49','4a','4b','4c','4d','4e','4f','50','51','52','53','54','55','56','57','58','59','5a','5b','5c','5d','5e','5f','60','61','62','63','64','65','66','67','68','69','6a','6b','6c','6d','6e','6f','70','71','72','73','74','75','76','77','78','79','7a','7b','7c','7d','7e','7f']
                try:
                    x = int(x)
                    x_float = float(x) / 128
                    if x_float > 128:
                        x_float /= 128
                        if x_float > 128:
                            x_float /= 128
                            if x_float > 128:
                                x_float /= 128
                                strx = int(x_float)
                                y = (x_float - strx) * 128
                                z = (y - int(y)) * 128
                                n = (z - int(z)) * 128
                                m = (n - int(n)) * 128
                                return dec[int(m)] + dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
                            else:
                                strx = int(x_float)
                                y = (x_float - strx) * 128
                                z = (y - int(y)) * 128
                                n = (z - int(z)) * 128
                                return dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
                    return None 
                except: 
                    return None
            
            Key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
            Iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import pad
            
            encrypted_id = encrypt_uid(uid)
            if not encrypted_id:
                return jsonify({'status': 'error', 'message': 'Encrypt failed'}), 400
            
            plain_text_payload = f'08a7c4839f1e10{encrypted_id}1801'
            cipher = AES.new(Key, AES.MODE_CBC, Iv)
            data = cipher.encrypt(pad(bytes.fromhex(plain_text_payload), AES.block_size))
            
            import requests
            domains = [
                'https://clientbp.ggpolarbear.com/RequestAddingFriend',
                'https://clientbp.ggpolarbear.com/RequestAddingFriend',
                'https://clientbp.ggpolarbear.com/RequestAddingFriend ',
            ]
            
            headers = {
                'X-Unity-Version': '2018.4.11f1',
                'ReleaseVersion': 'OB54',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-GA': 'v1 1',
                'Authorization': f'Bearer {token}',
                'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
                'Connection': 'Keep-Alive',
                'Accept-Encoding': 'gzip'
            }
            
            success = False
            msg = "Không kết nối được server"
            
            for url in domains:
                try:
                    response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
                    text = response.text
                    
                    if response.status_code == 200:
                        success = True
                        msg = "Gửi kết bạn thành công!"
                        break
                    elif 'BR_FRIEND_NOT_SAME_REGION' in text:
                        msg = "Khác khu vực!"
                        break
                    elif 'BR_FRIEND_MAX_REQUEST' in text:
                        msg = "Đã đạt giới hạn yêu cầu!"
                        break
                    elif 'BR_FRIEND_ALREADY_SENT_REQUEST' in text:
                        msg = "Đã gửi yêu cầu trước đó!"
                        break
                except:
                    continue
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': msg,
                    'data': {
                        'uid': uid,
                        'bot_id': bot_id,
                        'bot_uid': bot_uid,
                        'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}')
                    }
                }), 200
            else:
                return jsonify({'status': 'error', 'message': msg}), 400
                
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
        
@app.route("/kb/all", methods=["GET"])
def api_kb_all_get():
    try:
        uid = request.args.get('uid')
        if not uid:
            return jsonify({'status': 'error', 'message': 'Missing uid'}), 400
        
        results = []
        success_count = 0
        online_bots = 0
        
        # Hàm mã hóa UID
        def encrypt_uid(x):
            dec = ['80','81','82','83','84','85','86','87','88','89','8a','8b','8c','8d','8e','8f','90','91','92','93','94','95','96','97','98','99','9a','9b','9c','9d','9e','9f','a0','a1','a2','a3','a4','a5','a6','a7','a8','a9','aa','ab','ac','ad','ae','af','b0','b1','b2','b3','b4','b5','b6','b7','b8','b9','ba','bb','bc','bd','be','bf','c0','c1','c2','c3','c4','c5','c6','c7','c8','c9','ca','cb','cc','cd','ce','cf','d0','d1','d2','d3','d4','d5','d6','d7','d8','d9','da','db','dc','dd','de','df','e0','e1','e2','e3','e4','e5','e6','e7','e8','e9','ea','eb','ec','ed','ee','ef','f0','f1','f2','f3','f4','f5','f6','f7','f8','f9','fa','fb','fc','fd','fe','ff']
            xxx = ['1','01','02','03','04','05','06','07','08','09','0a','0b','0c','0d','0e','0f','10','11','12','13','14','15','16','17','18','19','1a','1b','1c','1d','1e','1f','20','21','22','23','24','25','26','27','28','29','2a','2b','2c','2d','2e','2f','30','31','32','33','34','35','36','37','38','39','3a','3b','3c','3d','3e','3f','40','41','42','43','44','45','46','47','48','49','4a','4b','4c','4d','4e','4f','50','51','52','53','54','55','56','57','58','59','5a','5b','5c','5d','5e','5f','60','61','62','63','64','65','66','67','68','69','6a','6b','6c','6d','6e','6f','70','71','72','73','74','75','76','77','78','79','7a','7b','7c','7d','7e','7f']
            try:
                x = int(x)
                x_float = float(x) / 128
                if x_float > 128:
                    x_float /= 128
                    if x_float > 128:
                        x_float /= 128
                        if x_float > 128:
                            x_float /= 128
                            strx = int(x_float)
                            y = (x_float - strx) * 128
                            z = (y - int(y)) * 128
                            n = (z - int(z)) * 128
                            m = (n - int(n)) * 128
                            return dec[int(m)] + dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
                        else:
                            strx = int(x_float)
                            y = (x_float - strx) * 128
                            z = (y - int(y)) * 128
                            n = (z - int(z)) * 128
                            return dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
                return None 
            except: 
                return None
        
        Key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
        Iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        import requests
        
        for bot_id, bot in TCPbot.bots.items():
            if not bot.running_event.is_set():
                continue
            online_bots += 1
            token = getattr(bot, 'token', None)
            if not token:
                continue
            bot_uid = getattr(bot, 'botid', '')
            
            try:
                encrypted_id = encrypt_uid(uid)
                if not encrypted_id:
                    results.append({
                        'bot_id': bot_id,
                        'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                        'success': False,
                        'message': 'Encrypt failed'
                    })
                    continue
                
                plain_text_payload = f'08a7c4839f1e10{encrypted_id}1801'
                cipher = AES.new(Key, AES.MODE_CBC, Iv)
                data = cipher.encrypt(pad(bytes.fromhex(plain_text_payload), AES.block_size))
                
                domains = [
                    'https://clientbp.ggpolarbear.com/RequestAddingFriend',
                    'https://clientbp.ggpolarbear.com/RequestAddingFriend',
                    'https://clientbp.ggpolarbear.com/RequestAddingFriend',
                ]
                
                headers = {
                    'X-Unity-Version': '2018.4.11f1',
                    'ReleaseVersion': 'OB54',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-GA': 'v1 1',
                    'Authorization': f'Bearer {token}',
                    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
                    'Connection': 'Keep-Alive',
                    'Accept-Encoding': 'gzip'
                }
                
                success = False
                msg = "Không kết nối được server"
                
                for url in domains:
                    try:
                        response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
                        text = response.text
                        
                        if response.status_code == 200:
                            success = True
                            msg = "Gửi kết bạn thành công!"
                            break
                        elif 'BR_FRIEND_NOT_SAME_REGION' in text:
                            msg = "Khác khu vực!"
                            break
                        elif 'BR_FRIEND_MAX_REQUEST' in text:
                            msg = "Đã đạt giới hạn yêu cầu!"
                            break
                        elif 'BR_FRIEND_ALREADY_SENT_REQUEST' in text:
                            msg = "Đã gửi yêu cầu trước đó!"
                            break
                    except:
                        continue
                
                if success:
                    success_count += 1
                
                results.append({
                    'bot_id': bot_id,
                    'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                    'success': success,
                    'message': msg
                })
                
            except Exception as e:
                results.append({
                    'bot_id': bot_id,
                    'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                    'success': False,
                    'message': str(e)
                })
        
        return jsonify({
            'status': 'success',
            'message': f'Completed: {success_count}/{online_bots} success',
            'data': {
                'uid': uid,
                'total_bots': online_bots,
                'success': success_count,
                'results': results
            }
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
        
@app.route("/xkb", methods=["GET"])
def api_xkb_get():
    try:
        uid = request.args.get('uid')
        bot_id = request.args.get('botid')
        if not uid:
            return jsonify({'status': 'error', 'message': 'Missing uid'}), 400
        if not bot_id:
            return jsonify({'status': 'error', 'message': 'Missing botid'}), 400
        if not bot_id.isdigit():
            return jsonify({'status': 'error', 'message': 'botid must be number'}), 400
        bot_id = int(bot_id)
        if bot_id not in TCPbot.bots:
            return jsonify({'status': 'error', 'message': f'Bot {bot_id} not found'}), 404
        bot = TCPbot.bots[bot_id]
        if not bot.running_event.is_set():
            return jsonify({'status': 'error', 'message': 'Bot offline'}), 400
        token = getattr(bot, 'token', None)
        if not token:
            return jsonify({'status': 'error', 'message': 'No token'}), 400
        bot_uid = getattr(bot, 'botid', '')
               
        try:
            def encrypt_uid(x):
                dec = ['80','81','82','83','84','85','86','87','88','89','8a','8b','8c','8d','8e','8f','90','91','92','93','94','95','96','97','98','99','9a','9b','9c','9d','9e','9f','a0','a1','a2','a3','a4','a5','a6','a7','a8','a9','aa','ab','ac','ad','ae','af','b0','b1','b2','b3','b4','b5','b6','b7','b8','b9','ba','bb','bc','bd','be','bf','c0','c1','c2','c3','c4','c5','c6','c7','c8','c9','ca','cb','cc','cd','ce','cf','d0','d1','d2','d3','d4','d5','d6','d7','d8','d9','da','db','dc','dd','de','df','e0','e1','e2','e3','e4','e5','e6','e7','e8','e9','ea','eb','ec','ed','ee','ef','f0','f1','f2','f3','f4','f5','f6','f7','f8','f9','fa','fb','fc','fd','fe','ff']
                xxx = ['1','01','02','03','04','05','06','07','08','09','0a','0b','0c','0d','0e','0f','10','11','12','13','14','15','16','17','18','19','1a','1b','1c','1d','1e','1f','20','21','22','23','24','25','26','27','28','29','2a','2b','2c','2d','2e','2f','30','31','32','33','34','35','36','37','38','39','3a','3b','3c','3d','3e','3f','40','41','42','43','44','45','46','47','48','49','4a','4b','4c','4d','4e','4f','50','51','52','53','54','55','56','57','58','59','5a','5b','5c','5d','5e','5f','60','61','62','63','64','65','66','67','68','69','6a','6b','6c','6d','6e','6f','70','71','72','73','74','75','76','77','78','79','7a','7b','7c','7d','7e','7f']
                try:
                    x = int(x)
                    x_float = float(x) / 128
                    if x_float > 128:
                        x_float /= 128
                        if x_float > 128:
                            x_float /= 128
                            if x_float > 128:
                                x_float /= 128
                                strx = int(x_float)
                                y = (x_float - strx) * 128
                                z = (y - int(y)) * 128
                                n = (z - int(z)) * 128
                                m = (n - int(n)) * 128
                                return dec[int(m)] + dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
                            else:
                                strx = int(x_float)
                                y = (x_float - strx) * 128
                                z = (y - int(y)) * 128
                                n = (z - int(z)) * 128
                                return dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
                    return None 
                except: 
                    return None
            
            Key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
            Iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import pad
            import requests
            
            encrypted_id = encrypt_uid(uid)
            if not encrypted_id:
                return jsonify({'status': 'error', 'message': 'Encrypt failed'}), 400
            
            plain_text_payload = f'08a7c4839f1e10{encrypted_id}1801'
            cipher = AES.new(Key, AES.MODE_CBC, Iv)
            data = cipher.encrypt(pad(bytes.fromhex(plain_text_payload), AES.block_size))
            
            domains = [
                'https://clientbp.ggpolarbear.com/RemoveFriend',
                'https://clientbp.ggpolarbear.com/RemoveFriend',
                'https://clientbp.ggpolarbear.com/RemoveFriend',
            ]
            
            headers = {
                'X-Unity-Version': '2018.4.11f1',
                'ReleaseVersion': 'OB54',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-GA': 'v1 1',
                'Authorization': f'Bearer {token}',
                'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
                'Connection': 'Keep-Alive',
                'Accept-Encoding': 'gzip'
            }
            
            success = False
            msg = "Không kết nối được server"
            
            for url in domains:
                try:
                    response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
                    text = response.text
                    
                    if response.status_code == 200:
                        success = True
                        msg = "Hủy kết bạn thành công!"
                        break
                    elif 'BR_FRIEND_NOT_SAME_REGION' in text:
                        msg = "Khác khu vực!"
                        break
                    elif 'BR_FRIEND_MAX_REQUEST' in text:
                        msg = "Đã đạt giới hạn yêu cầu!"
                        break
                    elif 'BR_FRIEND_ALREADY_SENT_REQUEST' in text:
                        msg = "Chưa gửi yêu cầu kết bạn!"
                        break
                except:
                    continue
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': msg,
                    'data': {
                        'uid': uid,
                        'bot_id': bot_id,
                        'bot_uid': bot_uid,
                        'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}')
                    }
                }), 200
            else:
                return jsonify({'status': 'error', 'message': msg}), 400
                
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route("/xkb/all", methods=["GET"])
def api_xkb_all_get():
    try:
        uid = request.args.get('uid')
        if not uid:
            return jsonify({'status': 'error', 'message': 'Missing uid'}), 400
        
        results = []
        success_count = 0
        online_bots = 0
        
        def encrypt_uid(x):
            dec = ['80','81','82','83','84','85','86','87','88','89','8a','8b','8c','8d','8e','8f','90','91','92','93','94','95','96','97','98','99','9a','9b','9c','9d','9e','9f','a0','a1','a2','a3','a4','a5','a6','a7','a8','a9','aa','ab','ac','ad','ae','af','b0','b1','b2','b3','b4','b5','b6','b7','b8','b9','ba','bb','bc','bd','be','bf','c0','c1','c2','c3','c4','c5','c6','c7','c8','c9','ca','cb','cc','cd','ce','cf','d0','d1','d2','d3','d4','d5','d6','d7','d8','d9','da','db','dc','dd','de','df','e0','e1','e2','e3','e4','e5','e6','e7','e8','e9','ea','eb','ec','ed','ee','ef','f0','f1','f2','f3','f4','f5','f6','f7','f8','f9','fa','fb','fc','fd','fe','ff']
            xxx = ['1','01','02','03','04','05','06','07','08','09','0a','0b','0c','0d','0e','0f','10','11','12','13','14','15','16','17','18','19','1a','1b','1c','1d','1e','1f','20','21','22','23','24','25','26','27','28','29','2a','2b','2c','2d','2e','2f','30','31','32','33','34','35','36','37','38','39','3a','3b','3c','3d','3e','3f','40','41','42','43','44','45','46','47','48','49','4a','4b','4c','4d','4e','4f','50','51','52','53','54','55','56','57','58','59','5a','5b','5c','5d','5e','5f','60','61','62','63','64','65','66','67','68','69','6a','6b','6c','6d','6e','6f','70','71','72','73','74','75','76','77','78','79','7a','7b','7c','7d','7e','7f']
            try:
                x = int(x)
                x_float = float(x) / 128
                if x_float > 128:
                    x_float /= 128
                    if x_float > 128:
                        x_float /= 128
                        if x_float > 128:
                            x_float /= 128
                            strx = int(x_float)
                            y = (x_float - strx) * 128
                            z = (y - int(y)) * 128
                            n = (z - int(z)) * 128
                            m = (n - int(n)) * 128
                            return dec[int(m)] + dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
                        else:
                            strx = int(x_float)
                            y = (x_float - strx) * 128
                            z = (y - int(y)) * 128
                            n = (z - int(z)) * 128
                            return dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
                return None 
            except: 
                return None
        
        Key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
        Iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        import requests
        
        for bot_id, bot in TCPbot.bots.items():
            if not bot.running_event.is_set():
                continue
            online_bots += 1
            token = getattr(bot, 'token', None)
            if not token:
                continue
            bot_uid = getattr(bot, 'botid', '')
            
            try:
                encrypted_id = encrypt_uid(uid)
                if not encrypted_id:
                    results.append({
                        'bot_id': bot_id,
                        'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                        'success': False,
                        'message': 'Encrypt failed'
                    })
                    continue
                
                plain_text_payload = f'08a7c4839f1e10{encrypted_id}1801'
                cipher = AES.new(Key, AES.MODE_CBC, Iv)
                data = cipher.encrypt(pad(bytes.fromhex(plain_text_payload), AES.block_size))
                
                domains = [
                    'https://clientbp.ggpolarbear.com/RemoveFriend',
                    'https://clientbp.ggwhitehawk.com/RemoveFriend',
                    'https://clientbp.ggpbn.com/RemoveFriend',
                ]
                
                headers = {
                    'X-Unity-Version': '2018.4.11f1',
                    'ReleaseVersion': 'OB54',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-GA': 'v1 1',
                    'Authorization': f'Bearer {token}',
                    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
                    'Connection': 'Keep-Alive',
                    'Accept-Encoding': 'gzip'
                }
                
                success = False
                msg = "Không kết nối được server"
                
                for url in domains:
                    try:
                        response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
                        text = response.text
                        
                        if response.status_code == 200:
                            success = True
                            msg = "Hủy kết bạn thành công!"
                            break
                        elif 'BR_FRIEND_NOT_SAME_REGION' in text:
                            msg = "Khác khu vực!"
                            break
                        elif 'BR_FRIEND_MAX_REQUEST' in text:
                            msg = "Đã đạt giới hạn yêu cầu!"
                            break
                        elif 'BR_FRIEND_ALREADY_SENT_REQUEST' in text:
                            msg = "Chưa gửi yêu cầu kết bạn!"
                            break
                    except:
                        continue
                
                if success:
                    success_count += 1
                
                results.append({
                    'bot_id': bot_id,
                    'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                    'success': success,
                    'message': msg
                })
                
            except Exception as e:
                results.append({
                    'bot_id': bot_id,
                    'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                    'success': False,
                    'message': str(e)
                })
        
        return jsonify({
            'status': 'success',
            'message': f'Completed: {success_count}/{online_bots} success',
            'data': {
                'uid': uid,
                'total_bots': online_bots,
                'success': success_count,
                'results': results
            }
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route("/join", methods=["GET"])
def join_api():
    tc = request.args.get("tc")
    mode = request.args.get("all", "s7").lower()
    bot_id = request.args.get("botid")
    if not tc:
        return jsonify({"success": False, "message": "Missing tc"}), 400
    if not bot_id:
        if not TCPbot.bots:
            return jsonify({"success": False, "message": "No bot"}), 400
        bot = list(TCPbot.bots.values())[0]
    else:
        try:
            bot_id = int(bot_id)
        except:
            return jsonify({"success": False, "message": "Invalid botid"}), 400
        if bot_id not in TCPbot.bots:
            return jsonify({"success": False, "message": "Bot not found"}), 404
        bot = TCPbot.bots[bot_id]
    try:
        tc = int(tc)
    except:
        return jsonify({"success": False, "message": "Invalid tc"}), 400
    if bot.bot_config.get("current_status") == "đang chạy...":
        return jsonify({
            "success": False,
            "message": "Bot is already running"
        }), 409
    def run():
        try:
            bot.bot_config["current_status"] = "đang chạy..."
            TCPbot.save_config()
            bot.rstatus = (4, '')
            bot.sock39699.send(bot._bot.join_squad(tc))
            time.sleep(2.5)
            if bot.ids:
                ids = list(set(bot.ids))
                emotes = list(bot.Emotes.values())
                if mode == "s7":
                    for emote in emotes:
                        bot.sock39699.send(
                            bot._bot.play_emote(emote, ids)
                        )
                        time.sleep(4)
                elif mode == "rd":
                    for uid in ids:
                        bot.sock39699.send(
                            bot._bot.play_emote(random.choice(emotes), [uid])
                        )
                        time.sleep(4)
                elif mode.upper() in bot.Emotes:
                    bot.sock39699.send(
                        bot._bot.play_emote(bot.Emotes[mode.upper()], ids)
                    )
            time.sleep(2)
            bot.sock39699.send(
                bot._bot.leave_squad(bot.botid)
            )
            bot.bot_config["current_status"] = "đã rời team"
            TCPbot.save_config()
        except Exception as e:
            bot.bot_config["current_status"] = "lỗi"
            TCPbot.save_config()
            print("JOIN ERROR:", e)
    threading.Thread(target=run, daemon=True).start()
    return jsonify({
        "success": True,
        "data": {
            "tc": tc,
            "all": mode,
            "status": bot.bot_config.get("current_status")
        }
    }), 200
    
@app.route("/sinv", methods=["GET"])
def api_sinv():
    uid = request.args.get("uid")
    if not uid or not uid.isdigit():
        return jsonify({"status": False, "error": "Invalid uid"}), 400
    uid = int(uid)
    bot = None
    for b in TCPbot.bots.values():
        if b.running_event.is_set():
            bot = b
            break
    if not bot:
        return jsonify({"status": False, "error": "No active bot"}), 500
    def run_spam():
        end_time = time.time() + 30
        while time.time() < end_time:
            try:
                bot.sock39699.send(
                    bot._bot.request_join_squad(uid)
                )
                time.sleep(0.35)
            except Exception as e:
                print("Spam error:", e)
                break
    threading.Thread(target=run_spam, daemon=True).start()
    return jsonify({
        "status": True,
        "message": f"Spamming invite to {uid} for 30 seconds"
    })
 
@app.route("/team5", methods=["GET"])
def api_team5():
    uid = request.args.get("uid")
    if not uid or not uid.isdigit():
        return jsonify({"status": False, "error": "Invalid uid"}), 400
    uid = int(uid)
    bot = None
    for b in TCPbot.bots.values():
        if b.running_event.is_set():
            bot = b
            break
    if not bot:
        return jsonify({"status": False, "error": "No active bot"}), 500
    def run():
        try:
            bot.sock39699.send(bot._bot.open_squad(5))
            time.sleep(0.5)
            bot.sock39699.send(bot._bot.invite_squad(uid, 1))
            bot.sock39699.send(bot._bot.invite_squad(uid, 2))
            time.sleep(4)
            bot.sock39699.send(bot._bot.leave_squad(bot.botid))
        except Exception as e:
            print("TEAM5 ERROR:", e)
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": True, "message": f"Team 5 done for UID {uid}"})

@app.route("/info", methods=["GET"])
def api_info():
    uid = request.args.get("uid")
    if not uid or not uid.isdigit():
        return jsonify({
            "success": False,
            "error": "Invalid uid"
        }), 400
    uid = int(uid)
    bot = None
    for b in TCPbot.bots.values():
        if b.running_event.is_set():
            bot = b
            break
    if not bot:
        return jsonify({
            "success": False,
            "error": "No active bot"
        }), 500
    try:
        result = send_info(uid, bot.token, bot.base_url)
        return jsonify({
            "success": True,
            "uid": uid,
            "result": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
                  
@app.route("/info")
def InfoApi():
 uid=request.args.get("uid")
 if not uid:
  return "Invalid Uid",400
 if not TCPbot.bots:
  return "No Info Bot",400

 _,bot=next(iter(TCPbot.bots.items()))

 try:
  return jsonify(send_info(uid,bot.token,bot.base_url))
 except Exception as e:
  return str(e),500
  
@app.route("/info1", methods=["GET"])
def api_info1():
    uid = request.args.get("uid")

    if not uid or not uid.isdigit():
        return jsonify({
            "success": False,
            "error": "Invalid uid"
        }), 400
    uid = int(uid)
    bot = None
    for b in TCPbot.bots.values():
        if b.running_event.is_set():
            bot = b
            break
    if not bot:
        return jsonify({
            "success": False,
            "error": "No active bot"
        }), 500
    try:
        result = send_info1(uid, bot.token, bot.base_url)

        return jsonify({
            "success": True,
            "uid": uid,
            "result": result
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500 
 
@app.get("/")
def home():
    return {
        "status": "online",
        "commands": {
            "info": "info?uid=",
            "info1": "info1?uid=",
            "join": "join?tc={tc}&all=s7",  
            "sinv": "sinv?uid=" 
        }
    } 

def sbot():
    for bot in TCPbot.bots.values():
        bot.start()

def run_telegram():  
    print("Telegram bot đang chạy...") 
    telegram_bot.infinity_polling()

if __name__ == "__main__": 
    threading.Thread(target=run_telegram, daemon=True).start()
    threading.Thread(target=sbot, daemon=True).start()
    app.run(host="0.0.0.0", port=2004)