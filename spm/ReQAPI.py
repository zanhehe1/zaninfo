import requests, json, base64, time, struct, datetime, re, hmac, hashlib, random, uuid, os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from protobuf_decoder.protobuf_decoder import Parser
from typing import Dict, Any, Optional, Tuple, Union, TypedDict, List
from dataclasses import dataclass
from enum import IntEnum

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEBUG = False
def _log(*a, **k):
    if DEBUG: print(*a, **k)

_DEVICE_ID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "device_id.txt")

def _load_device_id():
    try:
        if os.path.exists(_DEVICE_ID_FILE):
            with open(_DEVICE_ID_FILE, "r", encoding="utf-8") as f:
                did = f.read().strip()
                if did: return did
    except Exception: pass
    did = f"Google|{uuid.uuid4()}"
    try:
        with open(_DEVICE_ID_FILE, "w", encoding="utf-8") as f:
            f.write(did)
    except Exception: pass
    return did

_VN_IP_RANGES = [
    ("113.160", "113.161"), ("113.161", "113.162"), ("123.16", "123.17"),
    ("14.160", "14.161"), ("14.161", "14.162"), ("27.64", "27.65"),
    ("27.65", "27.66"), ("116.96", "116.97"), ("116.97", "116.98"),
    ("171.224", "171.225"), ("171.225", "171.226"), ("27.72", "27.73"),
    ("113.22", "113.23"), ("113.23", "113.24"), ("118.68", "118.69"),
    ("42.112", "42.113"), ("42.113", "42.114"), ("203.162", "203.163"),
]

def _random_vn_ip():
    try:
        a_str, b_str = random.choice(_VN_IP_RANGES)
        a1, a2 = a_str.split(".")
        prefix = f"{a1}.{a2}"
        o3 = random.randint(0, 255); o4 = random.randint(1, 254)
        return f"{prefix}.{o3}.{o4}"
    except Exception:
        while True:
            a = random.randint(1, 223)
            if a in (10, 127): continue
            b = random.randint(0, 31) if 172 <= a <= 172 else random.randint(0, 255)
            c = random.randint(0, 255); d = random.randint(1, 254)
            return f"{a}.{b}.{c}.{d}"

def _err(name, msg):
    if DEBUG: print(f"[ERR] {name}: {msg}")

class ProtoBuf:
    def __init__(self, data): self.data = data
    def varint(self, buffer, pos=0):
        result, shift = 0, 0
        while shift < 64 and pos < len(buffer):
            byte = buffer[pos]; pos += 1
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80): return result, pos
            shift += 7
        return result, pos
    def repeated(self, data):
        pos, out = 0, []
        while pos < len(data):
            val, pos = self.varint(data, pos); out.append(val)
        return out
    def string(self, buffer, pos):
        length, pos = self.varint(buffer, pos)
        newpos = min(pos + length, len(buffer))
        value = buffer[pos:newpos]
        try: value = value.decode("utf-8")
        except: pass
        return value, newpos
    def fixed32(self, buffer, pos):
        return (struct.unpack("<I", buffer[pos:pos + 4])[0], pos + 4) if pos + 4 <= len(buffer) else (0, pos)
    def fixed64(self, buffer, pos):
        return (struct.unpack("<Q", buffer[pos:pos + 8])[0], pos + 8) if pos + 8 <= len(buffer) else (0, pos)
    def parse_field(self, buffer, pos):
        if pos >= len(buffer): return 0, None, pos
        key, pos = self.varint(buffer, pos)
        fn, wt = key >> 3, key & 0x7
        try:
            if wt == 0: value, pos = self.varint(buffer, pos)
            elif wt == 1: value, pos = self.fixed64(buffer, pos)
            elif wt == 2: value, pos = self.string(buffer, pos)
            elif wt == 5: value, pos = self.fixed32(buffer, pos)
            else: return fn, None, pos
        except: return fn, None, pos
        return fn, value, pos
    def protobuf(self, buffer=None, offset=0):
        if buffer is None: buffer = self.data
        result = {}
        while offset < len(buffer):
            fn, value, offset = self.parse_field(buffer, offset)
            if isinstance(value, bytes) and value:
                try:
                    nested = self.protobuf(value)
                    if nested: value = nested
                except: pass
            result.setdefault(str(fn), []).append(value)
        return {k: v[0] if len(v) == 1 else v for k, v in result.items()}
    def fieldsRaw(self, buf, pos):
        start = pos
        key, pos = self.varint(buf, pos)
        num, wt = key >> 3, key & 0x7
        if wt == 0: _, end = self.varint(buf, pos)
        elif wt == 1: end = pos + 8
        elif wt == 2:
            length, lp = self.varint(buf, pos); end = lp + length
        elif wt == 5: end = pos + 4
        else: return num, wt, b'', pos, pos
        return num, wt, buf[start:end], pos, end
    def EXTRACT_FIELDS(self, fields, mode="repeated"):
        cur = self.data
        for depth, target in enumerate(fields):
            pos = 0; found = False
            if depth == len(fields) - 1:
                results = []
                while pos < len(cur):
                    num, wt, raw, vs, ve = self.fieldsRaw(cur, pos)
                    if num == target:
                        if mode == "repeated":
                            if wt == 0:
                                val, _ = self.varint(cur, vs); results.append(val)
                            elif wt == 2:
                                _, lp = self.varint(cur, vs)
                                results += self.repeated(cur[lp:ve])
                        elif mode == "bytes":
                            if wt == 2:
                                _, lp = self.varint(cur, vs)
                                results.append(cur[lp:ve])
                            else:
                                results.append(cur[vs:ve])
                    pos = ve
                if not results: return []
                return results[0] if len(results) == 1 else results
            else:
                while pos < len(cur):
                    num, wt, raw, vs, ve = self.fieldsRaw(cur, pos)
                    if num == target and wt == 2:
                        _, lp = self.varint(cur, vs); cur = cur[lp:ve]; found = True; break
                    pos = ve
                if not found: return []
        return []

def Encrypt(value):
    value = int(value); result = []
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80); value >>= 7
    result.append(value); return bytes(result)

def parse_results(parsed_results):
    result_dict = {}
    for result in parsed_results:
        if result.field not in result_dict: result_dict[result.field] = []
        if result.wire_type in ["varint", "string", "bytes"]:
            field_data = result.data
        elif result.wire_type == "length_delimited":
            field_data = parse_results(result.data.results)
        else: field_data = None
        result_dict[result.field].append(field_data)
    return {k: v[0] if len(v) == 1 else v for k, v in result_dict.items()}

protobuf_dec = lambda data: json.dumps(parse_results(Parser().parse(data)), ensure_ascii=False)

def AES_CBC128(data, key, iv):
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pad(data, 0x10))

def _scalar(v):
    while isinstance(v, (list, tuple)) and v: v = v[0]
    return v

def _as_bytes(v):
    v = _scalar(v)
    if v is None: return None
    if isinstance(v, bytes): return v
    if isinstance(v, bytearray): return bytes(v)
    if isinstance(v, str): return v.encode("latin-1")
    if isinstance(v, (list, tuple)):
        try: return bytes(v)
        except: return None
    return None

def create_varint_field(fn, value):
    return Encrypt((fn << 3) | 0) + Encrypt(value)

def create_length_delimited_field(fn, value):
    ev = value.encode() if isinstance(value, str) else value
    return Encrypt((fn << 3) | 2) + Encrypt(len(ev)) + ev

def pb_encode(fields):
    packet = bytearray()
    for field, value in fields.items():
        field = int(field)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    packet.extend(create_length_delimited_field(field, pb_encode(item)))
        elif isinstance(value, dict):
            packet.extend(create_length_delimited_field(field, pb_encode(value)))
        elif isinstance(value, int):
            packet.extend(create_varint_field(field, value))
        elif isinstance(value, (str, bytes)):
            packet.extend(create_length_delimited_field(field, value))
    return bytes(packet)

class gayerr(Exception): pass

@dataclass
class account_data:
    access_token = ""
    open_id = ""
    platform = 0x4
    login_platform = 0x4
    main_active_platform = 0x4
    chat_ip = chat_port = online_ip = online_port = ""
    create_time = None
    expiry_time = None
    guild_id = None
    guild_code = None
    login_token = None
    account_id = None
    server = None
    base_url = None
    login_time = None
    key = None
    iv = None
    device_id = None

class gringay:
    @staticmethod
    def tokendecode(token):
        try:
            parts = token.split(".")
            if len(parts) != 3: raise gayerr("Invalid token format")
            payload = parts[1] + "=" * (4 - len(parts[1]) % 4)
            return json.loads(base64.urlsafe_b64decode(payload).decode('utf-8'))
        except: pass
    @staticmethod
    def format_timestamp(timestamp):
        if timestamp is None: return ""
        return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp))

def bdversion(ver=None):
    try:
        if not ver:
            try:
                from google_play_scraper import app as play_store_app
                ver = play_store_app('com.dts.freefireth', lang="fr", country='fr')['version']
            except: ver = "1.132.9"
        r = requests.get(f'https://version.ggwhitehawk.com/live/ver.php?version={ver}&lang=en&device=android&channel=android&appsttore=googleplay&region=ME&whitelist_version=1.3.0&whitelist_sp_version=1.0.0&device_name=google%20G011A&device_CPU=ARMv7%20VFPv3%20NEON%20VMH&device_GPU=Adreno%20(TM)%20640&device_mem=1993', verify=False, timeout=10).json()
        return {"server_url": r['server_url'],
                "latest_release_version": r.get('latest_release_version') or "OB55",
                "remote_version": ver}
    except:
        return {"server_url": "https://loginbp.ppmainecoonghj.com/",
                "latest_release_version": "OB55", "remote_version": "1.132.9"}

class APIClient:
    def __init__(self, device_id=None):
        self._data = account_data()
        self.logindata = {}
        detail_vers = bdversion()
        self.is_emulator = False
        self.language = "en"
        self.base_url = detail_vers["server_url"]
        self.client_version = "1.132.9"
        self.release_version = detail_vers.get("latest_release_version") or "OB55"
        self.key = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
        self.iv = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
        self._data.device_id = device_id if device_id else _load_device_id()
        host_name = "loginbp.ppmainecoonghj.com"
        self.session = requests.Session()
        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            _retry = Retry(total=3, backoff_factor=0.5,
                           status_forcelist=[429, 500, 502, 503, 504],
                           allowed_methods=["POST", "GET"])
            _ad = HTTPAdapter(max_retries=_retry, pool_connections=10, pool_maxsize=10)
            self.session.mount("https://", _ad); self.session.mount("http://", _ad)
        except Exception as e: _log("[RetryAdapter]", e)
        self.session.headers.update({
            "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
            "X-GA": "v1 1", "X-GA-SV": str(int(time.time())),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "deflate, gzip", "Accept": "*/*",
            "X-Unity-Version": "2018.4.12f1",
            "Host": host_name, "ReleaseVersion": self.release_version})

    def auth_guest_token(self, uid, password):
        payload = {"uid": str(uid), "password": str(password),
                   "response_type": "token", "client_type": "2", "client_id": "100067",
                   "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"}
        try:
            data = requests.post("https://auth.garena.com/oauth/guest/token/grant",
                data=payload,
                headers={"Accept-Encoding": "gzip, deflate",
                         "Content-Type": "application/x-www-form-urlencoded",
                         "User-Agent": "Mozilla/5.0 (Android 9; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0"},
                timeout=15).json()
            if "access_token" not in data:
                _err("auth_guest_token", f"no access_token: {data}")
                return "account not found"
            self._data.access_token = data["access_token"]
            self._data.open_id = data["open_id"]
            self._data.platform = data.get("platform", 0x4)
            self._data.login_platform = data.get("login_platform", 0x4)
            self._data.main_active_platform = data.get("main_active_platform")
            self._data.create_time = data.get("create_time")
            self._data.expiry_time = data.get("expiry_time")
        except Exception as e: _err("auth_guest_token", e)

    def auth_token_inspect(self, access_token):
        try:
            data = requests.get("https://auth.garena.com/oauth/token/inspect",
                                params={"token": access_token}, timeout=36).json()
            if "open_id" not in data: raise gayerr("Invalid access token")
            self._data.access_token = access_token
            self._data.open_id = data["open_id"]
            self._data.platform = data.get("platform", 0x4)
            self._data.login_platform = data.get("login_platform", 0x4)
            self._data.main_active_platform = data.get("main_active_platform")
            self._data.create_time = data.get("create_time")
            self._data.expiry_time = data.get("expiry_time")
        except Exception as e: _err("auth_token_inspect", e)

    def MajorLogin(self):
        try:
            if not self._data.device_id:
                self._data.device_id = _load_device_id()
            fake_ip = _random_vn_ip()
            fields = {}
            fields[3] = str(datetime.datetime.now())[:-7]; fields[4] = "free fire"
            fields[5] = 1; fields[7] = "1.132.15"
            fields[8] = "Android OS 16 / API-36 (BP2A.250605.031.A3/compiler260821111235)"
            fields[9] = "Handheld"; fields[10] = "VNPT Corp"; fields[11] = "WIFI"
            fields[12] = 2800; fields[13] = 1260; fields[14] = "403"
            fields[15] = "ARM64 FP ASIMD AES | 6028 | 8"; fields[16] = 11284
            fields[17] = "Adreno (TM) 735"
            fields[18] = "OpenGL ES 3.2 V@0762.41 (GIT@f6b5df5188, I29aebc4401, 1758283784) (Date:09/19/25)"
            fields[19] = self._data.device_id; fields[20] = fake_ip
            fields[21] = "vn"; fields[22] = str(self._data.open_id)
            fields[23] = "4"; fields[24] = "Handheld"; fields[25] = "vivo V2352A"
            fields[26] = "VN"; fields[29] = str(self._data.access_token)
            fields[30] = 1; fields[41] = "VNPT Corp"; fields[42] = "WIFI"
            fields[57] = "7428b253defc164018c604a1ebbfebdf"
            fields[60] = 228423; fields[61] = 145375; fields[62] = 7639
            fields[63] = 900; fields[64] = 145503; fields[65] = 228423
            fields[66] = 145503; fields[67] = 228423; fields[70] = 2; fields[73] = 3
            fields[74] = "/data/app/~~-y-UIr3gmLEdmMjW2LQb8Q==/com.dts.freefireth--DZnru7704bHkg4HUT_TmA==/lib/arm64"
            fields[76] = 1
            fields[77] = "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~-y-UIr3gmLEdmMjW2LQb8Q==/com.dts.freefireth--DZnru7704bHkg4HUT_TmA==/base.apk"
            fields[78] = 3; fields[79] = 2; fields[81] = "64"; fields[83] = "2019121229"
            fields[85] = 3; fields[86] = "OpenGLES2"; fields[87] = 8191; fields[88] = 4
            fields[90] = "Hà Nội"; fields[91] = "01"; fields[92] = 6390; fields[93] = "android"
            fields[94] = "KqsHT1CLbxae244E4dTGVqfMNKgyfNgwdom5oUKUVVi5ketwd/fNOTTK7CCFbGyfUhCvdLIJVGPVNaJUo6gmLWB4RQfS+M90qolEywjfzgJysWyD"
            fields[95] = 110009
            fields[96] = '{"cur_rate":[60,90,120,144],"support_etc2":false}'
            fields[97] = 1; fields[98] = 1; fields[99] = "4"; fields[100] = "4"
            fields[102] = {}; fields[102][8] = 3771217491960797021
            fields[103] = 1; fields[104] = 61996; fields[105] = 1
            fields[106] = "https://dl.gmc.freefiremobile.com/live/ABHotUpdates/|https://core-gmc.freefiremobile.com/live/ABHotUpdates/|dff941d41e6e3a9e76f05ed71fdc8d87"
            fields[107] = "1.16032533697c9e9e"

            payload = AES_CBC128(pb_encode(fields), self.key, self.iv)
            url = "https://loginbp.ppmainecoonghj.com/MajorLogin"
            headers = {"X-Unity-Version": "2018.4.12f1", "ReleaseVersion": "OB55",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Bearer", "Accept": "*/*",
                "Expect": "100-continue", "X-GA": "v1 1",
                "X-GA-SV": str(int(time.time())),
                "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                "Host": "loginbp.ppmainecoonghj.com",
                "Connection": "Keep-Alive", "Accept-Encoding": "deflate, gzip"}
            r = requests.post(url, headers=headers, data=payload, verify=False, timeout=30)
            if r.status_code != 200:
                _err("MajorLogin", f"HTTP {r.status_code}"); return
            raw = r.content
            pb = ProtoBuf(raw); res = pb.protobuf()
            if len(raw) > 64:
                pb2 = ProtoBuf(raw[64:]); res2 = pb2.protobuf()
                if res2.get("8") or res2.get("1"): pb, res = pb2, res2
            tok = _scalar(res.get("8"))
            if isinstance(tok, bytes): tok = tok.decode("utf-8", "replace")
            if not (isinstance(tok, str) and tok.count(".") == 2):
                _err("MajorLogin", f"no token. keys: {list(res.keys())}"); return
            self._data.account_id = _scalar(res.get("1"))
            self._data.server = _scalar(res.get("3"))
            self._data.login_token = tok
            bu = _scalar(res.get("10"))
            if isinstance(bu, bytes): bu = bu.decode("utf-8", "replace")
            self._data.base_url = bu
            self._data.login_time = _scalar(res.get("21"))
            self._data.key = _as_bytes(pb.EXTRACT_FIELDS([22], mode="bytes"))
            self._data.iv = _as_bytes(pb.EXTRACT_FIELDS([23], mode="bytes"))
            if not self._data.key: self._data.key = self.key
            if not self._data.iv: self._data.iv = self.iv
        except Exception as e:
            _err("MajorLogin", f"{type(e).__name__}: {e}")

    def GetLoginData(self):
        try:
            if not self._data.login_token:
                _err("GetLoginData", "login_token rỗng"); return
            fake_ip = _random_vn_ip()
            fields = {}
            fields[3] = str(datetime.datetime.now())[:-7]; fields[4] = "free fire"
            fields[5] = 1; fields[7] = "1.132.15"
            fields[8] = "Android OS 16 / API-36 (BP2A.250605.031.A3/compiler260821111235)"
            fields[9] = "Handheld"; fields[10] = "VNPT Corp"; fields[11] = "WIFI"
            fields[12] = 2800; fields[13] = 1260; fields[14] = "403"
            fields[15] = "ARM64 FP ASIMD AES | 6028 | 8"; fields[16] = 11284
            fields[17] = "Adreno (TM) 735"
            fields[18] = "OpenGL ES 3.2 V@0762.41 (GIT@f6b5df5188, I29aebc4401, 1758283784) (Date:09/19/25)"
            fields[19] = self._data.device_id; fields[20] = fake_ip
            fields[21] = "vn"; fields[22] = str(self._data.open_id)
            fields[23] = "4"; fields[24] = "Handheld"; fields[25] = "vivo V2352A"
            fields[26] = "VN"; fields[29] = str(self._data.access_token)
            fields[30] = 1; fields[41] = "VNPT Corp"; fields[42] = "WIFI"
            fields[57] = "7428b253defc164018c604a1ebbfebdf"
            fields[60] = 228423; fields[61] = 145375; fields[62] = 7639
            fields[63] = 900; fields[64] = 145503; fields[65] = 228423
            fields[66] = 145503; fields[67] = 228423; fields[70] = 2; fields[73] = 3
            fields[74] = "/data/app/~~-y-UIr3gmLEdmMjW2LQb8Q==/com.dts.freefireth--DZnru7704bHkg4HUT_TmA==/lib/arm64"
            fields[76] = 1
            fields[77] = "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~-y-UIr3gmLEdmMjW2LQb8Q==/com.dts.freefireth--DZnru7704bHkg4HUT_TmA==/base.apk"
            fields[78] = 3; fields[79] = 2; fields[81] = "64"; fields[83] = "2019121229"
            fields[85] = 3; fields[86] = "OpenGLES2"; fields[87] = 8191; fields[88] = 4
            fields[90] = "Hà Nội"; fields[91] = "01"; fields[92] = 6390; fields[93] = "android"
            fields[94] = "KqsHT1CLbxae244E4dTGVqfMNKgyfNgwdom5oUKUVVi5ketwd/fNOTTK7CCFbGyfUhCvdLIJVGPVNaJUo6gmLWB4RQfS+M90qolEywjfzgJysWyD"
            fields[95] = 110009
            fields[96] = '{"cur_rate":[60,90,120,144],"support_etc2":false}'
            fields[97] = 1; fields[98] = 1; fields[99] = "4"; fields[100] = "4"
            fields[102] = {}; fields[102][8] = 3771217491960797021
            fields[103] = 1; fields[104] = 61996; fields[105] = 1
            fields[106] = "https://dl.gmc.freefiremobile.com/live/ABHotUpdates/|https://core-gmc.freefiremobile.com/live/ABHotUpdates/|dff941d41e6e3a9e76f05ed71fdc8d87"
            fields[107] = "1.16032533697c9e9e"

            base = str(self._data.base_url or "")
            url = base.rstrip("/") + "/GetLoginData"
            host_header = base.replace("https://", "").replace("http://", "").rstrip("/")
            response = self.session.post(url,
                headers={"Authorization": "Bearer %s" % self._data.login_token,
                         "Host": host_header},
                data=AES_CBC128(pb_encode(fields), self.key, self.iv),
                timeout=30, verify=False)
            data = json.loads(protobuf_dec(response.content.hex()))
            self.logindata = data
            self._data.guild_id = data.get("20")
            self._data.guild_code = data.get("55")
            sv = _scalar(data.get("14")); chat = _scalar(data.get("32"))
            sv = str(sv or ""); chat = str(chat or "")
            if len(chat) > 6: self._data.chat_port, self._data.chat_ip = chat[-5:], chat[:-6]
            if len(sv) > 6: self._data.online_port, self._data.online_ip = sv[-5:], sv[:-6]
        except Exception as e:
            _err("GetLoginData", f"{type(e).__name__}: {e}")

    def ChooseNewbieChoice(self, uid):
        try:
            url = f"{self.base_url.rstrip('/')}/ChooseNewbieChoice"
            host = self.base_url.replace("https://", "").replace("http://", "").rstrip("/")
            try: uid_val = int(uid) if str(uid).isdigit() else uid
            except: uid_val = uid
            proto = pb_encode({1: uid_val, 2: 2, 3: 3})
            payload = AES_CBC128(proto, self.key, self.iv)
            headers = {"Accept-Encoding": "gzip", "Authorization": "Bearer",
                "Connection": "Keep-Alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": host, "ReleaseVersion": self.release_version,
                "Content-Length": str(len(payload)),
                "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                "X-GA": "v1 1", "X-GA-SV": str(int(time.time())),
                "X-Unity-Version": "2018.4.12f1"}
            r = requests.post(url, headers=headers, data=payload, verify=False, timeout=30)
            return r.status_code == 200
        except Exception as e:
            _err("ChooseNewbieChoice", f"{type(e).__name__}: {e}"); return False

    def ChooseRegion(self, region_code="VN"):
        try:
            if not self._data.login_token: return False
            url = f"{self.base_url.rstrip('/')}/ChooseRegion"
            host = self.base_url.replace("https://", "").replace("http://", "").rstrip("/")
            rc = "RU" if region_code.upper() == "CIS" else region_code.upper()
            proto = pb_encode({1: rc})
            payload = AES_CBC128(proto, self.key, self.iv)
            headers = {"Accept-Encoding": "gzip",
                "Authorization": f"Bearer {self._data.login_token}",
                "Connection": "Keep-Alive",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": host, "ReleaseVersion": self.release_version,
                "Content-Length": str(len(payload)),
                "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                "X-GA": "v1 1", "X-GA-SV": str(int(time.time())),
                "X-Unity-Version": "2018.4.12f1"}
            r = requests.post(url, headers=headers, data=payload, verify=False, timeout=30)
            _log(f"[ChooseRegion] {region_code} → {r.status_code}")
            return r.status_code == 200
        except Exception as e:
            _err("ChooseRegion", f"{type(e).__name__}: {e}"); return False

    def _auth_packet(self, fox=True):
        if not self._data.login_token: return None
        regions = self.logindata.get("19") or []
        if isinstance(regions, dict): regions = [regions]
        esid = lambda rec: (lambda s: s[str(rec).upper()] if str(rec).upper() in s else None)(
            {str(x["2"]).upper(): x["1"] for x in regions if isinstance(x, dict) and "1" in x and "2" in x})
        tok = self._data.login_token
        if isinstance(tok, bytes): tok = tok.decode("utf-8", "replace")
        enc = AES_CBC128(str(tok).encode(), self._data.key, self._data.iv)
        region = int(_scalar(esid(self._data.server)) or 1)
        aid = int(_scalar(self._data.account_id) or 0)
        kts = int(_scalar(self._data.login_time) or 0)
        cmd = 1 if fox else (101 + (aid % 50))
        hdr = bytes([cmd & 0xFF, region & 0xFF]) + struct.pack(">Q", aid) + struct.pack(">I", kts & 0xFFFFFFFF)
        if fox: return hdr + struct.pack(">I", len(enc)) + enc
        return hdr + struct.pack(">Q", len(enc)) + enc

    def TAO_PACKET_XT(self):
        try: return self._auth_packet(True)
        except Exception as e:
            _err("TAO_PACKET_XT", e); return None

    def TAO_PACKET_LOBBY(self):
        try: return self._auth_packet(False)
        except Exception as e:
            _err("TAO_PACKET_LOBBY", e); return None

    def auth(self, access_token, is_emulator=False, force_region=None):
        try:
            self.is_emulator = is_emulator
            if ":" in access_token:
                uid, password = access_token.split(":")
                self.auth_guest_token(int(uid), password)
            else:
                self.auth_token_inspect(access_token)

            if not self._data.access_token:
                return "account not found: guest token fail"

            self.MajorLogin()
            if not self._data.login_token:
                return "account not found: major login fail"

            self.GetLoginData()
            if not self.logindata:
                # 🔥 ACC CHƯA VERIFY → bind region + login lại
                if force_region:
                    _log(f"[auth] acc chưa verify → bind {force_region}")
                    self.ChooseNewbieChoice(self._data.account_id or 0)
                    ok_bind = self.ChooseRegion(force_region)
                    _log(f"[auth] ChooseRegion {force_region} → {ok_bind}")
                    self.MajorLogin()
                    if self._data.login_token:
                        self.GetLoginData()
                if not self.logindata:
                    return "account not found: get logindata fail"

            pkt = self.TAO_PACKET_XT()
            if not pkt:
                return "account not found: build packet fail"

            return self._build_api_response(pkt)
        except Exception as e:
            return f"account not found: {type(e).__name__}: {e}"

    def _build_api_response(self, authpacket):
        if not self._data.login_token or not authpacket: return "account not found"
        if not self._data.key or not self._data.iv: return "account not found"
        tok = self._data.login_token
        if isinstance(tok, bytes): tok = tok.decode("utf-8", "replace")
        data = gringay.tokendecode(tok)
        if self._data.guild_id:
            guild = {"id": self._data.guild_id, "secret_code": self._data.guild_code}
        else: guild = False
        saddress = {"chatip": self._data.chat_ip, "chatport": self._data.chat_port,
                    "onlineip": self._data.online_ip, "onlineport": self._data.online_port}
        response = {}
        response["CreateTime"] = gringay.format_timestamp(self._data.create_time)
        response["ExpiryTime"] = gringay.format_timestamp(self._data.expiry_time)
        response["UserAuthPacket"] = list(authpacket)
        lobby_pkt = self.TAO_PACKET_LOBBY()
        response["UserAuthPacketLobby"] = list(lobby_pkt) if lobby_pkt else list(authpacket)
        response["UserAuthToken"] = tok
        response["LoginTime"] = self._data.login_time
        response["UserNickName"] = data.get("nickname")
        response["UserAccountUID"] = data.get("account_id")
        response["LockRegion"] = data.get("lock_region")
        response["ClientVersion"] = data.get("client_version")
        response["IsEmulator"] = data.get("is_emulator")
        response["GuildData"] = guild
        response["BaseUrl"] = self._data.base_url or ""
        response["key"] = list(self._data.key)
        response["iv"] = list(self._data.iv)
        response["logindata"] = self.logindata
        response["GameServerAddress"] = saddress
        return response

class FreeFireAPI:
    def __init__(self):
        self.client = APIClient()
    def get(self, target, is_emulator=False, force_region=None):
        return self.client.auth(target, is_emulator, force_region=force_region)