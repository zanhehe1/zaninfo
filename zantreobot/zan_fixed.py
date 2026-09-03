#!/usr/bin/env python3
import os, sys, json, time, random, string, hashlib, threading, subprocess, base64, codecs, re, socket, struct, shutil, importlib, hmac
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ====== MÀU SẮC ======
C = '\033[0m'
R = '\033[91m'
G = '\033[92m'
GD = '\033[92m' 
Y = '\033[93m'
B = '\033[94m'
P = '\033[95m'
M = '\033[96m'
GR = '\033[90m'
W = '\033[97m'

DEFAULT_REGION = "VN"
DEFAULT_TOTAL = 1000
DEFAULT_THREADS = 50
AUTO_ACTIVATE = True

AES_KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
AES_IV  = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])

# ====== KEY GIỐNG exe.py ======
KEY = bytes.fromhex("32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533")
CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
NICK_XOR_KEY = b'1e5898ccb8dfdd921f9bdea848768b64a201'

REGION_LANG = {
    "IND":"hi", "ID":"id", "TH":"th", "ME":"ar", "EUROPE":"fr",
    "VN":"vi", "BD":"bn", "PK":"ur", "TW":"zh", "RU":"ru",
    "NA":"na", "SAC":"es", "BR":"pt", "SG":"ms", "US":"us"
}

CLIENT_VERSION = "1.126.2"
RELEASE_VERSION = "OB54"

# ====== TOR - CÓ BẮT LỖI ======
def start_tor():
    try:
        subprocess.run(['pkill', '-9', 'tor'], capture_output=True)
        time.sleep(0.5)
        subprocess.Popen(['tor'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        for _ in range(15):
            time.sleep(0.5)
            if subprocess.run(['pgrep', '-x', 'tor'], capture_output=True).returncode == 0:
                return True
        return False
    except Exception as e:
        print(f"{Y}⚠️ Tor không chạy được: {e}{C}")
        print(f"{Y}⚠️ Tiếp tục dùng IP thường...{C}")
        return False

def renew_tor():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        sock.connect(('127.0.0.1', 9051))
        sock.send(b'AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\nQUIT\r\n')
        sock.close()
        time.sleep(1.5)
        return True
    except:
        return False

def varint_encode(value):
    result = []
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)

def build_field(field_num, value):
    if isinstance(value, int):
        return varint_encode((field_num << 3) | 0) + varint_encode(value)
    elif isinstance(value, (str, bytes)):
        data = value.encode('utf-8') if isinstance(value, str) else value
        return varint_encode((field_num << 3) | 2) + varint_encode(len(data)) + data
    elif isinstance(value, dict):
        sub = assemble_proto(value)
        return varint_encode((field_num << 3) | 2) + varint_encode(len(sub)) + sub
    raise TypeError()

def assemble_proto(fields):
    packet = bytearray()
    for k, v in fields.items():
        idx = int(k)
        if isinstance(v, list):
            for item in v:
                packet.extend(build_field(idx, item))
        else:
            packet.extend(build_field(idx, v))
    return bytes(packet)

def aes_encrypt(plain):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(plain, 16))

def parse_proto(data):
    from google.protobuf.internal.decoder import _DecodeVarint, _DecodeVarint32
    pos, length = 0, len(data)
    result = {}
    while pos < length:
        key, pos = _DecodeVarint(data, pos)
        field = key >> 3
        wire = key & 7
        if wire == 0:
            val, pos = _DecodeVarint(data, pos)
        elif wire == 2:
            size, pos = _DecodeVarint32(data, pos)
            raw = data[pos:pos+size]
            pos += size
            try:
                val = parse_proto(raw)
            except:
                try:
                    val = raw.decode('utf-8')
                except:
                    val = raw.hex()
        elif wire == 5:
            val = int.from_bytes(data[pos:pos+4], 'little')
            pos += 4
        elif wire == 1:
            val = int.from_bytes(data[pos:pos+8], 'little')
            pos += 8
        else:
            raise Exception()
        if field in result:
            if not isinstance(result[field], list):
                result[field] = [result[field]]
            result[field].append(val)
        else:
            result[field] = val
    return result

def random_user_agent():
    return "UnityPlayer/2022.3.47f1(UnityWebRequest/1.0,libcurl/8.5.0-DEV)"

def get_public_ip(session):
    try:
        return session.get('https://api.ipify.org', timeout=5).text
    except:
        return "104.28.156.112"

# ====== REGISTER GUEST ACCOUNT ======
def register_guest_account(session):
    password = "".join(random.choices("0123456789ABCDEF", k=64))
    payload = {"app_id": 100067, "client_type": 2, "password": password, "source": 2}
    body_json = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(KEY, body_json.encode("utf-8"), hashlib.sha256).hexdigest()
    
    headers = {
        "User-Agent": "GarenaMSDK/4.0.42(SM-A525F ;Android)",
        "Connection": "Keep-Alive",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Authorization": f"Signature {signature}",
        "Content-Type": "application/json; charset=utf-8",
        "Host": "100067.connect.garena.com"
    }
    response = session.post("https://100067.connect.garena.com/api/v2/oauth/guest:register", data=body_json, headers=headers, timeout=36)
    if response.status_code != 200:
        response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise Exception(f"Register error: {data.get('message', 'Unknown')} - Code: {data.get('code')}")
    return str(data["data"]["uid"]), password

def obtain_access_token(session, uid, password):
    url = "https://auth.garena.com/oauth/guest/token/grant"
    payload = {"uid": str(uid), "password": str(password), "response_type": "token", "client_type": "2", "client_id": "100067", "client_secret": CLIENT_SECRET}
    headers = {"User-Agent": "Mozilla/5.0 (Android 9; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0", "Content-Type": "application/x-www-form-urlencoded"}
    resp = session.post(url, data=payload, headers=headers, timeout=10)
    if resp.status_code != 200:
        resp.raise_for_status()
    data = resp.json()
    if "access_token" not in data:
        raise Exception()
    return data["access_token"], data["open_id"]

def major_register(session, nick_prefix, access_token, open_id, region, ghost=False):
    url = "https://loginbp.ggpolarbear.com/MajorRegister"
    exp_digits = {'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹'}
    num = random.randint(1,99999)
    suffix = ''.join(exp_digits[d] for d in f"{num:05d}")
    nickname = nick_prefix[:12] + suffix
    lang = "pt" if ghost else REGION_LANG.get(region.upper(), "vi")
    xor_key = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
    encoded = ''.join(chr(ord(c) ^ xor_key[i % len(xor_key)]) for i, c in enumerate(open_id))
    unicode_esc = ''.join(c if 32 <= ord(c) <= 126 else f'\\u{ord(c):04x}' for c in encoded)
    field_bytes = codecs.decode(unicode_esc, 'unicode_escape').encode('latin1')
    fields = {"1": nickname, "2": access_token, "3": open_id, "5": 102000007, "6": 4, "7": 1, "13": 1, "14": field_bytes, "15": lang, "16": 2}
    plain = assemble_proto(fields)
    encrypted = aes_encrypt(plain)
    headers = {"Accept-Encoding":"gzip", "Authorization":"Bearer", "Connection":"Keep-Alive", "Content-Type":"application/x-www-form-urlencoded", "Expect":"100-continue", "Host":"loginbp.ggpolarbear.com", "ReleaseVersion": RELEASE_VERSION, "User-Agent": random_user_agent(), "X-GA":"v1 1"}
    resp = session.post(url, headers=headers, data=encrypted, timeout=10)
    resp.raise_for_status()
    return parse_proto(resp.content)

def major_login(session, access_token, open_id, region, lang):
    url = "https://loginbp.ggpolarbear.com/MajorLogin"
    ip = get_public_ip(session)
    fields = {
        3: "2026-06-24 13:48:29", 4: "free fire", 5: 2, 7: CLIENT_VERSION,
        8: "Android OS 9 / API-28 (PQ3A.190605.03171033/3793265)", 9: "Handheld",
        10: "MobiFone", 11: "WIFI", 12: 1600, 13: 900, 14: "240",
        15: "x86-64 SSE3 SSE4.1 SSE4.2 AVX | 2865 | 4", 16: 3004, 17: "Adreno (TM) 640",
        18: "OpenGL ES 3.1 v1", 19: "Google|6d586c06-4a7b-4c8e-b2f1-99ac04c10d31",
        20: ip, 21: lang, 22: str(open_id), 23: "4", 25: "Xiaomi 2203121C", 26: "SG",
        29: str(access_token), 30: 1, 41: "MobiFone", 42: "WIFI", 57: "7428b253defc164018c604a1ebbfebdf",
        60: 49386, 61: 47035, 62: 2519, 63: 736, 64: 23753, 65: 25132, 66: 49227, 67: 49386,
        70: 4, 71: 4, 73: 3, 74: "/data/app/com.dts.freefireth-TGfGr55n7IBaojkeP6sM8Q==/lib/arm64",
        76: 1, 77: "17e6a447803a17e4f59e3fd734efc5ae|/data/app/com.dts.freefireth-TGfGr55n7IBaojkeP6sM8Q==/base.apk",
        78: 3, 79: 2, 81: "64", 83: "2019120270", 85: 3, 86: "OpenGLES2", 87: 255, 88: 4,
        90: "Singapore", 92: 36622, 93: "android", 94: "KqsHT1y2dlDX0ywnP1LQ75AXqqV8YVvFC48pUhDlHSFPi7zihMoH4je/A9lW1Sa5OUKZngMdKfCwTE8lUtNlp7X97/w=",
        96: '{"cur_rate":null,"support_etc2":false}', 97: 1, 98: 1, 99: "4", 100: "4",
        102: bytes.fromhex('14534c46530a04014c065f170f021609456e5b02585d59755c5f745b070a3b0b0335'), 108: 4
    }
    encrypted = aes_encrypt(assemble_proto(fields))
    headers = {"User-Agent": random_user_agent(), "X-GA": "v1 1", "Content-Type": "application/x-www-form-urlencoded", "Accept-Encoding": "deflate, gzip", "Accept": "*/*", "X-Unity-Version": "2022.3.47f1", "Host": "loginbp.ggblueshark.com", "ReleaseVersion": RELEASE_VERSION}
    resp = session.post(url, headers=headers, data=encrypted, timeout=10)
    resp.raise_for_status()
    return parse_proto(resp.content)

def choose_region(session, region, jwt):
    url = "https://loginbp.ggpolarbear.com/ChooseRegion"
    fields = {"1": region.upper()}
    plain = assemble_proto(fields)
    encrypted = aes_encrypt(plain)
    headers = {"Accept-Encoding":"gzip", "Authorization":f"Bearer {jwt}", "Connection":"Keep-Alive", "Content-Type":"application/x-www-form-urlencoded", "Expect":"100-continue", "ReleaseVersion": RELEASE_VERSION, "User-Agent": random_user_agent(), "X-GA":"v1 1"}
    resp = session.post(url, headers=headers, data=encrypted, timeout=10)
    return resp.status_code == 200

def decode_nickname(jwt):
    try:
        parts = jwt.split('.')
        payload = parts[1] + '=' * (4 - len(parts[1]) % 4)
        data = json.loads(base64.b64decode(payload))
        lock_region = data.get("lock_region") or data.get("noti_region")
        raw = data.get("nickname")
        if raw:
            decoded = base64.b64decode(raw)
            nick = bytes([decoded[i] ^ NICK_XOR_KEY[i % len(NICK_XOR_KEY)] for i in range(len(decoded))])
            nick = nick.decode('utf-8', errors='ignore')
        else:
            nick = ""
        return lock_region, nick
    except:
        return None, None

def activate_account(session, jwt_token, client_url, open_id):
    client_url = client_url.replace("https://", "").replace("http://", "").strip()
    url = f"https://{client_url}/GetLoginData"
    ip = get_public_ip(session)
    fields = {
        3: "2026-06-24 13:48:29", 4: "free fire", 5: 2, 7: CLIENT_VERSION,
        8: "Android OS 9 / API-28 (PQ3A.190605.03171033/3793265)", 9: "Handheld",
        10: "MobiFone", 11: "WIFI", 12: 1600, 13: 900, 14: "240",
        15: "x86-64 SSE3 SSE4.1 SSE4.2 AVX | 2865 | 4", 16: 3004, 17: "Adreno (TM) 640",
        18: "OpenGL ES 3.1 v1", 19: "Google|6d586c06-4a7b-4c8e-b2f1-99ac04c10d31",
        20: ip, 21: "vn", 22: "7428b253defc164018c604a1ebbfebdf", 23: "4",
        24: "Handheld", 25: "Xiaomi 2203121C", 26: "SG", 29: str(jwt_token), 30: 1,
        41: "MobiFone", 42: "WIFI", 57: "7428b253defc164018c604a1ebbfebdf",
        60: 49386, 61: 47035, 62: 2519, 63: 736, 64: 23753, 65: 25132, 66: 49227, 67: 49386,
        70: 4, 71: 4, 73: 3, 74: "/data/app/com.dts.freefireth-TGfGr55n7IBaojkeP6sM8Q==/lib/arm64",
        76: 1, 77: "17e6a447803a17e4f59e3fd734efc5ae|/data/app/com.dts.freefireth-TGfGr55n7IBaojkeP6sM8Q==/base.apk",
        78: 3, 79: 2, 81: "64", 83: "2019120270", 85: 3, 86: "OpenGLES2", 87: 255, 88: 4,
        90: "Singapore", 92: 36622, 93: "android", 94: "KqsHT1y2dlDX0ywnP1LQ75AXqqV8YVvFC48pUhDlHSFPi7zihMoH4je/A9lW1Sa5OUKZngMdKfCwTE8lUtNlp7X97/w=",
        95: 111111, 96: '{"cur_rate":null,"support_etc2":false}', 97: 1, 98: 1, 99: "4", 100: "4",
        102: bytes.fromhex('14534c46530a04014c065f170f021609456e5b02585d59755c5f745b070a3b0b0335'), 108: 4
    }
    encrypted = aes_encrypt(assemble_proto(fields))
    headers = {"Authorization": f"Bearer {jwt_token}", "Host": client_url, "User-Agent": random_user_agent(), "Content-Type": "application/x-www-form-urlencoded", "X-GA": "v1 1", "ReleaseVersion": RELEASE_VERSION}
    try:
        resp = session.post(url, headers=headers, data=encrypted, timeout=10)
        return resp.status_code == 200
    except:
        return False

# ====== CLASS XZAN ======
class xZan:
    def __init__(self, region, nickname_prefix, total, threads):
        self.region = region.upper()
        self.nick_base = nickname_prefix[:7]
        self.total = total
        self.threads = threads
        self.completed = 0
        self.stop_flag = False
        self.lock = threading.Lock()
        self.sessions = []
        self.ip_counter = 0
        self.results = []
        self.start_time = time.time()
        self.failed_count = 0
        self.tor_enabled = False  # Biến kiểm tra Tor có chạy không
        if os.path.exists("xZan.json"):
            try:
                with open("xZan.json", "r", encoding="utf-8") as f:
                    self.results = json.load(f)
                    if not isinstance(self.results, list):
                        self.results = []
            except:
                self.results = []

    def _generate_password(self):
        return "".join(random.choices("0123456789ABCDEF", k=64))

    def _get_session(self):
        if not self.sessions:
            for _ in range(self.threads * 2):
                s = requests.Session()
                # Nếu Tor đang chạy thì dùng proxy
                if self.tor_enabled:
                    try:
                        s.proxies.update({'http':'socks5h://127.0.0.1:9050', 'https':'socks5h://127.0.0.1:9050'})
                    except:
                        pass
                s.verify = False
                s.timeout = 15
                self.sessions.append(s)
        return random.choice(self.sessions)

    def _renew_sessions(self):
        if self.tor_enabled:
            renew_tor()
        for s in self.sessions:
            try:
                s.close()
            except:
                pass
        self.sessions = []

    def _save(self):
        try:
            with open("xZan.json", "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=4, ensure_ascii=False)
        except:
            pass

    def show_account(self, idx, acc):
        try:
            name = acc.get('nickname', 'N/A')
            uid = acc.get('game_uid', 'N/A')
            password = acc.get('password', 'N/A')
            region = acc.get('region', 'N/A')
            account_id = acc.get('uid', 'N/A')
            access_token = acc.get('access_token', '')
            jwt_token = acc.get('jwt_token', '')
            activated = acc.get('activated', False)
            emote = acc.get('emote', False)

            border = "═" * 58
            
            print(f"\n{C}╔{border}╗{R}")
            print(f"{C}║{GD}  ✅ ACCOUNT #{idx} CREATED SUCCESSFULLY{C}                     ║{R}")
            print(f"{C}╠{border}╣{R}")
            print(f"{C}║{R}  {P}👤 Name:{R}       {G}{name}{R}")
            print(f"{C}║{R}  {P}🆔 UID:{R}        {Y}{uid}{R}")
            print(f"{C}║{R}  {P}🔑 Password:{R}   {GR}{password[:20]}...{R}")
            print(f"{C}║{R}  {P}🌍 Region:{R}      {B}{region}{R}")
            print(f"{C}║{R}  {P}📛 Account ID:{R}  {M}{account_id}{R}")
            
            if access_token:
                print(f"{C}║{R}  {P}🔐 Access Token:{R} {GR}{access_token[:30]}...{R}")
            if jwt_token:
                print(f"{C}║{R}  {P}🔑 JWT Token:{R}    {GR}{jwt_token[:30]}...{R}")
                
            if activated:
                print(f"{C}║{R}  {P}📊 Status:{R}      {G}✅ Activated{R}")
            else:
                print(f"{C}║{R}  {P}📊 Status:{R}      {Y}○ Pending{R}")
            if emote:
                print(f"{C}║{R}  {P}🎭 Emote:{R}      {G}✅ Đã gắn{R}")
            else:
                print(f"{C}║{R}  {P}🎭 Emote:{R}      {R}❌ Chưa gắn{R}")
            print(f"{C}╚{border}╝{R}")        
        except Exception as e:
            print(f"{R}  [!] Error: {e}{C}")

    def _build_one(self):
        session = self._get_session()
        try:
            uid, password = register_guest_account(session)
            access_token, open_id = obtain_access_token(session, uid, password)
            reg_resp = major_register(session, self.nick_base, access_token, open_id, self.region)
            game_uid = str(reg_resp.get(3))
            if not game_uid:
                return None
            lang = REGION_LANG.get(self.region, "vi")
            login_resp = major_login(session, access_token, open_id, self.region, lang)
            jwt = login_resp.get(8)
            if isinstance(jwt, list):
                jwt = jwt[0]
            lock_region, nickname = decode_nickname(jwt)
            if not nickname:
                nickname = self.nick_base
            if AUTO_ACTIVATE and (not lock_region or lock_region != self.region):
                try:
                    choose_region(session, self.region, jwt)
                    login_resp2 = major_login(session, access_token, open_id, self.region, lang)
                    jwt2 = login_resp2.get(8)
                    if isinstance(jwt2, list):
                        jwt2 = jwt2[0]
                    if jwt2:
                        jwt = jwt2
                        _, nickname = decode_nickname(jwt)
                        if not nickname:
                            nickname = self.nick_base
                        login_resp = login_resp2
                except:
                    pass
            client_url = "clientbp.ggpolarbear.com"
            client_url_raw = login_resp.get(10)
            if isinstance(client_url_raw, list) and client_url_raw:
                client_url_raw = client_url_raw[0]
            if client_url_raw and isinstance(client_url_raw, str):
                client_url = client_url_raw.replace("https://", "").replace("http://", "").strip()
            activated = False
            if AUTO_ACTIVATE and jwt:
                activated = activate_account(session, jwt, client_url, open_id)
            
            # ====== GẮN EMOTE ======
            emote_success = False
            if jwt:
                try:
                    ChooseEmoteUrl = "https://clientbp.ggpolarbear.com/ChooseEmote"
                    EmotePayload = "CA F6 83 22 2A 25 C7 BE FE B5 1F 59 54 4D B3 13"
                    payload = bytes.fromhex(EmotePayload.replace(" ", ""))
                    headers = {
                        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 7.1.2; SM-G988N Build/NRD90M)",
                        "Connection": "Keep-Alive",
                        "Accept-Encoding": "gzip",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Authorization": f"Bearer {jwt}",
                        "X-Unity-Version": "2018.4.11f1",
                        "X-GA": "v1 1",
                        "ReleaseVersion": "OB54",
                        "Expect": "100-continue"
                    }
                    response = session.post(ChooseEmoteUrl, headers=headers, data=payload, verify=False, timeout=15)
                    if response.status_code == 200:
                        emote_success = True
                except:
                    pass
            
            return {
                "uid": uid, 
                "game_uid": game_uid, 
                "password": password, 
                "nickname": nickname, 
                "region": self.region, 
                "activated": activated, 
                "access_token": access_token,
                "jwt_token": jwt,
                "emote": emote_success,
                "created_at": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"{R}❌ Error: {e}{C}")
            return None

    def _worker(self):
        while not self.stop_flag:
            with self.lock:
                if self.completed >= self.total:
                    break
                self.ip_counter += 1
                if self.ip_counter >= 8:
                    self.ip_counter = 0
                    if self.tor_enabled:
                        renew_tor()
                    self._renew_sessions()
            acc = self._build_one()
            if acc:
                with self.lock:
                    if self.completed < self.total:
                        self.completed += 1
                        self.results.append(acc)
                        self._save()
                        self.show_account(self.completed, acc)
            else:
                with self.lock:
                    self.failed_count += 1
                time.sleep(0.5)

    def run(self):
        # ====== THỬ KHỞI ĐỘNG TOR ======
        print(f"{Y}[*] Đang khởi động Tor...{C}")
        if start_tor():
            self.tor_enabled = True
            print(f"{G}[✓] Tor đã chạy!{C}")
        else:
            self.tor_enabled = False
            print(f"{Y}[!] Không thể chạy Tor, dùng IP thường...{C}")
        
        # ====== HIỂN THỊ THÔNG TIN SERVER ======
        print(f"\n{G}┌─────────────────────────────────────────────────────────┐")
        print(f"│{W}  Free Fire Account Creator (FIXED){G}                    │")
        print(f"├─────────────────────────────────────────────────────────┤")
        print(f"│  {Y}Server  :{W} https://loginbp.ggblueshark.com/")
        print(f"│  {Y}Version :{W} {CLIENT_VERSION} ({RELEASE_VERSION})")
        print(f"│  {Y}Region  :{W} {self.region}  |  Prefix : {self.nick_base}")
        print(f"│  {Y}Target  :{W} {self.total}  |  Threads: {self.threads}")
        print(f"│  {Y}Tor     :{W} {'✅ Enabled' if self.tor_enabled else '❌ Disabled'}")
        print(f"└─────────────────────────────────────────────────────────┘{C}\n")
        
        # ====== LOADING ANIMATION ======
        chars = "●○◉◎◈◆◇"
        for i in range(15):
            sys.stdout.write(f"\r{G}  {chars[i % len(chars)]} {W}Loading Register Account...{C}")
            sys.stdout.flush()
            time.sleep(0.05)
        print()
        
        threads = []
        for _ in range(min(self.threads, self.total)):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            threads.append(t)
        
        try:
            while self.completed < self.total:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{R}[!] Stopped by user{C}")
            self.stop_flag = True
        
        self.stop_flag = True
        for t in threads:
            try:
                t.join(timeout=2)
            except:
                pass
        
        elapsed = time.time() - self.start_time
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        
        # ====== KẾT QUẢ ======
        print(f"\n{G}┌─────────────────────────────────────────────────────────┐")
        print(f"│{W}  ✅ Done: {self.completed}/{self.total} accounts{G}                 │")
        print(f"│  {Y}⏱️  Time:{W} {hours}h {minutes}m {seconds}s{G}                     │")
        print(f"│  {Y}❌ Failed:{W} {self.failed_count}{G}                                 │")
        print(f"│  {Y}💾 Saved to:{W} xZan.json{G}                                    │")
        print(f"└─────────────────────────────────────────────────────────┘{C}")

# ====== MAIN ======
if __name__ == "__main__":
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print(f"""
{G}   ███████╗ █████╗ ███╗   ██╗██╗  ██╗
{Y}   ╚══███╔╝██╔══██╗████╗  ██║╚██╗██╔╝
{Y}     ███╔╝ ███████║██╔██╗ ██║ ╚███╔╝ 
{Y}    ███╔╝  ██╔══██║██║╚██╗██║ ██╔██╗ 
{Y}   ███████╗██║  ██║██║ ╚████║██╔╝ ██╗
{Y}   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝{C}

{G}    FREE FIRE ACCOUNT CREATOR V.38 (FIXED){C}

{Y}    Admin   :{W} @zandev
{Y}    Group   :{W} https://t.me/zancommunity  
{Y}    Telegram :{W} t.me/zanbackj

{GR}    All Rights Reserved By ZanX{C}
""")
    
    print(f"\n{Y}[?]{W} Name prefix {GR}(default zan){W}: {C}", end='')
    name = input().strip() or "zan"
    
    print(f"\n{Y}[?]{W} Select Region {GR}(VN, IND, ME, BR...){W}: {C}", end='')
    region = input().strip().upper() or "VN"
    if region not in REGION_LANG:
        print(f"{R}  [!] Invalid region! Using VN default.{C}")
        region = "VN"
    
    print(f"\n{Y}[?]{W} Number of accounts {GR}(default 1000){W}: {C}", end='')
    count_input = input().strip()
    count = int(count_input) if count_input.isdigit() else 1000
    
    print(f"\n{Y}[?]{W} Number of threads {GR}(default 50){W}: {C}", end='')
    threads_input = input().strip()
    threads = int(threads_input) if threads_input.isdigit() else 50
    threads = max(1, min(threads, 100))
    
    print(f"\n{G}  [+] Starting Register in {region} region...{C}")
    
    generator = xZan(region, name, count, threads)
    generator.run()
