#usr/bin/env python3
"""
Auto Proxy Manager - Reg Free Fire
- Đọc proxy từ data.txt (ip:port) trước, fallback tải từ URL
- Reg TUYỆT ĐỐI chỉ qua proxy — KHÔNG BAO GIỜ direct
- Reg OK → Verify ReQAPI 30 lần → lưu vào ac.json (uid:pass)
"""

import os, sys, json, time, random, string, hashlib, hmac, uuid, queue

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED

import requests, urllib3
from requests.adapters import HTTPAdapter
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

try:
    import blackboxprotobuf
except ImportError:
    os.system("pip install blackboxprotobuf -q")
    import blackboxprotobuf

# ReQAPI
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from ReQAPI import FreeFireAPI
    _REQAPI_ERR = None
except Exception as _e:
    FreeFireAPI = None
    _REQAPI_ERR = _e

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
if os.name == "nt":
    os.system("chcp 65001 > nul")
    os.system("")

# ═══════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════
GUEST_REGISTER = "https://ffmconnect.live.gop.garenanow.com/api/v2/oauth/guest:register"
TOKEN_GRANT    = "https://ffmconnect.live.gop.garenanow.com/api/v2/oauth/guest/token:grant"
MAJOR_REGISTER = "https://loginbp.ppmainecoonghj.com/MajorRegister"
NEWBIE_CHOICE  = "https://loginbp.ppmainecoonghj.com/ChooseNewbieChoice"
CHECK_URL      = "https://ffmconnect.live.gop.garenanow.com/"

MAIN_KEY = bytes.fromhex(
    '326565343438313965396234353938383435313431303637'
    '6232383136323138373464306435643761663964386637653030'
    '6331653534373135623764316533'
)
AES_KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
AES_IV  = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
APP_ID       = 100067
RELEASE_VER  = "OB55"
GAME_VERSION = "2.132.4"

# ═══════════════════════════════════════════════════════════
#  🔥 PROXY SOURCE — ĐỌC TỪ data.txt
# ═══════════════════════════════════════════════════════════
PROXY_FILE = "data.txt"
USE_FILE_PROXY = True   # True = dùng data.txt, False = tải từ URL

# Fallback: nếu data.txt rỗng/không có thì tải từ URL
PROXY_SOURCE_URL = [
    "https://raw.githubusercontent.com/Monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/proxy.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
]

RUN_LIMIT         = 0
THREADS           = 30
CHECK_THREADS     = 50
PROXY_TIMEOUT     = (6, 10)
HTTP_TIMEOUT      = (10, 20)
PROXY_RETRY       = 5
PROXY_429_LIMIT   = 20
VERIFY_ATTEMPTS   = 30
CHECK_INTERVAL    = 300
ACQUIRE_TIMEOUT   = 15
# ═══════════════════════════════════════════════════════════

ACC_FILE = os.environ.get("AC_FILE", "ac.json")

# ═══════════════════════════════════════════════════════════
#  COLOR
# ═══════════════════════════════════════════════════════════
rs="\033[0m"; b="\033[1m"; dim="\033[2m"
red="\033[38;5;196m"; grn="\033[38;5;46m"; yel="\033[38;5;226m"
cyan="\033[38;5;51m"; pur="\033[38;5;141m"; pink="\033[38;5;201m"
gry="\033[38;5;239m"; wht="\033[38;5;255m"

def cls():
    if os.environ.get("NO_CLEAR") == "1":
        return
    os.system("cls" if os.name == "nt" else "clear")
def ts(): return f"{gry}[{time.strftime('%H:%M:%S')}]{rs}"

PRINT_LOCK = threading.Lock()
def out(m):
    with PRINT_LOCK: print(m)
def info(m): out(f"{ts()} {cyan}[ INFO ]{rs} {m}")
def warn(m): out(f"{ts()} {yel}[ WARN ]{rs} {m}")
def ok(m):   out(f"{ts()} {grn}[  OK  ]{rs} {m}")
def bad(m):  out(f"{ts()} {red}[ FAIL ]{rs} {m}")

# ═══════════════════════════════════════════════════════════
#  MSDK
# ═══════════════════════════════════════════════════════════
USERAGENTS_MSDK = [
    "GarenaMSDK/4.0.44(ASUS_AI2501_B ;Android 12;en;US;app 2.132.1 2019118525;)",
    "GarenaMSDK/4.0.42(SM-S918B ;Android 14;en;US;app 2.132.1 2019118525;)",
    "GarenaMSDK/4.0.45(Pixel 7 ;Android 14;en;US;app 2.132.1 2019118525;)",
    "GarenaMSDK/4.0.43(OnePlus 11 ;Android 14;en;US;app 2.132.1 2019118525;)",
    "GarenaMSDK/4.0.41(Xiaomi 13 ;Android 13;en;US;app 2.132.1 2019118525;)",
    "GarenaMSDK/4.0.40(POCO F5 ;Android 13;en;US;app 2.132.1 2019118525;)",
    "GarenaMSDK/4.0.39(Redmi Note 11 ;Android 12;en;US;app 2.132.1 2019118525;)",
    "GarenaMSDK/4.0.38(SM-A546B ;Android 14;en;US;app 2.132.1 2019118525;)",
]

HEADERS_MSDK = {
    "User-Agent": USERAGENTS_MSDK[0],
    "Content-Type": "application/json; charset=utf-8",
    "Connection": "keep-alive",
}
HEADERS_LOGINBP = {
    'Host': 'loginbp.ppmainecoonghj.com',
    'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
    'Accept': '*/*',
    'Accept-Encoding': 'deflate, gzip',
    'Authorization': 'Bearer',
    'X-GA': 'v1 1',
    'ReleaseVersion': RELEASE_VER,
    'Content-Type': 'application/x-www-form-urlencoded',
    'X-Unity-Version': '2018.4.12f1',
}

# ═══════════════════════════════════════════════════════════
#  ACC.JSON — load/save thread-safe
# ═══════════════════════════════════════════════════════════
ACC_LOCK = threading.Lock()
ACC_DATA = {}

def acc_load():
    global ACC_DATA
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ACC_FILE)
    if not os.path.exists(path):
        ACC_DATA = {}
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            ACC_DATA = d
        else:
            ACC_DATA = {}
    except Exception as e:
        warn(f"acc_load: {e} — bắt đầu với dict rỗng")
        ACC_DATA = {}
    return len(ACC_DATA)

def acc_save():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ACC_FILE)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ACC_DATA, f, indent=4, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception as e:
        warn(f"acc_save: {e}")

def acc_add(uid, pwd):
    with ACC_LOCK:
        if str(uid) in ACC_DATA:
            return "duplicate"
        ACC_DATA[str(uid)] = str(pwd)
        acc_save()
        return "added"

# ═══════════════════════════════════════════════════════════
#  ĐỌC PROXY TỪ data.txt
# ═══════════════════════════════════════════════════════════
def load_proxies_from_file(filepath):
    """Đọc proxy từ file data.txt (mỗi dòng ip:port)"""
    if not os.path.exists(filepath):
        warn(f"[FILE] Không tìm thấy {filepath}")
        return []

    proxies = []
    seen = set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line in seen:
                    continue
                seen.add(line)
                proxies.append(line)
        if proxies:
            info(f"[FILE] Đọc {grn}{len(proxies)}{rs} proxy từ {cyan}{filepath}{rs}")
        else:
            warn(f"[FILE] {filepath} rỗng")
    except Exception as e:
        warn(f"[FILE] Lỗi đọc {filepath}: {e}")
        return []

    return proxies

# ═══════════════════════════════════════════════════════════
#  TẢI PROXY TỪ URL (fallback)
# ═══════════════════════════════════════════════════════════
def fetch_proxies_from_url(urls):
    """Đọc proxy từ data.txt trước, nếu không có thì tải từ URL"""

    # Ưu tiên file data.txt
    if USE_FILE_PROXY:
        file_proxies = load_proxies_from_file(PROXY_FILE)
        if file_proxies:
            return file_proxies
        info(f"[FILE] {PROXY_FILE} rỗng → fallback tải từ URL")

    # Fallback: tải từ URL
    if not urls:
        return []
    if isinstance(urls, str):
        urls = [urls]

    all_lines = []
    seen = set()
    ok_urls = 0

    for url in urls:
        url = url.strip()
        if not url:
            continue
        try:
            info(f"[FETCH] Tải: {cyan}{url[:80]}{'...' if len(url) > 80 else ''}{rs}")
            r = requests.get(
                url, timeout=30, verify=False,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code != 200:
                warn(f"[FETCH] HTTP {r.status_code} — bỏ qua")
                continue

            count = 0
            for line in r.text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line in seen:
                    continue
                seen.add(line)
                all_lines.append(line)
                count += 1

            info(f"[FETCH] {grn}✓ +{count}{rs} proxy (URL ok)")
            ok_urls += 1
        except Exception as e:
            warn(f"[FETCH] Fail: {type(e).__name__}: {str(e)[:80]}")

    if all_lines:
        info(f"[FETCH] {grn}✓ TỔNG {len(all_lines)}{rs} proxy từ {ok_urls}/{len(urls)} URL")
    else:
        warn(f"[FETCH] Không tải được proxy từ bất kỳ URL nào")

    return all_lines

# ═══════════════════════════════════════════════════════════
#  PARSE + CHECK
# ═══════════════════════════════════════════════════════════
def parse_proxy(pstr):
    if not pstr: return None
    if "://" in pstr:
        return {"http": pstr, "https": pstr}
    if "@" in pstr:
        u = f"http://{pstr}"
        return {"http": u, "https": u}
    parts = pstr.split(":")
    if len(parts) == 2:
        u = f"http://{pstr}"
        return {"http": u, "https": u}
    if len(parts) == 4:
        ip, port, user, pw = parts
        u = f"http://{user}:{pw}@{ip}:{port}"
        return {"http": u, "https": u}
    return None

def check_one_proxy(pstr):
    parsed = parse_proxy(pstr)
    if not parsed:
        return pstr, False
    try:
        r = requests.get(
            CHECK_URL, proxies=parsed, verify=False,
            timeout=PROXY_TIMEOUT,
            headers={"User-Agent": "GarenaMSDK/4.0.44"},
            allow_redirects=False,
        )
        content_type = r.headers.get("Content-Type", "")
        if "html" in content_type.lower():
            return pstr, False
        return pstr, r.status_code in (200, 400, 401, 404, 405)
    except Exception:
        return pstr, False

# ═══════════════════════════════════════════════════════════
#  PROXY POOL
# ═══════════════════════════════════════════════════════════
PROXY_CHECKING = threading.Event()

class ProxyPool:
    def __init__(self):
        self._lock = threading.Lock()
        self._q = queue.Queue()
        self._fail_count = {}
        self._count_429 = {}
        self._dead_set = set()
        self._seen = set()

    def reset(self):
        with self._lock:
            while not self._q.empty():
                try: self._q.get_nowait()
                except queue.Empty: break
            self._fail_count = {}
            self._count_429 = {}
            self._dead_set = set()
            self._seen = set()

    def add_proxy(self, pstr):
        with self._lock:
            if pstr in self._seen:
                return
            self._seen.add(pstr)
            self._q.put(pstr)

    def acquire(self, timeout=None):
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def release(self, pstr, fail=False):
        if not pstr: return
        with self._lock:
            if pstr not in self._seen:
                return
            if fail:
                cnt = self._fail_count.get(pstr, 0) + 1
                self._fail_count[pstr] = cnt
                if cnt >= 3:
                    self._dead_set.add(pstr)
                    return
        self._q.put(pstr)

    def record_429(self, pstr):
        if not pstr: return
        with self._lock:
            cnt = self._count_429.get(pstr, 0) + 1
            self._count_429[pstr] = cnt
            if cnt >= PROXY_429_LIMIT:
                self._dead_set.add(pstr)
                out(f"{ts()} {pur}[429DEAD]{rs} {pstr} bị 429 {cnt} lần → LOẠI")
                return
        self._q.put(pstr)

    def alive_count(self):
        return self._q.qsize()

    def dead_count(self):
        with self._lock:
            return len(self._dead_set)

PROXY_POOL = ProxyPool()

# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════
def h2o():
    return hashlib.sha256(''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32)).encode()).hexdigest().upper()

DEFAULT_NAMES = ["zanxgay", "zanxdev"]
SUPERSCRIPT_DIGITS = "¹²³⁴⁵⁶⁷⁸⁹"

def co2():
    prefix = random.choice(DEFAULT_NAMES)
    avail = 12 - len(prefix)
    suffix = "".join(random.choice(SUPERSCRIPT_DIGITS) for _ in range(max(1, avail)))
    return f"{prefix}{suffix}".encode("utf-8")

def enc_aes(data):
    return AES.new(AES_KEY, AES.MODE_CBC, AES_IV).encrypt(pad(data, AES.block_size))

def encode_f14(s):
    ks = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
    return bytes(ord(c) ^ ks[i % len(ks)] for i, c in enumerate(s))

def _tf(t): return {'type': t, 'name': ''}
typedef_reg = {'1':_tf('bytes'),'2':_tf('bytes'),'3':_tf('bytes'),'5':_tf('int'),'6':_tf('int'),'7':_tf('int'),'13':_tf('int'),'14':_tf('bytes'),'15':_tf('bytes'),'16':_tf('int'),'20':_tf('bytes'),'21':_tf('int'),'22':_tf('bytes')}
typedef_newbie = {'1':_tf('int'),'2':_tf('int'),'3':_tf('int')}
FIELD_22 = bytes.fromhex("4747524501010100620200001052aa0d669c6a368f08338060d2ee0690053af84a41edcd3558556ec10f24f46c93ac64ca41a16732c46a2cb071246a79b8929032f9e1b6f4ef331bd53cabf29b09b97349a46e9863c0314e1a0d80819fef8aabf03876b3d037db354a7ccb5c1bce96411fb3753f6f50e44c69c4ed617fa30efb8ffc0517ff2f636739be1f304d999cfd6fd48bf69454199794c3dc88f55a4bdbd66534d5a061359cdfd1fb680cd37918df9fdb3cf7d80067b0a3506c90063cf62b2ccec11e23913a2fd7c4ef091331967bb518a5ad1e551146b90821be800883abadde39d6c80a5d798611466c748f075481806c5842ce45e6bd4e3368ec08fe2ec41ceb880cd86249eb71693f79f0bccf9e590c3fae12519fe08c7a1905d0927690109e0df28574bb14847225db1a59230e6662ed7730e15ff9a6c815cb41b420edeada735a4b03e181037c37c2c850257311df2f07b0a56e759372cbd0268e3f13a292ee4373e38ab5096e0342a5e0d7fec6da2bbc265d74baadd2b24ee4f74862f82c21d6694bac53f8ce80312a30068a6276a641c19b11d0305c6fe2f531ac7de578b29f543697f5c73663e6f23aa15277b6122dcd4d4171e38f9ac0b173f39c58416a16c5c1f4a35acd065ce78f449cf538a249339e763272d458e4ed86c976591a9c066b3a37111e44091eb6b5a795249f3e5145db022a6055f2cc675936391312f688f89627845df222a91156555225be36f9714a0ba50246d0f003bda3c9c1292ab73b4f79635ddd023218eda93a302d79e023404c14396544a930b98ed54771aca7fec10d095587685b473e81a9619764fad9256529dcd6e911f4f4629612287d4ee3ec5389f6ec4ec020b0e2aac017232a9197be9e46239ce690fe5d4872b2e98e651510c971667f3aca8b59f3e9d50e43")

# ═══════════════════════════════════════════════════════════
#  PROXY AUTO-CHECKER
# ═══════════════════════════════════════════════════════════
_stop_event = threading.Event()

def proxy_checker_loop():
    while not _stop_event.is_set():
        try:
            PROXY_CHECKING.set()
            raw = fetch_proxies_from_url(PROXY_SOURCE_URL)

            if raw:
                info(f"[CHECKER] Check {cyan}{len(raw)}{rs} proxy vừa tải...")
                start = time.time()
                PROXY_POOL.reset()
                found = 0
                first_alive_logged = False
                with ThreadPoolExecutor(max_workers=min(CHECK_THREADS, len(raw))) as ex:
                    futures = {ex.submit(check_one_proxy, p): p for p in raw}
                    for f in as_completed(futures):
                        try:
                            pstr, ok_flag = f.result()
                            if ok_flag:
                                PROXY_POOL.add_proxy(pstr)
                                found += 1
                                if not first_alive_logged:
                                    info(f"[CHECKER] {grn}✓ Proxy sống đầu tiên → engine dùng được NGAY{rs}")
                                    first_alive_logged = True
                        except Exception:
                            pass
                dt = time.time() - start
                info(f"[CHECKER] Xong {pink}{dt:.1f}s{rs} — sống: {grn}{found}{rs}/{cyan}{len(raw)}{rs} | lần tới sau {CHECK_INTERVAL}s")
            else:
                warn(f"[CHECKER] Không tải được proxy → giữ pool cũ (alive: {PROXY_POOL.alive_count()})")
        except Exception as e:
            warn(f"[CHECKER] exception: {type(e).__name__}: {e}")
        finally:
            PROXY_CHECKING.clear()

        _stop_event.wait(CHECK_INTERVAL)

# ═══════════════════════════════════════════════════════════
#  REGISTER — chỉ qua proxy, KHÔNG BAO GIỜ direct
# ═══════════════════════════════════════════════════════════
def register_one(proxy_str):
    if not proxy_str:
        return None, "no_proxy", "proxy"

    session = requests.Session()
    a = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=0)
    session.mount("https://", a); session.mount("http://", a)
    parsed = parse_proxy(proxy_str)
    if parsed:
        session.proxies.update(parsed)

    try:
        pwd = h2o()
        body = json.dumps({"app_id": APP_ID, "client_type": 2, "password": pwd, "source": 2}, separators=(",", ":"))
        sig  = hmac.new(MAIN_KEY, body.encode(), hashlib.sha256).hexdigest()

        h = dict(HEADERS_MSDK)
        h["User-Agent"]    = random.choice(USERAGENTS_MSDK)
        h["Authorization"] = "Signature " + sig

        r = session.post(GUEST_REGISTER, headers=h, data=body, verify=False, timeout=HTTP_TIMEOUT)
        if r.status_code == 429: return None, "guest 429", "429"
        if r.status_code != 200: return None, f"guest {r.status_code}", "other"

        uid = r.json()["data"]["uid"]
        gl  = f"02-{uuid.uuid4()}"
        grant_body = {
            "client_id": APP_ID, "client_secret": CLIENT_SECRET,
            "client_type": 2, "device_id": gl, "password": pwd,
            "response_type": "token", "uid": int(uid),
        }
        r2 = session.post(TOKEN_GRANT, headers=HEADERS_MSDK, json=grant_body, verify=False, timeout=HTTP_TIMEOUT)
        if r2.status_code == 429: return None, "grant 429", "429"
        if r2.status_code != 200: return None, f"grant {r2.status_code}", "other"

        gd = r2.json()["data"]
        access_token, open_id = gd["access_token"], gd["open_id"]

        ni = co2()
        reg_msg = {
            '1': ni, '2': access_token.encode(), '3': open_id.encode(),
            '5': 102000007, '6': 4, '7': 1, '13': 1,
            '14': encode_f14(open_id), '15': b'vi', '16': 2,
            '20': GAME_VERSION.encode(), '21': 1, '22': FIELD_22,
        }
        hdr = dict(HEADERS_LOGINBP)
        rr = session.post(
            MAJOR_REGISTER, headers=hdr,
            data=enc_aes(blackboxprotobuf.encode_message(reg_msg, typedef_reg)),
            verify=False, timeout=HTTP_TIMEOUT,
        )
        if rr.status_code == 429: return None, "majorreg 429", "429"
        if rr.status_code != 200: return None, f"majorreg {rr.status_code}", "other"

        res, _ = blackboxprotobuf.decode_message(rr.content)
        acc_id = res.get('3') or res.get(b'3') if isinstance(res, dict) else None
        if not acc_id:
            return None, "no account_id", "other"

        nr = session.post(
            NEWBIE_CHOICE, headers=hdr,
            data=enc_aes(blackboxprotobuf.encode_message({'1': int(acc_id), '2': 2, '3': 3}, typedef_newbie)),
            verify=False, timeout=HTTP_TIMEOUT,
        )
        if nr.status_code == 429: return None, "newbie 429", "429"
        if nr.status_code != 200: return None, f"newbie {nr.status_code}", "other"

        ni_str = ni.decode('utf-8', errors='ignore')
        acc = {
            "uid": str(uid), "password": str(pwd),
            "name": ni_str, "account_id": str(acc_id),
            "proxy": proxy_str,
        }
        return acc, None, None

    except (requests.exceptions.ProxyError,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError) as e:
        return None, f"PROXY_ERR: {type(e).__name__}", "proxy"
    except Exception as e:
        return None, str(e), "other"
    finally:
        try: session.close()
        except Exception: pass

# ═══════════════════════════════════════════════════════════
#  VERIFY qua ReQAPI (IP máy)
# ═══════════════════════════════════════════════════════════
def verify_account_reqapi(uid, pwd, attempts=VERIFY_ATTEMPTS):
    if FreeFireAPI is None:
        return None, f"ReQAPI not loaded: {_REQAPI_ERR}"
    for i in range(attempts):
        try:
            api = FreeFireAPI()
            res = api.get(f"{uid}:{pwd}")
            if isinstance(res, dict) and res.get("UserAuthToken"):
                return res, None
        except Exception:
            pass
        time.sleep(random.uniform(0.2, 0.6))
    return None, f"failed {attempts} attempts"

# ═══════════════════════════════════════════════════════════
#  ENGINE
# ═══════════════════════════════════════════════════════════
SUCCESS_COUNT      = 0
FAIL_COUNT         = 0
VERIFY_FAIL_COUNT  = 0
DUPLICATE_COUNT    = 0
NO_PROXY_COUNT     = 0
PROGRESS_LOCK      = threading.Lock()
_IDX_LOCK          = threading.Lock()
_IDX               = 0

def _worker():
    global SUCCESS_COUNT, FAIL_COUNT, VERIFY_FAIL_COUNT, _IDX
    global DUPLICATE_COUNT, NO_PROXY_COUNT

    with _IDX_LOCK:
        _IDX += 1
        idx = _IDX

    acc = None
    err = None
    final_proxy = None

    for proxy_attempt in range(PROXY_RETRY):
        proxy_str = None
        wait_cycles = 0
        while proxy_str is None and wait_cycles < 30:
            if _stop_event.is_set():
                break
            if PROXY_POOL.alive_count() > 0:
                proxy_str = PROXY_POOL.acquire(timeout=ACQUIRE_TIMEOUT)
                break
            elif PROXY_CHECKING.is_set():
                time.sleep(1)
                wait_cycles += 1
            else:
                break

        if not proxy_str:
            err = "NO_PROXY (chờ 30s)"
            break

        a, e, et = register_one(proxy_str)
        if a:
            acc = a
            final_proxy = proxy_str
            PROXY_POOL.release(proxy_str, fail=False)
            break
        else:
            err = e
            if et == "429":
                PROXY_POOL.record_429(proxy_str)
                continue
            elif et == "proxy":
                PROXY_POOL.release(proxy_str, fail=True)
                continue
            else:
                PROXY_POOL.release(proxy_str, fail=False)
                break

    if acc is None:
        with PROGRESS_LOCK:
            if "NO_PROXY" in (err or ""):
                NO_PROXY_COUNT += 1
            else:
                FAIL_COUNT += 1
        bad(f"#{idx}  {(err or 'unknown')[:110]}")
        return

    v_res, v_err = verify_account_reqapi(acc["uid"], acc["password"], VERIFY_ATTEMPTS)
    if not v_res:
        with PROGRESS_LOCK: VERIFY_FAIL_COUNT += 1
        bad(f"#{idx} VERIFY FAIL ({v_err}) — BỎ acc {acc['uid']}")
        return

    save_status = acc_add(acc["uid"], acc["password"])

    if save_status == "added":
        with PROGRESS_LOCK: SUCCESS_COUNT += 1
    else:
        with PROGRESS_LOCK: DUPLICATE_COUNT += 1

    tag = f"{dim}{final_proxy}{rs}"

    if save_status == "added":
        ok(f"#{idx} ✓VERIFY ✓SAVE  UID: {yel}{acc['uid']}{rs} | proxy: {tag}")
    else:
        warn(f"#{idx} ✓VERIFY ⚠DUP  UID: {yel}{acc['uid']}{rs} (đã có trong {ACC_FILE})")

def engine():
    global SUCCESS_COUNT, FAIL_COUNT, VERIFY_FAIL_COUNT, _IDX
    global DUPLICATE_COUNT, NO_PROXY_COUNT
    SUCCESS_COUNT = 0
    FAIL_COUNT = 0
    VERIFY_FAIL_COUNT = 0
    DUPLICATE_COUNT = 0
    NO_PROXY_COUNT = 0
    _IDX = 0

    limit = RUN_LIMIT
    mode = f"{grn}∞ VÔ HẠN{rs}" if limit <= 0 else f"{pink}{limit} acc{rs}"
    info(f"MODE: {mode} | Threads: {cyan}{THREADS}{rs}")

    start = time.time()

    try:
        if limit > 0:
            with ThreadPoolExecutor(max_workers=THREADS) as ex:
                futures = [ex.submit(_worker) for _ in range(limit)]
                for f in as_completed(futures):
                    try: f.result()
                    except Exception: pass
        else:
            with ThreadPoolExecutor(max_workers=THREADS) as ex:
                running = set()
                for _ in range(THREADS):
                    running.add(ex.submit(_worker))
                while True:
                    done, running = wait(running, return_when=FIRST_COMPLETED)
                    for f in done:
                        try: f.result()
                        except Exception: pass
                    while len(running) < THREADS:
                        running.add(ex.submit(_worker))
    except KeyboardInterrupt:
        warn("Dừng bởi người dùng")

    dt = time.time() - start
    print()
    print(f"{wht}{b}═══ HOÀN TẤT ═══{rs}")
    print(f"  {grn}[+] Lưu {ACC_FILE} : {b}{SUCCESS_COUNT}{rs}")
    print(f"  {yel}[!] Duplicate    : {b}{DUPLICATE_COUNT}{rs}")
    print(f"  {red}[-] Reg thất bại : {b}{FAIL_COUNT}{rs}")
    print(f"  {pur}[!] Không có proxy: {b}{NO_PROXY_COUNT}{rs}")
    print(f"  {red}[-] Verify fail  : {b}{VERIFY_FAIL_COUNT}{rs}")
    print(f"  {pur}[*] Proxy dead   : {b}{PROXY_POOL.dead_count()}{rs}  (còn sống {PROXY_POOL.alive_count()})")
    print(f"  {pink}[*] Thời gian    : {b}{dt:.1f}s{rs}")
    print(f"  {pink}[*] Speed        : {b}{SUCCESS_COUNT / max(dt, 1) * 60:.1f} acc/min{rs}")
    print(f"  {dim}→ File: {ACC_FILE} (tổng {len(ACC_DATA)} acc){rs}")
    print()

# ═══════════════════════════════════════════════════════════
#  UI
# ═══════════════════════════════════════════════════════════
def banner():
    cls()
    print()
    print(f"{pink}{b}        zanxgay - ACCOUNT GENERATOR{rs}")
    print(f"{cyan}   ── đọc proxy data.txt • reg via proxy • verify ReQ • ac.json ──{rs}")
    print()
    print(f"{rs}{b}{pink}GUEST ACCOUNT GENERATOR {gry}| {wht}Version: {yel}OB55 {gry}| {wht}Status: {grn}ONLINE{rs}")
    print()

def main():
    banner()

    if FreeFireAPI is None:
        warn(f"{red}ReQAPI KHÔNG load được:{rs} {_REQAPI_ERR}")
        warn(f"{red}→ Verify sẽ FAIL 100%, mọi acc bị bỏ.{rs}")
        return

    existed = acc_load()
    if existed:
        ok(f"Đã load {cyan}{existed}{rs} acc từ {pink}{ACC_FILE}{rs} (append, không xoá)")
    else:
        info(f"{ACC_FILE} chưa có → sẽ tạo mới")

    mode = f"{grn}∞ vô hạn{rs}" if RUN_LIMIT <= 0 else f"{pink}{RUN_LIMIT} acc{rs}"

    print()
    print(f" {b}{grn}[ AUTO MODE ]{rs}")
    print(f" {cyan}• Tên     :{rs} zanxgay / zanxdev + số mũ (12 ký tự)")
    print(f" {cyan}• Threads :{rs} {THREADS}")
    print(f" {cyan}• Mode    :{rs} {mode}")
    if USE_FILE_PROXY:
        proxy_count = len(load_proxies_from_file(PROXY_FILE)) if os.path.exists(PROXY_FILE) else 0
        print(f" {cyan}• Proxy   :{rs} {grn}{PROXY_FILE}{rs} ({proxy_count} proxy) — reload mỗi {pink}{CHECK_INTERVAL}s{rs}")
    else:
        print(f" {cyan}• Proxy   :{rs} {grn}{len(PROXY_SOURCE_URL)}{rs} URL — tải lại mỗi {pink}{CHECK_INTERVAL}s{rs}")
    print(f" {cyan}• Reg     :{rs} {red}TUYỆT ĐỐI CHỈ PROXY{rs}")
    print(f" {cyan}• 429     :{rs} x{PROXY_429_LIMIT} → dead | tối đa {PROXY_RETRY} proxy/acc")
    print(f" {cyan}• Verify  :{rs} ReQAPI x{pink}{VERIFY_ATTEMPTS}{rs} — fail bỏ acc")
    print(f" {cyan}• Output  :{rs} → {pink}{ACC_FILE}{rs} (uid : password)")
    print()

    checker = threading.Thread(target=proxy_checker_loop, daemon=True)
    checker.start()
    info("Checker khởi động — engine chạy SONG SONG")

    time.sleep(1)
    engine()

    _stop_event.set()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        sys.exit(0)