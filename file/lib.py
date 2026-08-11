import threading, json, requests, time, random, datetime, string
from ReQAPI import *
import json, os, datetime


key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
 
host = ""
class File:
 @staticmethod
 def add(filename):
  try:
   res = requests.post("{0}/add-file?filename={1}".format(host, filename), timeout=10)
   if res.status_code == 200:
    return True, res.json().get("message", "File created")
   return False, ""
  except requests.RequestException as e: return False, ""
  except json.JSONDecodeError as e: return False, ""
  except Exception as e: return False, ""

 @staticmethod
 def delete(filename):
  try:
   res = requests.delete("{0}/del-file?filename={1}".format(host, filename), timeout=10)
   if res.status_code == 200:
    return True, res.json().get("message", "File deleted")
   return False, ""
  except Exception as e: return False, ""

 @staticmethod
 def check(filename):
  try:
   res = requests.get("{0}/check?filename={1}".format(host, filename), timeout=10)
   if res.status_code == 200:
    content = res.json().get("content", "")
    return True, content if content else "[]"
   return False, ""
  except Exception as e: return False, ""

 @staticmethod
 def edit(filename, content):
  try:
   content_str = json.dumps(content) if isinstance(content, (list, dict)) else content
   res = requests.put("{0}/edit-file?filename={1}".format(host, filename), data=content_str, timeout=10)
   if res.status_code == 200:
    return True, res.json().get("message", "File updated")
   return False, ""
  except Exception as e: return False, ""

class UserLikeLimit:
 filename = "user_likes_limit.json"
 @staticmethod
 def all(): return UserLikeLimit._load()
 @staticmethod
 def _load():
  ok, content = File.check(UserLikeLimit.filename)
  return json.loads(content) if ok else {}
 @staticmethod
 def _save(data):
  File.edit(UserLikeLimit.filename, data)

 @staticmethod
 def get(user_id: int):
  user_id = str(user_id)
  data = UserLikeLimit._load()
  today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
  info = data.get(user_id, {"count": 0, "limit": 3, "date": today})

  if info.get("date") != today:
   info["count"] = 0
   info["date"] = today
  allowed = info["count"] < info["limit"]
  if allowed: info["count"] += 1
  data[user_id] = info
  UserLikeLimit._save(data)
  return allowed, f"{info['count']}/{info['limit']}"

 @staticmethod
 def add(user_id: int, count: int):
  user_id = str(user_id)
  data = UserLikeLimit._load()
  today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
  data[user_id] = {"count": 0, "limit": count, "date": today}
  UserLikeLimit._save(data)



class GiftCode:
 filename = "giftcode.json"
 @staticmethod
 def _load():
  ok, content = File.check(GiftCode.filename)
  return json.loads(content) if ok else {}
 @staticmethod
 def _save(data):
  File.edit(GiftCode.filename, data)
 
 @staticmethod
 def generate_code():
  chars = string.ascii_uppercase + string.digits
  code = "G-" + ''.join(random.choices(chars, k=5))
  return code
 
 @staticmethod
 def create(time_str, max_uses, creator_id):
  data = GiftCode._load()
  code = GiftCode.generate_code()
  while code in data:
   code = GiftCode.generate_code()
  
  now = datetime.datetime.now()
  data[code] = {
   "time": time_str,
   "max_uses": max_uses,
   "used_count": 0,
   "used_by": [],
   "created_by": creator_id,
   "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
   "status": "active"
  }  
  GiftCode._save(data)
  return code
 
 @staticmethod
 def redeem(code, user_id):
  data = GiftCode._load()
  if code not in data: return False, "Mã giftcode không tồn tại!"
  gift = data[code]
  if gift["status"] != "active": return False, "Not available!"
  if gift["used_count"] >= gift["max_uses"]:
   return False, "Mã giftcode đã hết lượt sử dụng :))"
  if user_id in gift["used_by"]:
   return False, "Mày đã sử dụng mã giftcode này rồi!"
  gift["used_count"] += 1
  gift["used_by"].append(user_id)
  GiftCode._save(data)
  return True, gift["time"]
 
 @staticmethod
 def list_all():
  data = GiftCode._load()
  return data
 
 @staticmethod
 def delete_code(code):
  data = GiftCode._load()
  if code in data:
   del data[code]
   GiftCode._save(data)
   return True
  return False

class AdminManager:
 filename = "admin_list.json"
 _cached_data = None

 @staticmethod
 def _load():
  ok, content = File.check(AdminManager.filename)
  return json.loads(content) if ok else {}

 @staticmethod
 def _save(data):
  File.edit(AdminManager.filename, data)
  AdminManager._cached_data = data

 @staticmethod
 def refresh():
  AdminManager._cached_data = AdminManager._load()

 @staticmethod
 def add_admin(bot_id, admin_id):
  data = AdminManager._cached_data or AdminManager._load()
  bot_key = str(bot_id)
  if bot_key not in data:
   data[bot_key] = []
  if admin_id not in data[bot_key]:
   data[bot_key].append(admin_id)
   AdminManager._save(data)
   return True
  return False

 @staticmethod
 def is_admin(bot_id, user_id):
  default_admins = [16104663154]
  if user_id in default_admins: return
  if AdminManager._cached_data is None:
   AdminManager._cached_data = AdminManager._load()

  data = AdminManager._cached_data
  bot_key = str(bot_id)
  return user_id in data.get(bot_key, [])

 @staticmethod
 def get_admins(bot_id):
  default_admins = [16104663154]
  if AdminManager._cached_data is None:
   AdminManager._cached_data = AdminManager._load()

  data = AdminManager._cached_data
  bot_key = str(bot_id)
  bot_admins = data.get(bot_key, [])
  return list(set(default_admins + bot_admins))

class UserRegister:
    filename = "user_register.json"
    _cache = None


    @staticmethod
    def _load():
        if UserRegister._cache is not None:
            return UserRegister._cache
        if not os.path.exists(UserRegister.filename):
            with open(UserRegister.filename, "w", encoding="utf-8") as f:
                json.dump({}, f)
        try:
            with open(UserRegister.filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = {}
        UserRegister._cache = data
        return data

    @staticmethod
    def _save(data):
        UserRegister._cache = data
        with open(UserRegister.filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def register(user_id: int, name: str):
        user_id = str(user_id)
        data = UserRegister._load()
        if user_id in data:
            return False, "User đã đăng ký trước đó!"
        now = datetime.datetime.now()
        data[user_id] = {
            "Nickname": name,
            "Time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "IsRegister": True
        }
        UserRegister._save(data)
        return True, "Đăng ký thành công!"

    @staticmethod
    def is_registered(user_id: int):
        user_id = str(user_id)
        data = UserRegister._load()
        return user_id in data

    @staticmethod
    def unregister(user_id: int):
        user_id = str(user_id)
        data = UserRegister._load()
        if user_id in data:
            del data[user_id]
            UserRegister._save(data)
            return True, "Đã hủy đăng ký!"
        return False, "User không tồn tại!"



def grcolor(): return random.choice(["FFFF00", "00FF00", "87CEEB", "AAFF00"])
class data1200:
 def __init__(self, data):
  self.valid = False
  try:
   info = json.loads(protobuf_dec(data.hex()[10:])).get("5", {})
   if not isinstance(info, dict): return None
   PlayerId, ClientId, self.type = info.get("1"), info.get("2"), info.get("3")
   if self.type == 1: PlayerId, ClientId = info["1"], info["2"]
   elif self.type == 2: PlayerId = ClientId = info["1"]
   self.cid = ClientId
   self.uid = PlayerId
   self.name = info.get("9", {}).get("1", "")
   self.message = ("/bot" if "8" in info else info.get("4", "")).lower()
   self.valid = True
  except Exception as e:
   self.cid = self.uid = self.name = self.message = self.type = None

def extract_uid_fields(data):
 uids, seen = [], set()
 def add_uid(value):
  if isinstance(value, str) and value.isdigit():
   value = int(value)
  if isinstance(value, int) and value not in seen:
   seen.add(value)
   uids.append(value)
 if "1" in data: add_uid(data["1"])
 if "5" in data and isinstance(data["5"], dict):
  field_5 = data["5"]
  if "1" in field_5: add_uid(field_5["1"])
  if "6" in field_5 and isinstance(field_5["6"], list):
   for item in field_5["6"]:
    if isinstance(item, dict) and "1" in item:
     add_uid(item["1"])
 return uids

def get_player_status(data):
 status_info = {
 0: ("OFFLINE", "{}"),
 1: ("ONLINE", "{}"),
 2: ("In Squads", "{}"),
 3: ("In Games", "{}"),
 4: ("In Rooms", "{}"),
 5: ("In Games", "{}"),
 6: ("In Social Island Mode", "{}"),
 7: ("In Social Island Mode", "{}")
 }
 player = data.get("5", {}).get("1")
 if not player: return {"status": status_info[0][1].format(status_info[0][0])}
 uid = player.get("1")
 stt = player.get("3", 0)
 name, color = status_info.get(stt, ("null", "[AAAAAA]{}"))
 base = {"status": color.format(name), "uid": uid}
 if name == "In Squads":
  g, c = player.get("9"), player.get("10")
  if g is not None and c is not None: base["group"] = "{}/{}".format(g, c + 1)
 if name == "In Rooms":
  base["roomid"] = player.get("15")
 return base

def fstr(text):
 data = bytes([91, 34, 100, 225, 187, 165, 34, 44, 32, 34, 196, 145, 225, 187, 165, 34, 44, 32, 34, 225, 187, 139, 116, 34, 44, 32, 34, 195, 169, 111, 34, 44, 32, 34, 98, 195, 186, 34, 44, 32, 34, 225, 187, 147, 110, 34, 44, 32, 34, 225, 186, 183, 99, 34, 44, 32, 34, 225, 187, 165, 99, 34, 44, 32, 34, 196, 169, 34, 44, 32, 34, 99, 225, 186, 183, 99, 34, 44, 32, 34, 108, 225, 187, 147, 110, 34, 44, 32, 34, 98, 117, 225, 187, 147, 105, 34, 44, 32, 34, 108, 105, 195, 170, 110, 34, 44, 32, 34, 98, 117, 102, 102, 34, 44, 32, 34, 196, 145, 196, 169, 34, 44, 32, 34, 99, 97, 118, 101, 34, 44, 32, 34, 103, 195, 161, 105, 34, 44, 32, 34, 116, 114, 97, 105, 34, 44, 32, 34, 115, 101, 120, 34, 44, 32, 34, 120, 120, 120, 34, 44, 32, 34, 112, 111, 114, 110, 34, 44, 32, 34, 100, 117, 99, 107, 34, 44, 32, 34, 115, 104, 105, 116, 34, 44, 32, 34, 100, 97, 109, 110, 34, 44, 32, 34, 97, 100, 100, 101, 100, 34, 44, 32, 34, 116, 104, 225, 186, 177, 110, 103, 34, 44, 32, 34, 99, 111, 110, 34, 44, 32, 34, 109, 195, 160, 121, 34, 44, 32, 34, 116, 97, 111, 34, 44, 32, 34, 99, 104, 195, 179, 34, 44, 32, 34, 104, 101, 111, 34, 44, 32, 34, 108, 225, 187, 163, 110, 34, 44, 32, 34, 107, 104, 225, 187, 145, 110, 34, 44, 32, 34, 110, 225, 186, 161, 110, 34, 44, 32, 34, 196, 145, 105, 195, 170, 110, 34, 44, 32, 34, 104, 116, 116, 112, 34, 44, 32, 34, 110, 103, 117, 34, 44, 32, 34, 196, 145, 225, 186, 167, 110, 34, 44, 32, 34, 99, 195, 162, 109, 34, 44, 32, 34, 196, 145, 105, 225, 186, 191, 99, 34, 44, 32, 34, 113, 117, 195, 168, 34, 44, 32, 34, 99, 225, 187, 165, 116, 34, 44, 32, 34, 116, 225, 186, 173, 116, 34, 44, 32, 34, 110, 103, 117, 121, 225, 187, 129, 110, 34, 44, 32, 34, 115, 195, 186, 99, 34, 44, 32, 34, 109, 111, 100, 34, 44, 32, 34, 97, 100, 100, 34, 44, 32, 34, 99, 104, 101, 99, 107, 34, 44, 32, 34, 104, 97, 99, 107, 34, 44, 32, 34, 98, 117, 121, 34, 44, 32, 34, 103, 97, 121, 34, 44, 32, 34, 107, 105, 108, 108, 34, 44, 32, 34, 100, 105, 101, 34, 44, 32, 34, 100, 101, 97, 116, 104, 34, 44, 32, 34, 116, 101, 108, 101, 103, 114, 97, 109, 34, 44, 32, 34, 46, 34, 44, 32, 34, 109, 101, 115, 115, 97, 103, 101, 34, 44, 32, 34, 116, 105, 116, 116, 108, 101, 34, 44, 32, 34, 117, 105, 100, 34, 44, 32, 34, 110, 105, 99, 107, 34, 44, 32, 34, 100, 105, 34, 44, 32, 34, 98, 117, 34, 44, 32, 34, 225, 186, 183, 34, 44, 32, 34, 225, 187, 147, 34, 44, 32, 34, 195, 186, 34, 44, 32, 34, 225, 187, 165, 34, 44, 32, 34, 115, 112, 97, 109, 34, 44, 32, 34, 114, 101, 113, 117, 101, 115, 116, 34, 44, 32, 34, 112, 108, 97, 121, 101, 114, 34, 44, 32, 34, 99, 111, 100, 101, 34, 44, 32, 34, 97, 100, 100, 105, 110, 103, 34, 44, 32, 34, 103, 114, 105, 110, 103, 111, 34, 44, 32, 34, 102, 117, 99, 107, 34, 44, 32, 34, 98, 105, 116, 99, 104, 34, 44, 32, 34, 97, 115, 115, 104, 111, 108, 101, 34, 44, 32, 34, 105, 100, 105, 111, 116, 34, 44, 32, 34, 115, 116, 117, 112, 105, 100, 34, 44, 32, 34, 110, 111, 111, 98, 34, 44, 32, 34, 116, 114, 97, 115, 104, 34, 93])
 bad_words = json.loads(data.decode())
 res = ""
 i = 0 
 while i < len(text):
  if text[i] == "[":
   end = text.find("]", i)
   if end != -1:
    res += text[i:end+1]
    i = end + 1
    continue
  matched = False
  for word in bad_words:
   word_len = len(word)
   if i + word_len <= len(text) and text[i:i+word_len].lower() == word.lower():
    res += "😏".join(text[i:i+word_len])
    i += word_len
    matched = True
    break
  if matched: continue
  if text[i].isdigit():
   start = i
   while i < len(text) and text[i].isdigit():
    i += 1
   num = text[start:i]
   res += "😏".join(num) if len(num) > 2 else num
  else:
   res += text[i]
   i += 1 
 return res

def get_user_input(message):
 parts = message.split()
 if len(parts) < 2:
  return "[b][c][FFFF00]Vui lòng nhập ID.\nVí dụ: {} 12345678".format(
   message.split()[0]
  )
 return parts[1].strip()

def getavatar():
 AvatarList = [902000207, 902000306, 902045006, 902047018, 902027027, 902042011, 902040027, 902040028]
 return random.choice(AvatarList)

def ChooseEmote(token, url):
 url = "{}/ChooseEmote".format(url)
 headers = {
  "ReleaseVersion": "OB54", "X-GA": "v1 1",
  "Authorization": "Bearer %s" % token}
 data = "5D 16 45 26 18 C5 DE 3E E8 F4 C5 36 03 7F 84 B7"
 res = requests.post(url, data=bytes.fromhex(data), headers=headers)
 return res.content

def RemoveFriend(uid, token, url):
    url = "{}/RemoveFriend".format(url)
    headers = {
        "ReleaseVersion": "OB54",
        "X-GA": "v1 1",
        "Authorization": "Bearer {}".format(token)
    }
    packet = pb_encode({1: int(uid)})
    payload = AES_CBC128(packet, key, iv)
    res = requests.post(url, data=payload, headers=headers)
    return res.content

def ConfirmFriendRequest(uid, token, url):
 url = "{}/ConfirmFriendRequest".format(url)
 headers = {
  "ReleaseVersion": "OB54", "X-GA": "v1 1",
  "Authorization": "Bearer {}".format(token)}
 packet = pb_encode({1: int(uid), 2: 1})
 payload = AES_CBC128(packet, key, iv)
 res = requests.post(url, data=payload, headers=headers)
 return res.content

def RequestAddingFriend(uid, token, url):
 url = "{}/RequestAddingFriend".format(url)
 headers = {
  "ReleaseVersion": "OB54", "X-GA": "v1 1",
  "Authorization": "Bearer {}".format(token)}
 packet = pb_encode({1: 6393938381, 2: int(uid), 3: 22})
 payload = AES_CBC128(packet, key, iv)
 res = requests.post(url, data=payload, headers=headers)
 return res.content

def GetPlayerPersonalShow(uid, token, url):
 url = "{}/GetPlayerPersonalShow".format(url)
 headers = {
  "ReleaseVersion": "OB54", "X-GA": "v1 1",
  "Authorization": "Bearer {}".format(token)}
 packet = pb_encode({1: int(uid), 2: 1})
 payload = AES_CBC128(packet, key, iv)
 res = requests.post(url, data=payload, headers=headers)
 return res.content

def napthe(uid):
 url = "https://napthe.vn/api/auth/player_id_login"
 payload = {}
 payload["app_id"] = 100067
 payload["login_id"] = str(uid)
 payload["app_server_id"] = 0x000
 payload = json.dumps(payload)

 headers = {}
 headers["Accept-Encoding"] = "gzip, deflate, br, zstd"
 headers["Accept"] = "application/json"
 headers["Referer"] = "https://napthe.vn/app/100067/idlogin"
 headers["Accept-Language"] = "vi-VN,vi;q=0.9"
 headers["User-Agent"] = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36"
 headers["Cookie"] = "datadome=9SKY0NQDmJskwyYecdQm4AwRLX5Cw6QGHXVojTXdB9zyO2XqhZi3yP6FPDZ8tBTHxKwCLlIYRUL35e_XKcYDT4Sr3shME1ZypsukSWpj0rHxPX6fzlfg242Azyw3wIjQ"

 response = requests.post(url, data=payload, headers=headers)
 if response.status_code !=200:
  return response.text
 return response.json()

def check_banned(uid):
 url = f"https://ff.garena.com/api/antihack/check_banned?lang=vi&uid={uid}"
 headers = {
   "Accept": "application/json, text/plain, */*",
   "authority": "ff.garena.com",
   "referer": "https://ff.garena.com/en/support/",
   "x-requested-with": "B6FksShzIgjfrYImLpTsadjS86sddhFH"}
 res = requests.get(url, headers=headers)
 if res.status_code == 200:
  data = res.json().get("data", {})
  is_banned = data.get("is_banned", 0)
  return True if is_banned else False
 return False

def send_likes(uid):
 try:
  url = f"http://103.139.155.35:####/likes?keys=cdanhdev&uid={uid}"  #thay api của bạn
  res = requests.get(url, timeout=15)

  if res.status_code != 200:
   return "[c][FF0000]API ERROR"

  data = res.json().get("result", {})

  api = data.get("API", {})
  likes = data.get("Likes Info", {})
  user = data.get("User Info", {})

  likes_added = likes.get("Likes Added", 0)
  likes_before = likes.get("Likes Before", 0)
  likes_after = likes.get("Likes After", 0)
  if not likes_added or likes_added == 0 or likes_before == likes_after:
   return f"""[b][c][FF0000]MAXX LIKES
   
[FF0000]Trạng thái: Đã đạt giới hạn likes hôm nay
[AAAAAA]Vui lòng thử lại vào ngày mai
"""
  result = f"""[b][c][00FF00]LIKES SENT SUCCESS

=>[ffffff] Nick UID: [00FFFF]{user.get('Account UID', uid)}
=>[ffffff] Nick Name: [00FFFF]{user.get('Account Name', 'null')}
=>[ffffff] Nick Region: [00FFFF]{user.get('Account Region', 'null')}
=>[ffffff] Nick Level: [00FFFF]{user.get('Account Level', 'null')}
=> [ffffff]Nick Before: [00FFFF]{likes_before}
=> [ffffff]Nick Likes After: [00FFFF]{likes_after}
=> [ffffff]Nick Likes Added: [00FFFF]{likes_added}
"""
  return result
 except Exception as e:
  return f"[c][FF0000]Lỗi ku gì rồi"
 

get_history_grok = []
def grok(message):
 global get_history_grok
 get_history_grok.append({"role": "user", "content": message})
 headers = {
  "Authorization": "Bearer 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",
  "Host": "openrouter.ai",
  "Accept-Encoding": "gzip, deflate, br",
  "Accept-Language": "vi-VN",
 }

 payload = {
	"stream": True,
	"model":"x-ai/grok-2-vision-1212",
	"messages": get_history_grok,
	"include_reasoning": True,
	"reasoning": {},
	"transforms":["middle-out"],
	"plugins":[],
	"provider":{"order":["xAI"], "allow_fallbacks": False},
	"max_tokens":25,
	"top_p":1,
	"frequency_penalty":0,
	"presence_penalty":0,
	"repetition_penalty":1,
	"temperature":1,
	"top_k":0,
	"min_p":0,
	"top_a":0
 }

 try:
  response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, data=json.dumps(payload))
  full_response = ""
  for line in response.iter_lines():
   if line:
    decoded_line = line.decode('utf-8')
    if decoded_line.startswith("data: "):
     json_str = decoded_line[6:]
     if json_str == "[DONE]": break
     data = json.loads(json_str)
     delta_content = data["choices"][0]["delta"].get("content", "")
     full_response += delta_content
  get_history_grok.append({"role": "assistant", "content": full_response})
  return full_response
 except requests.exceptions.RequestException as e: pass

get_history_gemini = []
def gemini(message):
 global get_history_gemini
 get_history_gemini.append({"role": "user", "parts": [{"text": message}]})
 headers = {"Content-Type": "application/json"}
 payload = {"contents": get_history_gemini}
 response = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AIzaSyDZvi8G_tnMUx7loUu51XYBt3t9eAQQLYo", headers=headers, json=payload)
 if response.status_code == 200:
  reply = response.json()["candidates"][0]["content"]["parts"][0]["text"]
  get_history_gemini.append({"role": "model", "parts": [{"text": reply}]})
  return reply
 else: return "null"

def send_info(uid, token, url):
 response = GetPlayerPersonalShow(int(uid), token, url)
 data = protobuf_dec(response.hex())
 if data is None: return "Account does not exist"
 try: data = json.loads(data)
 except:return "FAILED"
 def sg(data, key, default=None):
  return data[key] if key in data else default
 def convert_time(timestamp):
  return datetime.datetime.fromtimestamp(timestamp).strftime("Ngày %d, tháng %m, năm %Y, %H giờ, %M phút")
 s1, s2, s3 = sg(data, "1", {}), sg(data, "6", {}), sg(data, "7", {})

 info = """Account Profile Info: 
- Name: %s
- Region: %s
- Level: %s (EXP: %s)

Guild Info:
- Name:  %s
- ID: %s
- Member: %s/%s

Guild Owner:
 - Name: %s
 - Region: %s
 - Level: %s (EXP: %s)

%s""" % (s1.get("3"),s1.get("5"), s1.get("6"), s1.get("7"), s2.get("2"),
s2.get("1"), s2.get("6"), s2.get("5"), s3.get("3"), s3.get("5"), s3.get("6"), s3.get("7"), convert_time(s1.get("44")))
 return info
 
import datetime
from google.protobuf.json_format import MessageToDict
from AccountPersonalShow_pb2 import AccountPersonalShowInfo

def send_info1(uid, token, url):
    response = GetPlayerPersonalShow(int(uid), token, url)
    msg = AccountPersonalShowInfo()
    msg.ParseFromString(response)
    data_dict = MessageToDict(msg, preserving_proto_field_name=True)
    return data_dict