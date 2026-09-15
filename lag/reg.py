import hmac, hashlib, requests, string, random, time, json, os, sys, subprocess, socket, shutil, importlib
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import threading, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ====== CÀI ĐẶT & CHECK ======
PY_MODULES = {
    "requests": "requests",
    "urllib3": "urllib3",
    "Crypto": "pycryptodome",
}


def run(cmd):
    try:
        subprocess.check_call(cmd)
        return True
    except:
        return False


def auto_check():
    print("[*] Checking system...")
    for module, package in PY_MODULES.items():
        try:
            importlib.import_module(module)
            print(f"[✓] {module}")
        except ImportError:
            print(f"[+] pip install {package}")
            run([sys.executable, "-m", "pip", "install", "--upgrade", package])


auto_check()


# ====== CONFIG ======
try:
    from ReQAPI import bdversion
    _bd = bdversion() or {}
    LOGIN_SERVER_URL = _bd.get("server_url", "https://loginbp.ggpolarbear.com/")
    if not LOGIN_SERVER_URL.endswith("/"):
        LOGIN_SERVER_URL += "/"
    CLIENT_VERSION = _bd.get("remote_version", "1.126.1")
    RELEASE_VERSION = _bd.get("latest_release_version", "OB54")
except Exception:
    LOGIN_SERVER_URL = "https://loginbp.ggpolarbear.com/"
    CLIENT_VERSION = "1.126.1"
    RELEASE_VERSION = "OB54"

LOGIN_HOST = LOGIN_SERVER_URL.replace("https://", "").replace("http://", "").rstrip("/")

# 🔥 Hardcode URL cho MajorLogin + GetLoginData
MAJOR_LOGIN_URL = "https://loginbp.ggpolarbear.com/MajorLogin"
CLIENT_LOGIN_DATA_URL = "https://clientbp.ggpolarbear.com/GetLoginData"
CLIENT_HOST = "clientbp.ggpolarbear.com"

HMAC_KEY_HEX = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
HMAC_KEY = HMAC_KEY_HEX.encode('utf-8')
AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
FIELD_102 = bytes.fromhex("14534c46530a04014c065f170f021609456e5b02585d59755c5f745b070a3b0b0335")

REGION_LANG = {
    "ME": "ar", "IND": "hi", "ID": "id", "VN": "vi", "TH": "th",
    "BD": "bn", "PK": "ur", "TW": "zh", "EU": "en", "RU": "ru",
    "NA": "en", "SAC": "es", "BR": "pt", "SG": "en"
}

_XOR_KEY = bytes([
    0x30, 0x30, 0x30, 0x32, 0x30, 0x31, 0x37, 0x30,
    0x30, 0x30, 0x30, 0x30, 0x32, 0x30, 0x31, 0x37,
    0x30, 0x30, 0x30, 0x30, 0x30, 0x32, 0x30, 0x31,
    0x37, 0x30, 0x30, 0x30, 0x30, 0x30, 0x32, 0x30
])


# ====== UTILS ======
def _varint(n):
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


def _pb_varint(field, val):
    return _varint((field << 3) | 0) + _varint(val)


def _pb_ld(field, val):
    b = val.encode() if isinstance(val, str) else val
    return _varint((field << 3) | 2) + _varint(len(b)) + b


def pb_encode(fields):
    pkt = bytearray()
    for f, v in fields.items():
        if isinstance(v, dict):
            pkt.extend(_pb_ld(f, pb_encode(v)))
        elif isinstance(v, int):
            pkt.extend(_pb_varint(f, v))
        elif isinstance(v, (str, bytes)):
            pkt.extend(_pb_ld(f, v))
    return bytes(pkt)


def aes_encrypt(data: bytes) -> bytes:
    c = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return c.encrypt(pad(data, AES.block_size))


def encrypt_pb(fields: dict) -> bytes:
    return aes_encrypt(pb_encode(fields))


_SUPER = "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079"


def generate_password():
    raw = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))
    acc_pass = "chun_dz_" + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
    return raw, acc_pass


def generate_nickname(prefix: str, max_len=12) -> str:
    clean = prefix.replace("/", "").replace("/", "").strip()
    if len(clean) >= max_len:
        return clean[:max_len]
    missing = max_len - len(clean)
    return f"{clean}{''.join(random.choice(_SUPER) for _ in range(missing))}"


def xor_open_id(open_id: str) -> bytes:
    return bytes(ord(open_id[i]) ^ _XOR_KEY[i % len(_XOR_KEY)] for i in range(len(open_id)))


# ====== SESSION ======
_session = None
_session_lock = threading.Lock()


def get_session():
    global _session
    if _session is None:
        with _session_lock:
            if _session is None:
                s = requests.Session()
                s.verify = False
                _session = s
    return _session


# ====== API CALLS ======
def guest_register(pw_hash: str):
    payload = {"app_id": 100067, "client_type": 2, "password": pw_hash, "source": 2}
    body = json.dumps(payload, separators=(',', ':'))
    sig = hmac.new(HMAC_KEY, body.encode(), hashlib.sha256).hexdigest()
    for attempt in range(3):
        try:
            r = get_session().post(
                "https://100067.connect.garena.com/api/v2/oauth/guest:register",
                headers={
                    "User-Agent": "GarenaMSDK/4.0.41(2107113SI ;Android 11;vi;VN;app 1.123.1 2019120270;)",
                    "Authorization": f"Signature {sig}",
                    "Content-Type": "application/json; charset=utf-8",
                    "Host": "100067.connect.garena.com",
                }, data=body, timeout=30)
            d = r.json()
            if d.get("code") == 0:
                return d["data"]["uid"]
        except Exception as e:
            print(f"guest_register EXC: {e}")
        if attempt < 2:
            time.sleep(2)
    return None


def token_grant(uid: int, pw_hash: str):
    payload = {
        "client_id": 100067, "client_secret": HMAC_KEY_HEX,
        "client_type": 2, "password": pw_hash,
        "response_type": "token", "uid": uid,
    }
    body = json.dumps(payload, separators=(',', ':'))
    for attempt in range(3):
        try:
            r = get_session().post(
                "https://100067.connect.garena.com/api/v2/oauth/guest/token:grant",
                headers={
                    "User-Agent": "GarenaMSDK/4.0.41(2107113SI ;Android 11;vi;VN;app 1.123.1 2019120270;)",
                    "Content-Type": "application/json; charset=utf-8",
                    "Host": "100067.connect.garena.com",
                }, data=body, timeout=30)
            d = r.json()
            if d.get("code") == 0:
                dd = d["data"]
                return dd.get("open_id"), dd.get("access_token")
        except Exception as e:
            print(f"token_grant EXC: {e}")
        if attempt < 2:
            time.sleep(2)
    return None, None


def major_register(access_token: str, open_id: str, nickname: str, lang: str):
    fields = {
        1: nickname, 2: access_token, 3: open_id,
        5: 102000007, 6: 4, 7: 1,
        13: 1, 14: xor_open_id(open_id), 15: lang,
        16: 1, 17: 1,
    }
    for attempt in range(3):
        try:
            r = get_session().post(
                f"{LOGIN_SERVER_URL}MajorRegister",
                headers={
                    "Accept-Encoding": "gzip", "Authorization": "Bearer",
                    "Connection": "Keep-Alive",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Expect": "100-continue", "Host": LOGIN_HOST,
                    "ReleaseVersion": RELEASE_VERSION,
                    "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                    "X-GA": "v1 1", "X-Unity-Version": "2022.3.47f1",
                },
                data=encrypt_pb(fields), verify=False, timeout=30)
            if r.status_code == 200:
                return True
        except Exception as e:
            print(f"major_register EXC: {e}")
        if attempt < 2:
            time.sleep(2)
    return False


# ============ MAJOR LOGIN (dùng payload giống ReQAPI, hardcode URL) ============
def _build_major_login_fields(access_token, open_id, lang):
    """Build fields cho MajorLogin — giống hệt ReQAPI.APIClient.MajorLogin"""
    return {
        3: time.strftime("%Y-%m-%d %H:%M:%S"),
        4: "free fire",
        5: 4,
        7: CLIENT_VERSION,
        8: "Android OS 14 / API-34",
        9: "Handheld",
        10: "Viettel",
        11: "5G",
        12: 1440,
        13: 3120,
        15: "ARM64 FP ASIMD AES | 3200 | 12",
        16: 8192,
        17: "Adreno (TM) 740",
        18: "OpenGL ES 3.2",
        19: "Google|a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        20: "192.168.1.100",
        21: lang,
        22: str(open_id),
        23: 4,
        24: "Handheld",
        25: "Xiaomi 14 Pro",
        29: str(access_token),
        30: 1,
        41: "O2",
        42: "5G",
        57: bytes([49, 97, 99, 52, 98, 56, 48, 101, 99, 102, 48, 52, 55, 56, 97, 52, 52, 50, 48, 51, 98, 102, 56, 102, 97, 99, 54, 49, 50, 48, 102, 53]),
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
        93: "android",
        94: "KqsHT1r9GNgPJ0nDb82dJ+mJ4wwzqfR9fk7HviQ+4tx58ObceZuLaFrmk9qaVIP+qB3CV0DG40yTeS+2h1GA1rqKtMVPLfDUz7rIThfm4ZKedCh3",
        95: 111111,
        97: 1,
        98: 1,
        99: "4",
        100: "4",
        102: bytes([71, 87, 76, 65, 86, 89, 9, 4, 78, 1, 12, 19, 15, 4, 64, 94, 65, 57, 89, 83, 15, 80, 91, 61, 15, 81, 91, 110, 82, 9, 60, 10, 84, 50]),
    }


def major_login(access_token, open_id, lang):
    """
    MajorLogin — Dùng payload giống hệt ReQAPI, hardcode URL
    Trả về dict chứa login_token, key, iv, account_id
    """
    from ReQAPI import ProtoBuf

    fields = _build_major_login_fields(access_token, open_id, lang)
    encrypted = aes_encrypt(pb_encode(fields))

    for attempt in range(3):
        try:
            r = get_session().post(
                MAJOR_LOGIN_URL,
                headers={
                    "Accept-Encoding": "gzip",
                    "Authorization": "Bearer",
                    "Connection": "Keep-Alive",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Expect": "100-continue",
                    "Host": "loginbp.ggpolarbear.com",
                    "ReleaseVersion": RELEASE_VERSION,
                    "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                    "X-GA": "v1 1",
                    "X-Unity-Version": "2022.3.47f1",
                },
                data=encrypted, verify=False, timeout=15
            )

            print(f"[MajorLogin] HTTP={r.status_code} | len={len(r.content)}B")

            if r.status_code != 200:
                print(f"[MajorLogin] body={r.text[:200]}")
                return None

            pb = ProtoBuf(r.content)
            res = pb.protobuf()

            # Kiểm tra ban
            if "13" in res:
                ban_text = r.content[10:].decode('utf-8', errors='ignore')
                print(f"🚫 BỊ BAN: {ban_text}")
                return None

            account_id = res.get("1")
            server = res.get("3")
            login_token = res.get("8")
            login_time = res.get("21")
            key = pb.EXTRACT_FIELDS([22], mode="bytes")
            iv = pb.EXTRACT_FIELDS([23], mode="bytes")

            if not login_token:
                print(f"[MajorLogin] no login_token | fields={list(res.keys())}")
                return None

            print(f"[MajorLogin] OK | account_id={account_id} | token=OK | key={'OK' if key else 'MISSING'} | iv={'OK' if iv else 'MISSING'}")

            return {
                "account_id": account_id,
                "server": server,
                "login_token": login_token,
                "login_time": login_time,
                "key": key,
                "iv": iv,
            }
        except Exception as e:
            print(f"❌ major_login EXC: {e}")
            import traceback
            traceback.print_exc()
        if attempt < 2:
            time.sleep(2)
    return None


# ============ GET LOGIN DATA (hardcode URL) ============
def get_login_data(login_token, key, iv, lang):
    """
    GetLoginData — Hardcode URL clientbp.ggpolarbear.com
    """
    from ReQAPI import gringay

    tokendec = gringay.tokendecode(login_token) or {}
    ext_type = tokendec.get("external_type", 8)
    ext_id = tokendec.get("external_id", "")
    sig_md5 = tokendec.get("signature_md5", "")

    fields = {
        3: time.strftime("%Y-%m-%d %H:%M:%S"),
        7: CLIENT_VERSION,
        23: int(ext_type) if str(ext_type).isdigit() else 8,
        29: str(ext_id) if ext_id else "",
        4: "free fire",
        5: 4,
        8: "Android OS 14 / API-34",
        9: "Handheld",
        10: "Viettel",
        11: "5G",
        12: 1440,
        13: 3120,
        15: "ARM64 FP ASIMD AES | 3200 | 12",
        17: "Adreno (TM) 740",
        18: "OpenGL ES 3.2",
        19: "Google|a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        20: "192.168.1.100",
        21: lang,
        22: "40254b1770e14131d3879ea51acb93ad",
        24: "Handheld",
        25: "Xiaomi 14 Pro",
        41: "Viettel",
        42: "5G",
        57: str(sig_md5),
        60: 32969,
        61: 29665,
        62: 2479,
        63: 900,
        64: 31063,
        65: 32969,
        66: 31063,
        67: 32969,
        70: 4,
        73: 3,
        76: 1,
        78: 6,
        79: 1,
        85: 3,
        88: 4,
        92: 11111,
        95: 11111,
        97: 1,
        98: 1,
    }

    encrypted = aes_encrypt(pb_encode(fields))

    for attempt in range(3):
        try:
            r = get_session().post(
                CLIENT_LOGIN_DATA_URL,
                headers={
                    "Accept-Encoding": "gzip",
                    "Authorization": f"Bearer {login_token}",
                    "Connection": "Keep-Alive",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Expect": "100-continue",
                    "Host": CLIENT_HOST,
                    "ReleaseVersion": RELEASE_VERSION,
                    "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                    "X-GA": "v1 1",
                    "X-Unity-Version": "2022.3.47f1",
                },
                data=encrypted, verify=False, timeout=15
            )

            print(f"[GetLoginData] HTTP={r.status_code} | len={len(r.content)}B")

            if r.status_code == 200:
                return True
            else:
                print(f"[GetLoginData] body={r.text[:200]}")
        except Exception as e:
            print(f"❌ get_login_data EXC: {e}")
        if attempt < 2:
            time.sleep(2)
    return False


def choose_region(login_token: str, region: str):
    fields = {1: region}
    for attempt in range(3):
        try:
            r = get_session().post(
                f"{LOGIN_SERVER_URL}ChooseRegion",
                headers={
                    "Accept-Encoding": "gzip",
                    "Authorization": f"Bearer {login_token}",
                    "Connection": "Keep-Alive",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Expect": "100-continue", "Host": LOGIN_HOST,
                    "ReleaseVersion": RELEASE_VERSION,
                    "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                    "X-GA": "v1 1", "X-Unity-Version": "2022.3.47f1",
                },
                data=encrypt_pb(fields), verify=False, timeout=30)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        if attempt < 2:
            time.sleep(2)
    return False


# ============ CREATE ACCOUNT ============
def create_account(name_prefix: str, region: str, bio_text: str = None):
    from ReQAPI import gringay

    lang = REGION_LANG.get(region, "en")

    for overall in range(3):
        try:
            if overall > 0:
                time.sleep(5)

            nickname = generate_nickname(name_prefix)
            raw_pw, pw_hash = generate_password()

            # Bước 1: Guest register
            uid = guest_register(pw_hash)
            if not uid:
                print(f"[{overall+1}/3] guest_register FAIL")
                continue
            print(f"[{overall+1}/3] guest_register OK | uid={uid}")

            # Bước 2: Token grant
            open_id, access_token = token_grant(uid, pw_hash)
            if not open_id:
                print(f"[{overall+1}/3] token_grant FAIL")
                continue
            print(f"[{overall+1}/3] token_grant OK | open_id={open_id}")

            # Bước 3: Major register
            if not major_register(access_token, open_id, nickname, lang):
                print(f"[{overall+1}/3] major_register FAIL")
                continue
            print(f"[{overall+1}/3] major_register OK")
            time.sleep(1)

            # Bước 4: Major login — payload giống ReQAPI, hardcode URL
            ml = major_login(access_token, open_id, lang)
            if not ml:
                print(f"[{overall+1}/3] major_login FAIL")
                continue

            login_token = ml["login_token"]
            key = ml["key"]
            iv = ml["iv"]
            account_id = ml["account_id"]

            # Kiểm tra lock_region
            tokendec = gringay.tokendecode(login_token) or {}
            lock_region = tokendec.get("lock_region", "")

            if not lock_region:
                choose_region(login_token, region)
                time.sleep(1)
                ml2 = major_login(access_token, open_id, lang)
                if ml2:
                    login_token = ml2["login_token"]
                    key = ml2["key"]
                    iv = ml2["iv"]
                    account_id = ml2["account_id"]
                    tokendec = gringay.tokendecode(login_token) or {}
                    lock_region = tokendec.get("lock_region", "")

            # Bước 5: GetLoginData — hardcode URL
            gld_ok = get_login_data(login_token, key, iv, lang)

            print(f"✅ UID: {uid} | Name: {nickname} | status={'full_login' if gld_ok else 'login_only'}")

            return {
                "uid": uid,
                "password": pw_hash,
                "raw_password": raw_pw,
                "name": nickname,
                "region": region,
                "access_token": access_token,
                "open_id": open_id,
                "account_id": account_id,
                "login_token": login_token,
                "lock_region": lock_region,
                "status": "full_login" if gld_ok else "login_only",
            }

        except Exception as e:
            print(f"❌ create_account EXC: {e}")
            import traceback
            traceback.print_exc()
            if overall < 2:
                time.sleep(5)

    return None


def save_account(acc, filename="acc.json"):
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
        data[str(acc.get("uid"))] = acc.get("password", acc.get("raw_password", ""))
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Lỗi ghi file {filename}: {e}")


# ============ GENERATE ============
def generate_accounts(name: str, region: str, count: int, max_threads: int,
                     bio_text: str = None, use_tor: bool = False):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    count = max(1, int(count))
    region = region.upper()
    if region not in REGION_LANG:
        print(f"Unknown region '{region}', defaulting to VN")
        region = "VN"

    max_threads = min(max(1, int(max_threads)), 2)

    print(f"\n{'='*55}")
    print(f"  Free Fire Account Creator - OB54")
    print(f"  Server  : {LOGIN_SERVER_URL}")
    print(f"  Version : {CLIENT_VERSION} ({RELEASE_VERSION})")
    print(f"  Region  : {region}  |  Prefix : {name}")
    print(f"  Count   : {count}  |  Threads: {max_threads}")
    print(f"  Delay   : 15-30s giữa các acc")
    print(f"{'='*55}\n")

    results = []
    lock = threading.Lock()
    created = [0]
    fail_streak = [0]

    def worker():
        while True:
            with lock:
                if created[0] >= count:
                    return

            acc = create_account(name_prefix=name, region=region, bio_text=bio_text)

            if acc:
                save_account(acc)
                with lock:
                    created[0] += 1
                    results.append(acc)
                    fail_streak[0] = 0
                    print(f"\n✅ Đã {created[0]}/{count} | UID: {acc['uid']}\n")
                time.sleep(random.randint(15, 30))
            else:
                with lock:
                    fail_streak[0] += 1
                    streak = fail_streak[0]
                if streak >= 5:
                    print(f"⚠️ Fail {streak} lần liên tiếp → nghỉ 60s")
                    time.sleep(60)
                    with lock:
                        fail_streak[0] = 0
                else:
                    time.sleep(10)

    with ThreadPoolExecutor(max_workers=max_threads) as ex:
        futs = [ex.submit(worker) for _ in range(max_threads)]
        for f in as_completed(futs):
            pass

    print(f"\n{'='*55}")
    print(f"  ✅ Done: {len(results)}/{count} accounts created")
    print(f"  📁 Saved to: acc.json")
    print(f"{'='*55}")
    return results


# ============ MAIN ============
if __name__ == '__main__':
    print(f"Login server: {LOGIN_SERVER_URL}")
    print(f"Version: {CLIENT_VERSION} ({RELEASE_VERSION})\n")

    name = input("Name prefix (default HLxGH): ").strip() or "HLxGH"
    region = input("Region code (default VN): ").strip() or "VN"
    count = int(input("Number of accounts (default 20): ").strip() or "20")

    threads = int(input("Threads (default 2, max 2): ").strip() or "2")
    if threads > 2:
        print("⚠️ Max 2 thread — tự động set = 2")
        threads = 2

    generate_accounts(name, region, count, threads, use_tor=False)