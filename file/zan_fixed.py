#zan_fixed.py - Free Fire Account Creator (FINAL FIX)
import hashlib
import hmac
import string
import random
import base64
import time
import sys
import time 
import requests
import re
import json
import os
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import concurrent.futures, threading

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings()

# ====== CONFIG ======
def storeApps(package):
    try:
        I = requests.get(f"https://play.google.com/store/apps/%s" % package, timeout=5)
        I = re.search(r'\[\[\["(\d+\.\d+\.\d+)"\]\]', I.text)
        if I: return I.group(1)
    except: pass
    return "1.104.1"

def bdversion():
    try:
        url = "https://version.common.redflamenco.com/live/ver.php?version=1.126.1&lang=vi&device=android&region=VN"
        res = requests.get(url, timeout=5, verify=False)
        return res.json()
    except:
        return {"latest_release_version": "OB54", "remote_version": "1.126.1", "server_url": "https://loginbp.ggblueshark.com/"}

_bd = bdversion()
LOGIN_SERVER_URL = _bd.get("server_url", "https://loginbp.ggblueshark.com/")
if not LOGIN_SERVER_URL.endswith("/"): LOGIN_SERVER_URL += "/"
CLIENT_VERSION = _bd.get("remote_version", "1.126.1")
RELEASE_VERSION = _bd.get("latest_release_version", "OB54")
LOGIN_HOST = LOGIN_SERVER_URL.replace("https://","").replace("http://","").rstrip("/")
DEFAULT_CLIENT_URL = LOGIN_SERVER_URL.replace("loginbp","clientbp")

HMAC_KEY = bytes.fromhex("2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3")
AES_KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
AES_IV = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
FIELD_102 = bytes.fromhex("14534c46530a04014c065f170f021609456e5b02585d59755c5f745b070a3b0b0335")
_XOR_KEY = bytes([0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30])
REGION_LANG = {"ME":"ar","IND":"hi","ID":"id","VN":"vi","TH":"th","BD":"bn","PK":"ur","TW":"zh","EU":"en","RU":"ru","NA":"en","SAC":"es","BR":"pt","SG":"en"}

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

# ====== PROTOBUF ======
def read_varint(data, pos):
    result = 0; shift = 0
    while pos < len(data):
        byte = data[pos]; pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80): return result, pos
        shift += 7
    return result, pos

def parse_protobuf(data):
    result = {}; pos = 0
    while pos < len(data):
        try:
            key, pos = read_varint(data, pos)
            field_num = key >> 3; wire_type = key & 0x7
            if wire_type == 0:
                value, pos = read_varint(data, pos); result[str(field_num)] = value
            elif wire_type == 2:
                length, pos = read_varint(data, pos)
                value = data[pos:pos+length]; pos += length
                if field_num == 8:
                    try: result[str(field_num)] = value.decode('utf-8', errors='ignore')
                    except: result[str(field_num)] = value
                else:
                    try:
                        nested = parse_protobuf(value)
                        result[str(field_num)] = nested if nested else value.decode('utf-8', errors='ignore')
                    except:
                        result[str(field_num)] = value.decode('utf-8', errors='ignore')
            elif wire_type == 1:
                if pos + 8 <= len(data):
                    result[str(field_num)] = int.from_bytes(data[pos:pos+8], 'little'); pos += 8
            elif wire_type == 5:
                if pos + 4 <= len(data):
                    result[str(field_num)] = int.from_bytes(data[pos:pos+4], 'little'); pos += 4
        except: break
    return result

class ProtoBuf:
    def __init__(self, data): self.data = data
    def protobuf(self): return parse_protobuf(self.data)

def _varint(n):
    r = []
    while True:
        b = n & 0x7F; n >>= 7
        if n: b |= 0x80
        r.append(b)
        if not n: break
    return bytes(r)

def _pb_varint(field, val): return _varint((field << 3) | 0) + _varint(val)
def _pb_ld(field, val):
    b = val.encode() if isinstance(val, str) else val
    return _varint((field << 3) | 2) + _varint(len(b)) + b

def pb_encode(fields):
    pkt = bytearray()
    for f, v in fields.items():
        if isinstance(v, dict): pkt.extend(_pb_ld(f, pb_encode(v)))
        elif isinstance(v, int): pkt.extend(_pb_varint(f, v))
        elif isinstance(v, (str, bytes)): pkt.extend(_pb_ld(f, v))
    return bytes(pkt)

def aes_encrypt(data): return AES.new(AES_KEY, AES.MODE_CBC, AES_IV).encrypt(pad(data, AES.block_size))
def encrypt_pb(fields): return aes_encrypt(pb_encode(fields))

_SUPER = "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079"

def generate_password():
    raw = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))
    return raw, hashlib.sha256(raw.encode()).hexdigest().upper()

def generate_nickname(prefix, max_len=12):
    clean = prefix.replace("/","").strip()
    if len(clean) >= max_len: return clean[:max_len]
    return clean + ''.join(random.choice(_SUPER) for _ in range(max_len - len(clean)))

def xor_open_id(open_id):
    return bytes(ord(open_id[i]) ^ _XOR_KEY[i % len(_XOR_KEY)] for i in range(len(open_id)))

def decode_jwt(token):
    try:
        parts = token.split('.')
        if len(parts) != 3: return None
        payload = parts[1] + '=' * (4 - len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload).decode('utf-8'))
    except: return None

_tl = threading.local()
def _session():
    if not hasattr(_tl, "s"):
        s = requests.Session(); s.verify = False; s.timeout = 15
        _tl.s = s
    return _tl.s

# ====== STEP 1: GUEST REGISTER ======
def guest_register(pw_hash):
    payload = {"app_id":100067,"client_type":2,"password":pw_hash,"source":2}
    body = json.dumps(payload, separators=(',',':'))
    sig = hmac.new(HMAC_KEY, body.encode(), hashlib.sha256).hexdigest()
    for attempt in range(3):
        try:
            r = _session().post(
                "https://100067.connect.garena.com/api/v2/oauth/guest:register",
                headers={
                    "User-Agent":"GarenaMSDK/4.0.41(2107113SI ;Android 11;vi;VN;app 1.123.1 2019120270;)",
                    "Authorization":f"Signature {sig}",
                    "Content-Type":"application/json; charset=utf-8",
                    "Host":"100067.connect.garena.com",
                }, data=body, timeout=30)
            d = r.json()
            if d.get("code") == 0: return d["data"]["uid"]
        except: pass
        if attempt < 2: time.sleep(2)
    return None

# ====== STEP 2: TOKEN GRANT ======
def token_grant(uid, pw_hash):
    payload = {
        "client_id":100067, "client_secret":HMAC_KEY.hex(),
        "client_type":2, "password":pw_hash,
        "response_type":"token", "uid":uid,
    }
    body = json.dumps(payload, separators=(',',':'))
    for attempt in range(3):
        try:
            r = _session().post(
                "https://100067.connect.garena.com/api/v2/oauth/guest/token:grant",
                headers={
                    "User-Agent":"GarenaMSDK/4.0.41(2107113SI ;Android 11;vi;VN;app 1.123.1 2019120270;)",
                    "Content-Type":"application/json; charset=utf-8",
                    "Host":"100067.connect.garena.com",
                }, data=body, timeout=30)
            d = r.json()
            if d.get("code") == 0:
                dd = d["data"]
                return dd.get("open_id"), dd.get("access_token")
        except: pass
        if attempt < 2: time.sleep(2)
    return None, None

# ====== STEP 3: MAJOR REGISTER ======
def major_register(access_token, open_id, nickname, lang):
    fields = {
        1:nickname, 2:access_token, 3:open_id,
        5:102000007, 6:4, 7:1,
        13:1, 14:xor_open_id(open_id), 15:lang,
        16:1, 17:1,
    }
    try:
        r = _session().post(
            f"{LOGIN_SERVER_URL}MajorRegister",
            headers={
                "Accept-Encoding":"gzip","Authorization":"Bearer",
                "Connection":"Keep-Alive",
                "Content-Type":"application/x-www-form-urlencoded",
                "Host":LOGIN_HOST,
                "ReleaseVersion":RELEASE_VERSION,
                "User-Agent":"UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                "X-GA":"v1 1","X-Unity-Version":"2022.3.47f1",
            },
            data=encrypt_pb(fields), verify=False, timeout=30)
        return r.status_code == 200
    except: return False

# ====== STEP 4: MAJOR LOGIN ======
def _build_major_login(access_token, open_id, lang):
    try:
        ip = requests.get('https://api.ipify.org', timeout=5).text
    except:
        ip = "192.136.11.167"
    return {
        3: time.strftime("%Y-%m-%d %H:%M:%S"),
        4: "free fire",
        5: 4,
        7: CLIENT_VERSION,
        8: "Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)",
        9: "Handheld",
        10: "Verizon Wireless",
        11: "WIFI",
        12: 1280,
        13: 960,
        15: "x86-64 SSE3 SSE4.1 SSE4.2 AVX AVX2 | 2400 | 4",
        16: 5951,
        17: "Adreno (TM) 640",
        18: "OpenGL ES 3.0",
        19: "Google|d00d071a-5662-486c-82e2-5dc03c5cb82e",
        20: ip,
        21: lang,
        22: str(open_id),
        23: 4,
        24: "Handheld",
        25: "Asus ASUS_I005DA",
        29: str(access_token),
        30: 1,
        41: "O2",
        42: "WIFI",
        57: "49ac4b80ecf0478a44203bf8fac6120f5",
        60: 32969,
        61: 29901,
        62: 2479,
        63: 900,
        64: 31298,
        65: 32969,
        66: 31298,
        67: 32969,
        70: 4,
        73: 3,
        76: 1,
        78: 6,
        79: 1,
        85: 3,
        88: 4,
        93: "3rd_party",
        94: "KqsHT0qaTCGUXRYnJ0Rqk4rOvTBtqRFCqrxSLo/afYBAXyCA5v4zw5F/rWCSaZuZONmV1TMDDY0q0rZ4Kys1ITUFfGM=",
        95: 111111,
        97: 1,
        98: 1,
        99: "4",
        100: "4",
        101: 1,
        102: bytes([71, 87, 76, 65, 86, 89, 9, 4, 78, 1, 12, 19, 15, 4, 64, 94, 65, 57, 89, 83, 15, 80, 91, 61, 15, 81, 91, 110, 82, 9, 60, 10, 84, 50]),
        103: 1,
        104: 0
    }

def major_login(access_token, open_id, lang):
    try:
        r = _session().post(
            f"{LOGIN_SERVER_URL}MajorLogin",
            headers={
                "Accept-Encoding": "gzip",
                "Authorization": "Bearer",
                "Connection": "Keep-Alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": LOGIN_HOST,
                "ReleaseVersion": RELEASE_VERSION,
                "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                "X-GA": "v1 1",
                "X-Unity-Version": "2022.3.47f1",
            },
            data=aes_encrypt(pb_encode(_build_major_login(access_token, open_id, lang))),
            verify=False,
            timeout=30
        )
        if r.status_code != 200:
            return None
        pb = ProtoBuf(r.content)
        res = pb.protobuf()
        account_id = res.get("1")
        lock_region = res.get("2")
        login_token = res.get("8")
        client_url = res.get("10", "")
        if isinstance(login_token, bytes):
            login_token = login_token.decode('utf-8', errors='ignore')
        elif isinstance(login_token, dict):
            login_token = str(login_token)
        if not client_url or not str(client_url).startswith("http"):
            client_url = DEFAULT_CLIENT_URL
        client_url = str(client_url).rstrip("/") + "/"
        return {
            "login_token": str(login_token) if login_token else "",
            "client_url": client_url,
            "account_id": account_id,
            "lock_region": str(lock_region) if lock_region else "",
        }
    except:
        return None
        
# ====== STEP 5: CHOOSE REGION ======
def choose_region(login_token, region):
    try:
        r = _session().post(
            f"{LOGIN_SERVER_URL}ChooseRegion",
            headers={
                "Accept-Encoding":"gzip",
                "Authorization":f"Bearer {login_token}",
                "Connection":"Keep-Alive",
                "Content-Type":"application/x-www-form-urlencoded",
                "Host":LOGIN_HOST,
                "ReleaseVersion":RELEASE_VERSION,
                "User-Agent":"UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                "X-GA":"v1 1","X-Unity-Version":"2022.3.47f1",
            },
            data=encrypt_pb({1:region}), verify=False, timeout=30)
        return r.status_code == 200
    except: return False

# ====== STEP 6: GET LOGIN DATA ======
def get_login_data(client_url, login_token, access_token, open_id, lang):
    if not client_url.endswith("/"): client_url += "/"
    host = client_url.replace("https://","").replace("http://","").rstrip("/")
    td = decode_jwt(login_token) or {}
    ext_type = td.get("external_type", 0); ext_id = td.get("external_id", ""); sig_md5 = td.get("signature_md5", "")
    fields = {
        3:time.strftime("%Y-%m-%d %H:%M:%S"), 7:CLIENT_VERSION,
        23:int(ext_type) if str(ext_type).isdigit() else 0, 29:str(ext_id) if ext_id else "",
        4:"free fire", 5:1, 8:"Android OS 9 / API-28 (PQ3A.190605.03171033/3793265)",
        9:"Handheld", 10:"MobiFone", 11:"WIFI", 12:1600, 13:900, 14:"240",
        15:"x86-64 SSE3 SSE4.1 SSE4.2 AVX | 2865 | 4", 17:"Adreno (TM) 640",
        18:"OpenGL ES 3.1 v1", 19:"Google|6d586c06-4a7b-4c8e-b2f1-99ac04c10d31",
        20:"104.28.156.112", 21:lang, 22:str(open_id), 24:"Handheld", 25:"Xiaomi 2203121C",
        26:"SG", 41:"MobiFone", 42:"WIFI", 57:str(sig_md5),
        60:49386, 61:47035, 62:2519, 63:736, 64:23753, 65:25132,
        66:49227, 67:49386, 70:4, 73:3,
        74:"/data/app/com.dts.freefireth-TGfGr55n7IBaojkeP6sM8Q==/lib/arm64",
        76:1, 77:"17e6a447803a17e4f59e3fd734efc5ae|/data/app/com.dts.freefireth-TGfGr55n7IBaojkeP6sM8Q==/base.apk",
        78:3, 79:2, 81:"64", 83:"2019120270", 85:3, 86:"OpenGLES2",
        87:255, 88:4, 90:"Singapore", 93:"android",
        94:"KqsHT1y2dlDX0ywnP1LQ75AXqqV8YVvFC48pUhDlHSFPi7zihMoH4je/A9lW1Sa5OUKZngMdKfCwTE8lUtNlp7X97/w=",
        95:11111, 96:'{"cur_rate":null,"support_etc2":false}', 97:1, 98:1
    }
    try:
        r = _session().post(
            f"{client_url}GetLoginData",
            headers={
                "Accept-Encoding":"gzip",
                "Authorization":f"Bearer {login_token}",
                "Connection":"Keep-Alive",
                "Content-Type":"application/x-www-form-urlencoded",
                "Host":host,
                "ReleaseVersion":RELEASE_VERSION,
                "User-Agent":"UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                "X-GA":"v1 1","X-Unity-Version":"2022.3.47f1",
            },
            data=encrypt_pb(fields), verify=False, timeout=30)
        return r.status_code == 200
    except: return False

# ====== HÀM CHỌN EMOTE ======
ChooseEmoteUrl = "https://clientbp.ggpolarbear.com/ChooseEmote"
EmotePayload = "CA F6 83 22 2A 25 C7 BE FE B5 1F 59 54 4D B3 13"

async def choose_emote_async(token: str):
    """Chọn emote cho acc"""
    payload = binascii.unhexlify(EmotePayload.replace(" ", ""))
    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 7.1.2; SM-G988N Build/NRD90M)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Bearer {token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB54",
        "Expect": "100-continue"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ChooseEmoteUrl,
                headers=headers,
                data=payload,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as res:
                return res.status == 200
    except:
        return False

def choose_emote_sync(token: str):
    """Chọn emote (đồng bộ)"""
    try:
        import requests
        import binascii
        
        payload = binascii.unhexlify(EmotePayload.replace(" ", ""))
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 7.1.2; SM-G988N Build/NRD90M)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54",
            "Expect": "100-continue"
        }
        response = requests.post(ChooseEmoteUrl, headers=headers, data=payload, verify=False, timeout=15)
        return response.status_code == 200
    except:
        return False

# ====== SỬA HÀM CREATE_ACCOUNT ======
def create_account(name_prefix, region):
    lang = REGION_LANG.get(region, "en")
    for overall in range(3):
        try:
            if overall > 0: time.sleep(3)
            nickname = generate_nickname(name_prefix)
            raw_pw, pw_hash = generate_password()
            uid = guest_register(pw_hash)
            if not uid: continue
            open_id, access_token = token_grant(uid, pw_hash)
            if not open_id: continue
            if not major_register(access_token, open_id, nickname, lang): continue
            time.sleep(0.5)
            ml_result = None
            for attempt in range(3):
                ml_result = major_login(access_token, open_id, lang)
                if ml_result: break
                time.sleep(1)
            if not ml_result: continue
            if not ml_result.get("lock_region"):
                choose_region(ml_result["login_token"], region)
                time.sleep(0.5)
                ml2 = None
                for attempt in range(3):
                    ml2 = major_login(access_token, open_id, lang)
                    if ml2 and ml2.get("lock_region"): break
                    time.sleep(1)
                if ml2: ml_result = ml2
            gld_ok = get_login_data(ml_result["client_url"], ml_result["login_token"], access_token, open_id, lang)
            status = "success" if gld_ok else "failed"
            
            # ====== GẮN EMOTE VÀO ACC ======
            emote_success = False
            if ml_result.get("login_token"):
                try:
                    emote_success = choose_emote_sync(ml_result["login_token"])
                    if emote_success:
                        print(f"{G}✅ Đã gắn emote cho {nickname}{C}")
                    else:
                        print(f"{Y}⚠️ Gắn emote thất bại cho {nickname}{C}")
                except Exception as e:
                    print(f"{R}❌ Lỗi gắn emote: {e}{C}")
            
            return {
                "uid": uid,
                "password": pw_hash,
                "raw_password": raw_pw,
                "name": nickname,
                "region": region,
                "access_token": access_token,
                "open_id": open_id,
                "account_id": ml_result.get("account_id", "N/A"),
                "login_token": ml_result.get("login_token", ""),
                "client_url": ml_result.get("client_url", ""),
                "lock_region": ml_result.get("lock_region", ""),
                "status": status,
                "emote": emote_success,
            }
        except:
            if overall < 2: time.sleep(3)
    return None
    
# ====== SAVE & SHOW ======
def save_account(acc, filename="accounts.json"):
    data = []
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except: pass
    
    data.append({
        "uid": acc.get("uid", "N/A"),
        "password": acc.get("password", ""),       
        "name": acc.get("name", "N/A"),
        "region": acc.get("region", "N/A"),
        "access_token": acc.get("access_token", ""),
        "open_id": acc.get("open_id", ""),
        "account_id": acc.get("account_id", "N/A"),
        "lock_region": acc.get("lock_region", ""),
        "status": acc.get("status", "unknown"),  
        "jwt": acc.get("login_token", ""),
    })
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ====== ĐỔI BIO ======
def change_bio(jwt_token, bio_text):
    """Đổi bio bằng JWT"""
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
    
    # Build protobuf
    def build_bio_proto(bio_text):
        result = b''
        
        def encode_varint(n):
            r = []
            while True:
                b = n & 0x7F
                n >>= 7
                if n:
                    b |= 0x80
                r.append(b)
                if not n:
                    break
            return bytes(r)
        
        # field_2 = 17
        header = (2 << 3) | 0
        result += encode_varint(header)
        result += encode_varint(17)
        
        # field_5 = EmptyMessage
        empty = b''
        header5 = (5 << 3) | 2
        result += encode_varint(header5)
        result += encode_varint(len(empty))
        result += empty
        
        # field_6 = EmptyMessage
        header6 = (6 << 3) | 2
        result += encode_varint(header6)
        result += encode_varint(len(empty))
        result += empty
        
        # field_8 = bio
        bio_encoded = bio_text.encode('utf-8')
        header8 = (8 << 3) | 2
        result += encode_varint(header8)
        result += encode_varint(len(bio_encoded))
        result += bio_encoded
        
        # field_9 = 1
        header9 = (9 << 3) | 0
        result += encode_varint(header9)
        result += encode_varint(1)
        
        # field_11 = EmptyMessage
        header11 = (11 << 3) | 2
        result += encode_varint(header11)
        result += encode_varint(len(empty))
        result += empty
        
        # field_12 = EmptyMessage
        header12 = (12 << 3) | 2
        result += encode_varint(header12)
        result += encode_varint(len(empty))
        result += empty
        
        return result
    
    for url in endpoints:
        try:
            proto = build_bio_proto(bio_text)
            cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
            encrypted = cipher.encrypt(pad(proto, AES.block_size))
            resp = requests.post(url, headers=headers, data=encrypted, verify=False, timeout=10)
            
            if resp.status_code == 200:
                return True, "✅ Đổi bio thành công!"
                            
            headers_json = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json",
                "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; SM-G998B Build/TP1A.220624.014)"
            }
            resp2 = requests.post(url, headers=headers_json, json={"bio": bio_text}, verify=False, timeout=10)
            
            if resp2.status_code == 200:
                return True, "✅ Đổi bio thành công!"
                
        except:
            continue
    
    return False, "❌ Đổi bio thất bại!"

# ====== show_account ======
def show_account(idx, acc):
    try:
        name = acc.get('name', 'N/A')
        uid = acc.get('uid', 'N/A')
        password = acc.get('raw_password', 'N/A')
        region = acc.get('region', 'N/A')
        account_id = acc.get('account_id', 'N/A')
        login_token = acc.get('login_token', '')
        status = acc.get('status', 'unknown')
        bio = acc.get('bio', '')
        bio_status = acc.get('bio_status', '')
        emote = acc.get('emote', False)  # THÊM DÒNG NÀY
         
        border = "═" * 58
        
        print(f"\n{C}╔{border}╗{R}")
        print(f"{C}║{GD}  ✅ ACCOUNT #{idx} CREATED SUCCESSFULLY{C}                     ║{R}")
        print(f"{C}╠{border}╣{R}")
        print(f"{C}║{R}  {P}👤 Name:{R}       {G}{name}{R}")
        print(f"{C}║{R}  {P}🆔 UID:{R}        {Y}{uid}{R}")
        print(f"{C}║{R}  {P}🔑 Password:{R}   {GR}{password[:10]}...{R}")
        print(f"{C}║{R}  {P}🌍 Region:{R}      {B}{region}{R}")
        print(f"{C}║{R}  {P}📛 Account ID:{R}  {M}{account_id}{R}")
        print(f"{C}║{R}  {P}📊 Status:{R}      {G}{status}{R}")
        
        # ====== HIỂN THỊ EMOTE ======
        if emote:
            print(f"{C}║{R}  {P}🎭 Emote:{R}      {G}✅ Đã gắn{R}")
        else:
            print(f"{C}║{R}  {P}🎭 Emote:{R}      {R}❌ Chưa gắn{R}")
            
        if login_token and login_token != "N/A" and isinstance(login_token, str) and login_token.startswith('eyJ'):
            print(f"{C}║{R}  {P}🔐 Login Token:{R} {GR}{login_token[:30]}...{R}")
        if bio:
            bio_icon = "✅" if bio_status == "success" else "❌"
            bio_color = G if bio_status == "success" else R
            print(f"{C}║{R}  {P}📝 Bio:{R}        {bio_color}{bio}{R}")
        print(f"{C}╚{border}╝{R}")        
    except Exception as e:
        print(f"{R}  [!] Error: {e}{C}")
                
# ====== generate_accounts ======

def generate_accounts(name, region, target_count, max_threads, bio=None):
    target_count = max(1, int(target_count))
    region = region.upper()
    if region not in REGION_LANG: region = "VN"
    max_threads = min(max(1, int(max_threads)), 100)
    
    print(f"\n{G}┌─────────────────────────────────────────────────────────┐")
    print(f"│{W}  Free Fire Account Creator Fixed{G}                    │")
    print(f"├─────────────────────────────────────────────────────────┤")
    print(f"│  {Y}Server  :{W} {LOGIN_SERVER_URL}")
    print(f"│  {Y}Version :{W} {CLIENT_VERSION} ({RELEASE_VERSION})")
    print(f"│  {Y}Region  :{W} {region}  |  Prefix : {name}")
    print(f"│  {Y}Target  :{W} {target_count}  |  Threads: {max_threads}")
    if bio:
        print(f"│  {Y}Bio     :{W} {bio[:30]}{'...' if len(bio)>30 else ''}")
    print(f"└─────────────────────────────────────────────────────────┘{C}\n")
    
    results = []
    start_time = time.time()
    failed_count = 0
    idx = 0
    bio_success = 0
    bio_fail = 0
    
    while len(results) < target_count:
        batch = min(9999, target_count - len(results))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as ex:
            futs = [ex.submit(create_account, name, region) for _ in range(batch)]
            for f in concurrent.futures.as_completed(futs):
                acc = f.result()
                idx += 1
                if acc:
                    if bio and acc.get('login_token'):
                        success, msg = change_bio(acc['login_token'], bio)
                        if success:
                            bio_success += 1
                            acc['bio'] = bio
                            acc['bio_status'] = 'success'
                        else:
                            bio_fail += 1
                            acc['bio_status'] = 'failed'
                    
                    results.append(acc)
                    save_account(acc)
                    show_account(idx, acc)
                else:
                    failed_count += 1
                    print(f"{R}❌ Failed ({failed_count}){C}")
    
    elapsed = time.time() - start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    seconds = int(elapsed % 60)
    
    print(f"\n{G}┌─────────────────────────────────────────────────────────┐")
    print(f"│{W}  ✅ Done: {len(results)}/{target_count} accounts{G}                 │")
    print(f"│  {Y}⏱️  Time:{W} {hours}h {minutes}m {seconds}s{G}                     │")
    print(f"│  {Y}❌ Failed:{W} {failed_count}{G}                                 │")
    if bio:
        print(f"│  {Y}📝 Bio success:{W} {bio_success}  ❌ failed:{W} {bio_fail}{G}         │")
    print(f"│  {Y}💾 Saved to:{W} accounts.json{G}                           │")
    print(f"└─────────────────────────────────────────────────────────┘{C}")
    return results

# ====== MAIN ======
if __name__ == '__main__':
    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"""
{G}   ███████╗ █████╗ ███╗   ██╗██╗  ██╗
{Y}   ╚══███╔╝██╔══██╗████╗  ██║╚██╗██╔╝
{Y}     ███╔╝ ███████║██╔██╗ ██║ ╚███╔╝ 
{Y}    ███╔╝  ██╔══██║██║╚██╗██║ ██╔██╗ 
{Y}   ███████╗██║  ██║██║ ╚████║██╔╝ ██╗
{Y}   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝{C}

{G}    FREE FIRE ACCOUNT CREATOR V.36 (FIXED BANNED){C}

{Y}    Admin   :{W} @zandev
{Y}    Group     :{W} https://t.me/zancommunity  
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
        
        print(f"\n{Y}[?]{W} Number of accounts {GR}(default 10){W}: {C}", end='')
        count_input = input().strip()
        count = int(count_input) if count_input.isdigit() else 10
        
        print(f"\n{Y}[?]{W} Number of threads {GR}(default 10){W}: {C}", end='')
        threads_input = input().strip()
        threads = int(threads_input) if threads_input.isdigit() else 10
        threads = max(1, min(threads, 100))
        
        print(f"\n{Y}[?]{W} Bio to set {GR}(leave empty to skip){W}: {C}", end='')
        bio = input().strip() or None
        
        print(f"\n{G}  [+] Starting Register in {region} region...{C}")
        
        # Loading animation
        chars = "●○◉◎◈◆◇"
        for i in range(15):
            sys.stdout.write(f"\r{G}  {chars[i % len(chars)]} {W}Loading Register Account...{C}")
            sys.stdout.flush()
            time.sleep(0.05)
        print()
        
        generate_accounts(name, region, count, threads, bio)
        
        print(f"\n{Y}[?]{W} Continue? {GR}(y/n){W}: {C}", end='')
        if input().strip().lower() != 'y':
            break