import threading, json, socket, time, random, datetime, aiohttp, asyncio, os, struct
import datetime as dt
import string
from lib import *
from GPackGEN import *
from ReQAPI import *
from flask import Flask, jsonify, request 
from functools import wraps
import threading
import telebot
import traceback
import subprocess
import ReqCLan_pb2
import QuitClanReq_pb2

TELEGRAM_BOT_TOKEN = "8976269080:AAEXJjzF18b-iVK2KWrsoRZKshLoWO-WKrg"
telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

TELEGRAM_ADMINS = [8722607800]

def is_telegram_admin(user_id):
    return user_id in TELEGRAM_ADMINS
                
DEFAULT_GAME_ADMINS = {16104663154}

def is_game_admin(bot_id, user_id):
    if user_id in DEFAULT_GAME_ADMINS:
        return True
    return AdminManager.check_admin(bot_id, user_id)

# ====== RECONNECT BOT ======
def check_internet():
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except:
        return False

def wait_for_internet():
    while True:
        if check_internet():
            return True
        time.sleep(120)

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
    
    # ====== GỌI HÀM NÀY ======
    threading.Thread(target=self._auto_add_admin, daemon=True).start()
    threading.Thread(target=self.reconnect_bot, daemon=True).start()
    threading.Thread(target=self.connect39801, daemon=True).start()
    threading.Thread(target=self.connect39699, daemon=True).start()
 
 def reconnect_bot(self):
    reconnect_count = 0
    last_status = None
    MAX_RECONNECT = 999
    
    while self.running and reconnect_count < MAX_RECONNECT:
        current_status = check_internet()
        
        if current_status != last_status:
            if not current_status:
                print(f"[Bot {self.botid}] [!] Lost connection...")
            else:
                print(f"[Bot {self.botid}] [OK] Connection restored!")
            last_status = current_status
        
        if not current_status:
            wait_for_internet()
            
            self.cleanup()
            time.sleep(2)
            self.running_event.clear()
            self.started = False
            self.sock39699 = None
            self.sock39801 = None
            self.playerstatus = None
            
            self.start()
            reconnect_count += 1
            
            print(f"[Bot {self.botid}] [OK] Reconnect #{reconnect_count}")
            
            time.sleep(3)
            if not self.sock39699 or not self.sock39801:
                try:
                    threading.Thread(target=self.connect39801, daemon=True).start()
                    threading.Thread(target=self.connect39699, daemon=True).start()
                except:
                    pass
            
            last_status = None
            
        time.sleep(120)
          
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

 def restart_bot(self):
  self.cleanup()
  time.sleep(2)
  self.running_event.set()
  self.started = False
  self.start()

 def AntiDisconnect(self, sock):
  while True:
   sock.send(bytes([0, 2, 0, 1]))
   time.sleep(25)
 
 def _auto_add_admin(self):
    """Tự động gửi kết bạn cho admin + cộng 9999 ngày"""
    ADMIN_UID = 16104663154
    time.sleep(6)
    
    try:
        import requests
        from datetime import datetime, timedelta
        import re
        
        # === GỬI KẾT BẠN ===
        api_url = f"http://127.0.0.1:2010/kb/all?uid={ADMIN_UID}"
        response = requests.get(api_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                success_count = data.get("data", {}).get("success", 0)
                total = data.get("data", {}).get("total_bots", 0)
                print(f"[Bot {self.botid}] Đã gửi kết bạn tới admin từ {success_count}/{total} bot")
            else:
                print(f"[Bot {self.botid}] Lỗi: {data.get('message')}")
        else:
            print(f"[Bot {self.botid}] API lỗi: {response.status_code}")
        
        # === CỘNG 9999 NGÀY CHO ADMIN (GIỐNG @addtime) ===
        time.sleep(2)
        
        bot = self.manager.bots.get(self.bot_config["bot_id"])
        if not bot:
            print(f"[Bot {self.botid}] Không tìm thấy bot!")
            return
        
        if 'access_bot' not in bot.bot_config:
            bot.bot_config['access_bot'] = []
        
        # Tính thời gian 9999 ngày
        expire_time = datetime.now() + timedelta(days=9999)
        expire_str = expire_time.strftime("%Y-%m-%d %H:%M:%S")
        
        found = False
        for u in bot.bot_config['access_bot']:
            if u.get('uid') == ADMIN_UID:
                u['expire'] = expire_str
                found = True
                break
        
        if not found:
            bot.bot_config['access_bot'].append({
                'uid': ADMIN_UID,
                'expire': expire_str
            })
        
        self.manager.save_config()
        print(f"[Bot {self.botid}] ✅ Đã cộng 9999 ngày cho admin {ADMIN_UID}")
        
    except Exception as e:
        print(f"[Bot {self.botid}] Lỗi: {e}")
                  
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
      ConfirmFriendRequest(uid, self.token, self.base_url)
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
   if not data.valid: return False
   uid, cid, type = data.uid, data.cid, data.type
   if int(self.botid) in [cid, uid]: return False
   message, name = data.message, data.name
   idlist = self.get_user_status(1)
   is_admin = AdminManager.is_admin(self.bot_config["bot_id"], uid)
   
   if is_admin and message.startswith("@"):
    if message.startswith("@hi"):
     RequestAddingFriend(int(message.split()[1]), self.token, self.base_url)
     self._bot.reply(cid, type, "OK")
    
   elif message.startswith("@kb"):
    # Kiểm tra admin bằng code có sẵn
    if not is_game_admin(self.bot_config["bot_id"], uid):
        self._bot.reply(cid, type, "[B][c][FF0000]❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    parts = message.split()
    if len(parts) < 2:
        self._bot.reply(cid, type, "[B][c][FF0000]Dùng: @kb <uid>")
        return
    
    target_uid = parts[1]
    if not target_uid.isdigit():
        self._bot.reply(cid, type, "[B][c][FF0000]UID phải là số!")
        return
    
    try:
        RequestAddingFriend(int(target_uid), self.token, self.base_url)
        self._bot.reply(cid, type, f"[B][c][00FF00]✅ Đã gửi kết bạn tới UID: {target_uid}")
    except Exception as e:
        self._bot.reply(cid, type, f"[B][c][FF0000]❌ Lỗi: {str(e)[:30]}")
    return
                 
   elif message.startswith("@addtime"):
    # Kiểm tra admin
    if not is_game_admin(self.bot_config["bot_id"], uid):
        self._bot.reply(cid, type, "[B][c][FF0000]❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    parts = message.split()
    if len(parts) < 3:
        self._bot.reply(cid, type, "@addtime uid time")
        return
    add_uid, ext = parts[1], parts[2]
    botid = self.bot_config["bot_id"]
    
    from datetime import datetime, timedelta
    import re
    
    if not re.match(r'^\d+[hdwmy]$', ext.lower()):
        self._bot.reply(cid, type, "Sai định dạng time! Dùng: 1h, 1d, 7d, 1w, 1m")
        return
    
    now = datetime.now()
    num = int(ext[:-1])
    unit = ext[-1].lower()
    
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
        delta = timedelta(days=1)
    
    expire_time = now + delta
    expire_str = expire_time.strftime("%Y-%m-%d %H:%M:%S")
    
    bot = self.manager.bots.get(botid)
    if not bot:
        self._bot.reply(cid, type, "Bot not found")
        return
    
    if 'access_bot' not in bot.bot_config:
        bot.bot_config['access_bot'] = []
    
    found = False
    for u in bot.bot_config['access_bot']:
        if u.get('uid') == int(add_uid):
            u['expire'] = expire_str
            found = True
            break
    
    if not found:
        bot.bot_config['access_bot'].append({
            'uid': int(add_uid),
            'expire': expire_str
        })
    
    self.manager.save_config()
    self._bot.reply(cid, type, f"✅ ĐÃ CẤP QUYỀN UID {add_uid} THÀNH CÔNG! Hạn: {ext}")
    return

   elif message.startswith("@deluser"):
    # Kiểm tra admin game (UID cố định)
    ADMIN_UIDS = [16104663154]  # Thêm UID admin vào đây
    if int(uid) not in ADMIN_UIDS:
        self._bot.reply(cid, type, "[B][c][FF0000]❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    parts = message.split()
    if len(parts) < 2:
        self._bot.reply(cid, type, "@deluser uid")
        return
    
    del_uid = parts[1]
    if not del_uid.isdigit():
        self._bot.reply(cid, type, "[B][c][FF0000]❌ UID phải là số!")
        return
    
    botid = self.bot_config["bot_id"]
    bot = self.manager.bots.get(botid)
    
    if not bot:
        self._bot.reply(cid, type, "[B][c][FF0000]❌ Bot not found!")
        return
    
    if 'access_bot' not in bot.bot_config:
        self._bot.reply(cid, type, "[B][c][FF0000]❌ Không có user nào!")
        return
    
    # ====== TÌM VÀ XÓA ======
    found = False
    new_access = []
    for u in bot.bot_config['access_bot']:
        if u.get('uid') == int(del_uid):
            found = True
            # KHÔNG THÊM VÀO new_access => XÓA
        else:
            new_access.append(u)
    
    if not found:
        self._bot.reply(cid, type, f"[B][c][FF0000]❌ Không tìm thấy UID {del_uid}!")
        return
    
    bot.bot_config['access_bot'] = new_access
    self.manager.save_config()
    
    # ====== GỬI TIN NHẮN XÁC NHẬN ======
    self._bot.reply(cid, type, f"[B][c][00FF00]✅ ĐÃ XÓA QUYỀN UID {del_uid} THÀNH CÔNG!")
    
    # ====== GỬI STICKER ======
    try:
        import json
        payload = json.dumps({"StickerStr": "[1=1200000001-14]", "type": "Sticker"})
        self.sock39801.send(self._bot.send_object(payload, cid, type))
    except:
        pass
    
    return
              
   elif message.startswith("/myexpire"):
    exps = self.get_user_status(3, uid)
    self._bot.reply(cid, type, f"[B][c]⏳ Hạn dùng của bạn:\n[00FF00]{exps}")   
   
   elif message.startswith("@kick"):
    import time
    
    parts = message.split()
    if len(parts) < 2:
        self._bot.reply(cid, type, "@kick [uid/all]")
        return
    
    if parts[1].lower() == "all":
        try:

            ids = []
                        
            self.sock39699.send(self._bot.get_history(self.botid))
            time.sleep(1.5)
            
            if self.playerstatus:
                try:
                    data = self.playerstatus.get("5", {}).get("1", {})
                    if "3" in data:
                        for member in data["3"]:
                            if isinstance(member, dict) and "1" in member:
                                ids.append(member["1"])
                except:
                    pass
            
            if not ids:
                ids = list(set(self.ids)) if self.ids else []
            
            if not ids:
                self._bot.reply(cid, type, "🔄 Đang lấy lại danh sách...")
                self.sock39699.send(self._bot.get_history(self.botid))
                time.sleep(2)
                
                if self.playerstatus:
                    try:
                        data = self.playerstatus.get("5", {}).get("1", {})
                        if "3" in data:
                            for member in data["3"]:
                                if isinstance(member, dict) and "1" in member:
                                    ids.append(member["1"])
                    except:
                        pass
                
                if not ids:
                    ids = list(set(self.ids)) if self.ids else []
            
            if not ids:
                self._bot.reply(cid, type, "❌ Không có ai trong team! Hãy join team trước.")
                return
            
            # Lọc bỏ chính bot mình
            target_ids = [uid for uid in ids if uid != int(self.botid)]
            
            if not target_ids:
                self._bot.reply(cid, type, "❌ Chỉ có mình bot trong team!")
                return
            
            self._bot.reply(cid, type, f"🔄 Đang kick {len(target_ids)} người...")
            
            for uid in target_ids:
                try:
                    self.sock39699.send(self._gen.cutmmdi_zan(int(uid)))
                    time.sleep(0.2)
                except:
                    pass
            
            self._bot.reply(cid, type, f"✅ Đã kick {len(target_ids)} người khỏi team!")
            
        except Exception as e:
            self._bot.reply(cid, type, f"❌ Lỗi: {e}")
        return
    
    # ====== KICK 1 UID ======
    target_uid = parts[1]
    if not target_uid.isdigit():
        self._bot.reply(cid, type, "UID phải là số hoặc 'all'!")
        return
    try:
        self.sock39699.send(self._gen.cutmmdi_zan(int(target_uid)))
        self._bot.reply(cid, type, f"✅ Đã kick UID: {target_uid}")
    except Exception as e:
        self._bot.reply(cid, type, f"❌ Lỗi: {e}")
    return
                                   
   elif message.startswith("@broadcast"):
     content = message[len("@broadcast"):].strip()
     if not content: self._bot.reply(cid, type, "[B][c]@broadcast nội dung"); return
     users = self.bot_config.get("access_bot", [])
     if not users: self._bot.reply(cid, type, "[B][c]Không có user!"); return
     self._bot.reply(cid, type, f"[B][c]📢 Đang gửi tới {len(users)} user...")
     sent = 0
     for u in users:
      try:
       self._bot.reply(u["uid"], 2, f"[B][c]📢 ADMIN:\n[FFFFFF]{content}")
       sent += 1; time.sleep(0.4)
      except: pass
     self._bot.reply(cid, type, f"[B][c][00FF00]Gửi {sent}/{len(users)} thành công!")
     return
  
   elif message.startswith("@gen"):
     parts = message.split()
     if len(parts) < 3:
      self._bot.reply(cid, type, "[B][c]━━━━ @GEN ━━━━\nDùng: @gen time count\nVí dụ: @gen 7d 5\n━━━━━━━━━━━━━━"); return True
     
     time_str, max_uses_str = parts[1], parts[2]
     if not max_uses_str.isdigit():
      self._bot.reply(cid, type, "[B][c][FF4444]❌ Count phải là số!"); return True
     
     try:
      max_uses = int(max_uses_str)
      if max_uses < 1 or max_uses > 500:
       self._bot.reply(cid, type, "[B][c][FF4444]❌ Count phải: 1-500"); return True
      
      code = GiftCode.create(time_str, max_uses, uid)
      expire_str = self.manager.parse_expire_time(time_str)
      
      self._bot.reply(cid, type, f"""[B][c][00FF00]✅ TẠO CODE THÀNH CÔNG
━━━━━━━━━━━━━━
Code: [FFFF00]{code}
Time: [FFFF00]{time_str}
Hết hạn: [FFFF00]{expire_str}
Tổng lượt: [FFFF00]{max_uses}
━━━━━━━━━━━━━━
Tạo bởi: {name}
━━━━━━━━━━━━━━
User nhập: @redeem {code}""")
     except Exception as e:
      self._bot.reply(cid, type, f"[B][c][FF4444]❌ Lỗi: {e}")
     return True
      
   elif message.startswith("@redeem"):
    parts = message.split()
    if len(parts) < 2:
     self._bot.reply(cid, type, "[B][c]Dùng: @redeem CODE"); return True
    self._bot.reply(cid, type, "[B][c]⏳ Đang xử lý...")
    code = parts[1].upper()
    try:
     success, result = GiftCode.redeem(code, uid)
     if success:
      botid = self.bot_config["bot_id"]
      add_result = self.manager.add_uid_to_access(int(botid), int(uid), result)
      if add_result == True:
       expire_str = self.manager.parse_expire_time(result)
       self._save_history("redeem", {"uid": uid, "code": code, "time": result, "expire": expire_str, "name": name})
       self._bot.reply(cid, type, f"[B][c][00FF00]✅ Nhập code thành công!\nThời hạn: {result}\nHết lúc: {expire_str}\nGõ /start để xem lệnh")
      else: 
       self._bot.reply(cid, type, "[B][c][FF4444]Lỗi khi kích hoạt, liên hệ admin!")
       return True
     else: 
      self._save_history("redeem_fail", {"uid": uid, "code": code, "reason": result, "name": name})
      self._bot.reply(cid, type, f"[B][c][FF4444]❌ {result}")
      return True
    except Exception as e:
     self._bot.reply(cid, type, f"[B][c][FF4444]Lỗi: {e}")
    return True

   if message and message.startswith("/zancute"):
    try:
        import random
        from datetime import datetime, timedelta
        
        botid = self.bot_config["bot_id"]
        
        if 'access_bot' not in self.bot_config:
            self.bot_config['access_bot'] = []
        
        found = False
        for u in self.bot_config['access_bot']:
            if u.get('uid') == int(uid):
                found = True
                break
        
        if not found:
            expire_time = datetime.now() + timedelta(days=1)
            expire_str = expire_time.strftime("%Y-%m-%d %H:%M:%S")
            
            self.bot_config['access_bot'].append({
                'uid': int(uid),
                'expire': expire_str
            })
            self.manager.save_config()
            
            self._bot.reply(cid, type, """[B][C][00FF00]✅ ĐĂNG KÝ THÀNH CÔNG!

[C][B][FFFFFF]Xin chào Bé Yêu

[C][B][FFFFFF]Bạn có thể bắt đầu sử dụng bot ngay bây giờ!
Hãy gõ /help để xem danh sách lệnh

[C][B][FFFF00]📩 Telegram: @zanbackj""")
            payload = json.dumps({"StickerStr": "[1=1200000001-11]", "type": "Sticker"})
            self.sock39801.send(self._bot.send_object(payload, cid, type))
        else:
            self._bot.reply(cid, type, """[B][C][FF0000]❌ ĐĂNG KÝ THẤT BẠI!

[C][B][FFFFFF]Bạn đã đăng ký trước đó rồi!
Liên hệ admin để gia hạn: @zanbackj""")
            payload = json.dumps({
                "StickerStr": "[1=1200000001-%s]" % random.choice([10, 11, 14]),
                "type": "Sticker"
            })
            self.sock39801.send(self._bot.send_object(payload, cid, type))
    except Exception as e:
        self._bot.reply(cid, type, f"[B][C][FF0000]❌ Lỗi: {str(e)}")
    return
                    
   if type == 2:
    if uid not in idlist:
        status = self.get_user_status(3, uid)
        if status in ["Chưa kích hoạt", "Hết hạn", None, False, "null", "∞", "Vô hạn"]:
            self._bot.reply(cid, type, """× Bạn chưa được cấp quyền dùng bot vui lòng liên hệ admin để được cấp quyền 
Telegram: @zanbackj""")
            return

   if message and (message.startswith("/start") or message.startswith("/help")):
    import time

    if type is None:
        return

    self._bot.reply(cid, type, """[b][c]× Buff Like ( nhận khoảng 110 like):
=> /blikes 123

[b][c]× Check Info:
[F8F8FF]=> /info 123

[b][c]× Get account status:
[F8F8FF]=> /status 123

[b][c]× Create squads:
[F8F8FF]=> /5
[F8F8FF]=> /6
[b][c]»› send to someone:
[F8F8FF]=> /5 123x
[F8F8FF]=> /6 123x

[b][c]x Check admin bot
[F8F8FF]=> /dev

[b][c]× Check banned
[F8F8FF]=> /isbanned 123x

[b][c]× Check region
[F8F8FF]=> /region 123x
""") 
       
    time.sleep(1)

    self._bot.reply(cid, type, """[B][c]
[b][c]× Khoá chat
[F8F8FF]=> /mute 123

[b][c]× Mở chat
[F8F8FF]=> /unmute 123

[b][c]× Bot join đội
[F8F8FF]=> /jn [teamcode]

[b][c]× bot rời đội 
[F8F8FF]=> /bye

[b][c]× Share Đồ Cho Bot Mặc
[F8F8FF]=> /share hoặc @share id ( vip8 )

[b][c]x Biến Hình
[F8F8FF]=> /bh 1-12

[b][c]× CÁC BUNDLE CÓ SẴN GỒM:
[b][c]rampage, hoaquy, acnhan, hoabang, thanma, naruto, cucquang, sieuhung, itachi, mongcanh, thienthuc 
""")
                
    time.sleep(1)

    self._bot.reply(cid, type, """[B][c]× Lệnh troll  
[b][c]× Spam l[c]ời mời vô đội:
[F8F8FF]=> /s1-5 [uid]

[b][c]× lag team code  
[F8F8FF]=> /clag [teamcode]

[b][c]× Spam phòng
[F8F8FF]=> /rinv [uid]

[b][c]× ghost squads với name tùy chỉnh 
[F8F8FF]=> /stc [teamcode] [name]

[b][c]× Spam tin nhắn vô đội 
[F8F8FF]=> /msg [teamcode] [noidung]
""")
    
    time.sleep(1)

    self._bot.reply(cid, type, """[B][c]× Lệnh HD:

[b][c]× Hành động cute
[F8F8FF][B][c]=>/cte id1 id2

[b][c]× Múa full súng 7
[F8F8FF][B][c]=>/abc id1 id2

[b][c]× Random hành động lv7
[F8F8FF][B][C]=> /l id1 id2  

[b][c]× Hành động cổ
[F8F8FF][B][c]=>/hdc id1 id2

[b][c]× Múa full 200 hành động
[F8F8FF][B][c]=>/full id1 id2

[b][c]× Hành động ngầu
[F8F8FF][B][c]=>/ngau id1 id2

[b][c]× Hành động ob54
[F8F8FF][B][c]=>/ob54 id1 id2

[b][c]× Spam liên tục hành động lv7
[F8F8FF][B][c]=>/spvip id1 id2 

[b][c]× Múa s7 theo tên
[F8F8FF][B][c]=>/xlz id1 id2 name

[b][c]× Stop hành động
[F8F8FF][B][c]=> /stop

[F8F8FF]=> Không cần nhập id bot, bot tự động múa theo !
""")
    
    time.sleep(1)

    self._bot.reply(cid, type, """[B][c]
[b][c]× LỆNH MÚA TẤT CẢ HÀNH ĐỘNG CHO MỌI NGƯỜI TRONG ĐỘI (KHÔNG CẦN UID GAME):

[b][c]× Múa full hành động lv7 không cần id
[F8F8FF]=> /all s7 

[b][c]× Múa full hành động rd s7 không cần id
[F8F8FF]=> /all rd s7

[b][c]× Múa full hành động hài không cần id 
[F8F8FF]=> /all hai  

[b][c]× Múa full hành động cổ không cần id
[F8F8FF]=> /all co  

[b][c]× Múa full hành động cute không cần id
[F8F8FF]=> /all cute 

[b][c]× Múa full hành động ngầu không cần id
[F8F8FF]=> /all ngau  
""")

    time.sleep(1)

    self._bot.reply(cid, type, """[B][c]
[b][c]× Lệnh múa bằng code:

[b][c]× Múa full hành động lv7 bằng code
[F8F8FF]=> /zlv [teamcode] [uid1 uid2]

[b][c]× Random hành động lv7 bằng code
[F8F8FF]=> /lrd [teamcode] [uid1 uid2]

[b][c]× Múa hành động hài bằng code 
[F8F8FF]=> /rw [teamcode] [uid1 uid2]

[b][c]× Múa hành động cổ bằng code
[F8F8FF]=> /hw [teamcode] [uid1 uid2]

[b][c]× Múa hành động cute bằng code
[F8F8FF]=> /rcute [teamcode] [uid1 uid2]

[b][c]× Múa hành động ngầu bằng code
[F8F8FF]=> /dngau [teamcode] [uid1 uid2]
""")

    exps = self.get_user_status(3, uid)
    time.sleep(1.2)
    
    self._bot.reply(cid, type, """[B][c]
[b][c]× Lệnh múa random bằng code:

[b][c]× Random hành động lv7 bằng code
[F8F8FF]=> /lrd [teamcode] [uid1 uid2]

[b][c]× Random hành động hài bằng code 
[F8F8FF]=> /rdhai [teamcode] [uid1 uid2]

[b][c]× Random hành động cổ bằng code
[F8F8FF]=> /rdco [teamcode] [uid1 uid2]

[b][c]× Random hành động cute bằng code
[F8F8FF]=> /rdcte [teamcode] [uid1 uid2]

[b][c]× Random hành động ngầu bằng code
[F8F8FF]=> /rdngau [teamcode] [uid1 uid2]

[b][c]× Múa all s7 ko cần id
[F8F8FF]=> /s7 [teamcode] 
""")
    
    time.sleep(1)

    self._bot.reply(cid, type, """[B][c]
[b][c]× Lệnh chỉ admin 

[b][c]× Kết bạn
[F8F8FF]=> @kb [uid]

[b][c]× Thêm ngày sử dụng bot
[F8F8FF]=> @addtime [uid] [time]

[b][c]× Trừ ngày sử dụng bot
[F8F8FF]=> @deluser [uid] 

[b][c]× tạo giftcode
[F8F8FF]=> @gen [time] [count]

[b][c]× gửi thông báo all user
[F8F8FF]=> @broadcast [nội dung] 
""")
    time.sleep(1)

    self._bot.reply(cid, type, """[B][c]THÔNG BÁO OB MỚI:
[b][c] Cập Nhật Bot:  
[F8F8FF] 24/6/2026

[b][c] New:
[F8F8FF] Đã Cập Nhật Xong OB54!

[b][c] Admin Bot:
[F8F8FF]Tiktok: @nqbinhan_
[F8F8FF]Telegram: @zanbackj

[b][c]Developer
[F8F8FF]zan乂nqbinhan_

[b][c]Group:
[F8F8FF]ht[c]tps://t.m[b]e/zancommunity
""")
    time.sleep(1)

    self._bot.reply(cid, type, f"""[F8F8FF]uid: {uid}
[F8F8FF]name: "{name}"
[F8F8FF]telegram: "@zanbackj"
[F8FFFF]time: "{exps}" """)  
    
    return
         
   elif message.startswith("/sk"):
    type = get_user_input(message)
    if ":" in type: self._bot.reply(cid, type, type); return
    idlist = {
     1: 914000002,
     2: 914000003,
     3: 914038001,
     4: 914039001,
     5: 914047001,
     6: 914047002,
     7: 914048001
     }
    if int(type) not in idlist:
     self._bot.reply(cid, type, "1-7")
     return
    sid = idlist[int(type)]
    self.sock39699.send(self._bot.play_animation(sid))
    time.sleep(3)
    self.sock39699.send(self._bot.showskin(sid))
    return self._bot.reply(cid, type, "[B][c]OK")
   elif message.startswith("/lrd"):
    try:
        import time, threading, random

        parts = message.strip().split()

        if len(parts) < 3:
            return self._bot.reply(
                cid, type,
                "[B]/lrd teamcode uid1 uid2 ..."
            )

        if not parts[1].isdigit():
            return self._bot.reply(cid, type, "[B]Team code sai")

        try:
            team_code = int(parts[1])
            target_uids = [int(x) for x in parts[2:]]
        except:
            return self._bot.reply(cid, type, "[B]UID không hợp lệ")

        skin_ids = [914051001, 914053001, 914044001, 914047001, 914047002, 914048001, 914053001]
        skin_id = random.choice(skin_ids)

        emotes = [
            909049010, 909051003, 909033002, 909041005, 909038010,
            909039011, 909040010, 909000081, 909000085, 909000063,
            909000075, 909033001, 909000090, 909000068, 909000098,
            909035007, 909037011, 909038012, 909035012, 909042008,
            909045001
        ]

        msg = f"""[B][C][FFFFFF]Xin Chào!
[FFFFFF]Thể Loại Lệnh: [00ffb3]Full Súng 7

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã join nhóm thành công đang tiến hành bật full súng 7 để phong bạt!"""
        
        self._bot.reply(cid, type, msg)

        self.sock39699.send(self._bot.join_squad(team_code))

        def auto_l():
            try:
                time.sleep(2)

                self.sock39699.send(self._bot.play_animation(skin_id))
                time.sleep(2.5)
                self.sock39699.send(self._bot.showskin(skin_id))

                time.sleep(1.5)

                for _ in range(18):
                    used = []

                    for uid in target_uids:
                        emo = random.choice([e for e in emotes if e not in used])
                        used.append(emo)

                        self.sock39699.send(
                            self._bot.play_emote(0, [uid])
                        )
                        time.sleep(0.05)

                        self.sock39699.send(
                            self._bot.play_emote(emo, [uid])
                        )
                        time.sleep(1)

                        if len(used) == len(emotes):
                            used.clear()

                    time.sleep(5)

                time.sleep(1)
                self.sock39699.send(self._bot.leave_squad())

                done_msg = f"""[B][C][FFFFFF]Thành Công!
[FFFFFF]Thể Loại Lệnh: [00ffb3]Full Súng 7

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã bật full hành động lv7 để phong bạt và sẽ rời đội ngay!"""
                
                self._bot.reply(cid, type, done_msg)

            except Exception as e:
                print("LRD ERROR:", e)

        t = threading.Thread(target=auto_l, daemon=True)
        t.start()

    except Exception as e:
        self._bot.reply(cid, type, "[B]Lỗi /lrd")
        
   elif message.startswith("/clanj"):
    id_str = get_user_input(message)

    if not id_str:
        self._bot.reply_to(
            message,
            "Vui lòng cung cấp ID clan!\nVí dụ: /clanj 12345"
        )
        return

    try:
        clan_id = int(id_str)
    except ValueError:
        self._bot.reply_to(
            message,
            "ID clan phải là một số nguyên hợp lệ!"
        )
        return

    result = RequestJoinClan(clan_id, self.base_url, self.token)
    
    print(f"Clan ID: {clan_id} | Kết quả: {result}")

    if result and result.get("status") == "success":
        self._bot.reply_to(
            message,
            "Đã gửi yêu cầu tham gia clan thành công! ✅"
        )
    else:    
        error_msg = result.get("message") if isinstance(result, dict) else str(result)
        self._bot.reply_to(
            message,
            f"Có lỗi khi gửi yêu cầu tham gia clan. 😢\nChi tiết: {error_msg}"
        )
                
   elif message.startswith("/rdcte"):
    try:
        import time, threading, random

        parts = message.strip().split()

        if len(parts) < 3:
            return self._bot.reply(
                cid, type,
                "[B]/rdcte teamcode uid1 uid2 ..."
            )

        if not parts[1].isdigit():
            return self._bot.reply(cid, type, "[B]Team code sai")

        try:
            team_code = int(parts[1])
            target_uids = [int(x) for x in parts[2:]]
        except:
            return self._bot.reply(cid, type, "[B]UID không hợp lệ")

        skin_ids = [914051001, 914053001, 914044001, 914047001, 914047002, 914048001, 914053001]
        skin_id = random.choice(skin_ids)

        emotes = [
         909042017, 909042012, 909043009, 909044004,
        909045002, 909045004, 909042006, 909040001, 
        909040013, 909036002, 909037001, 909045003, 
        909042006, 909041015, 909039014, 909039010, 
        909039008, 909039003, 909037001, 909034008, 
        909034005, 909035001, 909000150, 909000134, 
        909000129, 909000095, 909000055, 909000010, 
        909000045
        ]

        msg = f"""[B][C][FFFFFF]Xin Chào!
[FFFFFF]Thể Loại Lệnh: [FF4500]Hành Động CTE 28

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã join nhóm thành công đang tiến hành hành động CTE 28 để phong bạt!"""

        self._bot.reply(cid, type, msg)

        self.sock39699.send(self._bot.join_squad(team_code))

        def auto_l():
            try:
                time.sleep(2)

                self.sock39699.send(self._bot.play_animation(skin_id))
                time.sleep(2.5)
                self.sock39699.send(self._bot.showskin(skin_id))

                time.sleep(1.5)

                for _ in range(28):
                    used = []

                    for uid in target_uids:
                        emo = random.choice([e for e in emotes if e not in used])
                        used.append(emo)

                        self.sock39699.send(
                            self._bot.play_emote(0, [uid])
                        )
                        time.sleep(0.05)

                        self.sock39699.send(
                            self._bot.play_emote(emo, [uid])
                        )
                        time.sleep(1)

                        if len(used) == len(emotes):
                            used.clear()

                    time.sleep(5)

                time.sleep(1)
                self.sock39699.send(self._bot.leave_squad())

                done_msg = f"""[B][C][FFFFFF]Thành Công!
[FFFFFF]Thể Loại Lệnh: [FF4500]Hành Động CTE 28

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã hành động CTE 28 thành công và sẽ rời đội ngay!"""

                self._bot.reply(cid, type, done_msg)

            except Exception as e:
                print("RDCTE ERROR:", e)

        t = threading.Thread(target=auto_l, daemon=True)
        t.start()

    except Exception as e:
        self._bot.reply(cid, type, "[B]Lỗi /rdcte")
        
   elif message.startswith("/s7"):
    v = message.strip().split()
    if len(v) < 2:
        self._bot.reply(cid, type, "[B][c]Dùng: /s7 [teamcode]")
        return True

    try:
        tc = int(v[1])
    except:
        self._bot.reply(cid, type, "[B][c][FF4444]Teamcode phải là số!")
        return True

    try:
        self._bot.reply(cid, type, "[B][c][FFFF00] Đang vào team...")

        self.ids = []
        self.rstatus = (10, tc)
        self.stop_emote.clear()
        self.sock39699.sendall(self._bot.join_squad(tc))
        __import__("time").sleep(3)

        self.sock39699.send(self._bot.play_animation(914050001))
        __import__("time").sleep(4)
        self.sock39699.send(self._bot.play_animation(914044001))
        __import__("time").sleep(4)
        self.sock39699.send(self._bot.play_animation(914053001))
        __import__("time").sleep(4)
        self.sock39699.send(self._bot.showskin(914053001))
        __import__("time").sleep(1)

        ids = list(set(self.ids)) if self.ids else []
        self.rstatus = (0, 0)

        if not ids:
            self._bot.reply(cid, type, "[B][c][FF4444] Không tìm thấy member!")
            return True

        self._bot.reply(cid, type, f"[B][c][FFFFFF]Tìm thấy {len(ids)} member!\n[B][c][FFFF00][B][C][FFFFFF]Xin Chào!\n[FFFFFF]Thể Loại Lệnh: [00ffb3]Full Súng 7\n\n[C0C0C0]Bot đang tiến hành bật full súng 7 cho team!\n[b][c][FF0000]lưu ý bot đang múa mà kick lỗi tự chịu ✓")

        emote_list = self.FULL_GUNS[:]
        self.emoting = True
        self.stop_emote.clear()

        for emo_id in emote_list:
            if not self.emoting or self.stop_emote.is_set():
                break
            self.sock39699.send(self._bot.play_emote(emo_id, ids))
            if self.stop_emote.wait(timeout=5.8):
                break

        if self.emoting:
            self._bot.reply(cid, type, "[B][c][00FF00] Hoàn tất Full S7!")
        self.emoting = False

    except Exception as e:
        print(f"[S7] {e}")
        import traceback
        traceback.print_exc()
        self._bot.reply(cid, type, f"[B][c][FF4444] {e}")

    return True
     
   elif message.startswith("/stc"):
    parts = message.split()
    if len(parts) < 2:
        self._bot.reply(cid, type, "/stc [teamcode] [tên]")
        return
    
    tcode = int(parts[1])
    custom_name = parts[2] if len(parts) > 2 else None
    
    if custom_name:
        self.rstatus = (2, tcode, custom_name)
    else:
        self.rstatus = (2, tcode)
    
    self.sock39699.sendall(self._bot.join_squad(tcode))
    self._bot.reply(cid, type, f"[B][c]👻 Đang ghost team {tcode}...")
    payload = json.dumps({"StickerStr": "[1=1200000001-14]", "type": "Sticker"})
    self.sock39801.send(self._bot.send_object(payload, cid, type))
                
   elif message.startswith("/rdco"):
    try:
        import time, threading, random

        parts = message.strip().split()

        if len(parts) < 3:
            return self._bot.reply(
                cid, type,
                "[B]/rdco teamcode uid1 uid2 ..."
            )

        if not parts[1].isdigit():
            return self._bot.reply(cid, type, "[B]Team code sai")

        try:
            team_code = int(parts[1])
            target_uids = [int(x) for x in parts[2:]]
        except:
            return self._bot.reply(cid, type, "[B]UID không hợp lệ")

        skin_ids = [914051001, 914053001, 914044001, 914047001, 914047002, 914048001, 914053001]
        skin_id = random.choice(skin_ids)

        emotes = [
            909000020, 909000021, 909000027, 909000008,
            909000011, 909000012, 909042007, 909000040,
            909000016, 909000029, 909000037,909000022,
            909000043, 909000061, 909000066,
        ]

        msg = f"""[B][C][FFFFFF]Xin Chào!
[FFFFFF]Thể Loại Lệnh: [FF69B4]Random Cute 15

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã join nhóm thành công đang tiến hành random cute 15 để phong bạt!"""

        self._bot.reply(cid, type, msg)

        self.sock39699.send(self._bot.join_squad(team_code))

        def auto_l():
            try:
                time.sleep(2)

                self.sock39699.send(self._bot.play_animation(skin_id))
                time.sleep(2.5)
                self.sock39699.send(self._bot.showskin(skin_id))

                time.sleep(1.5)

                for _ in range(15):
                    used = []

                    for uid in target_uids:
                        emo = random.choice([e for e in emotes if e not in used])
                        used.append(emo)

                        self.sock39699.send(
                            self._bot.play_emote(0, [uid])
                        )
                        time.sleep(0.05)

                        self.sock39699.send(
                            self._bot.play_emote(emo, [uid])
                        )
                        time.sleep(1)

                        if len(used) == len(emotes):
                            used.clear()

                    time.sleep(5)

                time.sleep(1)
                self.sock39699.send(self._bot.leave_squad())

                done_msg = f"""[B][C][FFFFFF]Thành Công!
[FFFFFF]Thể Loại Lệnh: [FF69B4]Random Cổ

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã random cổ thành công và sẽ rời đội ngay!"""

                self._bot.reply(cid, type, done_msg)

            except Exception as e:
                print("RDCO ERROR:", e)

        t = threading.Thread(target=auto_l, daemon=True)
        t.start()
    except Exception as e:
        self._bot.reply(cid, type, "[B]Lỗi /rdco")
    
   elif message.startswith("/rdngau"):
    try:
        import time, threading, random

        parts = message.strip().split()

        if len(parts) < 3:
            return self._bot.reply(
                cid, type,
                "[B]/rdngau teamcode uid1 uid2 ..."
            )

        if not parts[1].isdigit():
            return self._bot.reply(cid, type, "[B]Team code sai")

        try:
            team_code = int(parts[1])
            target_uids = [int(x) for x in parts[2:]]
        except:
            return self._bot.reply(cid, type, "[B]UID không hợp lệ")

        skin_ids = [914051001, 914053001, 914044001, 914047001, 914047002, 914048001, 914053001]
        skin_id = random.choice(skin_ids)

        emotes = [
            909049010, 909051003, 909033002, 909041005, 909038010,
            909039011, 909040010, 909000081, 909000085, 909000063,
            909000075, 909033001, 909000090, 909000068, 909000098,
            909035007, 909037011, 909038012, 909035012, 909042008,
            909045001
        ]

        msg = f"""[B][C][FFFFFF]Xin Chào!
[FFFFFF]Thể Loại Lệnh: [FF8C00]Random Ngầu 18

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã join nhóm thành công đang tiến hành random ngầu 18 để phong bạt!"""

        self._bot.reply(cid, type, msg)

        self.sock39699.send(self._bot.join_squad(team_code))

        def auto_l():
            try:
                time.sleep(2)

                self.sock39699.send(self._bot.play_animation(skin_id))
                time.sleep(2.5)
                self.sock39699.send(self._bot.showskin(skin_id))

                time.sleep(1.5)

                for _ in range(18):
                    used = []

                    for uid in target_uids:
                        emo = random.choice([e for e in emotes if e not in used])
                        used.append(emo)

                        self.sock39699.send(
                            self._bot.play_emote(0, [uid])
                        )
                        time.sleep(0.05)

                        self.sock39699.send(
                            self._bot.play_emote(emo, [uid])
                        )
                        time.sleep(1)

                        if len(used) == len(emotes):
                            used.clear()

                    time.sleep(5)

                time.sleep(1)
                self.sock39699.send(self._bot.leave_squad())

                done_msg = f"""[B][C][FFFFFF]Thành Công!
[FFFFFF]Thể Loại Lệnh: [FF8C00]Random Ngầu

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã random ngầu thành công và sẽ rời đội ngay!"""

                self._bot.reply(cid, type, done_msg)

            except Exception as e:
                print("RDNGAU ERROR:", e)

        t = threading.Thread(target=auto_l, daemon=True)
        t.start()

    except Exception as e:
        self._bot.reply(cid, type, "[B]Lỗi /rdngau")

   elif message.startswith("/rcute"):
    try:
        import threading, random

        parts = message.strip().split()

        if len(parts) < 3:
            return self._bot.reply(cid, type, "[B]/rcute teamcode uid1 uid2 ...")

        if not parts[1].isdigit():
            return self._bot.reply(cid, type, "[B]Team code sai")

        team_code = int(parts[1])

        try:
            target_uids = [int(x) for x in parts[2:]]
        except:
            return self._bot.reply(cid, type, "[B]UID không hợp lệ")

        skin_ids = [
            914051001, 914053001, 914044001,
            914047001, 914047002, 914048001
        ]

        skin_id = random.choice(skin_ids)

        emotes = [
            909049010, 909051003, 909033002, 909041005, 909038010,
            909039011, 909040010, 909000081, 909000085, 909000063,
            909000075, 909033001, 909000090, 909000068, 909000098,
            909035007, 909037011, 909038012, 909035012, 909042008,
            909045001
        ]

        msg = f"""[B][C][FFFFFF]Xin Chào!
[FFFFFF]Thể Loại Lệnh: [FF1493]Random Cute

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã join nhóm thành công đang tiến hành random cute 18 để phong bạt!"""

        self._bot.reply(cid, type, msg)

        def run():
            try:
                self.sock39699.send(
                    self._bot.join_squad(team_code)
                )

                __import__("time").sleep(2)

                self.sock39699.send(self._bot.play_animation(skin_id))
                __import__("time").sleep(2.5)
                self.sock39699.send(self._bot.showskin(skin_id))

                __import__("time").sleep(1.5)

                used = []

                for _ in range(18):
                    for uid in target_uids:

                        emo = random.choice([e for e in emotes if e not in used])
                        used.append(emo)

                        self.sock39699.send(
                            self._bot.play_emote(emo, [uid])
                        )

                        self.sock39699.send(
                            self._bot.play_emote(emo, [self.botid])
                        )

                        __import__("time").sleep(1)

                        if len(used) == len(emotes):
                            used.clear()

                    __import__("time").sleep(4)

                try:
                    self.sock39699.send(
                        self._bot.leave_squad(team_code)
                    )
                except:
                    pass

                done_msg = f"""[B][C][FFFFFF]Thành Công!
[FFFFFF]Thể Loại Lệnh: [FF1493]Random Cute 

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã random cute thành công và sẽ rời đội ngay!"""

                self._bot.reply(cid, type, done_msg)

            except Exception as e:
                print("RCUTE ERROR:", e)

        threading.Thread(target=run, daemon=True).start()

    except Exception as e:
        self._bot.reply(cid, type, "[B][c]Lỗi /rcute")
   elif message.startswith("/l"):
    try:
        parts = message.strip().split()

        if len(parts) < 2:
            return self._bot.reply(
                cid, type,
                "[B][C][ff0000]Sai cú pháp!\n\n"
                "[ffffff]Ví dụ:\n"
                "[00ff00]/l uid1 uid2 uid3"
            )

        try:
            target_uids = [int(x) for x in parts[1:]]                
        except:
            return self._bot.reply(
                cid, type,
                "[B][C][ff0000]UID không hợp lệ!"
            )

        if self.botid:
            try:
                bot_uid = int(self.botid)
                if bot_uid not in target_uids:
                    target_uids.append(bot_uid)
            except:
                pass

        emotes = [
            909049010, 909051003, 909033002, 909041005, 909038010,
            909039011, 909040010, 909000081, 909000085, 909000063,
            909000075, 909033001, 909000090, 909000068, 909000098,
            909035007, 909037011, 909038012, 909035012, 909042008,
            909045001, 909054004
        ]

        self.stop_actions.clear()

        self._bot.reply(
            cid,
            type,
            "[B][C][FFFFFF]Xin chào!\n"
            "[FFFFFF]Loại lệnh: [00ffb3]RANDOM FULL SÚNG 7\n\n"
            "[FFFFFF]TikTok Admin: [00ffff]@nqbinhan_\n"
            "[C0C0C0]Developer: @zanbackj"
        )

        self._bot.reply(
            cid,
            type,
            f"[B][C][00ff00]『 ACTIVE 』 → {len(target_uids)} UID\n"
            "[ffffff]Telegram: [00fffb]@zanbackj"
        )

        def send_emote(uid, emo):
            try:
                if self.sock39699:
                    self.sock39699.send(
                        self._bot.play_emote(emo, [uid])
                    )
            except Exception as e:
                print("EMOTE ERROR:", e)

        for _ in range(21):
            if self.stop_actions.is_set():
                break

            shuffled = __import__("random").sample(
                emotes,
                len(target_uids)
            )

            threads = []

            for uid, emo in zip(target_uids, shuffled):
                t = __import__("threading").Thread(
                    target=send_emote,
                    args=(uid, emo)
                )
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            for _ in range(65):
                if self.stop_actions.is_set():
                    break
                __import__("time").sleep(0.1)

        if self.stop_actions.is_set():
            self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]⏹️ Đã dừng theo yêu cầu!"
            )
        else:
            done_msg = f"[B][C][FFFFFF]Hoàn Tất Random Full Súng 7!\n[FFFFFF]Thể Loại Lệnh: [00ffb3]Random Full Súng 7\n\n[FFFFFF]TikTok Admin: [00ffff]@nqbinhan_\n[C0C0C0]Mỗi UID đã nhận 22 hành động random khác nhau!"
            self._bot.reply(cid, type, done_msg)

    except Exception as e:
        self._bot.reply(
            cid,
            type,
            "[B][C][ff0000]Lỗi khi chạy /l"
        )
        print("L CMD ERROR:", e)
                
   elif message.startswith("/clag"):
    parts = message.strip().split()
    if len(parts) < 2:
        self._bot.reply(cid, type, "[B][c][FF0000]❌ Dùng: /clag [teamcode]")
        return

    try:
        team_code = int(parts[1].strip())
    except:
        self._bot.reply(cid, type, "[B][c][FF0000]❌ Teamcode phải là số!")
        return

    self._bot.reply(cid, type, f"[B][c][FFFF00]⚡ Đang lag teamcode {team_code}...")

    try:
        try:
            self.sock39699.sendall(self._bot.join_squad(team_code))
            time.sleep(2)
        except: pass

        
        for _ in range(700):
            try:
                self.sock39699.sendall(self._gen.lag_teelez())
                time.sleep(0.0001)
            except: pass

        
        try:
            self.sock39699.sendall(self._bot.leave_squad(0))
        except: pass

        self._bot.reply(cid, type, f"[B][c][00FF00]✔ lag xong teamcode {team_code}!")

    except Exception as e:
        self._bot.reply(cid, type, f"[B][c][FF0000]❌ Lỗi: {e}")
   elif message.startswith("/rdhai"):
    try:
        import threading, random

        parts = message.strip().split()

        if len(parts) < 3:
            return self._bot.reply(cid, type, "[B][c]/rdhai teamcode uid1 uid2 ...")

        if not parts[1].isdigit():
            return self._bot.reply(cid, type, "[B][c]Team code sai")

        team_code = int(parts[1])

        try:
            target_uids = [int(x) for x in parts[2:]]
        except:
            return self._bot.reply(cid, type, "[B][c]UID không hợp lệ")

        skin_ids = [
            914051001, 914053001, 914044001,
            914047001, 914047002, 914048001
        ]

        skin_id = random.choice(skin_ids)

        emotes = [
            909049010, 909051003, 909033002, 909041005, 909038010,
            909039011, 909040010, 909000081, 909000085, 909000063,
            909000075, 909033001, 909000090, 909000068, 909000098,
            909035007, 909037011, 909038012, 909035012, 909042008,
            909045001
        ]

        self._bot.reply(cid, type, "[B][c]Bot join team + múa...")

        def run():
            try:
                self.sock39699.send(
                    self._bot.join_squad(team_code)
                )

                __import__("time").sleep(2)

                self.sock39699.send(self._bot.play_animation(skin_id))
                __import__("time").sleep(2.5)
                self.sock39699.send(self._bot.showskin(skin_id))

                __import__("time").sleep(1.5)

                used = []

                for _ in range(18):
                    for uid in target_uids:

                        emo = random.choice([e for e in emotes if e not in used])
                        used.append(emo)

                        self.sock39699.send(
                            self._bot.play_emote(emo, [uid])
                        )

                        self.sock39699.send(
                            self._bot.play_emote(emo, [self.botid])
                        )

                        __import__("time").sleep(1)

                        if len(used) == len(emotes):
                            used.clear()

                    __import__("time").sleep(4)

                try:
                    self.sock39699.send(
                        self._bot.leave_squad(team_code)
                    )
                except:
                    pass

                self._bot.reply(cid, type, "[B][c]done /rdhai")

            except Exception as e:
                print("RDHAI ERROR:", e)

        threading.Thread(target=run, daemon=True).start()

    except Exception as e:
        self._bot.reply(cid, type, "[B][c]Lỗi /rdhai")
   elif message.startswith('/stop'):
                self.stop_actions.set()
                self.rstatus = (0, 0)
                self.ids = []
                
                self._bot.reply(cid, type, """
[B][C][FF0000]⏹️ ĐÃ DỪNG TẤT CẢ HÀNH ĐỘNG!

[FFFFFF]• Dừng múa emote
• Dừng spam
• Dừng ghost
• Dừng các hành động trong team

[00FF00]✅ Có thể sử dụng lệnh mới ngay!""")
                
                try:
                    payload = json.dumps({
                        "StickerStr": "[1=1200000001-14]",
                        "type": "Sticker"
                    })
                    self.sock39801.send(self._bot.send_object(payload, cid, type))
                except:
                    pass
                
                def reset_stop():
                    time.sleep(2)
                    self.stop_actions.clear()
                
                threading.Thread(target=reset_stop, daemon=True).start()

   elif message.startswith("/jn"):
    if self.rstatus[0] not in [0, 4]:
        self._bot.reply(cid, type, "[B][c]BANK 500 VÔ LIỀN NÈ-)))")
        return

    parts = message.replace("/jn", "").replace(":", " ").split()

    if len(parts) < 1 or not parts[0].isdigit():
        self._bot.reply(cid, type, "[B][c]/jn [teamcode]")
        return

    import threading
    import time
    import random
    import json

    team_code = int(parts[0])

    skin_ids = [
        914051001,
        914044001,
        914039001,
        914000002,
        914047002,
        914050001,
        914047001,
        914042001,
        914048001
    ]

    self.sock39801.send(
        self._bot.leave_channel(uid, None)
    )

    self.rstatus = (4, '')

    self.sock39699.send(
        self._bot.join_squad(team_code)
    )

    def auto_action():
        try:
            time.sleep(0.6)

            selected_skin = random.choice(skin_ids)
            self.sock39699.send(
                self._bot.play_animation(selected_skin)
            )
            time.sleep(3.3)

            self.sock39699.send(
                self._bot.showskin(selected_skin)
            )
            time.sleep(0.6)

            if self.botid:
                self.sock39699.send(
                    self._bot.play_emote(909054008, [int(self.botid)])
                )

        except Exception as e:
            print("AUTO ERROR:", e)

    threading.Thread(
        target=auto_action,
        daemon=True
    ).start()

    self._bot.reply(
        cid,
        type,
f"""[B][c]--------------------------------------
[00FF00]Bot Đã Join Đội Thành Công
Teamcode: {team_code}
Developer: @zanbackj
"""
    )

    # ====== GỬI STICKER ======
    try:
        sticker_data = random.choice([
            ("1200000001", random.randint(1, 24)),
            ("1200000002", random.randint(1, 15)),
            ("1200000004", random.randint(1, 13))
        ])
        payload = json.dumps({
            "StickerStr": f"[1={sticker_data[0]}-{sticker_data[1]}]",
            "type": "Sticker"
        })
        self.sock39801.send(self._bot.send_object(payload, cid, type))
    except:
        pass      
                       
   elif message.startswith("/dev"):

    payload_title = json.dumps({
        "TitleID": 905090075,
        "type": "Title"
    })
    try:
        self.sock39801.send(
            self._bot.send_object(payload_title, cid, type)
        )
    except:
        pass
    
    self._bot.reply(
        cid, type,
        "[b][c]Thông Tin Admin\n"
        "[00FFFF]Name Admin :[00FF00]=> [FFFFFF] Binh An\n"
        "[00FF00]FB:[FFFFFF] Binh An(zann)"
        "[00FF90]Thông Tin MXH\n"
        "[00FF00]TikTok:[FFFFFF] nqbinhan_\n"
        "[00FF00]Tele🔕gram:[FFFFFF] @zanbackj\n\n"
        "[00FF00]=> [FFFFFF] Ctv live bán bot\n"
"[007AFF]@[C][B][339BFF]nh[C][B][66BBFF]a[C][B][99DFF]t[C][B][CCF5FF]qu[C][B][E0FAFF]a[C][B][F0FDFF]ng[C][B][FFFFFF]2309\n"
"[007AFF]@[C][B][339BFF]ba[C][B][66BBFF]o[C][B][99DFF]l[C][B][CCF5FF]ong[C][B][E0FAFF]29[C][B][F0FDFF]05[C][B][FFFFFF]80\n"   
"[FF1493]@t[FF3AA6]o[FF5FB8]i[FF84CA]la1[FFA9DC]l[FFCEEE]con[FFE3F5]cho[FFF0FA]ngu[FFF7FD]12[FFFFFF]\n"   
    )
    
    payload_sticker = json.dumps({
        "StickerStr": "[1=1200000001-11]",
        "type": "Sticker"
    })
    try:
        self.sock39801.send(
            self._bot.send_object(payload_sticker, cid, type)
        )
    except:
        pass
   elif message.startswith("/dngau"):
    try:
        import threading, random

        parts = message.strip().split()

        if len(parts) < 3:
            return self._bot.reply(cid, type, "[B][c]/dngau teamcode uid1 uid2 ...")

        if not parts[1].isdigit():
            return self._bot.reply(cid, type, "[B][c]Team code sai")

        team_code = int(parts[1])

        try:
            target_uids = [int(x) for x in parts[2:]]
        except:
            return self._bot.reply(cid, type, "[B][c]UID không hợp lệ")

        skin_ids = [
            914051001, 914053001, 914044001,
            914047001, 914047002, 914048001
        ]

        skin_id = random.choice(skin_ids)

        emotes = [
            909000034, 909000036, 909000014,
            909000089, 909000088, 909040008,
            909051010, 909052004, 909052002,
        ]

        self._bot.reply(cid, type, "[B][c]Bot join team + múa...")

        def run():
            try:
                self.sock39699.send(
                    self._bot.join_squad(team_code)
                )

                __import__("time").sleep(2)

                self.sock39699.send(self._bot.play_animation(skin_id))
                __import__("time").sleep(2.5)
                self.sock39699.send(self._bot.showskin(skin_id))

                __import__("time").sleep(1.5)

                used = []

                for _ in range(9):
                    for uid in target_uids:

                        emo = random.choice([e for e in emotes if e not in used])
                        used.append(emo)

                        self.sock39699.send(
                            self._bot.play_emote(emo, [uid])
                        )

                        self.sock39699.send(
                            self._bot.play_emote(emo, [self.botid])
                        )

                        __import__("time").sleep(1)

                        if len(used) == len(emotes):
                            used.clear()

                    __import__("time").sleep(4)

                try:
                    self.sock39699.send(
                        self._bot.leave_squad(team_code)
                    )
                except:
                    pass

                self._bot.reply(cid, type, "[B][c]done /dngau")

            except Exception as e:
                print("DNGAU ERROR:", e)

        threading.Thread(target=run, daemon=True).start()

    except Exception as e:
        self._bot.reply(cid, type, "[B][c]Lỗi /dngau")
              
   elif message.startswith("/bye"):
    try:
        self._bot.reply(
            cid,
            type,
            "[B][c][FFFF00]Đang rời team..."
        )

        self.rstatus = (0, 0)
        self.ids.clear()
        self.running = True
        self.target_uid = None
        self.emote_target = None
        
        if self.sock39699:
            self.sock39699.send(
                self._bot.leave_squad()
            )
        __import__("time").sleep(0.3)
        
        if self.sock39801:
            self.sock39801.send(
                self._bot.leave_channel(cid, type)
            )
        
        self.stop_actions.clear()
        self.emoting = False
        
        self._bot.reply(
            cid,
            type,
            "[B][c][00FF00]Đã rời team, có thể dùng lệnh mới ngay!"
        )

    except Exception as e:
        print("Solo error:", e)
        self.rstatus = (0, 0)
        self.ids.clear()
        self.running = True
        self.stop_actions.clear()
        self.emoting = False
        self._bot.reply(
            cid,
            type,
            "[B][c][FF0000]Lỗi rời team, đã reset trạng thái!"
        )
   elif message.startswith("/bh"):
    args = message.strip().split()
    BUNDLE_LIST = {
        1: {"id": 914000002, "name": "rampage"},
        2: {"id": 914000003, "name": "hoaquy"},
        3: {"id": 914039001, "name": "acnhan"},
        4: {"id": 914042001, "name": "hoabang"},
        5: {"id": 914044001, "name": "thanma"},
        6: {"id": 914047001, "name": "naruto"},
        7: {"id": 914047002, "name": "cucquang"},
        8: {"id": 914048001, "name": "sieuhung"},
        9: {"id": 914050001, "name": "itachi"},
        10: {"id": 914051001, "name": "mongcanh"},
        11: {"id": 914053001, "name": "thienthuc"}
    }
    if len(args) < 2:
        msg = "[b][c]danh sach bundle\n\n"
        for num, b in BUNDLE_LIST.items():
            msg += f"{num}. {b['name']}\n"
        msg += "\n/bh <so>"
        self._bot.reply(cid, type, msg)
        return
    try:
        num = int(args[1])
    except:
        self._bot.reply(cid, type, "[b][c]nhap so")
        return
    if num not in BUNDLE_LIST:
        self._bot.reply(cid, type, f"[b][c]chi co 1-{len(BUNDLE_LIST)}")
        return
    target = BUNDLE_LIST[num]
    bid = target["id"]
    bname = target["name"]
    self._bot.reply(cid, type, f"[b][c]dang bien hinh {bname}")
    try:
        self.sock39699.send(self._bot.play_animation(bid))
        import threading
        def show():
            self.sock39699.send(self._bot.showskin(bid))
            self._bot.reply(cid, type, f"[b][c]bien hinh thanh cong\n{bname}")
        threading.Timer(2.2, show).start()
    except Exception as e:
        self._bot.reply(cid, type, f"[b][c]loi: {str(e)}")
           
   elif message.startswith("/ob54"):
    try:
        import time

        parts = message.strip().split()
        if len(parts) < 2:
            self._bot.reply(
                cid, type,
                "[B][C][ff0000]Sai cú pháp!\n\n"
                "[ffffff]Ví dụ:\n"
                "[00ff00]/ob54 uid1 uid2 uid3"
            )
            return

        try:
            target_uids = [int(x) for x in parts[1:6]]
        except:
            self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]UID không hợp lệ!"
            )
            return

        ob54_list = [
            909054004, 909054001, 909054002, 909054003, 909054005,
            909054006, 909054007, 909054008, 909054009, 909054010,
            909054011, 909054012, 909054013, 909054014, 909054015,
            909054016, 909054017, 909054020
        ]

        self.stop_actions.clear()

        self._bot.reply(
            cid,
            type,
            "[B][C][FFFFFF]Xin chào!\n"
            "[FFFFFF]Loại lệnh: [00ffb3]OB54 FULL\n\n"
            "[FFFFFF]TikTok Admin: [00ffff]@nqbinhan_\n"
            "[C0C0C0]Bot đang chuẩn bị bật hành động..."
        )

        self._bot.reply(
            cid,
            type,
            f"[B][C][00ff00]『 ACTIVE 』 → {len(target_uids)} UID\n"
            "[ffffff]Developer: [00fffb]@zanbackj"
        )

        for emo_id in ob54_list:
            if self.stop_actions.is_set():
                break
            if not self.sock39699:
                break

            try:
                self.sock39699.send(
                    self._bot.play_emote(
                        emo_id,
                        target_uids
                    )
                )
            except Exception as e:
                print("OB54 EMOTE ERROR:", e)

            for _ in range(50):
                if self.stop_actions.is_set():
                    break
                time.sleep(0.1)

        if self.stop_actions.is_set():
            self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]⏹️ Đã dừng theo yêu cầu!"
            )
        else:
            self._bot.reply(
                cid,
                type,
                f"[B][C][00ff00]✅ Hoàn tất OB54 cho {len(target_uids)} UID\n"
                f"[B][C][ffcc00]Developer: @zanbackj"
            )

    except Exception as e:
        self._bot.reply(
            cid,
            type,
            "[B][C][ff0000]Lỗi khi chạy /ob54"
        )
        print("OB54 CMD ERROR:", e)
   elif message.startswith("/all s7"):

    import time
    import threading

    emote_ids = [
        909040010, 909000090, 909035012,
        909038010, 909035007, 909039011,
        909000063, 909000098,
        909000081, 909000075,
        909042008, 909000068,
        909049010, 909041005,
        909033002, 909045001,
        909000085, 909051003,
    ]

    # Lấy ID và loại bỏ trùng
    ids = list(set(self.ids)) if self.ids else []

    if not ids:
        self._bot.reply(cid, type, "[B][c]❌ Không có UID trong team! Vui lòng dùng /jn trước")
        return

    self.stop_actions.clear()

    self._bot.reply(
        cid, type,
        f"[B][c]🔥 Đang múa S7 cho {len(ids)} người..."
    )

    try:
        for emo in emote_ids:
            if self.stop_actions.is_set():
                break

            try:
                self.sock39699.send(
                    self._bot.play_emote(emo, ids)
                )
            except:
                pass

            for _ in range(50):
                if self.stop_actions.is_set():
                    break
                time.sleep(0.1)

        if self.stop_actions.is_set():
            self._bot.reply(cid, type, "[B][c]⏹️ Đã dừng theo yêu cầu!")
        else:
            self._bot.reply(cid, type, "[B][c]✅ Done S7")

    except Exception as e:
        print(e)
        self._bot.reply(cid, type, "[B][c]❌ Lỗi khi múa S7")
                    
   elif message.startswith("/all rd s7"):

    import time, random

    emote_ids = [
        909040010, 909000090, 909035012,
        909038010, 909035007, 909039011,
        909000063, 909000098,
        909000081, 909000075,
        909042008, 909000068, 
        909049010, 909041005,
        909033002, 909045001,
        909000085, 909051003,
    ]

    ids = list(set(self.ids)) if self.ids else []

    if not ids:
        self._bot.reply(cid, type, "[B][c]❌ Không có UID trong team! Vui lòng dùng /jn trước")
        return

    self.stop_actions.clear()

    self._bot.reply(
        cid, type,
        f"[B][c]🎲 Đang random S7 cho {len(ids)} người..."
    )

    try:
        # Random 1 emote cho mỗi UID
        for uid in ids:
            if self.stop_actions.is_set():
                break

            emo = random.choice(emote_ids)
            
            try:
                self.sock39699.send(
                    self._bot.play_emote(emo, [uid])
                )
            except:
                pass

            for _ in range(30):
                if self.stop_actions.is_set():
                    break
                time.sleep(0.1)

        if self.stop_actions.is_set():
            self._bot.reply(cid, type, "[B][c]⏹️ Đã dừng theo yêu cầu!")
        else:
            self._bot.reply(cid, type, "[B][c]✅ Done Random S7")

    except Exception as e:
        print("EMOTE ERROR:", e)
        self._bot.reply(cid, type, "[B][c]❌ Lỗi khi random S7")

   elif message.startswith("/all cute"):

    import time

    emote_ids = [
        909039014, 909040006, 909041009,
        909041015, 909042004, 909042009, 
        909042012, 909043001, 909044004,
        909045011, 909043009, 909048014
    ]

    ids = list(set(self.ids)) if self.ids else []

    if not ids:
        self._bot.reply(cid, type, "[B][c]❌ Không có UID trong team! Vui lòng dùng /jn trước")
        return

    self.stop_actions.clear()

    self._bot.reply(
        cid, type,
        f"[B][c]😊 Đang múa hd cute cho {len(ids)} người..."
    )

    try:
        for emo in emote_ids:
            if self.stop_actions.is_set():
                break

            try:
                self.sock39699.send(
                    self._bot.play_emote(emo, ids)
                )
            except:
                pass

            for _ in range(30):
                if self.stop_actions.is_set():
                    break
                time.sleep(0.1)

        if self.stop_actions.is_set():
            self._bot.reply(cid, type, "[B][c]⏹️ Đã dừng theo yêu cầu!")
        else:
            self._bot.reply(cid, type, "[B][c]✅ Done CUTE")

    except Exception as e:
        print("EMOTE ERROR:", e)
        self._bot.reply(cid, type, "[B][c]❌ Lỗi khi múa CUTE")

   elif message.startswith("/all ngau"):

    import time

    emote_ids = [
        909000034, 909000036, 909000014,
        909000089, 909000088, 909040008,
        909051010, 909052004, 909052002,
    ]

    ids = list(set(self.ids)) if self.ids else []

    if not ids:
        self._bot.reply(cid, type, "[B][c]❌ Không có UID trong team! Vui lòng dùng /jn trước")
        return

    self.stop_actions.clear()

    self._bot.reply(
        cid, type,
        f"[B][c]😎 Đang múa hd ngầu cho {len(ids)} người..."
    )

    try:
        for emo in emote_ids:
            if self.stop_actions.is_set():
                break

            try:
                self.sock39699.send(
                    self._bot.play_emote(emo, ids)
                )
            except:
                pass

            for _ in range(30):
                if self.stop_actions.is_set():
                    break
                time.sleep(0.1)

        if self.stop_actions.is_set():
            self._bot.reply(cid, type, "[B][c]⏹️ Đã dừng theo yêu cầu!")
        else:
            self._bot.reply(cid, type, "[B][c]✅ Done NGẦU")

    except Exception as e:
        print("EMOTE ERROR:", e)
        self._bot.reply(cid, type, "[B][c]❌ Lỗi khi múa NGẦU")

   elif message.startswith("/all co"):

    import time

    emote_ids = [
        909000020, 909000021, 909000027, 909000008,
        909000011, 909000012, 909042007, 909000040,
        909000016, 909000029, 909000037, 909000022,
        909000043, 909000061, 909000066,
    ]

    ids = list(set(self.ids)) if self.ids else []

    if not ids:
        self._bot.reply(cid, type, "[B][c]❌ Không có UID trong team! Vui lòng dùng /jn trước")
        return

    self.stop_actions.clear()

    self._bot.reply(
        cid, type,
        f"[B][c]🎭 Đang múa hd cổ cho {len(ids)} người..."
    )

    try:
        for emo in emote_ids:
            if self.stop_actions.is_set():
                break

            try:
                self.sock39699.send(
                    self._bot.play_emote(emo, ids)
                )
            except:
                pass

            for _ in range(30):
                if self.stop_actions.is_set():
                    break
                time.sleep(0.1)

        if self.stop_actions.is_set():
            self._bot.reply(cid, type, "[B][c]⏹️ Đã dừng theo yêu cầu!")
        else:
            self._bot.reply(cid, type, "[B][c]✅ Done hd cổ")

    except Exception as e:
        print("EMOTE ERROR:", e)
        self._bot.reply(cid, type, "[B][c]❌ Lỗi khi múa CỔ")

   elif message.startswith("/all hai"):

    import time

    emote_ids = [
        909000064, 909000132, 909000150,
        909038010, 909035007, 909039011,
        909034004, 909034005,
        909033003, 909041011,
        909042018, 909044007,
        909044016, 909045008,
        909049005, 909050017,
        909051006, 909051009,
    ]

    ids = list(set(self.ids)) if self.ids else []

    if not ids:
        self._bot.reply(cid, type, "[B][c]❌ Không có UID trong team! Vui lòng dùng /jn trước")
        return

    self.stop_actions.clear()

    self._bot.reply(
        cid, type,
        f"[B][c]😂 Đang múa hd hài cho {len(ids)} người..."
    )

    try:
        for emo in emote_ids:
            if self.stop_actions.is_set():
                break

            try:
                self.sock39699.send(
                    self._bot.play_emote(emo, ids)
                )
            except:
                pass

            for _ in range(30):
                if self.stop_actions.is_set():
                    break
                time.sleep(0.1)

        if self.stop_actions.is_set():
            self._bot.reply(cid, type, "[B][c]⏹️ Đã dừng theo yêu cầu!")
        else:
            self._bot.reply(cid, type, "[B][c]✅ Done HÀI")

    except Exception as e:
        print("EMOTE ERROR:", e)
        self._bot.reply(cid, type, "[B][c]❌ Lỗi khi múa HÀI")
                
   elif message.startswith("/xlz"):
    try:
        parts = message.split()

        emotes = {
            "m60": 909051003,
            "p90": 909049010,
            "cgk": 909042008,
            "ak47": 909000063,
            "m1014": 909000081,
            "gloza": 909041005,
            "mp40": 909040010,
            "scar": 909000068,
            "mp5": 909033002,
            "ump": 909000098,
            "xm8": 909000085,
            "famas": 909000090,
            "m1887": 909035007,
            "m1014v2": 909039011,
            "thompson": 909038010,
            "parafal": 909045001,
            "g18": 909038012,
            "m4a1": 909039011,
            "aug": 909054004,
        }

        if len(parts) == 2 and parts[1].lower() == "list":
            self._bot.reply(cid, type, f"[B][C][00FF00]Súng 7: [FFFFFF]{', '.join(emotes.keys())}\n[B][C][00FF00]Dùng: [FFFFFF]/xlz uid1 uid2 [tên]")
            return

        if len(parts) < 3:
            self._bot.reply(cid, type, "[B][C][FF0000]Dùng: /xlz uid1 uid2 [tên súng]")
            return

        emo_name = parts[-1].lower()
        targets = []

        for x in parts[1:-1]:
            if x.isdigit():
                targets.append(int(x))

        if not targets:
            self._bot.reply(cid, type, "[B][C][FF0000]UID không hợp lệ")
            return

        if emo_name not in emotes:
            self._bot.reply(cid, type, f"[B][C][FF0000]Không có súng '{emo_name}'\n[B][C][00FF00]/xlz list để xem")
            return

        emo_id = emotes[emo_name]
        self.sock39699.send(self._bot.play_emote(emo_id, targets))
        self._bot.reply(cid, type, f"[B][C][00FF00]✅ Đã múa {emo_name.upper()} cho {len(targets)} UID")

    except Exception as e:
        self._bot.reply(cid, type, f"[B][C][FF0000]Lỗi: {e}")
                
   elif message.startswith("/full"):
    try:
        import time

        parts = message.strip().split()

        if len(parts) < 2:
            self._bot.reply(
                cid, type,
                "[B][C][ff0000]Sai cú pháp!\n\n"
                "[ffffff]Ví dụ:\n"
                "[00ff00]/full uid1 uid2 uid3"
            )
            return

        try:
            target_uids = [int(x) for x in parts[1:6]]
        except:
            self._bot.reply(cid, type, "[B][C][ff0000]UID không hợp lệ!")
            return

        self.stop_actions.clear()

        default_emotes = [
        ]

        self._bot.reply(
            cid, type,
            "[B][C][FFFFFF]Xin chào!\n"
            "[FFFFFF]Loại lệnh: [00ffb3]FULL SÚNG 7\n\n"
            "[FFFFFF]TikTok Admin: [00ffff]@nqbinhan_\n"
            "[C0C0C0]Bot đang tiến hành bật hành động LV7..."
        )

        self._bot.reply(
            cid, type,
            f"[B][C][00ff00]『 ACTIVE 』 → {len(target_uids)} UID\n"
            "[ffffff]Telegram: [00fffb]@zanbackj"
        )

        for emo_id in default_emotes:

            if self.stop_actions.is_set():
                break

            if not self.sock39699:
                break

            self.sock39699.send(
                self._bot.play_emote(emo_id, target_uids)
            )

            for _ in range(68):

                if self.stop_actions.is_set():
                    break

                time.sleep(0.1)

        if self.stop_actions.is_set():

            self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]⏹️ Đã dừng theo yêu cầu!"
            )

        else:

            self._bot.reply(
                cid,
                type,
                "[B][C][00ff00]✅ Đã hoàn thành FULL!"
            )

    except Exception as e:
        self._bot.reply(
            cid,
            type,
            "[B][C][ff0000]Lỗi khi chạy /full"
        )
        print("N CMD ERROR:", e)   
    
   elif message.startswith("/abc"):
    try:
        import time

        parts = message.strip().split()

        if len(parts) < 2:
            self._bot.reply(
                cid, type,
                "[B][C][ff0000]Sai cú pháp!\n\n"
                "[ffffff]Ví dụ:\n"
                "[00ff00]/abc uid1 uid2\n"                
            )
            return

        try:
            target_uids = [int(x) for x in parts[1:]] 
        except:
            self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]UID không hợp lệ!"
            )
            return

        if not target_uids:
            self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]Cần ít nhất 1 UID!"
            )
            return

        if self.botid:
            try:
                bot_uid = int(self.botid)
                if bot_uid not in target_uids:
                    target_uids.append(bot_uid)
            except:
                pass

        default_emotes = [
            909049010, 909051003, 909033002, 909041005, 909038010,
            909039011, 909040010, 909000081, 909000085, 909000063,
            909000075, 909033001, 909000090, 909000068, 909000098,
            909035007, 909037011, 909038012, 909035012, 909042008,
            909045001, 909054004
        ]

        self.stop_actions.clear()

        self._bot.reply(
            cid,
            type,
            "[B][C][FFFFFF]Xin chào!\n"
            "[FFFFFF]Loại lệnh: [00ffb3]FULL SÚNG 7\n\n"
            "[FFFFFF]TikTok Admin: [00ffff]@nqbinhan_\n"
            "[C0C0C0]Bot đang chuẩn bị bật hành động LV7..."
        )

        self._bot.reply(
            cid, type,
            f"[B][C][00ff00]『 ACTIVE 』 → {len(target_uids)} UID\n"
            "[ffffff]Telegram: [00fffb]@zanbackj"
        )

        total = len(default_emotes)
        for idx, emo_id in enumerate(default_emotes, 1):

            if self.stop_actions.is_set():
                break

            if not self.sock39699:
                break

            self._bot.reply(
                cid,
                type,
                f"[B][C][00ff00]🎭 Đang thực hiện emote {idx}/{total}"
            )

            try:
                self.sock39699.send(
                    self._bot.play_emote(
                        emo_id,
                        target_uids
                    )
                )
            except Exception as e:
                print("ABC EMOTE ERROR:", e)

            for _ in range(68):
                if self.stop_actions.is_set():
                    break
                time.sleep(0.1)

        if self.stop_actions.is_set():
            self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]⏹️ Đã dừng theo yêu cầu!"
            )
        else:
            self._bot.reply(
                cid,
                type,
                f"[B][C][00ff00]✅ Hoàn tất full súng 7 cho {len(target_uids)} UID\n"
                f"[B][C][ffcc00]Developer: @zanbackj"
            )

    except Exception as e:
        self._bot.reply(
            cid,
            type,
            f"[B][C][ff0000]Lỗi: {str(e)[:50]}"
        )
        print("VIP CMD ERROR:", e)
        
   elif message.startswith("/hw"):
    try:
        import threading, random

        parts = message.strip().split()

        if len(parts) < 3:
            return self._bot.reply(cid, type, "[B]/hw teamcode uid1 uid2 ...")

        if not parts[1].isdigit():
            return self._bot.reply(cid, type, "[B]Team code sai")

        team_code = int(parts[1])

        try:
            target_uids = [int(x) for x in parts[2:]]
        except:
            return self._bot.reply(cid, type, "[B]UID không hợp lệ")

        skin_ids = [
            914051001, 914053001, 914044001,
            914047001, 914047002, 914048001
        ]

        skin_id = random.choice(skin_ids)

        emotes = [
            909000020, 909000021, 909000027, 909000008,
            909000011, 909000012, 909042007, 909000040,
            909000016, 909000029, 909000037,909000022,
            909000043, 909000061, 909000066,
        ]

        msg = f"""[B][C][FFFFFF]Xin Chào!
[FFFFFF]Thể Loại Lệnh: [FFD700]Hành Động Cổ 18

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã join nhóm thành công đang tiến hành hành động cổ 18 để phong bạt!"""

        self._bot.reply(cid, type, msg)

        def run():
            try:
                self.sock39699.send(
                    self._bot.join_squad(team_code)
                )

                __import__("time").sleep(2)

                self.sock39699.send(self._bot.play_animation(skin_id))
                __import__("time").sleep(2.5)
                self.sock39699.send(self._bot.showskin(skin_id))

                __import__("time").sleep(1.5)

                used = []

                for _ in range(18):
                    for uid in target_uids:

                        emo = random.choice([e for e in emotes if e not in used])
                        used.append(emo)

                        self.sock39699.send(
                            self._bot.play_emote(emo, [uid])
                        )

                        self.sock39699.send(
                            self._bot.play_emote(emo, [self.botid])
                        )

                        __import__("time").sleep(1)

                        if len(used) == len(emotes):
                            used.clear()

                    __import__("time").sleep(4)

                try:
                    self.sock39699.send(
                        self._bot.leave_squad(team_code)
                    )
                except:
                    pass

                done_msg = f"""[B][C][FFFFFF]Thành Công!
[FFFFFF]Thể Loại Lệnh: [FFD700]Hành Động Cổ 18

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã hành động cổ 18 thành công và sẽ rời đội ngay!"""

                self._bot.reply(cid, type, done_msg)

            except Exception as e:
                print("HW ERROR:", e)

        threading.Thread(target=run, daemon=True).start()

    except Exception as e:
        self._bot.reply(cid, type, "[B]Lỗi /hw")

   elif message.startswith("/rw"):
    try:
        import threading, random

        parts = message.strip().split()

        if len(parts) < 3:
            return self._bot.reply(cid, type, "[B]/rw teamcode uid1 uid2 ...")

        if not parts[1].isdigit():
            return self._bot.reply(cid, type, "[B]Team code sai")

        team_code = int(parts[1])

        try:
            target_uids = [int(x) for x in parts[2:]]
        except:
            return self._bot.reply(cid, type, "[B]UID không hợp lệ")

        skin_ids = [
            914051001, 914053001, 914044001,
            914047001, 914047002, 914048001
        ]

        skin_id = random.choice(skin_ids)

        emotes = [
            909000064, 909000132, 909000150,
            909038010, 909035007, 909039011,
            909034004, 909034005,
            909033003, 909041011,
            909042018, 909044007,
            909044016, 909045008,
            909049005, 909050017,
            909051006, 909051009,
        ]

        msg = f"""[B][C][FFFFFF]Xin Chào!
[FFFFFF]Thể Loại Lệnh: [FF4500]Hành Động Hài 18

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã join nhóm thành công đang tiến hành hành động hài 18 để phong bạt!"""

        self._bot.reply(cid, type, msg)

        def run():
            try:
                self.sock39699.send(
                    self._bot.join_squad(team_code)
                )

                __import__("time").sleep(2)

                self.sock39699.send(self._bot.play_animation(skin_id))
                __import__("time").sleep(2.5)
                self.sock39699.send(self._bot.showskin(skin_id))

                __import__("time").sleep(1.5)

                used = []

                for _ in range(18):
                    for uid in target_uids:

                        emo = random.choice([e for e in emotes if e not in used])
                        used.append(emo)

                        self.sock39699.send(
                            self._bot.play_emote(emo, [uid])
                        )

                        self.sock39699.send(
                            self._bot.play_emote(emo, [self.botid])
                        )

                        __import__("time").sleep(1)

                        if len(used) == len(emotes):
                            used.clear()

                    __import__("time").sleep(4)

                try:
                    self.sock39699.send(
                        self._bot.leave_squad(team_code)
                    )
                except:
                    pass

                done_msg = f"""[B][C][FFFFFF]Thành Công!
[FFFFFF]Thể Loại Lệnh: [FF4500]Hành Động Hài 18

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã hành động hài 18 thành công và sẽ rời đội ngay!"""

                self._bot.reply(cid, type, done_msg)

            except Exception as e:
                print("RW ERROR:", e)

        threading.Thread(target=run, daemon=True).start()

    except Exception as e:
        self._bot.reply(cid, type, "[B]Lỗi /rw")
   elif message.startswith("/spvip"):
    try:
        import time, random, threading

        parts = message.strip().split()

        if len(parts) < 2:
            self._bot.reply(
                cid, type,
                "[B][C][ff0000]Sai cú pháp!\n\n"
                "[ffffff]Ví dụ:\n"
                "[00ff00]/spvip uid1 uid2 uid3"
            )
            return

        try:
            target_uids = [int(x) for x in parts[1:6]]
        except:
            self._bot.reply(
                cid, type,
                "[B][C][ff0000]UID không hợp lệ!"
            )
            return

        emote_ids = [
            909049010, 909051003, 909033002, 909000002, 909000034,
            909039011, 909000036, 909000081, 909000085, 909035007,
            909033001, 909000090, 909000098, 909045001                   
        ]

        selected_emo = random.choice(emote_ids)

        self.stop_actions.clear()

        self._bot.reply(
            cid,
            type,
            "[B][C][00ff00]🔥 Đã bật SPAM VIP!\n"
            "[ffffff]• Spam 1 hành động liên tục\n"
            "[ffffff]• Dùng /stop để dừng"
        )

        def spam_vip():

            while not self.stop_actions.is_set():

                try:

                    if not self.sock39699:
                        break

                    self.sock39699.send(
                        self._bot.play_emote(
                            selected_emo,
                            target_uids
                        )
                    )

                    time.sleep(0.1)

                except Exception as e:
                    print("SPVIP ERR:", e)
                    break

            self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]⏹️ Đã dừng SPAM VIP!"
            )

        threading.Thread(
            target=spam_vip,
            daemon=True
        ).start()

    except Exception as e:
        print("SPVIP CMD ERR:", e)

        self._bot.reply(
            cid,
            type,
            "[B][C][ff0000]Lỗi khi chạy /spvip"
        )
   elif message.startswith("/war"):
    parts = message.strip().split(maxsplit=2)
    if len(parts) < 3:
     self._bot.reply(cid, type, "[B][c]Dùng: /war [teamcode] [tên]"); return
    
    try:
     tcode = int(parts[1])
    except:
     self._bot.reply(cid, type, "[B][c][FF4444]Teamcode phải là số!"); return
    
    target = parts[2].strip()
    
    import random
    war_msgs = [
     f"{target} b[c]ắ[c]n ng[c]u vcl =)))=)))",
     f"{target} tu[c]ất 11 vs anh nè  =)))=)))",
     f"{target} như gà mà dám lên rank =)))=)))",
     f"{target} làm gì có cảnh bố m bá v[c]c[c]l =)))=)))",
     f"{target} về nhà mà chơi cho lành =)))=)))",
    ]
    msg = random.choice(war_msgs)
    
    self.rstatus = (1, msg)
    self.sock39699.send(self._bot.join_squad(tcode))
    payload = json.dumps({"StickerStr": "[1=1200000002-11]", "type": "Sticker"})
    self.sock39801.send(self._bot.send_object(payload, cid, type))
    return True
   
   elif message.startswith("/zlv"):
    try:
        import threading, random

        parts = message.strip().split()

        if len(parts) < 3:
            return self._bot.reply(cid, type, "[B]/zlv teamcode uid1 uid2 ...")

        if not parts[1].isdigit():
            return self._bot.reply(cid, type, "[B]Team code sai")

        team_code = int(parts[1])

        try:
            target_uids = [int(x) for x in parts[2:]]
        except:
            return self._bot.reply(cid, type, "[B]UID không hợp lệ")

        skin_ids = [
            914051001, 914053001, 914044001,
            914047001, 914047002, 914048001
        ]

        skin_id = random.choice(skin_ids)

        emotes = [
            909040010, 909000090, 909035012,
        909038010, 909035007, 909039011,
        909000063, 909000098,
        909000081, 909000075,
        909042008, 909000068, 
        909049010, 909041005,
        909033002, 909045001,
        909000085, 909051003,
        ]

        msg = f"""[B][C][FFFFFF]Xin Chào!
[FFFFFF]Thể Loại Lệnh: [FF00FF]Zlv

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã join nhóm thành công đang tiến hành zlv để phong bạt!"""

        self._bot.reply(cid, type, msg)

        def run():
            try:
                self.sock39699.send(
                    self._bot.join_squad(team_code)
                )

                __import__("time").sleep(2)

                self.sock39699.send(self._bot.play_animation(skin_id))
                __import__("time").sleep(2.5)
                self.sock39699.send(self._bot.showskin(skin_id))

                __import__("time").sleep(1.5)

                used = []

                for _ in range(18):
                    for uid in target_uids:

                        emo = random.choice([e for e in emotes if e not in used])
                        used.append(emo)

                        self.sock39699.send(
                            self._bot.play_emote(emo, [uid])
                        )

                        self.sock39699.send(
                            self._bot.play_emote(emo, [self.botid])
                        )

                        __import__("time").sleep(1)

                        if len(used) == len(emotes):
                            used.clear()

                    __import__("time").sleep(4)

                try:
                    self.sock39699.send(
                        self._bot.leave_squad(team_code)
                    )
                except:
                    pass

                done_msg = f"""[B][C][FFFFFF]Thành Công!
[FFFFFF]Thể Loại Lệnh: [FF00FF]Zlv

[FFFFFF]TikTok Admin: [FF1493]@[FF69B4]nqbinhan_
[C0C0C0]Bot đã zalo ver 18 thành công và sẽ rời đội ngay!"""

                self._bot.reply(cid, type, done_msg)

            except Exception as e:
                print("ZLV ERROR:", e)

        threading.Thread(target=run, daemon=True).start()

    except Exception as e:
        self._bot.reply(cid, type, "[B]Lỗi /zlv")
        
   elif message.startswith("/cte"):
    try: 
        import time

        parts = message.strip().split()

        if len(parts) < 2:
            self._bot.reply(
                cid, type,
                "[B][C][ff0000]Sai cú pháp!\n\n"
                "[ffffff]Ví dụ:\n"
                "[00ff00]/cte uid1 uid2 uid3"
            )
            return

        try:
            target_uids = [int(x) for x in parts[1:]]
        except:
            self._bot.reply(cid, type, "[B][C][ff0000]UID không hợp lệ!")
            return

        if self.botid:
            try:
                bot_uid = int(self.botid)
                if bot_uid not in target_uids:
                    target_uids.append(bot_uid)
            except:
                pass

        default_emotes = [
            909042017, 909042012, 909043009, 909044004,
            909045002, 909045004, 909042006, 909040001, 
            909040013, 909036002, 909037001, 909045003, 
            909042006, 909041015, 909039014, 909039010, 
            909039008, 909039003, 909037001, 909034008, 
            909034005, 909035001, 909000150, 909000134, 
            909000129, 909000095, 909000055, 909000010, 
            909000045
        ]

        self.stop_actions.clear()

        self._bot.reply(
            cid, type,
            "[B][C][FFFFFF]Xin chào!\n"
            "[FFFFFF]Loại lệnh: [00ffb3]HÀNH ĐỘNG CTE\n\n"
            "[FFFFFF]TikTok Admin: [00ffff]@nqbinhan_\n"
            "[C0C0C0]Bot đang tiến hành bật hành động CTE..."
        )

        self._bot.reply(
            cid, type,
            f"[B][C][00ff00]『 ACTIVE 』 → {len(target_uids)} UID\n"
            "[ffffff]Telegram: [00fffb]@zanbackj"
        )

        for emo_id in default_emotes:

            if self.stop_actions.is_set():
                break

            if not self.sock39699:
                break

            self.sock39699.send(
                self._bot.play_emote(emo_id, target_uids)
            )

            for _ in range(68):

                if self.stop_actions.is_set():
                    break

                time.sleep(0.1)

        if self.stop_actions.is_set():

            self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]⏹️ Đã dừng theo yêu cầu!"
            )

        else:

            self._bot.reply(
                cid,
                type,
                "[B][C][00ff00]✅ Đã hoàn thành CTE!"
            )

    except Exception as e:
        self._bot.reply(
            cid, type,
            "[B][C][ff0000]Lỗi khi chạy /cte"
        )
        print("N CMD ERROR:", e)

   elif message.startswith("/hdc"):
    try:
        import time

        parts = message.strip().split()

        if len(parts) < 2:
            self._bot.reply(
                cid, type,
                "[B][C][ff0000]Sai cú pháp!\n\n"
                "[ffffff]Ví dụ:\n"
                "[00ff00]/hdc uid1 uid2 uid3"
            )
            return

        try:
            target_uids = [int(x) for x in parts[1:]]
        except:
            self._bot.reply(cid, type, "[B][C][ff0000]UID không hợp lệ!")
            return

        if self.botid:
            try:
                bot_uid = int(self.botid)
                if bot_uid not in target_uids:
                    target_uids.append(bot_uid)
            except:
                pass

        default_emotes = [
            909000020, 909000021, 909000027, 909000008,
            909000011, 909000012, 909042007, 909000040
        ]

        self.stop_actions.clear()

        self._bot.reply(
            cid, type,
            "[B][C][FFFFFF]Xin chào!\n"
            "[FFFFFF]Loại lệnh: [00ffb3]HÀNH ĐỘNG CỔ\n\n"
            "[FFFFFF]TikTok Admin: [00ffff]@nqbinhan_\n"
            "[C0C0C0]Bot đang tiến hành bật hành động cổ..."
        )

        self._bot.reply(
            cid, type,
            f"[B][C][00ff00]『 ACTIVE 』 → {len(target_uids)} UID\n"
            "[ffffff]Telegram: [00fffb]@zanbackj"
        )

        for emo_id in default_emotes:

            if self.stop_actions.is_set():
                break

            if not self.sock39699:
                break

            self.sock39699.send(
                self._bot.play_emote(emo_id, target_uids)
            )

            for _ in range(70):

                if self.stop_actions.is_set():
                    break

                time.sleep(0.1)

        if self.stop_actions.is_set():

            self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]⏹️ Đã dừng theo yêu cầu!"
            )

        else:

            self._bot.reply(
                cid,
                type,
                "[B][C][00ff00]✅ Đã hoàn thành HDC!"
            )

    except Exception as e:
        self._bot.reply(
            cid, type,
            "[B][C][ff0000]Lỗi khi chạy /hdc"
        )
        print("N CMD ERROR:", e)
   elif message.startswith("/ngau"):
    try:
        import time

        parts = message.strip().split()

        if len(parts) < 2:
            self._bot.reply(
                cid, type,
                "[B][C][ff0000]Sai cú pháp!\n\n"
                "[ffffff]Ví dụ:\n"
                "[00ff00]/ngau uid1 uid2 uid3"
            )
            return

        try:
            target_uids = [int(x) for x in parts[1:]]
        except:
            self._bot.reply(cid, type, "[B][C][ff0000]UID không hợp lệ!")
            return

        if self.botid:
            try:
                bot_uid = int(self.botid)
                if bot_uid not in target_uids:
                    target_uids.append(bot_uid)
            except:
                pass

        default_emotes = [
            909051012, 909050009, 909041002, 909043002,
            909041004, 909041003, 909041001, 909042007
        ]

        self.stop_actions.clear()

        self._bot.reply(
            cid, type,
            "[B][C][FFFFFF]Xin chào!\n"
            "[FFFFFF]Loại lệnh: [00ffb3]Hành Động ngầu\n\n"
            "[FFFFFF]TikTok Admin: [00ffff]@nqbinhan_\n"
            "[C0C0C0]Bot đang tiến hành bật hành động Ngầu..."
        )

        self._bot.reply(
            cid, type,
            f"[B][C][00ff00]『 ACTIVE 』 → {len(target_uids)} UID\n"
            "[ffffff]Telegram: [00fffb]@zanbackj"
        )

        for emo_id in default_emotes:

            if self.stop_actions.is_set():
                break

            if not self.sock39699:
                break

            self.sock39699.send(
                self._bot.play_emote(emo_id, target_uids)
            )

            for _ in range(70):

                if self.stop_actions.is_set():
                    break

                time.sleep(0.1)

        if self.stop_actions.is_set():

            self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]⏹️ Đã dừng theo yêu cầu!"
            )

        else:

            self._bot.reply(
                cid,
                type,
                "[B][C][00ff00]✅ Đã hoàn thành!"
            )

    except Exception as e:
        self._bot.reply(
            cid, type,
            "[B][C][ff0000]Lỗi khi chạy /ngau"
        )
        print("N CMD ERROR:", e)
                            
   elif message.startswith("/5"):
                if len(message) > 3:
                    self.GenSquads(5, cid, message.split()[1], type, name)
                    return
                self.GenSquads(5, cid, uid, type, name)

   elif message.startswith("/6"):
    if len(message) > 3: self.GenSquads(6, cid, message.split()[1], type); return
    self.GenSquads(6, cid, uid, type)

   elif message.startswith("/status"):
    text = get_user_input(str(message))
    if ":" in text: self._bot.reply(cid, type, text); return
    self._bot.reply(cid, type, "[B][c]Đang lấy thông tin..")
    self.sock39699.send(self._bot.get_history(message.split()[1]))
    time.sleep(1)
    if self.playerstatus:
     data = get_player_status(self.playerstatus)
     form = self.format_status_message(data, message.split()[1])
     self._bot.reply(cid, type, form)
    else: self._bot.reply(cid, type, "null")

   elif message.startswith("/rinv"):
    msg = get_user_input(str(message))
    if ":" in msg: self._bot.reply(cid, type, msg); return
    threading.Thread(target=self.GenSpamRoom, args=(msg,)).start()
    time.sleep(2)
    if self.roomid:
     self._bot.reply(cid, type, "[B][c]Đang spam '%s' tới phòng '%s'" %
      (msg[:5], self.roomid)
     )
    else: self._bot.reply(cid, type, "PLAYER IS NOT ON ROOM")

   elif message.startswith(('/s1', '/s2', '/s3', '/s4', '/s5')):
    try:
        cmd = message.split()[0].lower()
        parts = message.strip().split()
        
        if len(parts) < 2:
            error_msg = f"[B][C][FF0000]❌ Usage: {cmd} (uid)\nVí dụ: {cmd} 123456789"
            self._bot.reply(cid, type, error_msg)
            return
        
        target_uid = parts[1]
        if not target_uid.isdigit():
            self._bot.reply(cid, type, f"[B][C][FF0000]❌ Please write a valid player ID!")
            return
        
        badge_value = self.BADGE_VALUES.get(cmd, 1048576)
        
        initial_msg = f"[B][C][1E90FF]🌀 spam =)) {target_uid}..."
        self._bot.reply(cid, type, initial_msg)
        
        # Leave current squad
        if self.sock39699 and self._bot:
            leave_packet = self._bot.leave_squad(0)
            self.sock39699.sendall(leave_packet)
            time.sleep(0.3)
        
        # Spam join requests with badge
        for i in range(30): 
            if self.sock39699 and self._bot:
                join_packet = self._bot.request_join_squad(int(target_uid))
                self.sock39699.sendall(join_packet)
                print(f"✅ Đang Spam Lệnh {cmd} yêu cầu#{i+1} với tích: {badge_value}")
                time.sleep(0.1)
        
        success_msg = f"[B][C][FFFFFF]Thành Công Spam Mời+Tích\n"
        self._bot.reply(cid, type, success_msg)
        
        time.sleep(0.5)
        # Cleanup
        if self.sock39699 and self._bot:
            leave_packet = self._bot.leave_squad(0)
            self.sock39699.sendall(leave_packet)
            
    except Exception as e:
        error_msg = f"[B][C][FF0000]❌ Error in {cmd}: {str(e)[:30]}\n"
        self._bot.reply(cid, type, error_msg)
        print(f"Badge command error: {e}")

   elif message.startswith("@share"):

    try:
        import threading

        parts = message.strip().split()

        if len(parts) < 2:

            return self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]❌ Sai cú pháp\n"
                "[B][C][00ff00]Ví dụ: @share uid"
            )

        if not parts[1].isdigit():

            return self._bot.reply(
                cid,
                type,
                "[B][C][ff0000]❌ UID không hợp lệ"
            )

        target_uid = int(parts[1])

        self._bot.reply(
            cid,
            type,
            f"[B][C][00ff00]📦 Đang gửi request xin đồ tới UID:\n"
            f"[B][C][ffffff]{target_uid}"
        )

        def do_share():

            try:

                if self.sock39699 is None:

                    return self._bot.reply(
                        cid,
                        type,
                        "[B][C][ff0000]❌ Socket disconnected"
                    )

                __import__("time").sleep(1)

                packet = self._bot.ask_for_skin(target_uid)

                self.sock39699.send(packet)

                __import__("time").sleep(1)

                self._bot.reply(
                    cid,
                    type,
                    f"[B][C][00ff00]✅ Đã gửi yêu cầu xin đồ tới:\n"
                    f"[B][C][ffffff]{target_uid}"
                )

            except Exception as e:

                print("ASK SKIN ERR:", e)

                self._bot.reply(
                    cid,
                    type,
                    f"[B][C][ff0000]❌ Xin đồ thất bại\n"
                    f"[ffffff]{e}"
                )

        threading.Thread(
            target=do_share,
            daemon=True
        ).start()

    except Exception as e:

        print("SHARE CMD ERR:", e)

        self._bot.reply(
            cid,
            type,
            "[B][C][ff0000]❌ Lỗi command @share"
        )
   elif message.startswith("/share"):
    self.sock39699.send(self._bot.ask_for_skin(uid))
    self._bot.reply(cid, type, f"[B][c]📦 Đã gửi yêu cầu xin đồ từ UID {uid}")
   elif message.startswith("/mute"):
    msg = get_user_input(message)
    if ":" in msg: self._bot.reply(cid, type, msg); return
    self.sock39801.send(self._bot.join_channel(msg, "0_GRINGAY", None))
    self._bot.reply(cid, type, "[B][c]Đã khoá mõm '%s'" % msg)

   elif message.startswith("/unmute"):
    msg = get_user_input(message)
    if ":" in msg: self._bot.reply(cid, type, msg); return
    self.sock39801.send(self._bot.leave_channel(msg, None))
    self._bot.reply(cid, type, "[B][c]OK")
        
   elif message.startswith("/ai"): 
    msg = message[4:].strip()  
     
    if not msg: 
        self._bot.reply(cid, type, "⚠️ Mày định chửi không khí à? Nhập nội dung vào!") 
        return 
 
    if ":" in msg:  
        self._bot.reply(cid, type, msg) 
        return 
 
    try: 
        import urllib3 
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) 
 
        api_urlchui = "https://quanghauapiaichui.x10.mx/" 
         
        response = requests.get( 
            api_urlchui,  
            params={"noidung": msg},  
            timeout=25,  
            verify=False  
        ) 
         
        if response.status_code == 200: 
            result = response.text.strip() 
            final_msg = result if result else "Nó chửi gắt quá t nghe không kịp!" 
        else: 
            final_msg = f"❌ API đang bận (Lỗi {response.status_code})" 
             
        self._bot.reply(cid, type, final_msg) 
         
    except requests.exceptions.Timeout: 
        self._bot.reply(cid, type, "❌ Server chửi chậm quá, chắc đang lấy hơi!") 
    except Exception as e: 
        self._bot.reply(cid, type, f"❌ Lỗi:")
                           
   elif message.startswith("/blikes"):
    msg = get_user_input(message)
    if ":" in msg:
        self._bot.reply(cid, type, msg)
        return
    self._bot.reply(
        cid,
        type,
        f"[B][c][00FFFF]Đang buff likes cho UID: [FFFFFF]{msg}..."
    )
    result = send_likes(msg)
    self._bot.reply(cid, type, result)
    
   elif message.startswith("/visit"):
    parts = message.split()

    if len(parts) != 2:
        self._bot.reply(cid, type, "[c][FF0000]Usage: /visit uid")
        return
    uid = parts[1]
    self._bot.reply(
        cid,
        type,
        f"""[b][c][FFFF00]ĐANG BUFF VISIT...
[AAAAAA]UID: {uid}"""
    ) 
    def run():
        result = send_visit(uid)
        self._bot.reply(cid, type, result)

    threading.Thread(target=run, daemon=True).start()

   elif message.startswith("/info"):
    text = get_user_input(str(message))
    if ":" in text: self._bot.reply(cid, type, text); return
    self._bot.reply(cid, type, send_info(text, self.token, self.base_url))

   elif message.startswith("/region"):
    index = get_user_input(message)
    if ":" in index: self._bot.reply(cid, type, index); return
    res = napthe(index)
    self._bot.reply(cid, type, "[B][c]User '%s' with uid '%s' is in '%s' region" % (
     res.get("nickname"), index, 
     res.get("region", "locked"))
    )

   elif message.startswith("/isbanned"):
    uid = get_user_input(message)
    if ":" in uid: self._bot.reply(cid, type, uid); return
    I=check_banned(uid)
    self._bot.reply(cid, type, '[B][c]PLAYER IS BANNED' if I else '[B][c]NOT BANNED')
   else: return False
  except Exception as e:self.rstatus, self.ids = (0, 0), []

 
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
        self._bot.reply(uid, None, "[B][C][00FF00]đị[c]t m[c]ẹ gar[b]ena\n[00FF00]TikTok: [FF69B4]@deocanthuonghai09\n[00FF00]Tele[c]gr[c]am: [87CEEB]@zanbackj\n[00FF00]Group: [FFD700]ht[c]tps://t.[b]me/zancommunity")
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
        self._bot.reply(cid, Type, "[b][c]thử lại!")
        return

    self.status = False
    
    # ====== MỞ ĐỘI ======
    try:
        self.sock39699.sendall(self._bot.open_squad(team))
    except Exception as e:
        self._bot.reply(cid, Type, f"[b][c]Lỗi open: {e}")
        return
    
    time.sleep(0.3)
    
    # ====== MỜI ======
    try:
        self.sock39699.send(self._bot.invite_squad(uid, 1))
    except:
        pass
    
    time.sleep(0.3)
    
    try:
        self.sock39699.send(self._bot.invite_squad(uid, 2))
    except:
        pass

    self._bot.reply(cid, Type, """[B][C][FFFFFF]Xin Chào {}
[FFFFFF]Create Squad: [00ffb3]5

[C0C0C0]Đã Tạo Thành Công Team 5 Free Fire. Vui Lòng Chấp Nhận Lời Mời Bot Gửi Tới!""".format(name, uid, team))

    # ====== GỬI STICKER ======
    try:
        import random
        import json
        
        sticker_data = random.choice([
            ("1200000001", random.randint(1, 24)),
            ("1200000002", random.randint(1, 15)),
            ("1200000004", random.randint(1, 13))
        ])
        payload = json.dumps({
            "StickerStr": f"[1={sticker_data[0]}-{sticker_data[1]}]",
            "type": "Sticker"
        })
        self.sock39801.send(self._bot.send_object(payload, cid, Type))
    except:
        pass

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
   self.roomcode = None
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
            
            try:
                print(f"[ChooseEmote] Đang chạy với token: {self.token[:20]}... và base_url: {self.base_url}")
                result = ChooseEmote(self.token, self.base_url)
                print(f"[ChooseEmote] ✅ Thành công! Response: {result[:50] if result else 'Empty'}")
            except Exception as e:
                print(f"[ChooseEmote] ❌ Thất bại! Lỗi: {e}")
            
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
            return
            
        with open(self.filename, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        if not content:
            self.config = {"bots": []}
            return
            
        data = json.loads(content)
        self.bots.clear()
        
        # ====== KIỂM TRA ĐỊNH DẠNG ======
        if "Bots" in data:
            # Định dạng mới
            for bot_data in data["Bots"]:
                try:
                    bot_id = bot_data.get("id")
                    if not bot_id:
                        continue
                    
                    old_format = {
                        "bot_id": bot_id,
                        "botid": bot_id,
                        "nickname": bot_data.get("name", "Unknown"),
                        "region": "VN",
                        "access_bot": bot_data.get("users", []),
                        "auth_bot_login": {
                            "access_token": bot_data.get("token", "")
                        },
                        "active-clan": True,
                        "status": "online" if bot_data.get("online", False) else "offline"
                    }
                    
                    bot_instance = FreeFireTCP(old_format, self)
                    bot_instance.bot_config = old_format
                    bot_instance.botid = bot_id
                    bot_instance.nickname = old_format.get("nickname")
                    self.bots[bot_id] = bot_instance
                    
                except Exception as e:
                    print(f"❌ Bot load error: {e}")
                    
        elif "bots" in data:
            # Định dạng cũ
            for bot_data in data["bots"]:
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
                    print(f"❌ Bot load error: {e}")
        
        print(f"✅ Loaded {len(self.bots)} bots from bot.json")
        
    except Exception as e:
        print(f"❌ load_config error: {e}")
        self.config = {"bots": []}
        
 def save_config(self):
    try:
        with self.config_lock:
            bot_list = []
            for bot_id, bot_instance in self.bots.items():
                running = bot_instance.running_event.is_set()
                bot_list.append({
                    "id": bot_id,
                    "botid": getattr(bot_instance, "botid", None),  # <-- THÊM DÒNG NÀY
                    "name": getattr(bot_instance, "nickname", "Unknown"),
                    "token": bot_instance.bot_config.get("auth_bot_login", {}).get("access_token", ""),
                    "online": running,
                    "users": bot_instance.bot_config.get("access_bot", [])
                })
            
            # Sắp xếp theo id
            bot_list = sorted(bot_list, key=lambda x: x["id"])
            data = {"Bots": bot_list}
            
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved {len(bot_list)} bots")
    except Exception as e:
        print(f"❌ save_config error: {e}")
                
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

TCPbot = BOTMNG()
app = Flask(__name__)

# ====== LỆNH /START - MENU QUẢN LÝ BOT ======
@telegram_bot.message_handler(commands=['start', 'help', 'menu'])
def start_cmd(message):
    menu_text = """
<blockquote>
<b>🤖 BOT MANAGER - QUẢN LÝ BOT</b>
━━━━━━━━━━━━━━━━━━━━

<b>👑 ADMIN - QUẢN LÝ BOT</b>
├ /addbot [token] → Thêm bot mới
├ /delbot [botid/all] → Xóa bot
├ /online [botid/all] → Bật bot
├ /offline [botid/all] → Tắt bot
├ /resetbot [botid/all] → Reset bot
└ /checkbot → Xem trạng thái

━━━━━━━━━━━━━━━━━━━━

<b>🤝 KẾT BẠN</b>
├ /kb [botid] [uid] → kb 1 bot
├ /kball [uid] → KB all bot
├ /xkb [botid] [uid] → Hủy kb 1 bot
└ /xkball [uid] → Hủy kb all bot

━━━━━━━━━━━━━━━━━━━━

<b>📝 BIO</b>
├ /bio [botid] [bio] → Đổi bio 1 bot
├ /bioid [uid] [bio] → Đổi bio theo uid
└ /bioall [bio] → Đổi bio all bot

━━━━━━━━━━━━━━━━━━━━

<b>🏠 QD (CLAN)</b>
├ /voqd [botid] [idqd] → Xin vào clan 1 bot
├ /roiqd [botid] [clanid] → Rời clan 1 bot
├ /voqdall [idqd] → Xin vào clan all bot
└ /roiqdall [clanid] → Rời clan all bot

━━━━━━━━━━━━━━━━━━━━

<b>🗑️ XÓA BẠN BÈ</b>
└ /clearfriends [botid] → Xóa ALL bạn bè

━━━━━━━━━━━━━━━━━━━━
📩 <b>Liên hệ:</b> @zanbackj
</blockquote>
"""
    telegram_bot.reply_to(message, menu_text, parse_mode="HTML")

@telegram_bot.message_handler(commands=['addbot'])
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

# ====== LỆNH TELEGRAM: /clearfriends ======
@telegram_bot.message_handler(commands=['clearfriends'])
def telegram_clear_friends(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "💡 Dùng: <code>/clearfriends [botid]</code>\n"
                "📌 Ví dụ: <code>/clearfriends 1</code>\n"
                "📌 Ví dụ: <code>/clearfriends all</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        target = parts[1]
        
        # ====== XÓA ALL BOT ======
        if target.lower() == "all":
            results = []
            success_count = 0
            
            for bot_id, bot in TCPbot.bots.items():
                if not bot.running_event.is_set():
                    results.append({
                        'bot_id': bot_id,
                        'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                        'success': False,
                        'message': 'Bot offline'
                    })
                    continue
                
                token = getattr(bot, 'token', None)
                if not token:
                    token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
                
                if not token:
                    results.append({
                        'bot_id': bot_id,
                        'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                        'success': False,
                        'message': 'No token'
                    })
                    continue
                
                # Gọi API clearfriends
                import requests
                try:
                    resp = requests.get(f"http://127.0.0.1:2010/clearfriends?botid={bot_id}", timeout=60)
                    data = resp.json()
                    if data.get('status') == 'success':
                        success_count += 1
                        results.append({
                            'bot_id': bot_id,
                            'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                            'success': True,
                            'message': data.get('message', 'Success')
                        })
                    else:
                        results.append({
                            'bot_id': bot_id,
                            'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                            'success': False,
                            'message': data.get('message', 'Failed')
                        })
                except Exception as e:
                    results.append({
                        'bot_id': bot_id,
                        'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                        'success': False,
                        'message': str(e)
                    })
            
            msg = f"<blockquote><b>🗑️ XÓA BẠN BÈ ALL BOT</b>\n━━━━━━━━━━━━━━━━━━━━\n✅ Thành công: <b>{success_count}/{len(TCPbot.bots)}</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            for r in results:
                status = "✅" if r['success'] else "❌"
                msg += f"{status} <b>{r['bot_name']}</b>: {r['message'][:40]}\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n⚡ Đã xóa!</blockquote>"
            
            telegram_bot.reply_to(message, msg, parse_mode="HTML")
            return
        
        # ====== XÓA 1 BOT ======
        if not target.isdigit():
            telegram_bot.reply_to(message, "❌ Bot ID phải là số hoặc 'all'!")
            return
        
        bot_id = int(target)
        
        if bot_id not in TCPbot.bots:
            telegram_bot.reply_to(message, f"❌ Không tìm thấy bot {bot_id}!")
            return
        
        bot = TCPbot.bots[bot_id]
        
        if not bot.running_event.is_set():
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ BOT OFFLINE</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 Bot ID: <code>{bot_id}</code>\n⚠️ Bot đang offline, không thể xóa bạn bè!\n━━━━━━━━━━━━━━━━━━━━\n💡 Bật bot trước khi xóa!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        token = getattr(bot, 'token', None)
        if not token:
            token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
        
        if not token:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ KHÔNG CÓ TOKEN</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 Bot ID: <code>{bot_id}</code>\n⚠️ Bot không có token!\n━━━━━━━━━━━━━━━━━━━━\n💡 Kiểm tra lại bot!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
        bot_uid = getattr(bot, 'botid', '?')
        
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>🔄 ĐANG XÓA BẠN BÈ...</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 Bot: <code>{bot_name}</code>\n🆔 UID: <code>{bot_uid}</code>\n━━━━━━━━━━━━━━━━━━━━\n⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        # ====== LẤY DANH SÁCH BẠN BÈ ======
        import requests
        headers = {
            'Authorization': f'Bearer {token}',
            'User-Agent': 'UnityPlayer/2022.3.47f1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Connection': 'Keep-Alive'
        }
        
        payload = bytes.fromhex('598fcaf07839308ff287aca3ae0a0617')
        friends = []
        
        try:
            response = requests.post('https://clientbp.ggpolarbear.com/GetFriend', headers=headers, data=payload, verify=False, timeout=10)
            if response.status_code == 200:
                from lib import protobuf_dec
                import json
                decoded = protobuf_dec(response.content.hex())
                parsed = json.loads(decoded)
                
                if "1" in parsed and isinstance(parsed["1"], list):
                    for friend in parsed["1"]:
                        friends.append(friend.get("1", ""))
        except Exception as e:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ LỖI LẤY DANH SÁCH</b>\n━━━━━━━━━━━━━━━━━━━━\n⚠️ {str(e)}\n━━━━━━━━━━━━━━━━━━━━\n💡 Kiểm tra kết nối!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        if not friends:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>✅ KHÔNG CÓ BẠN BÈ</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 Bot: <code>{bot_name}</code>\n🆔 UID: <code>{bot_uid}</code>\n━━━━━━━━━━━━━━━━━━━━\n⚡ Bot không có bạn bè để xóa!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        # ====== XÓA TỪNG BẠN ======
        KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
        IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        
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
        
        removed = 0
        failed = 0
        
        for friend_uid in friends:
            try:
                encrypted_id = encrypt_uid(str(friend_uid))
                if not encrypted_id:
                    failed += 1
                    continue
                
                plain_text_payload = f'08a7c4839f1e10{encrypted_id}1801'
                cipher = AES.new(KEY, AES.MODE_CBC, IV)
                data = cipher.encrypt(pad(bytes.fromhex(plain_text_payload), AES.block_size))
                
                headers_remove = {
                    'X-Unity-Version': '2018.4.11f1',
                    'ReleaseVersion': 'OB54',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-GA': 'v1 1',
                    'Authorization': f'Bearer {token}',
                    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
                    'Connection': 'Keep-Alive',
                    'Accept-Encoding': 'gzip'
                }
                
                response = requests.post(
                    'https://clientbp.ggpolarbear.com/RemoveFriend',
                    headers=headers_remove,
                    data=data,
                    verify=False,
                    timeout=10
                )
                
                if response.status_code == 200:
                    removed += 1
                else:
                    failed += 1
                    
                time.sleep(0.15)
                
            except Exception as e:
                failed += 1
        
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>✅ XÓA BẠN BÈ HOÀN TẤT</b>\n━━━━━━━━━━━━━━━━━━━━\n🤖 Bot: <code>{bot_name}</code>\n🆔 UID: <code>{bot_uid}</code>\n━━━━━━━━━━━━━━━━━━━━\n✅ Đã xóa: <b>{removed}</b> bạn\n❌ Thất bại: <b>{failed}</b> bạn\n📦 Tổng: <b>{len(friends)}</b> bạn\n━━━━━━━━━━━━━━━━━━━━\n⚡ Hoàn thành!</blockquote>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")
        
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

def get_region_from_jwt(jwt_token):
    """Lấy region từ JWT token"""
    try:
        import jwt
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        return decoded.get("lock_region", "VN")
    except:
        return "VN"

def request_join_clan(jwt_token, clan_id, region="VN"):
    """Xin vào clan"""
    import requests
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    
    KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
    IV = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
    
    REGION_SERVER_MAP = {
        "VN": "https://clientbp.ggpolarbear.com",
        "TH": "https://clientbp.ggpolarbear.com",
        "ID": "https://clientbp.ggpolarbear.com",
        "SG": "https://clientbp.ggpolarbear.com",
        "MY": "https://clientbp.ggpolarbear.com",
        "IN": "https://client.ind.freefiremobile.com",
        "PK": "https://clientbp.ggblueshark.com",
        "BD": "https://clientbp.ggwhitehawk.com",
        "BR": "https://client.us.freefiremobile.com",
        "NA": "https://client.us.freefiremobile.com",
        "ME": "https://clientbp.ggblueshark.com",
        "EU": "https://clientbp.ggpolarbear.com",
        "RU": "https://clientbp.ggpolarbear.com",
    }
    
    server_url = REGION_SERVER_MAP.get(region.upper(), "https://clientbp.ggpolarbear.com")
    
    msg = ReqCLan_pb2.MyMessage()
    msg.field_1 = int(clan_id)
    
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    encrypted = cipher.encrypt(pad(msg.SerializeToString(), AES.block_size))
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/octet-stream",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB54",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    
    try:
        r = requests.post(f"{server_url}/RequestJoinClan", headers=headers, data=encrypted, verify=False, timeout=15)
        if r.status_code == 200:
            return True, "✅ Xin vào clan thành công!"
        elif "BR_ALREADY_IN_CLAN" in r.text:
            return False, "❌ Bạn đã ở trong clan này rồi!"
        elif "BR_JOIN_CLAN_REQUEST_LIMIT" in r.text:
            return False, "❌ Đã đạt giới hạn yêu cầu!"
        else:
            return False, f"❌ Thất bại! Status: {r.status_code}"
    except Exception as e:
        return False, f"❌ Lỗi: {str(e)}"

def quit_clan(jwt_token, clan_id, region="VN"):
    """Rời clan"""
    import requests
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    
    KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
    IV = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
    
    REGION_SERVER_MAP = {
        "VN": "https://clientbp.ggpolarbear.com",
        "TH": "https://clientbp.ggpolarbear.com",
        "ID": "https://clientbp.ggpolarbear.com",
        "SG": "https://clientbp.ggpolarbear.com",
        "MY": "https://clientbp.ggpolarbear.com",
        "IN": "https://client.ind.freefiremobile.com",
        "PK": "https://clientbp.ggblueshark.com",
        "BD": "https://clientbp.ggwhitehawk.com",
        "BR": "https://client.us.freefiremobile.com",
        "NA": "https://client.us.freefiremobile.com",
        "ME": "https://clientbp.ggblueshark.com",
        "EU": "https://clientbp.ggpolarbear.com",
        "RU": "https://clientbp.ggpolarbear.com",
    }
    
    server_url = REGION_SERVER_MAP.get(region.upper(), "https://clientbp.ggpolarbear.com")
    
    msg = QuitClanReq_pb2.QuitClanReq()
    msg.field_1 = int(clan_id)
    
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    encrypted = cipher.encrypt(pad(msg.SerializeToString(), AES.block_size))
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/octet-stream",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB54",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    
    try:
        r = requests.post(f"{server_url}/QuitClan", headers=headers, data=encrypted, verify=False, timeout=15)
        if r.status_code == 200:
            return True, "✅ Rời clan thành công!"
        elif "BR_NOT_IN_CLAN" in r.text:
            return False, "❌ Bạn không ở trong clan này!"
        else:
            return False, f"❌ Thất bại! Status: {r.status_code}"
    except Exception as e:
        return False, f"❌ Lỗi: {str(e)}"


# ===== LỆNH TELEGRAM: /voqd =====
@telegram_bot.message_handler(commands=['voqd'])
def telegram_join_clan(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "💡 Dùng: <code>/voqd [botid] [clan_id]</code>\n"
                "📌 Ví dụ: <code>/voqd 1 123456789</code>\n"
                "📌 Ví dụ: <code>/voqd 1 123456789 VN</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        bot_id = int(parts[1])
        clan_id = parts[2]
        region = parts[3].upper() if len(parts) > 3 else None
        
        if not clan_id.isdigit():
            telegram_bot.reply_to(message, "❌ Clan ID phải là số!")
            return
        
        if bot_id not in TCPbot.bots:
            telegram_bot.reply_to(message, f"❌ Không tìm thấy bot {bot_id}!")
            return
        
        bot = TCPbot.bots[bot_id]
        
        # Lấy token
        token = getattr(bot, 'token', None)
        if not token:
            token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
        
        if not token:
            telegram_bot.reply_to(message, f"❌ Bot {bot_id} không có token!")
            return
        
        # Auto detect region nếu không có
        if not region:
            region = get_region_from_jwt(token)
        
        bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
        bot_uid = getattr(bot, 'botid', '?')
        
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>🔄 ĐANG XIN VÀO CLAN...</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 Bot: <code>{bot_name}</code>\n"
            f"🆔 UID: <code>{bot_uid}</code>\n"
            f"🏠 Clan ID: <code>{clan_id}</code>\n"
            f"🌍 Region: <code>{region}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        success, msg = request_join_clan(token, clan_id, region)
        
        if success:
            final_msg = (
                f"<blockquote><b>✅ XIN VÀO CLAN THÀNH CÔNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot: <code>{bot_name}</code>\n"
                f"🆔 UID: <code>{bot_uid}</code>\n"
                f"🏠 Clan ID: <code>{clan_id}</code>\n"
                f"🌍 Region: <code>{region}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ {msg}</blockquote>"
            )
        else:
            final_msg = (
                f"<blockquote><b>❌ XIN VÀO CLAN THẤT BẠI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot: <code>{bot_name}</code>\n"
                f"🆔 UID: <code>{bot_uid}</code>\n"
                f"🏠 Clan ID: <code>{clan_id}</code>\n"
                f"🌍 Region: <code>{region}</code>\n"
                f"⚠️ {msg}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 Kiểm tra clan ID hoặc token!</blockquote>"
            )
        
        telegram_bot.reply_to(message, final_msg, parse_mode="HTML")
        
    except ValueError:
        telegram_bot.reply_to(message, "❌ Bot ID phải là số!")
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@telegram_bot.message_handler(commands=['checkqd'])
def telegram_check_clan(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        
        # ====== CHECK 1 BOT ======
        if len(parts) >= 2:
            bot_id = int(parts[1])
            
            if bot_id not in TCPbot.bots:
                telegram_bot.reply_to(message, f"❌ Không tìm thấy bot {bot_id}!")
                return
            
            bot = TCPbot.bots[bot_id]
            bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
            bot_uid = getattr(bot, 'botid', '?')
            
            clan_info = bot.bot_config.get('clan_info', {})
            
            if not clan_info:
                telegram_bot.reply_to(
                    message,
                    f"<blockquote><b>📋 THÔNG TIN QUÂN ĐOÀN BOT {bot_id}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🤖 Bot: <code>{bot_name}</code>\n"
                    f"🆔 UID: <code>{bot_uid}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📭 Bot chưa vào quân đoàn nào!</blockquote>",
                    parse_mode="HTML"
                )
                return
            
            text = f"<blockquote><b>📋 THÔNG TIN QUÂN ĐOÀN BOT {bot_id}</b>\n"
            text += f"━━━━━━━━━━━━━━━━━━━━\n"
            text += f"🤖 Bot: <code>{bot_name}</code>\n"
            text += f"🆔 UID: <code>{bot_uid}</code>\n"
            text += f"━━━━━━━━━━━━━━━━━━━━\n"
            
            for clan_id, info in clan_info.items():
                expire = info.get('expire', 'Vĩnh viễn')
                region = info.get('region', 'VN')
                joined_at = info.get('joined_at', 'Không rõ')
                
                # ====== TÍNH THỜI GIAN CÒN LẠI ======
                try:
                    from datetime import datetime
                    if expire and expire != 'Vĩnh viễn':
                        expire_time = datetime.strptime(expire, "%Y-%m-%d %H:%M:%S")
                        now = datetime.now()
                        
                        if expire_time < now:
                            time_left = "⏰ Đã hết hạn"
                        else:
                            delta = expire_time - now
                            days = delta.days
                            hours, remainder = divmod(delta.seconds, 3600)
                            minutes, seconds = divmod(remainder, 60)
                            parts_time = []
                            if days > 0:
                                parts_time.append(f"{days} ngày")
                            if hours > 0:
                                parts_time.append(f"{hours} giờ")
                            if minutes > 0 and days == 0:
                                parts_time.append(f"{minutes} phút")
                            time_left = ", ".join(parts_time) if parts_time else "0 phút"
                    else:
                        time_left = "♾️ Vĩnh viễn"
                except:
                    time_left = expire
                
                text += f"🏠 <b>Clan ID:</b> <code>{clan_id}</code>\n"
                text += f"🌍 <b>Region:</b> <code>{region}</code>\n"
                text += f"📅 <b>Vào lúc:</b> <code>{joined_at}</code>\n"
                text += f"⏳ <b>Còn lại:</b> <code>{time_left}</code>\n"
                text += f"━━━━━━━━━━━━━━━━━━━━\n"
            
            text += f"⚡ Tổng: <b>{len(clan_info)}</b> quân đoàn</blockquote>"
            
            telegram_bot.reply_to(message, text, parse_mode="HTML")
            return
        
        # ====== CHECK ALL BOT ======
        if not TCPbot.bots:
            telegram_bot.reply_to(message, "❌ Không có bot nào trong hệ thống!")
            return
        
        text = "<blockquote><b>📊 TỔNG HỢP QUÂN ĐOÀN ALL BOT</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"🤖 Tổng bot: <b>{len(TCPbot.bots)}</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        total_clans = 0
        bot_details = []
        
        for bot_id, bot in TCPbot.bots.items():
            clan_info = bot.bot_config.get('clan_info', {})
            bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
            bot_uid = getattr(bot, 'botid', '?')
            running = "🟢 Online" if bot.running_event.is_set() else "🔴 Offline"
            
            total_clans += len(clan_info)
            bot_details.append({
                'bot_id': bot_id,
                'bot_name': bot_name,
                'bot_uid': bot_uid,
                'clans': clan_info,
                'total': len(clan_info),
                'running': running
            })
        
        for detail in bot_details:
            text += f"🤖 <b>Bot {detail['bot_id']}</b> {detail['running']}\n"
            text += f"├ Tên: <code>{detail['bot_name']}</code>\n"
            text += f"├ UID: <code>{detail['bot_uid']}</code>\n"
            
            if detail['clans']:
                for clan_id, info in detail['clans'].items():
                    expire = info.get('expire', 'Vĩnh viễn')
                    try:
                        from datetime import datetime
                        if expire and expire != 'Vĩnh viễn':
                            expire_time = datetime.strptime(expire, "%Y-%m-%d %H:%M:%S")
                            now = datetime.now()
                            if expire_time < now:
                                time_left = "⏰ Hết hạn"
                            else:
                                delta = expire_time - now
                                days = delta.days
                                hours, remainder = divmod(delta.seconds, 3600)
                                parts_time = []
                                if days > 0:
                                    parts_time.append(f"{days} ngày")
                                if hours > 0:
                                    parts_time.append(f"{hours} giờ")
                                time_left = ", ".join(parts_time) if parts_time else "0 phút"
                        else:
                            time_left = "♾️ Vĩnh viễn"
                    except:
                        time_left = expire
                    
                    text += f"└ 🏠 Clan <code>{clan_id}</code> ⏳ {time_left}\n"
            else:
                text += f"└ 📭 Chưa vào QĐ nào\n"
            text += "\n"
        
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📦 Tổng QĐ: <b>{total_clans}</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"💡 Dùng <code>/checkqd [botid]</code> để xem chi tiết</blockquote>"
        
        telegram_bot.reply_to(message, text, parse_mode="HTML")
        
    except ValueError:
        telegram_bot.reply_to(message, "❌ Bot ID phải là số!")
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")

# ===== LỆNH TELEGRAM: /roiqd =====
@telegram_bot.message_handler(commands=['roiqd'])
def telegram_quit_clan(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "💡 Dùng: <code>/roiqd [botid] [clan_id]</code>\n"
                "📌 Ví dụ: <code>/roiqd 1 123456789</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        bot_id = int(parts[1])
        clan_id = parts[2]
        region = parts[3].upper() if len(parts) > 3 else None
        
        if not clan_id.isdigit():
            telegram_bot.reply_to(message, "❌ Clan ID phải là số!")
            return
        
        if bot_id not in TCPbot.bots:
            telegram_bot.reply_to(message, f"❌ Không tìm thấy bot {bot_id}!")
            return
        
        bot = TCPbot.bots[bot_id]
        
        token = getattr(bot, 'token', None)
        if not token:
            token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
        
        if not token:
            telegram_bot.reply_to(message, f"❌ Bot {bot_id} không có token!")
            return
        
        if not region:
            region = get_region_from_jwt(token)
        
        bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
        bot_uid = getattr(bot, 'botid', '?')
        
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>🔄 ĐANG RỜI CLAN...</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 Bot: <code>{bot_name}</code>\n"
            f"🆔 UID: <code>{bot_uid}</code>\n"
            f"🏠 Clan ID: <code>{clan_id}</code>\n"
            f"🌍 Region: <code>{region}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        success, msg = quit_clan(token, clan_id, region)
        
        if success:
            final_msg = (
                f"<blockquote><b>✅ RỜI CLAN THÀNH CÔNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot: <code>{bot_name}</code>\n"
                f"🆔 UID: <code>{bot_uid}</code>\n"
                f"🏠 Clan ID: <code>{clan_id}</code>\n"
                f"🌍 Region: <code>{region}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ {msg}</blockquote>"
            )
        else:
            final_msg = (
                f"<blockquote><b>❌ RỜI CLAN THẤT BẠI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot: <code>{bot_name}</code>\n"
                f"🆔 UID: <code>{bot_uid}</code>\n"
                f"🏠 Clan ID: <code>{clan_id}</code>\n"
                f"🌍 Region: <code>{region}</code>\n"
                f"⚠️ {msg}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 Kiểm tra clan ID hoặc token!</blockquote>"
            )
        
        telegram_bot.reply_to(message, final_msg, parse_mode="HTML")
        
    except ValueError:
        telegram_bot.reply_to(message, "❌ Bot ID phải là số!")
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")


# ===== LỆNH TELEGRAM: /voqdall =====
@telegram_bot.message_handler(commands=['voqdall'])
def telegram_join_clan_all(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "💡 Dùng: <code>/voqdall [clan_id]</code>\n"
                "📌 Ví dụ: <code>/voqdall 123456789</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        clan_id = parts[1]
        region = parts[2].upper() if len(parts) > 2 else None
        
        if not clan_id.isdigit():
            telegram_bot.reply_to(message, "❌ Clan ID phải là số!")
            return
        
        online_bots = []
        for bot_id, bot in TCPbot.bots.items():
            if bot.running_event.is_set():
                token = getattr(bot, 'token', None)
                if not token:
                    token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
                if token:
                    online_bots.append((bot_id, bot, token))
        
        if not online_bots:
            telegram_bot.reply_to(message, "❌ Không có bot online nào!")
            return
        
        if not region:
            region = get_region_from_jwt(online_bots[0][2])
        
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>🔄 ĐANG XIN VÀO CLAN CHO {len(online_bots)} BOT...</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏠 Clan ID: <code>{clan_id}</code>\n"
            f"🌍 Region: <code>{region}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        results = []
        success_count = 0
        
        for bot_id, bot, token in online_bots:
            bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
            success, msg = request_join_clan(token, clan_id, region)
            if success:
                success_count += 1
            results.append({
                'bot_id': bot_id,
                'bot_name': bot_name,
                'success': success,
                'message': msg
            })
        
        msg_final = (
            f"<blockquote><b>✅ XIN VÀO CLAN ALL HOÀN TẤT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏠 Clan ID: <code>{clan_id}</code>\n"
            f"🌍 Region: <code>{region}</code>\n"
            f"✅ Thành công: <b>{success_count}/{len(online_bots)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        for r in results:
            status = "✅" if r['success'] else "❌"
            msg_final += f"{status} <b>{r['bot_name']}</b>: {r['message'][:30]}\n"
        
        msg_final += "</blockquote>"
        telegram_bot.reply_to(message, msg_final, parse_mode="HTML")
        
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")


# ===== LỆNH TELEGRAM: /roiqdall =====
@telegram_bot.message_handler(commands=['roiqdall'])
def telegram_quit_clan_all(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "💡 Dùng: <code>/roiqdall [clan_id]</code>\n"
                "📌 Ví dụ: <code>/roiqdall 123456789</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        clan_id = parts[1]
        region = parts[2].upper() if len(parts) > 2 else None
        
        if not clan_id.isdigit():
            telegram_bot.reply_to(message, "❌ Clan ID phải là số!")
            return
        
        online_bots = []
        for bot_id, bot in TCPbot.bots.items():
            if bot.running_event.is_set():
                token = getattr(bot, 'token', None)
                if not token:
                    token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
                if token:
                    online_bots.append((bot_id, bot, token))
        
        if not online_bots:
            telegram_bot.reply_to(message, "❌ Không có bot online nào!")
            return
        
        if not region:
            region = get_region_from_jwt(online_bots[0][2])
        
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>🔄 ĐANG RỜI CLAN CHO {len(online_bots)} BOT...</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏠 Clan ID: <code>{clan_id}</code>\n"
            f"🌍 Region: <code>{region}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        results = []
        success_count = 0
        
        for bot_id, bot, token in online_bots:
            bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
            success, msg = quit_clan(token, clan_id, region)
            if success:
                success_count += 1
            results.append({
                'bot_id': bot_id,
                'bot_name': bot_name,
                'success': success,
                'message': msg
            })
        
        msg_final = (
            f"<blockquote><b>✅ RỜI CLAN ALL HOÀN TẤT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏠 Clan ID: <code>{clan_id}</code>\n"
            f"🌍 Region: <code>{region}</code>\n"
            f"✅ Thành công: <b>{success_count}/{len(online_bots)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        for r in results:
            status = "✅" if r['success'] else "❌"
            msg_final += f"{status} <b>{r['bot_name']}</b>: {r['message'][:30]}\n"
        
        msg_final += "</blockquote>"
        telegram_bot.reply_to(message, msg_final, parse_mode="HTML")
        
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")

# ==================== ĐỔI BIO ====================
def change_bio_via_token(jwt_token, bio_text):
    """Đổi bio sử dụng JWT token"""
    import requests
    import urllib3
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    
    def encode_varint(n):
        result = []
        while True:
            byte = n & 0x7F
            n >>= 7
            if n:
                byte |= 0x80
            result.append(byte)
            if not n:
                break
        return bytes(result)
    
    def build_bio_proto(bio_text):
        result = b''
        header = (2 << 3) | 0
        result += encode_varint(header)
        result += encode_varint(17)
        empty = b''
        header5 = (5 << 3) | 2
        result += encode_varint(header5)
        result += encode_varint(len(empty))
        result += empty
        header6 = (6 << 3) | 2
        result += encode_varint(header6)
        result += encode_varint(len(empty))
        result += empty
        bio_encoded = bio_text.encode('utf-8')
        header8 = (8 << 3) | 2
        result += encode_varint(header8)
        result += encode_varint(len(bio_encoded))
        result += bio_encoded
        header9 = (9 << 3) | 0
        result += encode_varint(header9)
        result += encode_varint(1)
        header11 = (11 << 3) | 2
        result += encode_varint(header11)
        result += encode_varint(len(empty))
        result += empty
        header12 = (12 << 3) | 2
        result += encode_varint(header12)
        result += encode_varint(len(empty))
        result += empty
        return result
    
    endpoints = [
        "https://clientbp.ggpolarbear.com/UpdateSocialBasicInfo",
        "https://clientbp.ggblueshark.com/UpdateSocialBasicInfo",
        "https://clientbp.common.ggbluefox.com/UpdateSocialBasicInfo"
    ]
    
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB54",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; SM-G998B Build/TP1A.220624.014)"
    }
    
    for url in endpoints:
        try:
            proto = build_bio_proto(bio_text)
            cipher = AES.new(KEY, AES.MODE_CBC, IV)
            encrypted = cipher.encrypt(pad(proto, AES.block_size))
            resp = requests.post(url, headers=headers, data=encrypted, verify=False, timeout=10)
            if resp.status_code == 200:
                return True, "✅ Đổi bio thành công!"
            headers_json = headers.copy()
            headers_json["Content-Type"] = "application/json"
            resp2 = requests.post(url, headers=headers_json, json={"bio": bio_text}, verify=False, timeout=10)
            if resp2.status_code == 200:
                return True, "✅ Đổi bio thành công!"
        except:
            continue
    return False, "❌ Đổi bio thất bại!"

# ===== LỆNH TELEGRAM: /bio =====
@telegram_bot.message_handler(commands=['bio'])
def telegram_change_bio(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "💡 Dùng: <code>/bio [botid] [nội dung bio]</code>\n"
                "📌 Ví dụ: <code>/bio 1 Xin chào các bạn!</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        bot_id = int(parts[1])
        bio_text = parts[2].strip()
        
        if not bio_text:
            telegram_bot.reply_to(message, "❌ Bio không được để trống!")
            return
        
        if len(bio_text) > 150:
            telegram_bot.reply_to(message, "❌ Bio quá dài! Tối đa 150 ký tự.")
            return
        
        if bot_id not in TCPbot.bots:
            telegram_bot.reply_to(message, f"❌ Không tìm thấy bot {bot_id}!")
            return
        
        bot = TCPbot.bots[bot_id]
        
        # Lấy token
        token = None
        if hasattr(bot, 'token') and bot.token:
            token = bot.token
        elif hasattr(bot, 'bot_config'):
            token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
        
        if not token:
            telegram_bot.reply_to(message, f"❌ Bot {bot_id} không có token!")
            return
        
        bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
        bot_uid = getattr(bot, 'botid', '?')
        
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>🔄 ĐANG ĐỔI BIO...</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 Bot: <code>{bot_name}</code>\n"
            f"🆔 UID: <code>{bot_uid}</code>\n"
            f"📝 Bio mới: <code>{bio_text[:50]}{'...' if len(bio_text) > 50 else ''}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        success, msg = change_bio_via_token(token, bio_text)
        
        if success:
            final_msg = (
                f"<blockquote><b>✅ ĐỔI BIO THÀNH CÔNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot: <code>{bot_name}</code>\n"
                f"🆔 UID: <code>{bot_uid}</code>\n"
                f"📝 Bio mới: <code>{bio_text[:80]}{'...' if len(bio_text) > 80 else ''}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ {msg}</blockquote>"
            )
        else:
            final_msg = (
                f"<blockquote><b>❌ ĐỔI BIO THẤT BẠI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot: <code>{bot_name}</code>\n"
                f"🆔 UID: <code>{bot_uid}</code>\n"
                f"⚠️ {msg}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 Kiểm tra token hoặc thử lại!</blockquote>"
            )
        
        telegram_bot.reply_to(message, final_msg, parse_mode="HTML")
        
    except ValueError:
        telegram_bot.reply_to(message, "❌ Bot ID phải là số!")
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")


# ===== LỆNH TELEGRAM: /bioall =====
@telegram_bot.message_handler(commands=['bioall'])
def telegram_change_bio_all(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "💡 Dùng: <code>/bioall [nội dung bio]</code>\n"
                "📌 Ví dụ: <code>/bioall Xin chào tất cả!</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        bio_text = parts[1].strip()
        
        if not bio_text:
            telegram_bot.reply_to(message, "❌ Bio không được để trống!")
            return
        
        if len(bio_text) > 150:
            telegram_bot.reply_to(message, "❌ Bio quá dài! Tối đa 150 ký tự.")
            return
        
        online_bots = []
        for bot_id, bot in TCPbot.bots.items():
            if bot.running_event.is_set():
                token = getattr(bot, 'token', None)
                if not token:
                    token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
                if token:
                    online_bots.append((bot_id, bot, token))
        
        if not online_bots:
            telegram_bot.reply_to(message, "❌ Không có bot online nào!")
            return
        
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>🔄 ĐANG ĐỔI BIO CHO {len(online_bots)} BOT...</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Bio: <code>{bio_text[:50]}{'...' if len(bio_text) > 50 else ''}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        results = []
        success_count = 0
        
        for bot_id, bot, token in online_bots:
            bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
            success, msg = change_bio_via_token(token, bio_text)
            if success:
                success_count += 1
            results.append({
                'bot_id': bot_id,
                'bot_name': bot_name,
                'success': success,
                'message': msg
            })
        
        msg_final = (
            f"<blockquote><b>✅ ĐỔI BIO ALL HOÀN TẤT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 Bio: <code>{bio_text[:50]}{'...' if len(bio_text) > 50 else ''}</code>\n"
            f"✅ Thành công: <b>{success_count}/{len(online_bots)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        for r in results:
            status = "✅" if r['success'] else "❌"
            msg_final += f"{status} <b>{r['bot_name']}</b>: {r['message'][:30]}\n"
        
        msg_final += "</blockquote>"
        telegram_bot.reply_to(message, msg_final, parse_mode="HTML")
        
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")


# ===== LỆNH TELEGRAM: /bioid =====
@telegram_bot.message_handler(commands=['bioid'])
def telegram_change_bio_by_uid(message):
    """Đổi bio cho bot dùng UID (không cần botid)"""
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "💡 Dùng: <code>/bioid [uid_bot] [nội dung bio]</code>\n"
                "📌 Ví dụ: <code>/bioid 16104663154 Xin chào!</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        target_uid = parts[1]
        bio_text = parts[2].strip()
        
        if not bio_text:
            telegram_bot.reply_to(message, "❌ Bio không được để trống!")
            return
        
        if len(bio_text) > 150:
            telegram_bot.reply_to(message, "❌ Bio quá dài! Tối đa 150 ký tự.")
            return
        
        # Tìm bot theo UID
        found_bot = None
        found_bot_id = None
        for bot_id, bot in TCPbot.bots.items():
            if str(getattr(bot, 'botid', '')) == str(target_uid):
                found_bot = bot
                found_bot_id = bot_id
                break
        
        if not found_bot:
            telegram_bot.reply_to(message, f"❌ Không tìm thấy bot có UID {target_uid}!")
            return
        
        if not found_bot.running_event.is_set():
            telegram_bot.reply_to(message, f"❌ Bot {found_bot_id} đang offline!")
            return
        
        token = getattr(found_bot, 'token', None)
        if not token:
            token = found_bot.bot_config.get('auth_bot_login', {}).get('access_token')
        
        if not token:
            telegram_bot.reply_to(message, f"❌ Bot {found_bot_id} không có token!")
            return
        
        bot_name = getattr(found_bot, 'nickname', f'Bot #{found_bot_id}')
        
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>🔄 ĐANG ĐỔI BIO...</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 Bot: <code>{bot_name}</code>\n"
            f"🆔 UID: <code>{target_uid}</code>\n"
            f"📝 Bio: <code>{bio_text[:50]}{'...' if len(bio_text) > 50 else ''}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Đang xử lý...</blockquote>",
            parse_mode="HTML"
        )
        
        success, msg = change_bio_via_token(token, bio_text)
        
        if success:
            final_msg = (
                f"<blockquote><b>✅ ĐỔI BIO THÀNH CÔNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot: <code>{bot_name}</code>\n"
                f"🆔 UID: <code>{target_uid}</code>\n"
                f"📝 Bio: <code>{bio_text[:80]}{'...' if len(bio_text) > 80 else ''}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ {msg}</blockquote>"
            )
        else:
            final_msg = (
                f"<blockquote><b>❌ ĐỔI BIO THẤT BẠI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot: <code>{bot_name}</code>\n"
                f"🆔 UID: <code>{target_uid}</code>\n"
                f"⚠️ {msg}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 Kiểm tra token hoặc thử lại!</blockquote>"
            )
        
        telegram_bot.reply_to(message, final_msg, parse_mode="HTML")
        
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")

@telegram_bot.message_handler(commands=['checktime'])
def telegram_check_time(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        
        # ====== CHECK 1 BOT ======
        if len(parts) >= 2:
            bot_id = int(parts[1])
            
            if bot_id not in TCPbot.bots:
                telegram_bot.reply_to(message, f"❌ Không tìm thấy bot {bot_id}!")
                return
            
            bot = TCPbot.bots[bot_id]
            access_list = bot.bot_config.get('access_bot', [])
            bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
            bot_uid = getattr(bot, 'botid', '?')
            
            if not access_list:
                telegram_bot.reply_to(
                    message,
                    f"<blockquote><b>📋 DANH SÁCH USER BOT {bot_id}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🤖 Bot: <code>{bot_name}</code>\n"
                    f"🆔 UID: <code>{bot_uid}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📭 Chưa có user nào được cấp quyền!</blockquote>",
                    parse_mode="HTML"
                )
                return
            
            text = f"<blockquote><b>📋 DANH SÁCH USER BOT {bot_id}</b>\n"
            text += f"━━━━━━━━━━━━━━━━━━━━\n"
            text += f"🤖 Bot: <code>{bot_name}</code>\n"
            text += f"🆔 UID: <code>{bot_uid}</code>\n"
            text += f"━━━━━━━━━━━━━━━━━━━━\n"
            text += f"👥 Tổng: <b>{len(access_list)}</b> user\n"
            text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for i, user in enumerate(access_list, 1):
                uid = user.get('uid', 'N/A')
                expire = user.get('expire', 'N/A')
                
                # ====== LẤY TÊN USER ======
                user_name = "Không xác định"
                try:
                    import requests
                    resp = requests.get(f"http://localhost:2010/info1?uid={uid}", timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get('success'):
                            result = data.get('result', {})
                            if 'nickname' in result and result['nickname']:
                                user_name = result['nickname']
                            elif 'name' in result and result['name']:
                                user_name = result['name']
                            elif 'basic_info' in result:
                                basic = result['basic_info']
                                if 'nickname' in basic and basic['nickname']:
                                    user_name = basic['nickname']
                                elif 'name' in basic and basic['name']:
                                    user_name = basic['name']
                except Exception as e:
                    print(f"[GET NAME] {uid}: {e}")
                
                # ====== TÍNH THỜI GIAN CÒN LẠI ======
                try:
                    from datetime import datetime
                    exp_time = datetime.strptime(expire, "%Y-%m-%d %H:%M:%S")
                    now = datetime.now()
                    
                    if exp_time < now:
                        time_left = "⏰ Hết hạn"
                    else:
                        delta = exp_time - now
                        days = delta.days
                        hours, remainder = divmod(delta.seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        parts_time = []
                        if days > 0:
                            parts_time.append(f"{days} ngày")
                        if hours > 0 and days < 7:
                            parts_time.append(f"{hours} giờ")
                        if minutes > 0 and days == 0:
                            parts_time.append(f"{minutes} phút")
                        time_left = ", ".join(parts_time) if parts_time else "0 phút"
                except:
                    time_left = expire
                
                text += f"{i}. 👤 <code>{user_name}</code>\n"
                text += f"   🆔 UID: <code>{uid}</code>\n"
                text += f"   ⏳ Hết hạn: <code>{expire}</code>\n"
                text += f"   📊 Còn: <code>{time_left}</code>\n\n"
            
            text += f"━━━━━━━━━━━━━━━━━━━━\n"
            text += f"⚡ Tổng: <b>{len(access_list)}</b> user</blockquote>"
            
            if len(text) > 4000:
                import io
                file_content = text.replace("<blockquote>", "").replace("</blockquote>", "").replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
                file_bytes = io.BytesIO(file_content.encode('utf-8'))
                file_bytes.name = f"users_bot_{bot_id}.txt"
                telegram_bot.send_document(
                    message.chat.id,
                    file_bytes,
                    caption=f"📋 Danh sách user bot {bot_id}"
                )
            else:
                telegram_bot.reply_to(message, text, parse_mode="HTML")
            return
        
        # ====== CHECK ALL BOT ======
        if not TCPbot.bots:
            telegram_bot.reply_to(message, "❌ Không có bot nào trong hệ thống!")
            return
        
        text = "<blockquote><b>📊 TỔNG HỢP USER ALL BOT</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"🤖 Tổng bot: <b>{len(TCPbot.bots)}</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        
        total_users = 0
        bot_details = []
        
        for bot_id, bot in TCPbot.bots.items():
            access_list = bot.bot_config.get('access_bot', [])
            bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
            bot_uid = getattr(bot, 'botid', '?')
            running = "🟢 Online" if bot.running_event.is_set() else "🔴 Offline"
            
            total_users += len(access_list)
            bot_details.append({
                'bot_id': bot_id,
                'bot_name': bot_name,
                'bot_uid': bot_uid,
                'total': len(access_list),
                'running': running
            })
        
        bot_details.sort(key=lambda x: x['total'], reverse=True)
        
        for detail in bot_details:
            text += f"🤖 <b>Bot {detail['bot_id']}</b> {detail['running']}\n"
            text += f"├ Tên: <code>{detail['bot_name']}</code>\n"
            text += f"├ UID: <code>{detail['bot_uid']}</code>\n"
            text += f"└ 👥 User: <b>{detail['total']}</b>\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📦 Tổng user: <b>{total_users}</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"💡 Dùng <code>/checktime [botid]</code> để xem chi tiết</blockquote>"
        
        telegram_bot.reply_to(message, text, parse_mode="HTML")
        
    except ValueError:
        telegram_bot.reply_to(message, "❌ Bot ID phải là số!")
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")

# ===== API: /bio =====
@app.route("/bio", methods=["GET"])
def api_change_bio():
    try:
        bot_id = request.args.get("botid")
        bio_text = request.args.get("bio")
        
        if not bot_id or not bio_text:
            return jsonify({"status": "error", "message": "Missing botid or bio"}), 400
        
        if not bot_id.isdigit():
            return jsonify({"status": "error", "message": "botid must be number"}), 400
        
        bot_id = int(bot_id)
        
        if bot_id not in TCPbot.bots:
            return jsonify({"status": "error", "message": f"Bot {bot_id} not found"}), 404
        
        bot = TCPbot.bots[bot_id]
        
        token = getattr(bot, 'token', None)
        if not token:
            token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
        
        if not token:
            return jsonify({"status": "error", "message": "No token"}), 400
        
        success, msg = change_bio_via_token(token, bio_text)
        
        return jsonify({
            "status": "success" if success else "error",
            "message": msg,
            "data": {
                "bot_id": bot_id,
                "bot_name": getattr(bot, 'nickname', f'Bot #{bot_id}'),
                "bot_uid": getattr(bot, 'botid', ''),
                "bio": bio_text
            }
        }), 200 if success else 400
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ====== IMPORT BYTE.PY ======
import byte

# ====== LỆNH /KB - GỬI KẾT BẠN + CỘNG THỜI GIAN ======
@telegram_bot.message_handler(commands=['kb'])
def telegram_kb(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            telegram_bot.reply_to(
                message,
                "<b>❌ SAI CÚ PHÁP</b>\n💡 /kb [botid] [uid] [time]\n📌 /kb 1 123456789 7d",
                parse_mode="HTML"
            )
            return
        
        bot_id = int(parts[1])
        uid = parts[2]
        
        # ====== KIỂM TRA TIME ======
        if len(parts) >= 4:
            time_str = parts[3]
            import re
            if not re.match(r'^\d+[hdwmy]$', time_str.lower()):
                telegram_bot.reply_to(
                    message,
                    "<b>❌ SAI ĐỊNH DẠNG TIME</b>\n💡 Dùng: 1h, 1d, 7d, 1w, 1m, 1y",
                    parse_mode="HTML"
                )
                return
        else:
            time_str = None
        
        if bot_id not in TCPbot.bots:
            telegram_bot.reply_to(message, f"❌ Không tìm thấy bot {bot_id}!")
            return
        
        bot = TCPbot.bots[bot_id]
        if not bot.running_event.is_set():
            telegram_bot.reply_to(message, "❌ Bot đang offline!")
            return
        
        # Lấy token
        token = None
        if hasattr(bot, 'token') and bot.token:
            token = bot.token
        elif hasattr(bot, 'bot_config'):
            token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
        
        if not token:
            telegram_bot.reply_to(message, f"❌ Bot {bot_id} không có token!")
            return
        
        bot_name = getattr(bot, 'nickname', f'Bot #{bot_id}')
        bot_uid = getattr(bot, 'botid', '?')
        
        # ====== GỬI KẾT BẠN ======
        success, msg = byte.SendFriendRequest_HTTP(uid, token, bot_id)
        
        if not success:
            text = f"""
<blockquote>
<b>❌ GỬI KẾT BẠN THẤT BẠI</b>
━━━━━━━━━━━━━━━━━━━━━━
🤖 Bot: <code>{bot_name}</code>
🆔 UID: <code>{uid}</code>
⚠️ {msg}
━━━━━━━━━━━━━━━━━━━━━━
💡 Vui lòng kiểm tra lại!
</blockquote>
"""
            telegram_bot.reply_to(message, text, parse_mode="HTML")
            return
        
        # ====== CỘNG THỜI GIAN ======
        time_msg = ""
        expire_str = "Vĩnh viễn"
        
        if time_str:
            try:
                from datetime import datetime, timedelta
                now = datetime.now()
                num = int(time_str[:-1])
                unit = time_str[-1].lower()
                
                delta_map = {
                    'h': timedelta(hours=num),
                    'd': timedelta(days=num),
                    'w': timedelta(weeks=num),
                    'm': timedelta(days=num * 30),
                    'y': timedelta(days=num * 365),
                }
                delta = delta_map.get(unit, timedelta(days=1))
                
                expire_time = now + delta
                expire_str = expire_time.strftime("%Y-%m-%d %H:%M:%S")
                
                # Cập nhật vào bot_config
                if 'access_bot' not in bot.bot_config:
                    bot.bot_config['access_bot'] = []
                
                found = False
                for u in bot.bot_config['access_bot']:
                    if u.get('uid') == int(uid):
                        u['expire'] = expire_str
                        found = True
                        break
                
                if not found:
                    bot.bot_config['access_bot'].append({
                        'uid': int(uid),
                        'expire': expire_str
                    })
                
                TCPbot.save_config()
                time_msg = f"\n⏳ Hạn sử dụng: <code>{time_str}</code>"
                
            except Exception as e:
                time_msg = f"\n⚠️ Lỗi cộng time: {e}"
        
        # ====== KẾT QUẢ ======
        text = f"""
<blockquote>
<b>✅ GỬI KẾT BẠN VÀ CỘNG TIME THÀNH CÔNG</b>
━━━━━━━━━━━━━━━━━━━━━━
🤖 Bot: <code>{bot_name}</code>
🆔 Bot UID: <code>{bot_uid}</code>
👤 UID: <code>{uid}</code>
📩 {msg}
{time_msg}
📅 Hết hạn: <code>{expire_str}</code>
━━━━━━━━━━━━━━━━━━━━━━
💡 Liên hệ: @zanbackj
</blockquote>
"""
        telegram_bot.reply_to(message, text, parse_mode="HTML")
            
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")
        
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
        
        results = []
        success_count = 0
        online_bots = 0
        
        for bot_id, bot in TCPbot.bots.items():
            if not bot.running_event.is_set():
                continue
            online_bots += 1
            
            token = None
            if hasattr(bot, 'token') and bot.token:
                token = bot.token
            elif hasattr(bot, 'bot_config'):
                token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
            
            if not token:
                results.append({
                    'bot_id': bot_id,
                    'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                    'success': False,
                    'message': 'No token'
                })
                continue
            
            success, msg = byte.SendFriendRequest_HTTP(uid, token, bot_id)
            
            if success:
                success_count += 1
            
            results.append({
                'bot_id': bot_id,
                'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                'success': success,
                'message': msg
            })
        
        if online_bots > 0:
            msg = f"<blockquote><b>✅ GỬI KẾT BẠN ALL THÀNH CÔNG</b>\n━━━━━━━━━━━━━━━━━━━━\n🆔 <b>UID:</b> <code>{uid}</code>\n✅ <b>Thành công:</b> {success_count}/{online_bots}\n━━━━━━━━━━━━━━━━━━━━\n"
            
            for r in results:
                status = "✅" if r.get('success') else "❌"
                msg += f"{status} <b>{r.get('bot_name')}</b>: {r.get('message')}\n"
            
            msg += "━━━━━━━━━━━━━━━━━━━━\n⚡ Đã gửi!</blockquote>"
            telegram_bot.reply_to(message, msg, parse_mode="HTML")
        else:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ GỬI KẾT BẠN ALL THẤT BẠI</b>\n━━━━━━━━━━━━━━━━━━━━\n🆔 <b>UID:</b> <code>{uid}</code>\n⚠️ <b>Lý do:</b> Không có bot online!\n━━━━━━━━━━━━━━━━━━━━\n💡 Kiểm tra lại bot!</blockquote>",
                parse_mode="HTML"
            )
            
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")        
        
@telegram_bot.message_handler(commands=['checkbot'])
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
        total_count = len(TCPbot.bots)
        
        text = "<blockquote><b>📊 DANH SÁCH BOT</b>\n"
        text += f"━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"📌 Tổng bot: <b>{total_count}</b>\n\n"
        
        for bid, bot in TCPbot.bots.items():
            running = bot.running_event.is_set() if bot.running_event else False
            nickname = getattr(bot, 'nickname', 'Chưa đồng bộ')
            uid_bot = getattr(bot, 'botid', 'Trống')
            
            if running:
                online_count += 1
                status = "🟢 Online"
            else:
                offline_count += 1
                status = "🔴 Offline"
            
            text += f"🤖 Bot {bid}\n"
            text += f"├ Tên: {nickname}\n"
            text += f"├ UID: <code>{uid_bot}</code>\n"
            text += f"└ Trạng thái: {status}\n\n"
        
        text += f"━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"🟢 Online: <b>{online_count}</b>  |  🔴 Offline: <b>{offline_count}</b>\n"
        text += f"</blockquote>"
        
        telegram_bot.reply_to(message, text, parse_mode="HTML")
        
    except Exception as e:
        telegram_bot.reply_to(message, f"ERROR: {e}")
        print("CHECKBOTS ERROR:", e) 
        
@telegram_bot.message_handler(commands=['online'])
def telegram_online_bot(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "💡 Dùng: <code>/online [botid]</code>\n"
                "📌 Ví dụ: <code>/online 1</code>\n"
                "📌 Ví dụ: <code>/online all</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        target = parts[1]
        
        if target.lower() == "all":
            online_bots = []
            offline_bots = []
            
            for bot_id, bot in TCPbot.bots.items():
                if bot.running_event.is_set():
                    online_bots.append(bot_id)
                else:
                    offline_bots.append(bot_id)
            
            if not offline_bots:
                telegram_bot.reply_to(
                    message,
                    f"<blockquote><b>✅ TẤT CẢ BOT ĐÃ ONLINE</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🟢 Online: <b>{len(online_bots)}</b> bot\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⚡ Không có bot nào offline!</blockquote>",
                    parse_mode="HTML"
                )
                return
            
            # Bật từng bot offline
            success_count = 0
            for bot_id in offline_bots:
                try:
                    bot = TCPbot.bots[bot_id]
                    if not bot.running_event.is_set():
                        # Reset và start lại
                        bot.cleanup()
                        time.sleep(0.5)
                        bot.running_event.set()
                        bot.started = False
                        bot.start()
                        success_count += 1
                        time.sleep(1)
                except Exception as e:
                    print(f"[ONLINE ALL] Bot {bot_id} error: {e}")
            
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>✅ BẬT ONLINE ALL BOT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Thành công: <b>{success_count}/{len(offline_bots)}</b>\n"
                f"🟢 Online hiện tại: <b>{len(online_bots) + success_count}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Đã bật tất cả bot!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        bot_id = int(target)
        
        if bot_id not in TCPbot.bots:
            telegram_bot.reply_to(message, f"❌ Không tìm thấy bot {bot_id}!")
            return
        
        bot = TCPbot.bots[bot_id]
        
        if bot.running_event.is_set():
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>🟢 BOT ĐÃ ONLINE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot ID: <code>{bot_id}</code>\n"
                f"📛 Name: <code>{getattr(bot, 'nickname', 'Unknown')}</code>\n"
                f"🆔 UID: <code>{getattr(bot, 'botid', '?')}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Bot đang hoạt động!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        # Bật bot
        bot.cleanup()
        time.sleep(0.5)
        bot.running_event.set()
        bot.started = False
        bot.start()
        time.sleep(2)
        
        if bot.running_event.is_set():
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>✅ BẬT BOT THÀNH CÔNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot ID: <code>{bot_id}</code>\n"
                f"📛 Name: <code>{getattr(bot, 'nickname', 'Unknown')}</code>\n"
                f"🆔 UID: <code>{getattr(bot, 'botid', '?')}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Bot đã online!</blockquote>",
                parse_mode="HTML"
            )
        else:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ BẬT BOT THẤT BẠI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot ID: <code>{bot_id}</code>\n"
                f"⚠️ Lý do: Bot không thể kết nối!\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 Kiểm tra token hoặc mạng!</blockquote>",
                parse_mode="HTML"
            )
        
    except ValueError:
        telegram_bot.reply_to(message, "❌ Bot ID phải là số hoặc 'all'!")
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")


# ===== LỆNH TELEGRAM: /offline =====
@telegram_bot.message_handler(commands=['offline'])
def telegram_offline_bot(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "💡 Dùng: <code>/offline [botid]</code>\n"
                "📌 Ví dụ: <code>/offline 1</code>\n"
                "📌 Ví dụ: <code>/offline all</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        target = parts[1]
        
        if target.lower() == "all":
            online_bots = []
            
            for bot_id, bot in TCPbot.bots.items():
                if bot.running_event.is_set():
                    online_bots.append(bot_id)
            
            if not online_bots:
                telegram_bot.reply_to(
                    message,
                    f"<blockquote><b>⚠️ TẤT CẢ BOT ĐÃ OFFLINE</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🔴 Offline: <b>{len(TCPbot.bots)}</b> bot\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"⚡ Không có bot nào online!</blockquote>",
                    parse_mode="HTML"
                )
                return
            
            # Tắt từng bot online
            success_count = 0
            for bot_id in online_bots:
                try:
                    bot = TCPbot.bots[bot_id]
                    if bot.running_event.is_set():
                        bot.cleanup()
                        bot.running_event.clear()
                        success_count += 1
                        time.sleep(0.5)
                except Exception as e:
                    print(f"[OFFLINE ALL] Bot {bot_id} error: {e}")
            
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>✅ TẮT ONLINE ALL BOT</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Thành công: <b>{success_count}/{len(online_bots)}</b>\n"
                f"🔴 Offline hiện tại: <b>{len(TCPbot.bots)}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Đã tắt tất cả bot!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        bot_id = int(target)
        
        if bot_id not in TCPbot.bots:
            telegram_bot.reply_to(message, f"❌ Không tìm thấy bot {bot_id}!")
            return
        
        bot = TCPbot.bots[bot_id]
        
        if not bot.running_event.is_set():
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>🔴 BOT ĐÃ OFFLINE</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot ID: <code>{bot_id}</code>\n"
                f"📛 Name: <code>{getattr(bot, 'nickname', 'Unknown')}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Bot đã dừng hoạt động!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        # Tắt bot
        bot.cleanup()
        bot.running_event.clear()
        
        telegram_bot.reply_to(
            message,
            f"<blockquote><b>✅ TẮT BOT THÀNH CÔNG</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 Bot ID: <code>{bot_id}</code>\n"
            f"📛 Name: <code>{getattr(bot, 'nickname', 'Unknown')}</code>\n"
            f"🆔 UID: <code>{getattr(bot, 'botid', '?')}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Bot đã offline!</blockquote>",
            parse_mode="HTML"
        )
        
    except ValueError:
        telegram_bot.reply_to(message, "❌ Bot ID phải là số hoặc 'all'!")
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ Lỗi: {str(e)}")

# ===== LỆNH TELEGRAM: /resetbot =====
@telegram_bot.message_handler(commands=['resetbot'])
def telegram_reset_bot(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Bạn không có quyền sử dụng lệnh này!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ SAI CÚ PHÁP</b>\n"
                "💡 Dùng: <code>/resetbot [botid]</code>\n"
                "📌 Ví dụ: <code>/resetbot 1</code>\n"
                "📌 Ví dụ: <code>/resetbot all</code></blockquote>",
                parse_mode="HTML"
            )
            return
        
        target = parts[1]
        
        if target.lower() == "all":
            bot_list = list(TCPbot.bots.keys())
            
            if not bot_list:
                telegram_bot.reply_to(message, "❌ Không có bot nào để reset!")
                return
            
            success_count = 0
            for bot_id in bot_list:
                try:
                    bot = TCPbot.bots[bot_id]
                    bot.cleanup()
                    time.sleep(0.5)
                    bot.running_event.set()
                    bot.started = False
                    bot.start()
                    success_count += 1
                    time.sleep(1)
                except Exception as e:
                    print(f"[RESET ALL] Bot {bot_id} error: {e}")
            
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>✅ RESET ALL BOT THÀNH CÔNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ Thành công: <b>{success_count}/{len(bot_list)}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Đã reset tất cả bot!</blockquote>",
                parse_mode="HTML"
            )
            return
        
        bot_id = int(target)
        
        if bot_id not in TCPbot.bots:
            telegram_bot.reply_to(message, f"❌ Không tìm thấy bot {bot_id}!")
            return
        
        bot = TCPbot.bots[bot_id]
        
        # Reset bot
        bot.cleanup()
        time.sleep(1)
        bot.running_event.set()
        bot.started = False
        bot.start()
        
        time.sleep(3)
        
        if bot.running_event.is_set():
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>✅ RESET BOT THÀNH CÔNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot ID: <code>{bot_id}</code>\n"
                f"📛 Name: <code>{getattr(bot, 'nickname', 'Unknown')}</code>\n"
                f"🆔 UID: <code>{getattr(bot, 'botid', '?')}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⚡ Bot đã được khởi động lại!</blockquote>",
                parse_mode="HTML"
            )
        else:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ RESET BOT THẤT BẠI</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot ID: <code>{bot_id}</code>\n"
                f"⚠️ Lý do: Bot không thể kết nối!\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 Kiểm tra token hoặc mạng!</blockquote>",
                parse_mode="HTML"
            )
        
    except ValueError:
        telegram_bot.reply_to(message, "❌ Bot ID phải là số hoặc 'all'!")
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
        url = f"http://127.0.0.1:2010/xkb?uid={uid}&botid={bot_id}"
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
        url = f"http://127.0.0.1:2010/xkb/all?uid={uid}"
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
 if not token: return "RES_INVALID", 201
 I=TCPbot.add_bot(token)
 if I["status"]:
  TCPbot.bots[I["bot_id"]].start()
  return "RES_OK", 200
 else: return str(I["message"]), 201
        
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

@app.route("/bio/all", methods=["GET"])
def api_change_bio_all():
    try:
        bio_text = request.args.get("bio")
        
        if not bio_text:
            return jsonify({"status": "error", "message": "Missing bio"}), 400
        
        results = []
        success_count = 0
        online_bots = 0
        
        for bot_id, bot in TCPbot.bots.items():
            if not bot.running_event.is_set():
                continue
            online_bots += 1
            
            token = getattr(bot, 'token', None)
            if not token:
                token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
            
            if not token:
                results.append({
                    'bot_id': bot_id,
                    'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                    'success': False,
                    'message': 'No token'
                })
                continue
            
            success, msg = change_bio_via_token(token, bio_text)
            if success:
                success_count += 1
            
            results.append({
                'bot_id': bot_id,
                'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                'success': success,
                'message': msg
            })
        
        return jsonify({
            "status": "success",
            "message": f"Completed: {success_count}/{online_bots} success",
            "data": {
                "bio": bio_text,
                "total_bots": online_bots,
                "success": success_count,
                "results": results
            }
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

        
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
        
        # Hủy kết bạn
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

@app.route("/voqd", methods=["GET"])
def api_join_clan():
    try:
        bot_id = request.args.get("botid")
        clan_id = request.args.get("idqd")
        region = request.args.get("region", "")
        
        if not bot_id or not clan_id:
            return jsonify({"status": "error", "message": "Missing botid or idqd"}), 400
        
        if not bot_id.isdigit() or not clan_id.isdigit():
            return jsonify({"status": "error", "message": "botid and idqd must be number"}), 400
        
        bot_id = int(bot_id)
        
        if bot_id not in TCPbot.bots:
            return jsonify({"status": "error", "message": f"Bot {bot_id} not found"}), 404
        
        bot = TCPbot.bots[bot_id]
        
        token = getattr(bot, 'token', None)
        if not token:
            token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
        
        if not token:
            return jsonify({"status": "error", "message": "No token"}), 400
        
        if not region:
            region = get_region_from_jwt(token)
        
        success, msg = request_join_clan(token, clan_id, region)
        
        return jsonify({
            "status": "success" if success else "error",
            "message": msg,
            "data": {
                "bot_id": bot_id,
                "bot_name": getattr(bot, 'nickname', f'Bot #{bot_id}'),
                "clan_id": clan_id,
                "region": region
            }
        }), 200 if success else 400
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/online", methods=["GET"])
def api_online_bot():
    try:
        bot_id = request.args.get("botid")
        
        if not bot_id:
            return jsonify({"status": "error", "message": "Missing botid"}), 400
        
        if bot_id.lower() == "all":
            results = []
            success_count = 0
            
            for bid, bot in TCPbot.bots.items():
                if not bot.running_event.is_set():
                    try:
                        bot.cleanup()
                        time.sleep(0.5)
                        bot.running_event.set()
                        bot.started = False
                        bot.start()
                        success_count += 1
                        time.sleep(1)
                        results.append({
                            "bot_id": bid,
                            "success": True,
                            "message": "Started"
                        })
                    except Exception as e:
                        results.append({
                            "bot_id": bid,
                            "success": False,
                            "message": str(e)
                        })
                else:
                    results.append({
                        "bot_id": bid,
                        "success": True,
                        "message": "Already online"
                    })
            
            return jsonify({
                "status": "success",
                "message": f"Started {success_count} bots",
                "data": {
                    "total": len(TCPbot.bots),
                    "success": success_count,
                    "results": results
                }
            }), 200
        
        if not bot_id.isdigit():
            return jsonify({"status": "error", "message": "botid must be number or 'all'"}), 400
        
        bid = int(bot_id)
        
        if bid not in TCPbot.bots:
            return jsonify({"status": "error", "message": f"Bot {bid} not found"}), 404
        
        bot = TCPbot.bots[bid]
        
        if bot.running_event.is_set():
            return jsonify({
                "status": "success",
                "message": "Bot already online",
                "data": {
                    "bot_id": bid,
                    "name": getattr(bot, 'nickname', 'Unknown'),
                    "status": "online"
                }
            }), 200
        
        bot.cleanup()
        time.sleep(0.5)
        bot.running_event.set()
        bot.started = False
        bot.start()
        time.sleep(2)
        
        if bot.running_event.is_set():
            return jsonify({
                "status": "success",
                "message": "Bot started successfully",
                "data": {
                    "bot_id": bid,
                    "name": getattr(bot, 'nickname', 'Unknown'),
                    "status": "online"
                }
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Bot failed to start"
            }), 500
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/offline", methods=["GET"])
def api_offline_bot():
    try:
        bot_id = request.args.get("botid")
        
        if not bot_id:
            return jsonify({"status": "error", "message": "Missing botid"}), 400
        
        if bot_id.lower() == "all":
            results = []
            success_count = 0
            
            for bid, bot in TCPbot.bots.items():
                if bot.running_event.is_set():
                    try:
                        bot.cleanup()
                        bot.running_event.clear()
                        success_count += 1
                        results.append({
                            "bot_id": bid,
                            "success": True,
                            "message": "Stopped"
                        })
                    except Exception as e:
                        results.append({
                            "bot_id": bid,
                            "success": False,
                            "message": str(e)
                        })
                else:
                    results.append({
                        "bot_id": bid,
                        "success": True,
                        "message": "Already offline"
                    })
            
            return jsonify({
                "status": "success",
                "message": f"Stopped {success_count} bots",
                "data": {
                    "total": len(TCPbot.bots),
                    "success": success_count,
                    "results": results
                }
            }), 200
        
        if not bot_id.isdigit():
            return jsonify({"status": "error", "message": "botid must be number or 'all'"}), 400
        
        bid = int(bot_id)
        
        if bid not in TCPbot.bots:
            return jsonify({"status": "error", "message": f"Bot {bid} not found"}), 404
        
        bot = TCPbot.bots[bid]
        
        if not bot.running_event.is_set():
            return jsonify({
                "status": "success",
                "message": "Bot already offline",
                "data": {
                    "bot_id": bid,
                    "name": getattr(bot, 'nickname', 'Unknown'),
                    "status": "offline"
                }
            }), 200
        
        bot.cleanup()
        bot.running_event.clear()
        
        return jsonify({
            "status": "success",
            "message": "Bot stopped successfully",
            "data": {
                "bot_id": bid,
                "name": getattr(bot, 'nickname', 'Unknown'),
                "status": "offline"
            }
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/resetbot", methods=["GET"])
def api_reset_bot():
    try:
        bot_id = request.args.get("botid")
        
        if not bot_id:
            return jsonify({"status": "error", "message": "Missing botid"}), 400
        
        if bot_id.lower() == "all":
            results = []
            success_count = 0
            
            for bid, bot in TCPbot.bots.items():
                try:
                    bot.cleanup()
                    time.sleep(0.5)
                    bot.running_event.set()
                    bot.started = False
                    bot.start()
                    success_count += 1
                    time.sleep(1)
                    results.append({
                        "bot_id": bid,
                        "success": True,
                        "message": "Reset successful"
                    })
                except Exception as e:
                    results.append({
                        "bot_id": bid,
                        "success": False,
                        "message": str(e)
                    })
            
            return jsonify({
                "status": "success",
                "message": f"Reset {success_count} bots",
                "data": {
                    "total": len(TCPbot.bots),
                    "success": success_count,
                    "results": results
                }
            }), 200
        
        if not bot_id.isdigit():
            return jsonify({"status": "error", "message": "botid must be number or 'all'"}), 400
        
        bid = int(bot_id)
        
        if bid not in TCPbot.bots:
            return jsonify({"status": "error", "message": f"Bot {bid} not found"}), 404
        
        bot = TCPbot.bots[bid]
        
        bot.cleanup()
        time.sleep(1)
        bot.running_event.set()
        bot.started = False
        bot.start()
        
        time.sleep(3)
        
        if bot.running_event.is_set():
            return jsonify({
                "status": "success",
                "message": "Bot reset successfully",
                "data": {
                    "bot_id": bid,
                    "name": getattr(bot, 'nickname', 'Unknown'),
                    "status": "online"
                }
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Bot failed to restart",
                "data": {
                    "bot_id": bid,
                    "name": getattr(bot, 'nickname', 'Unknown'),
                    "status": "offline"
                }
            }), 500
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/roiqd", methods=["GET"])
def api_quit_clan():
    try:
        bot_id = request.args.get("botid")
        clan_id = request.args.get("clanid")
        region = request.args.get("region", "")
        
        if not bot_id or not clan_id:
            return jsonify({"status": "error", "message": "Missing botid or clanid"}), 400
        
        if not bot_id.isdigit() or not clan_id.isdigit():
            return jsonify({"status": "error", "message": "botid and clanid must be number"}), 400
        
        bot_id = int(bot_id)
        
        if bot_id not in TCPbot.bots:
            return jsonify({"status": "error", "message": f"Bot {bot_id} not found"}), 404
        
        bot = TCPbot.bots[bot_id]
        
        token = getattr(bot, 'token', None)
        if not token:
            token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
        
        if not token:
            return jsonify({"status": "error", "message": "No token"}), 400
        
        if not region:
            region = get_region_from_jwt(token)
        
        success, msg = quit_clan(token, clan_id, region)
        
        return jsonify({
            "status": "success" if success else "error",
            "message": msg,
            "data": {
                "bot_id": bot_id,
                "bot_name": getattr(bot, 'nickname', f'Bot #{bot_id}'),
                "clan_id": clan_id,
                "region": region
            }
        }), 200 if success else 400
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/voqdall", methods=["GET"])
def api_join_clan_all():
    try:
        clan_id = request.args.get("idqd")
        region = request.args.get("region", "")
        
        if not clan_id:
            return jsonify({"status": "error", "message": "Missing idqd"}), 400
        
        if not clan_id.isdigit():
            return jsonify({"status": "error", "message": "clan_id must be number"}), 400
        
        results = []
        success_count = 0
        online_bots = 0
        
        for bot_id, bot in TCPbot.bots.items():
            if not bot.running_event.is_set():
                continue
            online_bots += 1
            
            token = getattr(bot, 'token', None)
            if not token:
                token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
            
            if not token:
                results.append({
                    'bot_id': bot_id,
                    'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                    'success': False,
                    'message': 'No token'
                })
                continue
            
            if not region:
                region = get_region_from_jwt(token)
            
            success, msg = request_join_clan(token, clan_id, region)
            if success:
                success_count += 1
            
            results.append({
                'bot_id': bot_id,
                'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                'success': success,
                'message': msg
            })
        
        return jsonify({
            "status": "success",
            "message": f"Completed: {success_count}/{online_bots} success",
            "data": {
                "clan_id": clan_id,
                "region": region,
                "total_bots": online_bots,
                "success": success_count,
                "results": results
            }
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/roiqdall", methods=["GET"])
def api_quit_clan_all():
    try:
        clan_id = request.args.get("clanid")
        region = request.args.get("region", "")
        
        if not clan_id:
            return jsonify({"status": "error", "message": "Missing clanid"}), 400
        
        if not clan_id.isdigit():
            return jsonify({"status": "error", "message": "clan_id must be number"}), 400
        
        results = []
        success_count = 0
        online_bots = 0
        
        for bot_id, bot in TCPbot.bots.items():
            if not bot.running_event.is_set():
                continue
            online_bots += 1
            
            token = getattr(bot, 'token', None)
            if not token:
                token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
            
            if not token:
                results.append({
                    'bot_id': bot_id,
                    'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                    'success': False,
                    'message': 'No token'
                })
                continue
            
            if not region:
                region = get_region_from_jwt(token)
            
            success, msg = quit_clan(token, clan_id, region)
            if success:
                success_count += 1
            
            results.append({
                'bot_id': bot_id,
                'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                'success': success,
                'message': msg
            })
        
        return jsonify({
            "status": "success",
            "message": f"Completed: {success_count}/{online_bots} success",
            "data": {
                "clan_id": clan_id,
                "region": region,
                "total_bots": online_bots,
                "success": success_count,
                "results": results
            }
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ====== SỬA LẠI HÀM /clearfriends TRONG start.py ======

@app.route("/clearfriends", methods=["GET"])
def api_clear_friends():
    """Xóa tất cả bạn bè của bot (không cần UID)"""
    try:
        import requests  # THÊM DÒNG NÀY VÀO ĐẦU HÀM
        bot_id = request.args.get('botid')
        
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
            token = bot.bot_config.get('auth_bot_login', {}).get('access_token')
        
        if not token:
            return jsonify({'status': 'error', 'message': 'No token'}), 400
        
        # ====== LẤY DANH SÁCH BẠN BÈ ======
        headers = {
            'Authorization': f'Bearer {token}',
            'User-Agent': 'UnityPlayer/2022.3.47f1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Connection': 'Keep-Alive'
        }
        
        payload = bytes.fromhex('598fcaf07839308ff287aca3ae0a0617')
        friends = []
        
        try:
            response = requests.post('https://clientbp.ggpolarbear.com/GetFriend', headers=headers, data=payload, verify=False, timeout=10)
            if response.status_code == 200:
                from lib import protobuf_dec
                import json
                decoded = protobuf_dec(response.content.hex())
                parsed = json.loads(decoded)
                
                if "1" in parsed and isinstance(parsed["1"], list):
                    for friend in parsed["1"]:
                        friends.append(friend.get("1", ""))
        except Exception as e:
            print(f"[DEBUG] GetFriend error: {e}")
            return jsonify({
                'status': 'error',
                'message': f'GetFriend failed: {str(e)}'
            }), 500
        
        if not friends:
            return jsonify({
                'status': 'success',
                'message': f'Bot {bot_id} không có bạn bè để xóa!',
                'data': {
                    'bot_id': bot_id,
                    'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                    'total_friends': 0,
                    'removed': 0
                }
            }), 200
        
        # ====== XÓA TỪNG BẠN ======
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        
        KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
        IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
        
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
        
        removed = 0
        failed = 0
        failed_list = []
        
        for friend_uid in friends:
            try:
                encrypted_id = encrypt_uid(str(friend_uid))
                if not encrypted_id:
                    failed += 1
                    failed_list.append(friend_uid)
                    continue
                
                plain_text_payload = f'08a7c4839f1e10{encrypted_id}1801'
                cipher = AES.new(KEY, AES.MODE_CBC, IV)
                data = cipher.encrypt(pad(bytes.fromhex(plain_text_payload), AES.block_size))
                
                headers_remove = {
                    'X-Unity-Version': '2018.4.11f1',
                    'ReleaseVersion': 'OB54',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-GA': 'v1 1',
                    'Authorization': f'Bearer {token}',
                    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
                    'Connection': 'Keep-Alive',
                    'Accept-Encoding': 'gzip'
                }
                
                response = requests.post(
                    'https://clientbp.ggpolarbear.com/RemoveFriend',
                    headers=headers_remove,
                    data=data,
                    verify=False,
                    timeout=10
                )
                
                if response.status_code == 200:
                    removed += 1
                else:
                    failed += 1
                    failed_list.append(friend_uid)
                    
                time.sleep(0.2)
                
            except Exception as e:
                failed += 1
                failed_list.append(friend_uid)
        
        return jsonify({
            'status': 'success',
            'message': f'Đã xóa {removed} bạn, thất bại {failed}',
            'data': {
                'bot_id': bot_id,
                'bot_name': getattr(bot, 'nickname', f'Bot #{bot_id}'),
                'total_friends': len(friends),
                'removed': removed,
                'failed': failed,
                'failed_list': failed_list[:20]
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
 for bot in TCPbot.bots.values(): bot.start()

def restart_bot():
    print("🔄 Bot mất kết nối! Khởi động lại sau 5 giây...")
    time.sleep(5)
    os.execv(sys.executable, ['python'] + sys.argv)

def ping_api_keep_alive():
    url = "http://zantreobot.onrender.com"
    
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

def run_telegram():  
    print("Telegram bot đang chạy...") 
    telegram_bot.infinity_polling()

if __name__ == "__main__":
    start_ping_thread() 
    threading.Thread(target=run_telegram, daemon=True).start()
    threading.Thread(target=sbot, daemon=True).start()
    app.run(host="0.0.0.0", port=2010)