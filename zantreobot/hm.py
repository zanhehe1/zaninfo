import hmac, hashlib, json, requests, time, random, urllib3, ipaddress, os, sys, threading, re, signal, base64, socket, string, uuid
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from protobuf_decoder.protobuf_decoder import Parser
from colorama import init, Fore, Style
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

init(autoreset=True)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProtoBuf:
    def __init__(self, data): self.data = data
    def varint(self, b, p=0):
        r, s = 0, 0
        while s < 64 and p < len(b):
            x = b[p]; p += 1; r |= (x & 0x7F) << s
            if not (x & 0x80): return r, p
            s += 7
        return r, p
    def string(self, b, p):
        l, p = self.varint(b, p); np = min(p + l, len(b)); v = b[p:np]
        try: v = v.decode("utf-8")
        except: pass
        return v, np
    def fixed32(self, b, p):
        return (struct.unpack("<I", b[p:p+4])[0], p+4) if p+4 <= len(b) else (0, p)
    def fixed64(self, b, p):
        return (struct.unpack("<Q", b[p:p+8])[0], p+8) if p+8 <= len(b) else (0, p)
    def parse_field(self, b, p):
        if p >= len(b): return 0, None, p
        k, p = self.varint(b, p); fn, wt = k >> 3, k & 0x7
        try:
            if wt == 0: v, p = self.varint(b, p)
            elif wt == 1: v, p = self.fixed64(b, p)
            elif wt == 2: v, p = self.string(b, p)
            elif wt == 5: v, p = self.fixed32(b, p)
            else: return fn, None, p
        except: return fn, None, p
        return fn, v, p
    def protobuf(self, buf=None, off=0):
        if buf is None: buf = self.data
        r = {}
        while off < len(buf):
            fn, v, off = self.parse_field(buf, off)
            if isinstance(v, bytes) and v:
                try:
                    n = self.protobuf(v)
                    if n: v = n
                except: pass
            r.setdefault(str(fn), []).append(v)
        return {k: v[0] if len(v) == 1 else v for k, v in r.items()}


def Encrypt(v):
    v = int(v); r = []
    while v > 0x7F: r.append((v & 0x7F) | 0x80); v >>= 7
    r.append(v); return bytes(r)


def parse_results(pr):
    rd = {}
    for x in pr:
        if x.field not in rd: rd[x.field] = []
        if x.wire_type in ["varint", "string", "bytes"]: fd = x.data
        elif x.wire_type == "length_delimited": fd = parse_results(x.data.results)
        else: fd = {}
        rd[x.field].append(fd)
    return {k: v[0] if len(v) == 1 else v for k, v in rd.items()}


protobuf_dec = lambda d: json.dumps(parse_results(Parser().parse(d)), ensure_ascii=False)
def AES_CBC128(d, k, iv): return AES.new(k, AES.MODE_CBC, iv).encrypt(pad(d, 0x10))

def create_varint_field(fn, v): return Encrypt((fn << 3) | 0) + Encrypt(v)
def create_length_delimited_field(fn, v):
    ev = v.encode() if isinstance(v, str) else v
    return Encrypt((fn << 3) | 2) + Encrypt(len(ev)) + ev

def pb_encode(fields):
    p = bytearray()
    for f, v in fields.items():
        f = int(f)
        if isinstance(v, list):
            for i in v:
                if isinstance(i, dict): p.extend(create_length_delimited_field(f, pb_encode(i)))
        elif isinstance(v, dict): p.extend(create_length_delimited_field(f, pb_encode(v)))
        elif isinstance(v, int): p.extend(create_varint_field(f, v))
        elif isinstance(v, str) or isinstance(v, bytes): p.extend(create_length_delimited_field(f, v))
    return bytes(p)

def create_vr(N):
    if N < 0: return b''
    H = []
    while True:
        S = N & 0x7F; N >>= 7
        if N: S |= 0x80
        H.append(S)
        if not N: break
    return bytes(H)

def create_variant(fn, v): return create_vr((fn << 3) | 0) + create_vr(v)
def create_length(fn, v):
    ev = v.encode() if isinstance(v, str) else v
    return create_vr((fn << 3) | 2) + create_vr(len(ev)) + ev

def create_proto(fields):
    packet = bytearray()
    for f, v in fields.items():
        f = int(f)
        if isinstance(v, dict): packet.extend(create_length(f, create_proto(v)))
        elif isinstance(v, int): packet.extend(create_variant(f, v))
        elif isinstance(v, (str, bytes)): packet.extend(create_length(f, v))
    return packet

def decode_varint(data, offset):
    result = 0; shift = 0
    while offset < len(data):
        byte = data[offset]
        result |= (byte & 0x7F) << shift
        offset += 1
        if not (byte & 0x80): return result, offset
        shift += 7
    return None, offset

def decode_protobuf(data):
    result = {}; offset = 0
    while offset < len(data):
        header, offset = decode_varint(data, offset)
        if header is None: break
        field_number = header >> 3
        wire_type = header & 0x7
        if wire_type == 0:
            value, offset = decode_varint(data, offset)
            if value is not None: result[field_number] = value
        elif wire_type == 2:
            length, offset = decode_varint(data, offset)
            if length is None: break
            value = data[offset:offset + length]; offset += length
            try: result[field_number] = value.decode('utf-8')
            except: result[field_number] = value.hex()
        elif wire_type == 1: offset += 8
        elif wire_type == 5: offset += 4
        else: break
    return result


# ==================== CONSTANTS ====================
aes_key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
aes_iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
HEX_KEY = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
API_KEY = HEX_KEY.encode('utf-8')
PASSWORD_PREFIX = "zanxgay_"
PIXEL_UA = "GarenaMSDK/4.0.44(Pixel ;Android 10;en;US;app 1.132.1 2019121229;)"

SIG94_FIXED = "KqsHT8at0g7Na/G7iOeF1IpesHMf+HoePFMFFE8Tq/dSk4fIbJ1j8TdV8OAyWIVnSmD2rM6vfFMtCD8Ig7iROgDJmIMrdtcB6orwuNRpMr4MVu3D7FoTcuQdq/8EyOkRQiUrbg=="
SIG102_FIXED = bytes.fromhex('4000434f07555f0637')
SIG_MD5_FIXED = "7428b253defc164018c604a1ebbfebdf"

MAX_TOTAL_TIMEOUT = 1800

EXIT_FLAG = False
accounts_dict = {}
accounts_lock = threading.Lock()
success_count = 0
success_lock = threading.Lock()
fail_count = 0
fail_lock = threading.Lock()
selected_region = "VN"
base_name = "zandev"
base_password = "ZANDEV"
account_count = 100
print_lock = threading.Lock()
total_started = 0
total_started_lock = threading.Lock()
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ACC_FILE = os.path.join(CURRENT_DIR, "acc.json")

TOR_PROXY = "socks5h://127.0.0.1:9050"
TOR_ENABLED = True
TOR_ROTATE_INTERVAL = 1
TOR_CONTROL_PORT = 9051
_tor_request_count = 0
_tor_lock = threading.Lock()


def signal_handler(sig, frame):
    global EXIT_FLAG
    print(f"\n{Fore.YELLOW}[!] Dang dung...{Style.RESET_ALL}")
    EXIT_FLAG = True
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def log_step(step, status, detail=""):
    with print_lock:
        icon = f"{Fore.GREEN}[OK]{Style.RESET_ALL}" if status == "OK" else (f"{Fore.RED}[!!]{Style.RESET_ALL}" if status == "FAIL" else f"{Fore.YELLOW}[..]{Style.RESET_ALL}")
        line = f"  {icon} {step:<20}"
        if detail: line += f" {Fore.WHITE}{detail}{Style.RESET_ALL}"
        print(line, flush=True)

def log_account_success(uid, password, account_id, access_token, index, total):
    with print_lock:
        print(f"\n{Fore.CYAN}-- ACC #{index}/{total} --{Style.RESET_ALL}", flush=True)
        print(f"  UID   : {Fore.CYAN}{uid}{Style.RESET_ALL}", flush=True)
        print(f"  Pass  : {Fore.MAGENTA}{password}{Style.RESET_ALL}", flush=True)
        print(f"  ID Game: {Fore.WHITE}{account_id}{Style.RESET_ALL}", flush=True)
        print(f"  Status: {Fore.GREEN}success{Style.RESET_ALL}", flush=True)

def get_next_started():
    global total_started
    with total_started_lock:
        total_started += 1
        return total_started


def load_accounts():
    global accounts_dict
    accounts_dict = {}
    try:
        if os.path.exists(ACC_FILE):
            with open(ACC_FILE, 'r', encoding='utf-8') as f:
                d = json.load(f)
            if isinstance(d, list):
                for info in d:
                    uid = str(info.get("uid", ""))
                    if uid: accounts_dict[uid] = info
            elif isinstance(d, dict):
                accounts_dict = d
            return len(accounts_dict)
    except: pass
    return 0

def save_accounts():
    with accounts_lock:
        data = list(accounts_dict.values())
    ordered = []
    for info in data:
        ordered.append({
            "uid": str(info.get("uid", "")),
            "password": str(info.get("password", "")),
            "account_id": str(info.get("account_id", "")),
            "access_token": str(info.get("access_token", "")),
            "status": str(info.get("status", ""))
        })
    try:
        with open(ACC_FILE, 'w', encoding='utf-8') as f:
            json.dump(ordered, f, indent=2, ensure_ascii=False)
        return True
    except: return False

def account_exists(uid):
    with accounts_lock:
        return str(uid) in accounts_dict

def get_next_count():
    global success_count
    with success_lock:
        success_count += 1
        return success_count


class IPRotator:
    CIDRS = {"VN": ["1.52.0.0/14", "14.160.0.0/11", "27.64.0.0/12", "113.160.0.0/12"]}
    _cache = {}
    @classmethod
    def get_ip(cls, region="VN"):
        r = region.upper()
        if r not in cls._cache:
            hosts = []
            for cidr in cls.CIDRS.get(r, ["27.0.0.0/8"]):
                try:
                    net = ipaddress.ip_network(cidr, strict=False)
                    for _ in range(3):
                        ii = int(net.network_address) + random.randint(1, 2 ** (32 - net.prefixlen) - 2)
                        hosts.append(str(ipaddress.IPv4Address(ii)))
                except: continue
            cls._cache[r] = hosts if hosts else [f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"]
        return random.choice(cls._cache[r])
    @classmethod
    def headers(cls, region="VN"):
        ip = cls.get_ip(region)
        return {'X-Forwarded-For': ip, 'X-Real-IP': ip, 'Client-IP': ip}


_SUPER = "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079"

def gen_name(bn):
    c = (bn or "zan").replace("/", "").replace("\\", "").strip()[:12]
    if len(c) >= 12: return c[:12]
    return f"{c}{''.join(random.choice(_SUPER) for _ in range(12 - len(c)))}"

def gen_pass():
    r = PASSWORD_PREFIX + os.urandom(10).hex(); return r, r


def tor_get_proxies():
    return {"http": TOR_PROXY, "https": TOR_PROXY} if TOR_ENABLED else None

def tor_rotate_ip():
    global _tor_request_count
    if not TOR_ENABLED: return False
    with _tor_lock:
        _tor_request_count += 1
        if _tor_request_count % TOR_ROTATE_INTERVAL != 0: return False
        try:
            s = socket.socket()
            s.connect(("127.0.0.1", TOR_CONTROL_PORT))
            s.send(b'AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\nQUIT\r\n')
            s.close()
            time.sleep(2)
            return True
        except: return False

def tor_request(method, url, **kw):
    px = tor_get_proxies()
    if px: kw.setdefault("proxies", px)
    kw.setdefault("timeout", 30)
    kw.setdefault("verify", False)
    for _ in range(3):
        try:
            tor_rotate_ip()
            return requests.get(url, **kw) if method.upper() == "GET" else requests.post(url, **kw)
        except requests.exceptions.ConnectionError as e:
            if "NameResolution" in str(e) or "resolve" in str(e):
                time.sleep(3); continue
            time.sleep(1)
        except: time.sleep(1)
    return None

def check_tor():
    if not TOR_ENABLED: return True
    try:
        r = requests.get("https://api.ipify.org?format=json", proxies=tor_get_proxies(), timeout=20, verify=False)
        if r.status_code == 200:
            ip = r.json().get("ip", "unknown")
            print(f"  {Fore.GREEN}[TOR OK]{Style.RESET_ALL} IP: {Fore.YELLOW}{ip}{Style.RESET_ALL}", flush=True)
            return ip
    except Exception as e:
        print(f"  {Fore.RED}[TOR FAIL]{Style.RESET_ALL} {str(e)[:60]}", flush=True)
        return None
    return None


# ==================== API ====================
def register_account(password, region, iph):
    url = "https://100067.connect.garena.com/api/v2/oauth/guest:register"
    pj = {"app_id": 100067, "client_type": 2, "password": password, "source": 2}
    pl = json.dumps(pj, separators=(',', ':'))
    sg = hmac.new(API_KEY, pl.encode(), hashlib.sha256).hexdigest()
    ts = str(int(time.time() * 1000) + random.randint(-999, 999))
    h = {"User-Agent": PIXEL_UA, "Authorization": f"Signature {sg}", "Content-Type": "application/json; charset=utf-8",
         "Accept": "application/json", "Connection": "Keep-Alive", "Host": "100067.connect.garena.com",
         "X-Garena-Timestamp": ts, **iph}
    try:
        r = tor_request("POST", url, headers=h, data=pl)
        if r and r.status_code == 200:
            j = r.json()
            if j.get("code") == 0 and "data" in j:
                return str(j["data"]["uid"]), str(password)
            log_step("GuestRegister", "FAIL", f"code={j.get('code')}")
        elif r: log_step("GuestRegister", "FAIL", f"HTTP {r.status_code}")
        else: log_step("GuestRegister", "FAIL", "no resp")
        return None, None
    except Exception as e:
        log_step("GuestRegister", "FAIL", str(e)[:40]); return None, None


def get_access_token(uid, password, region, iph):
    url = "https://100067.connect.garena.com/api/v2/oauth/guest/token:grant"
    h = {"Host": "100067.connect.garena.com", "User-Agent": PIXEL_UA, "Content-Type": "application/json; charset=utf-8",
         "Accept": "application/json", "Accept-Encoding": "gzip, deflate", "Connection": "close", **iph}
    d = {"client_id": 100067, "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
         "client_type": 2, "device_id": "01b05346c944b5e6", "password": password, "response_type": "token", "uid": int(uid)}
    try:
        r = tor_request("POST", url, headers=h, json=d)
        if r and r.status_code == 200:
            j = r.json()
            if j.get("code") == 0 and "data" in j:
                x = j["data"]
                return x.get("access_token"), x.get("open_id"), int(x.get("platform", 4) or 4)
        return None, None, None
    except: return None, None, None


def device_id_generate(open_id, region, iph):
    url = "https://100067.msdk.garena.com/device/api/v1/android/device-id:generate"
    pj = {"app_id": 100067, "data": {"ad_aaid": "", "android_id": "01b05346c944b5e6", "android_version_release": "10",
        "android_version_sdk": "29", "brand": "Google", "build_date": "1697185398000", "build_display": "NHG47O release-keys",
        "build_id": "NHG47O", "cpu_abis": "arm64-v8a,armeabi-v7a,armeabi", "drm_id": "", "drm_vendor": "",
        "fingerprint": "Google/sailfish/sailfish:10/NHG47O/eng.build.20231013.013027:user/release-keys", "gcbooster_uuid": "",
        "hardware": "msm8996", "imei": "", "model": "Pixel", "key_mqs_uuid": "", "product_name": "sailfish",
        "random_uuid": str(uuid.uuid4()), "soc_manufacturer": "", "soc_model": ""}}
    pl = json.dumps(pj, separators=(',', ':'))
    sg = hmac.new(API_KEY, pl.encode(), hashlib.sha256).hexdigest()
    h = {"User-Agent": PIXEL_UA, "Authorization": f"Signature {sg}", "Accept": "application/json",
         "Content-Type": "application/json; charset=utf-8", "Host": "100067.msdk.garena.com",
         "Connection": "Keep-Alive", "Accept-Encoding": "gzip", **iph}
    try:
        r = tor_request("POST", url, headers=h, data=pl)
        if r and r.status_code == 200:
            j = r.json()
            if j.get("code") == 0: return j["data"].get("device_id", "")
        return ""
    except: return ""


def major_register(access_token, open_id, name, region, iph, LANG='vi'):
    try:
        ks = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
        eo = ""
        for i, ch in enumerate(open_id): eo += chr(ord(ch) ^ ks[i % len(ks)])
        f14 = eo.encode('latin1')
        f22 = bytes.fromhex('474752450101010067020000a6a42db7bc5516876af3d1ba4adc337bac558af092eb3757d59d65c9323bba42c6593a48b74f33b2b5b3dc45cbd7ac02040db58f394045be4835213e12c35e5566445a5224f39d205fcf91c0e6bec797e7b3968ac00e90d7500b5865828a9d6f2091c3070f5319a130748e407ed57e6638974670ac045631b3d08c310cf1256cebcf1aed2d97d177534603d1c95d9c5d698340e797e72aa7ecc67a33122e48b0dfda050a1649586aca5e979be1fd9d99f48cd8cf59630e0ff60f67d4ed2ec4e5e7475970449a6c06329009ee0ce2567892587675781a31e4bb2774403b2f78e9811df2cb397fa602572266747704c6258077910902eb7420bcb4ab743d1610cddba9019e7867aaad3aa7ba9b04968064a409b66733f9f78c566a25ff478cba37a2ffe23203d4b05bceef826f174b0be7912d19432cc759325251fa094d70693fb672d6f9e799284081b3adb541dd8f27ef80dcf1e7f0ff30f2fd976659457ce41e175a2d6301b777981ccc16b9a8247abaab8de0867836c27de0146fe4d0e1fd39b86ba51f0b58601cfcbd7f6f3451fe4184b26ed44ac2f6f7bb4ce5d9a80f88c2cbfe7553e5ab97c8b028ae16b4f70f037753b8c229a6e5e9038fcbb9b4c2abb954894f8f2faf177bfdaab3b0ed537156633621d16b62d58ba4ebe518997c33e2304976ba6af9df7e7e34302c7910ae559c7e3d20a30d71c14f85c0e86f26291bbf18c2d9dfe9a908592eea4523e6c1e5d9bb5abfbebfccd5c4e136f9be777723e932b06c029df5125191000c90fde62a8e5f8fceb28648f0c69ec3037d09302b2ade908a20dbd42761ca449b2743fc362649e16235769d9fbd7f87cd64972b58d69c0441abb5d22ddc6ed059f7ac1bdbfaef8c60e64631809c5e08c7cb4074c8ce6170d94b411604986be4ae163a')
        rc = region.upper() if region else "VN"
        f = {}
        f[1] = name; f[2] = str(access_token); f[3] = str(open_id)
        f[5] = 102000007; f[6] = 4; f[7] = 1; f[8] = rc; f[9] = "live"; f[10] = rc; f[13] = 1
        f[14] = f14; f[15] = LANG; f[16] = 1; f[17] = 1; f[18] = 1; f[19] = "\x010"
        f[20] = "1.132.8"; f[21] = 1; f[22] = f22; f[23] = 1; f[24] = 56431; f[25] = 1
        f[26] = "https://dl.gmc.freefiremobile.com/live/ABHotUpdates/|https://core-gmc.freefiremobile.com/live/ABHotUpdates/|211c933168f55902c7dfbfd8c4e2957d"
        f[27] = "1.3fb8adbf45f44ce9"
        f[30] = base64.b64encode(str(access_token or "").encode()).decode()
        url = "https://loginbp.ppmainecoonghj.com/MajorRegister"
        pl = AES_CBC128(pb_encode(f), aes_key, aes_iv)
        h = {"Accept-Encoding": "gzip", "Authorization": "Bearer", "Connection": "Keep-Alive",
             "Content-Type": "application/x-www-form-urlencoded", "Expect": "100-continue",
             "Host": "loginbp.ppmainecoonghj.com", "ReleaseVersion": "OB55",
             "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
             "X-GA": "v1 1", "X-GA-SV": str(int(time.time())), "X-Unity-Version": "2018.4.12f1", **iph}
        try: r = tor_request("POST", url, headers=h, data=pl)
        except: r = None
        if r is None:
            log_step("MajorRegister", "FAIL", "conn fail"); return {}
        if r.status_code == 200:
            try:
                p = ProtoBuf(r.content).protobuf()
                p = {int(k) if isinstance(k, str) and str(k).isdigit() else k: v for k, v in p.items()}
                if 3 in p:
                    log_step("MajorRegister", "OK", f"account_id={p[3]}")
                    return p
            except: pass
            log_step("MajorRegister", "FAIL", "no field 3"); return {}
        log_step("MajorRegister", "FAIL", f"status={r.status_code}")
        return {}
    except Exception as e:
        log_step("MajorRegister", "FAIL", str(e)[:40]); return {}


def choose_newbie_choice(account_id, region, iph):
    url = "https://loginbp.ppmainecoonghj.com/ChooseNewbieChoice"
    if not account_id: return False
    pf = {1: int(account_id), 2: 1, 3: 3}
    pl = AES_CBC128(pb_encode(pf), aes_key, aes_iv)
    h = {"Accept-Encoding": "gzip", "Authorization": "Bearer", "Connection": "Keep-Alive",
         "Content-Type": "application/x-www-form-urlencoded", "Expect": "100-continue",
         "Host": "loginbp.ppmainecoonghj.com", "ReleaseVersion": "OB55",
         "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
         "X-GA": "v1 1", "X-GA-SV": str(int(time.time())), "X-Unity-Version": "2018.4.12f1", **iph}
    try:
        r = tor_request("POST", url, headers=h, data=pl)
        if r and r.status_code == 200:
            log_step("ChooseNewbie", "OK"); return True
        return False
    except: return False


def major_login_payload(access_token, open_id, platform_type):
    fields = {3: str(datetime.now())[:-7], 4: "free fire", 5: 1, 7: "1.132.6",
        8: "Android OS 10 / API-29 (NHG47O/eng.build.20231013.013027)", 9: "Handheld",
        10: "TelKila", 11: "WIFI", 12: 1708, 13: 750, 14: "440",
        15: "ARM64 FP ASIMD AES | 2850 | 8", 16: 3968, 17: "Mali-G610 MC6",
        18: "OpenGL ES 3.2 v1.r32p1-01eac0.54329dee8f160f288c574caaf67bbe3f",
        19: "Google|0ecc7b3b-6c41-462e-9050-26d835e84c53", 20: "116.97.105.60", 21: "en",
        22: open_id, 23: str(platform_type), 24: "Handheld", 25: "Google Pixel", 26: "SG",
        29: access_token, 30: 1, 41: "TelKila", 42: "WIFI",
        57: "7428b253defc164018c604a1ebbfebdf", 60: 109029, 61: 37616, 62: 2048, 63: 804,
        64: 37616, 65: 109029, 66: 37616, 67: 109029, 73: 3,
        74: "/data/app/com.dts.freefireth-oiglMJkEoNJlsRci10280Q==/lib/arm64", 76: 1,
        77: "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/com.dts.freefireth-oiglMJkEoNJlsRci10280Q==/base.apk",
        78: 3, 79: 2, 81: "64", 83: "2019121229", 85: 3, 86: "OpenGLES2", 87: 511, 88: platform_type,
        92: 36711, 93: "android", 94: SIG94_FIXED, 96: '{"cur_rate":null,"support_etc2":false}',
        97: 1, 99: f"{platform_type}", 100: f"{platform_type}", 102: SIG102_FIXED, 104: 1797, 105: 1,
        106: "https://dl.cdn.freefiremobile.com/live/ABHotUpdates/|https://dl-core.cdn.freefiremobile.com/live/ABHotUpdates/|4a0070ac356973792f002e0b25b96c3b",
        107: "c8e41b7a93f02d56e1a94c7b8203f5d1"}
    return AES_CBC128(create_proto(fields), aes_key, aes_iv)


def get_login_data_payload(access_token, open_id, platform_type):
    fields = {3: str(datetime.now())[:-7], 4: "free fire", 5: 1, 7: "1.132.6",
        8: "Android OS 10 / API-29 (NHG47O/eng.build.20231013.013027)", 9: "Handheld",
        10: "TelKila", 11: "WIFI", 12: 1708, 13: 750, 14: "440",
        15: "ARM64 FP ASIMD AES | 2850 | 8", 16: 3968, 17: "Mali-G610 MC6",
        18: "OpenGL ES 3.2 v1.r32p1-01eac0.54329dee8f160f288c574caaf67bbe3f",
        19: "Google|0ecc7b3b-6c41-462e-9050-26d835e84c53", 20: "116.97.105.60", 21: "en",
        22: open_id, 23: str(platform_type), 24: "Handheld", 25: "Google Pixel", 26: "SG",
        29: access_token, 30: 1, 41: "TelKila", 42: "WIFI",
        57: "7428b253defc164018c604a1ebbfebdf", 60: 109029, 61: 37616, 62: 2048, 63: 804,
        64: 37616, 65: 109029, 66: 37616, 67: 109029, 73: 3,
        74: "/data/app/com.dts.freefireth-oiglMJkEoNJlsRci10280Q==/lib/arm64", 76: 1,
        77: "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/com.dts.freefireth-oiglMJkEoNJlsRci10280Q==/base.apk",
        78: 3, 79: 2, 81: "64", 83: "2019121229", 85: 3, 86: "OpenGLES2", 87: 511, 88: platform_type,
        90: bytes.fromhex('48e1baa3692044c6b0c6a16e67'), 91: "61", 92: 36711, 93: "android",
        94: SIG94_FIXED, 96: '{"cur_rate":null,"support_etc2":false}', 97: 1, 99: "0",
        100: str(platform_type), 102: SIG102_FIXED, 103: 1, 104: 1797, 105: 1,
        106: "https://dl.cdn.freefiremobile.com/live/ABHotUpdates/|https://dl-core.cdn.freefiremobile.com/live/ABHotUpdates/|4a0070ac356973792f002e0b25b96c3b",
        107: "c8e41b7a93f02d56e1a94c7b8203f5d1"}
    return AES_CBC128(create_proto(fields), aes_key, aes_iv)


def _decode_varint(data, offset):
    r = 0; s = 0
    while offset < len(data):
        b = data[offset]; r |= (b & 0x7F) << s; offset += 1
        if not (b & 0x80): return r, offset
        s += 7
    return None, offset


def _extract_jwt(raw):
    o = 0
    while o < len(raw) - 1:
        idx = raw.find(b"\x42", o)
        if idx < 0: break
        length, after = _decode_varint(raw, idx + 1)
        if length is None: o = idx + 1; continue
        end = after + length
        if end <= len(raw) and raw[after:after + 3] == b"eyJ": return raw[after:end]
        o = idx + 1
    return None


def major_login(payload, region, iph):
    url = "https://loginbp.ppmainecoonghj.com/MajorLogin"
    headers = {'X-Unity-Version': '2018.4.12f1', 'ReleaseVersion': 'OB55',
        'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': 'Bearer',
        'Accept': '*/*', 'Expect': '100-continue', 'X-GA': 'v1 1', 'X-GA-SV': str(int(time.time())),
        'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
        'Host': 'loginbp.ppmainecoonghj.com', 'Connection': 'Keep-Alive',
        'Accept-Encoding': 'deflate, gzip', **iph}
    try:
        response = tor_request("POST", url, headers=headers, data=payload)
        if not response:
            log_step("MajorLogin", "FAIL", "no resp"); return {}
        if response.status_code == 200:
            jwt_bytes = _extract_jwt(response.content)
            if jwt_bytes:
                login_token = jwt_bytes.decode('utf-8', 'replace')
                account_id = ""
                try:
                    parts = login_token.split('.')
                    if len(parts) >= 2:
                        p = parts[1] + '=' * ((4 - len(parts[1]) % 4) % 4)
                        jd = json.loads(base64.urlsafe_b64decode(p))
                        account_id = str(jd.get('account_id', ''))
                except: pass
                log_step("MajorLogin", "OK", f"id={account_id}")
                return {"login_token": login_token, "account_id": account_id,
                        "server_url": "https://clientbp.ppmainecoonghj.com"}
            log_step("MajorLogin", "FAIL", "no jwt"); return {}
        log_step("MajorLogin", "FAIL", f"status={response.status_code}"); return {}
    except Exception as e:
        log_step("MajorLogin", "FAIL", str(e)[:40]); return {}


def get_login_data(server_url, jwt_token, payload, region, iph):
    url = f"{server_url}/GetLoginData"
    headers = {'X-Unity-Version': '2018.4.12f1', 'ReleaseVersion': 'OB55',
        'Content-Type': 'application/x-www-form-urlencoded', 'X-GA': 'v1 1',
        'X-GA-SV': str(int(time.time())),
        'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
        'Host': 'clientbp.ppmainecoonghj.com', 'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip', 'Authorization': f'Bearer {jwt_token}', **iph}
    try:
        response = tor_request("POST", url, headers=headers, data=payload)
        if response and response.status_code == 200:
            log_step("GetLoginData", "OK", f"len={len(response.content)}")
            return decode_protobuf(response.content)
        log_step("GetLoginData", "FAIL", f"status={response.status_code if response else 'None'}")
        return {}
    except Exception as e:
        log_step("GetLoginData", "FAIL", str(e)[:40]); return {}


def clientbp_post(endpoint, server_url, jwt_token, payload, region, iph):
    url = f"{server_url}/{endpoint}"
    headers = {'X-Unity-Version': '2018.4.12f1', 'ReleaseVersion': 'OB55',
        'Content-Type': 'application/x-www-form-urlencoded', 'X-GA': 'v1 1',
        'X-GA-SV': str(int(time.time())),
        'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
        'Host': 'clientbp.ppmainecoonghj.com', 'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip', 'Authorization': f'Bearer {jwt_token}', **iph}
    try:
        response = tor_request("POST", url, headers=headers, data=payload)
        if response and response.status_code == 200:
            return 200, decode_protobuf(response.content)
        return (response.status_code if response else -1), {}
    except: return -1, {}


def complete_login(server_url, jwt_token, access_token, open_id, account_id, region, iph):
    eps = [("GetPlatformProfile", {1: access_token, 2: open_id, 3: 1}),
        ("GetPlayerPersonalShow", {1: int(account_id), 2: 9, 3: 1, 4: 1}),
        ("GetWorkshopSwitch", {}), ("GetFriend", {1: 1, 7: 1, 9: 1}), ("LoginGetProfile", {}),
        ("GetPlayerDailyCSRankingSummary", {}), ("GetPlayerDailyRankingSummary", {}),
        ("LoginGetAccountInfo", {1: "en", 2: 1, 3: 1}), ("LoginGetSplash", {1: "en", 2: 2, 3: 1}),
        ("LoginGetDesc", {1: "en", 2: 1, 3: "VN", 4: 1}), ("Ping", {})]
    ok = 0
    for ep, fields in eps:
        payload = AES_CBC128(create_proto(fields), aes_key, aes_iv)
        status, _ = clientbp_post(ep, server_url, jwt_token, payload, region, iph)
        if status == 200: ok += 1
    log_step("CompleteLogin", "OK", f"{ok}/{len(eps)}")
    return ok


def create_full_account(thread_id, region, bn, bp, max_retries=5):
    global fail_count, EXIT_FLAG, account_count
    if EXIT_FLAG: return None
    for _ in range(max_retries):
        try:
            iph1 = IPRotator.headers(region)
            iph2 = IPRotator.headers(region)
            iph3 = IPRotator.headers(region)
            iph4 = IPRotator.headers(region)

            rp, _ = gen_pass()
            name = gen_name(bn)

            ruid, _ = register_account(rp, region, iph1)
            if not ruid: continue

            at, oid, pt = get_access_token(ruid, rp, region, iph2)
            if not at: continue
            log_step("GetAccessToken", "OK", f"uid={ruid}")

            device_id_generate(oid, region, iph2)

            rr = major_register(at, oid, name, region, iph3)
            if rr: rr = {int(k) if isinstance(k, str) and str(k).isdigit() else k: v for k, v in rr.items()}
            if not rr or 3 not in rr: continue
            aid = str(rr[3])

            choose_newbie_choice(aid, region, iph3)
            time.sleep(random.uniform(1, 3))

            payload = major_login_payload(at, oid, pt)
            lr = major_login(payload, region, iph4)
            if not lr: continue

            jwt_token = lr["login_token"]
            server_url = lr["server_url"]
            aid = lr.get("account_id") or aid

            gld_payload = get_login_data_payload(at, oid, pt)
            get_login_data(server_url, jwt_token, gld_payload, region, iph4)

            complete_login(server_url, jwt_token, at, oid, aid, region, iph4)

            if not account_exists(ruid):
                get_next_count()
                si = get_next_started()
                with accounts_lock:
                    accounts_dict[str(ruid)] = {
                        "uid": str(ruid), "password": str(rp),
                        "account_id": str(aid), "access_token": str(at),
                        "status": "success"
                    }
                save_accounts()
                log_account_success(ruid, rp, aid, at, si, account_count)
                return {"uid": str(ruid), "password": str(rp), "account_id": str(aid),
                        "access_token": str(at), "status": "success"}
            else: return None
        except Exception as e:
            log_step("Exception", "FAIL", str(e)[:40]); continue
    with fail_lock: fail_count += 1
    return None


def worker(thread_id, region, bn, bp):
    global EXIT_FLAG, success_count, account_count
    while not EXIT_FLAG:
        try:
            with success_lock:
                if success_count >= account_count: break
            create_full_account(thread_id, region, bn, bp)
        except: time.sleep(0.1)


def menu_input(prompt, default=None):
    m = f"  > {prompt} (mac dinh {default}): " if default else f"  > {prompt}: "
    try:
        v = input(m).strip(); return v if v else default
    except: return default


def main():
    global success_count, selected_region, base_name, account_count, fail_count, EXIT_FLAG, total_started
    selected_region = "VN"; total_started = 0
    print(f"\n{Fore.CYAN}=== GUEST GENERATOR - VN ==={Style.RESET_ALL}\n", flush=True)

    if TOR_ENABLED:
        ip = check_tor()
        if not ip:
            print(f"  {Fore.RED}[-] Tor THAT BAI{Style.RESET_ALL}\n", flush=True)
            if input(f"  Tiep tuc khong Tor? (y/n): ").lower() != "y": return

    print(f"  {Fore.GREEN}[+] Region: VN (co dinh){Style.RESET_ALL}\n", flush=True)

    ni = menu_input("Tien to ten acc", "zan")
    base_name = ni if ni else "zan"
    print(f"  {Fore.GREEN}[+] Tien to: {base_name}{Style.RESET_ALL}\n", flush=True)

    try:
        c = int(menu_input("So luong acc", "10"))
        account_count = c if c > 0 else 10
    except: account_count = 10
    print(f"  {Fore.GREEN}[+] Muc tieu: {account_count}{Style.RESET_ALL}\n", flush=True)

    try:
        tc = int(menu_input("So threads", "5"))
        tc = min(max(tc, 1), 100)
    except: tc = 5
    print(f"  {Fore.GREEN}[+] Threads: {tc}{Style.RESET_ALL}\n", flush=True)

    ex = load_accounts(); success_count = 0
    print(f"  {Fore.CYAN}Acc co san: {ex}{Style.RESET_ALL}", flush=True)
    print(f"  {Fore.YELLOW}[!] Nhan ENTER de bat dau...{Style.RESET_ALL}", end="", flush=True)
    input()

    print(f"\n  {Fore.GREEN}[+] Dang chay {tc} threads | Region VN...{Style.RESET_ALL}\n", flush=True)
    print(f"  {'-' * 60}", flush=True)

    st = time.time(); ths = []
    for i in range(tc):
        t = threading.Thread(target=worker, args=(i, selected_region, base_name, base_password), daemon=True)
        t.start(); ths.append(t)

    try:
        while not EXIT_FLAG:
            time.sleep(1)
            with success_lock:
                success_done = success_count
            with fail_lock:
                fail_done = fail_count

            # Dung khi success du HOAC tong thu du
            if success_done >= account_count or (success_done + fail_done) >= account_count:
                break

            # Timeout cung 30 phut
            if time.time() - st > MAX_TOTAL_TIMEOUT:
                print(f"\n  {Fore.YELLOW}[!] TIMEOUT 30 phut - Dung{Style.RESET_ALL}\n", flush=True)
                EXIT_FLAG = True
                break
    except KeyboardInterrupt:
        EXIT_FLAG = True
        print(f"\n  {Fore.YELLOW}[!] Dang dung...{Style.RESET_ALL}", flush=True)

    for t in ths: t.join(timeout=2)
    el = time.time() - st
    save_accounts()

    print(f"\n  {'=' * 60}", flush=True)
    print(f"  {Fore.GREEN}Da tao: {success_count}{Style.RESET_ALL}  |  {Fore.RED}That bai: {fail_count}{Style.RESET_ALL}  |  {Fore.CYAN}Thoi gian: {el:.2f}s{Style.RESET_ALL}", flush=True)
    print(f"  {Fore.CYAN}Da luu: acc.json{Style.RESET_ALL}\n", flush=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] DA DUNG - Dang luu...{Style.RESET_ALL}", flush=True)
        try:
            save_accounts()
            print(f"{Fore.GREEN}[+] Da luu acc.json{Style.RESET_ALL}\n", flush=True)
        except: pass
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}[-] LOI: {e}{Style.RESET_ALL}", flush=True)
        try: save_accounts()
        except: pass
        sys.exit(1)