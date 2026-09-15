import threading
import json
import os
import requests
import time
import logging
import socket
import sys
import base64
from datetime import datetime
from threading import Thread
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.timestamp_pb2 import Timestamp
import urllib3
try:
    from protobuf_decoder.protobuf_decoder import Parser
except ImportError:
    logging.critical("[×] Thiếu thư viện protobuf_decoder!")
    sys.exit(1)

# --- CONFIG ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ghi log ra cả console lẫn file
_log_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

# File vẫn giữ nguyên mức WARNING để lưu lại toàn bộ lịch sử debug
_file_handler = logging.FileHandler("debug_session.log", mode="w", encoding="utf-8")
_file_handler.setLevel(logging.WARNING)
_file_handler.setFormatter(_log_formatter)

# Console nâng lên mức ERROR để ẩn đi các dòng warning rác
_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.ERROR) 
_console_handler.setFormatter(_log_formatter)

logging.basicConfig(level=logging.WARNING, handlers=[_file_handler, _console_handler])


FREEFIRE_VERSION = "OB54"
CLIENT_SECRET = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"

# --- UTILS ---
def aes_encrypt(data_hex, key, iv):
    try:
        key = key if isinstance(key, bytes) else bytes.fromhex(key)
        iv = iv if isinstance(iv, bytes) else bytes.fromhex(iv)
        data = bytes.fromhex(data_hex) if isinstance(data_hex, str) else data_hex
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.encrypt(pad(data, AES.block_size)).hex()
    except Exception: return None

def encrypt_api(plain_text_hex):
    try:
        key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
        iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
        return aes_encrypt(plain_text_hex, key, iv)
    except Exception: return None

def dec_to_hex(number):
    hex_val = hex(int(number))[2:]
    return f"0{hex_val}" if len(hex_val) % 2 != 0 else hex_val

def create_protobuf_packet(fields):
    try:
        from utils import create_protobuf_packet
        return create_protobuf_packet(fields)
    except ImportError:
        logging.error("[×] • Thiếu Files...!")
        return b''

def parse_results(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {"wire_type": result.wire_type}
        if result.wire_type == "length_delimited":
            field_data["data"] = parse_results(result.data.results)
        else:
            field_data["data"] = result.data
        result_dict[result.field] = field_data
    return result_dict

def get_available_room(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        return parse_results(parsed_results)
    except Exception as e:
        logging.error(f"Protobuf Parse Error: {e}")
        return None


def GET_LOGIN_DATA(JWT_TOKEN, PAYLOAD):
    url = "https://clientbp.ggpolarbear.com/GetLoginData"
    headers = {
        'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
        'Accept': '*/*',
        'Accept-Encoding': 'deflate, gzip',
        'Authorization': f'Bearer {JWT_TOKEN}',
        'X-Ga': 'v1 1',
        'ReleaseVersion': FREEFIRE_VERSION,
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Unity-Version': '2022.3.47f1'
    }    
    
    try:
        response = requests.post(url, headers=headers, data=PAYLOAD, verify=False, timeout=10)
        if response.status_code != 200:
            logging.error(f"❌ GET_LOGIN_DATA HTTP {response.status_code} | body={response.text[:200]}")
            return None, None, None, None
        
        x = response.content.hex()
        parsed_data = get_available_room(x)
        if 32 not in parsed_data or 14 not in parsed_data:
            logging.error(f"❌ GET_LOGIN_DATA: thiếu field 14/32 | fields={list(parsed_data.keys()) if parsed_data else 'None'}")
            return None, None, None, None

        whisper_raw = parsed_data[32]['data']
        online_raw  = parsed_data[14]['data']
        logging.info(f"📡 RAW whisper={whisper_raw} | online={online_raw}")

        def parse_addr(raw):
            if isinstance(raw, str) and ':' in raw:
                ip, port = raw.rsplit(':', 1)
                return ip, int(port)
            if isinstance(raw, dict):
                for ip_f in [1, 2, 3]:
                    for port_f in [2, 3, 4]:
                        if ip_f in raw and port_f in raw and ip_f != port_f:
                            ip_c   = raw[ip_f].get('data', '')
                            port_c = raw[port_f].get('data', 0)
                            if isinstance(ip_c, str) and '.' in ip_c:
                                return ip_c, int(port_c)
                logging.error(f"parse_addr: cannot parse dict: {raw}")
                return None, None
            if isinstance(raw, bytes):
                try:
                    s = raw.decode('utf-8')
                    if ':' in s:
                        ip, port = s.rsplit(':', 1)
                        return ip, int(port)
                except Exception:
                    pass
                logging.error(f"parse_addr: bytes fail: {raw}")
                return None, None
            logging.error(f"parse_addr: unknown type {type(raw)}: {raw}")
            return None, None

        w_ip, w_port = parse_addr(whisper_raw)
        o_ip, o_port = parse_addr(online_raw)
        logging.info(f"Parsed: whisper={w_ip}:{w_port} | online={o_ip}:{o_port}")
        if not o_ip:
            return None, None, None, None
        return w_ip, w_port, o_ip, o_port
    except Exception as e:
        logging.error(f"❌ GET_LOGIN_DATA EXCEPTION: {e}", exc_info=True)
        return None, None, None, None

# --- CLIENT ---
class FFClient(threading.Thread):
    def __init__(self, uid, password, teamcode):
        super().__init__()
        self.uid = uid
        self.password = password
        self.teamcode = teamcode
        self.key = None
        self.iv = None
        self.is_running = True

    def parse_login_response(self, serialized_data):
        try:
            import MajorLg
            res = MajorLg.MajorLoginRes()
            res.ParseFromString(serialized_data)
            timestamp_obj = Timestamp()
            timestamp_obj.FromNanoseconds(res.kts)
            combined_timestamp = timestamp_obj.seconds * 1_000_000_000 + timestamp_obj.nanos
            self.key = res.ak
            self.iv = res.aiv
            return res.token, res.ak, res.aiv, combined_timestamp
        except Exception: return None, None, None, None

    def prepare_packet(self, fields):
        try:
            packet_raw = create_protobuf_packet(fields).hex()
            if not packet_raw:
                logging.error(f"❌ [{self.uid}] create_protobuf_packet trả về rỗng | fields={fields}")
                return None
            encrypted_payload = aes_encrypt(packet_raw, self.key, self.iv)
            if not encrypted_payload:
                logging.error(f"❌ [{self.uid}] aes_encrypt packet FAILED | key={self.key is not None} iv={self.iv is not None}")
                return None
            header_len = len(encrypted_payload) // 2
            header_hex = dec_to_hex(header_len)
            prefix = "051500" + "0" * (6 - len(header_hex))
            return bytes.fromhex(prefix + header_hex + encrypted_payload)
        except Exception as e:
            logging.error(f"❌ [{self.uid}] prepare_packet FAILED: {e}", exc_info=True)
            return None

    def build_bytes_payload(self, access_token, openid):
        dT = (
            b'\x1a\x132026-01-14 12:19:02"\tfree fire(\x04:\x071.130.1B2Android OS 9 / '
            b'API-28 (PI/rel.cjw.20220518.114133)J\x08HandheldR\x0cMTN/SpacetelZ\x04WIFI`\x80\n'
            b'h\xd0\x05r\x03240z-x86-64 SSE3 SSE4.1 SSE4.2 AVX AVX2 | 2400 | 4\x80\x01\xe6\x1e'
            b'\x8a\x01\x0fAdreno (TM) 640\x92\x01\rOpenGL ES 3.2\x9a\x01+Google|625f716f-91a7-495b-9f16-08fe9d3c6533'
            b'\xa2\x01\r176.28.145.29\xaa\x01\x02ar\xb2\x01 9132c6fb72caccfdc8120d9ec2cc06b8\xba\x01\x014\xc2\x01\x08'
            b'Handheld\xca\x01\rOnePlus A5010\xd2\x01\x02SG\xea\x01@3dfa9ab9d25270faf432f7b528564be9ec4790bc744a4eba70225207427d0c40'
            b'\xf0\x01\x01\xca\x02\x0cMTN/Spacetel\xd2\x02\x04WIFI\xca\x03 1ac4b80ecf0478a44203bf8fac6120f5\xe0\x03\xb5\xee\x02'
            b'\xe8\x03\xc2\x83\x02\xf0\x03\xaf\x13\xf8\x03\x84\x07\x80\x04\xcf\x92\x02\x88\x04\xb5\xee\x02\x90\x04\xcf\x92\x02'
            b'\x98\x04\xb5\xee\x02\xb0\x04\x04\xc8\x04\x03\xd2\x04X/data/app/~~lqYdjEs9bd43CagTaQ9JPg==/com.dts.freefireth-i72Sh_-sI0zZHs5Bw6aufg==/lib/arm'
            b'\xe0\x04\x01\xea\x04z4a10243f7968f0b4bea6b7c7c678e6fa|/data/app/~~lqYdjEs9bd43CagTaQ9JPg==/com.dts.freefireth-i72Sh_-sI0zZHs5Bw6aufg==/base.apk'
            b'\xf0\x04\x06\xf8\x04\x01\x8a\x05\x0232\x9a\x05\n2019119624\xb2\x05\tOpenGLES2\xb8\x05\xff\x01\xc0\x05\x04'
            b'\xe0\x05\xed\xb4\x02\xea\x05\t3rd_party\xf2\x05\\KqsHT8Q+ls0+DdIl/OavRrovpyZYcwgnQHQQcmWwjGmXvBQKOMctxpyopTQWTHvS5JqMigGkSLCLB6Q8x9TAavMfljo='
            b'\x88\x06\x01\x90\x06\x01\x9a\x06\x014\xa2\x06\x014\xb2\x06"@\x06GOVT\n\x01\x1a]\x0e\x11^\x00\x17\rKn\x08W\tQ\nhZ\x02Xh\x00\to\x00\x01a'
        )

        now_str = str(datetime.now())[:19].encode()
        dT = dT.replace(b'2026-01-14 12:19:02', now_str)
        dT = dT.replace(b'9132c6fb72caccfdc8120d9ec2cc06b8', openid.encode())
        dT = dT.replace(b'3dfa9ab9d25270faf432f7b528564be9ec4790bc744a4eba70225207427d0c40', access_token.encode())

        try:
            return encrypt_api(dT.hex())
        except Exception as e:
            logging.error(f"Lỗi mã hóa Bytes Payload: {e}")
            return None
            
    def pkt_squad(self): return self.prepare_packet({1: 15, 2: {1: 907104541, 2: 0}})#907104541 - new id owen group
    def pkt_start(self): return self.prepare_packet({1: 9, 2: {1: 13256361202}})
    def pkt_join_team(self, code):
        return self.prepare_packet({1: 4, 2: {4: bytes.fromhex("01090a0b121920"), 5: str(code), 6: 6, 8: 1, 9: {2: 843, 6: 11, 8: "1.126.1", 9: 4, 10: 1}}})
    
    #get tokens..
    def get_guest_token(self):
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        headers = {
            "Host": "100067.connect.garena.com",
            "User-Agent": "GarenaMSDK/4.0.42(SM-G935F ;Android 9;en;US;app 1.128.2 2019120828;)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "close",
            "If-Modified-Since": datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT"),
        }
        payload = {"uid": str(self.uid), "password": str(self.password), "response_type": "token", "client_type": "2", "client_secret": CLIENT_SECRET, "client_id": "100067"}
        
        try:
            resp = requests.post(url, headers=headers, data=payload, timeout=10)
            data = resp.json()
            if 'access_token' in data: return data['access_token'], data['open_id']
            logging.error(f"❌ [{self.uid}] Token Error: {data.get('error')}")
            return None, None
        except Exception as e:
            logging.error(f"❌ [{self.uid}] Net Error: {e}")
            return None, None

    def major_login(self, new_token, new_openid):
        url = "https://loginbp.ggpolarbear.com/MajorLogin"
        headers = {
            'X-Unity-Version': '2022.3.47f1',
            'ReleaseVersion': FREEFIRE_VERSION,
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-GA': 'v1 1',
            'Content-Length': '928',
            'User-Agent': 'GarenaMSDK/4.0.42(SM-G935F ;Android 9;en;US;app 1.128.2 2019120828;)',
            'Host': 'loginbp.ggpolarbear.com',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip'
        }

        try:
            encrypted_payload = self.build_bytes_payload(new_token, new_openid)
            if not encrypted_payload: return None, None, None, None
            
            resp = requests.post(url, headers=headers, data=bytes.fromhex(encrypted_payload), verify=False, timeout=10)
            if resp.status_code == 200:
                return self.parse_login_response(resp.content) 
            else:
                logging.error(f"❌ [{self.uid}] MajorLogin Failed HTTP {resp.status_code}")
                return None, None, None, None
        except Exception as e:
            logging.error(f"❌ [{self.uid}] Lỗi MajorLogin: {e}")
            return None, None, None, None

    def connect_and_spam(self, whisper_ip, whisper_port, online_ip, online_port, token_packet):
        pass

    def run(self):
        logging.info(f"🔥 Start UID: {self.uid}")
        
        new_access_token, new_open_id = self.get_guest_token()
        if not new_access_token:
            logging.error(f"❌ [{self.uid}] get_guest_token FAILED → dừng")
            return
        logging.info(f"✅ [{self.uid}] get_guest_token OK | open_id={new_open_id}")

        base64_token, key, iv, ts = self.major_login(new_access_token, new_open_id)
        if not base64_token:
            logging.error(f"❌ [{self.uid}] major_login FAILED → dừng")
            return
        logging.info(f"✅ [{self.uid}] major_login OK | key={key[:4] if key else None}... ts={ts}")

        try:
            jwt_parts = base64_token.split('.')
            payload_part = jwt_parts[1] + '=' * (-len(jwt_parts[1]) % 4)
            decoded_jwt = json.loads(base64.urlsafe_b64decode(payload_part))
            acc_id = decoded_jwt['account_id']
            external_id = decoded_jwt['external_id']   
            signature_md5 = decoded_jwt['signature_md5']
            logging.info(f"✅ [{self.uid}] JWT decode OK | acc_id={acc_id}")
        except Exception as e:
            logging.error(f"❌ [{self.uid}] JWT decode FAILED: {e}")
            return

        try:
            payload_template = "1a13323032352d30372d33302031313a30323a3531220966726565206669726528013a07312e3132362e31422c416e64726f6964204f5320372e312e32202f204150492d323320284e32473438482f373030323530323234294a0848616e6468656c645207416e64726f69645a045749464960c00c68840772033332307a1f41524d7637205646507633204e454f4e20564d48207c2032343635207c203480019a1b8a010f416472656e6f2028544d292036343092010d4f70656e474c20455320332e319a012b476f6f676c657c31663361643662372d636562342d343934622d383730622d623164616364373230393131a2010c3139372e312e31322e313335aa0102656eb201203939366136323964626364623339363462653662363937386635643831346462ba010134c2010848616e6468656c64ca011073616d73756e6720534d2d473935354eea014066663930633037656239383135616633306134336234613966363031393531366530653463373033623434303932353136643064656661346365663531663261f00101ca0207416e64726f6964d2020457494649ca03203734323862323533646566633136343031386336303461316562626665626466e003daa907e803899b07f003bf0ff803ae088004999b078804daa9079004999b079804daa907c80403d204262f646174612f6170702f636f6d2e6474732e667265656669726574682d312f6c69622f61726de00401ea044832303837663631633139663537663261663465376665666630623234643964397c2f646174612f6170702f636f6d2e6474732e667265656669726574682d312f626173652e61706bf00403f804018a050233329a050a32303139313138363933a80503b205094f70656e474c455332b805ff7fc00504e005dac901ea0507616e64726f6964f2055c4b71734854394748625876574c6668437950416c52526873626d43676542557562555551317375746d525536634e30524f3751453141486e496474385963784d614c575437636d4851322b7374745279377830663935542b6456593d8806019006019a060134a2060134b2060612004a001a00"
            
            now_str = str(datetime.now())[:19]
            pl_bytes = bytes.fromhex(payload_template)
            pl_bytes = pl_bytes.replace(b"2025-07-30 11:02:51", now_str.encode())
            pl_bytes = pl_bytes.replace(b"ff90c07eb9815af30a43b4a9f6019516e0e4c703b44092516d0defa4cef51f2a", new_access_token.encode())
            pl_bytes = pl_bytes.replace(b"996a629dbcdb3964be6b6978f5d814db", external_id.encode())
            pl_bytes = pl_bytes.replace(b"7428b253defc164018c604a1ebbfebdf", signature_md5.encode())
            
            final_pl_encrypted = encrypt_api(pl_bytes.hex())
            if not final_pl_encrypted:
                logging.error(f"❌ [{self.uid}] encrypt_api GetLoginData payload FAILED")
                return
            logging.info(f"✅ [{self.uid}] Calling GET_LOGIN_DATA...")
            whisper_ip, whisper_port, online_ip, online_port = GET_LOGIN_DATA(base64_token, bytes.fromhex(final_pl_encrypted))
            logging.info(f"📡 [{self.uid}] GET_LOGIN_DATA → whisper={whisper_ip}:{whisper_port} | online={online_ip}:{online_port}")
            if not online_ip:
                logging.error(f"❌ [{self.uid}] GET_LOGIN_DATA trả về online_ip=None → dừng")
                return
        except Exception as e:
            logging.error(f"❌ [{self.uid}] GetLoginData block FAILED: {e}", exc_info=True)
            return

        try:
            encoded_acc = hex(acc_id)[2:]
            time_hex = dec_to_hex(ts)
            token_hex = base64_token.encode().hex()
            encrypted_token = aes_encrypt(token_hex, self.key, self.iv)
            if not encrypted_token:
                logging.error(f"❌ [{self.uid}] aes_encrypt token FAILED (key/iv None?)")
                return

            head_len_hex = hex(len(encrypted_token) // 2)[2:]            
            acc_len = len(encoded_acc)
            zeros = '0' * (16 - acc_len)
            if acc_len == 9: zeros = '0000000'
            elif acc_len == 8: zeros = '00000000'
            elif acc_len == 10: zeros = '000006'
            
            login_header = f'0115{zeros}{encoded_acc}{time_hex}00000{head_len_hex}'
            final_login_packet = login_header + encrypted_token
            logging.warning(f"[{self.uid}] Login OK | acc_id={acc_id} | ts={ts} | online={online_ip}:{online_port}")
            # Reset session counter khi login mới (acc mới hoặc token mới)
            _session_counters[self.uid] = 0
            
            # Reconnect loop
            stop_ev = getattr(self, "_stop_event", None)
            self._run_reconnect_loop(
                whisper_ip, whisper_port, online_ip, online_port,
                final_login_packet, stop_ev,
                n_workers=25, delay=0.1
            )
        except Exception as e:
            logging.error(f"[-] run() block: {e}", exc_info=True)

#ACCOUNT MANAGEMENT
ACCOUNTS_FILE = "acc.json"

def load_accounts(filename=ACCOUNTS_FILE):
    if not os.path.exists(filename):
        logging.warning(f"[×] Không tìm thấy {filename}")
        return {}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def get_available_account():
    accounts = load_accounts("acc.json")
    if accounts:
        uid, pwd = next(iter(accounts.items()))
        return uid, pwd
    return None, None

def get_remaining_count():
    return len(load_accounts("acc.json"))

# Cập nhật hàm start_all_bots đọc từ lag.json
def start_all_bots(tc, delay=5):
    """Hàm xử lý đọc tất cả acc trong lag.json và khởi chạy đồng thời"""
    global current_stop_event, current_thread  
    
    accounts = load_accounts("lag.json")
    if not accounts:
        return False, "❌ Không có account nào trong lag.json", 0, 0

    # Dừng bot cũ trước khi chạy loạt mới
    stop_current()
    old = current_thread
    if old and old.is_alive():
        old.join(timeout=5)

    stop_event = threading.Event()
    
    with thread_lock:
        current_stop_event = stop_event

    started_count = 0
    for uid, pwd in list(accounts.items()):
        try:
            t = threading.Thread(target=_launch_bot_single, args=(tc, uid, pwd, stop_event), daemon=True)
            t._teamcode = tc
            with thread_lock:
                current_thread = t 
            t.start()
            started_count += 1
        except Exception as e:
            logging.error(f"[-] Không thể khởi chạy bot UID {uid}: {e}")

    if started_count > 0:
        _auto_stop_bot(delay)
        return True, None, started_count, len(accounts)
    else:
        return False, "❌ Không thể khởi chạy bất kỳ bot nào từ lag.json.", 0, len(accounts)


# ===== STOP CONTROL =====
current_stop_event: threading.Event = None
current_thread:     threading.Thread = None
thread_lock = threading.Lock()

def stop_current():
    global current_stop_event
    with thread_lock:
        if current_stop_event and not current_stop_event.is_set():
            current_stop_event.set()
            return True
    return False

def _spam_worker(sock, packets, sock_lock, stop_ev, is_running_ref, delay, label):
    while is_running_ref[0]:
        if stop_ev and stop_ev.is_set():
            break
        try:
            with sock_lock:
                for pkt in packets:
                    sock.send(pkt)
            if delay > 0:
                time.sleep(delay)
        except socket.error as e:
            logging.debug(f"[{label}] socket.error: {e}")
            break   #sockes die

# Track session count per uid
_session_counters = {}

# Track số lần run_bot được gọi (lần 1, lần 2...)
_run_call_count  = 0
_run_call_lock   = threading.Lock()

def _get_run_label():
    global _run_call_count
    with _run_call_lock:
        _run_call_count += 1
        n = _run_call_count

    log_file = f"debug_run_{n}.log"
    # Thêm file handler mới cho lần chạy này
    fh = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    fh.setLevel(logging.WARNING)
    fh.setFormatter(_log_formatter)
    logging.getLogger().addHandler(fh)
    logging.warning(f"{'='*60}")
    logging.warning(f"LẦN CHẠY #{n} — log file: {log_file}")
    logging.warning(f"{'='*60}")
    return n, log_file, fh

def _connect_once(self, online_ip, online_port, token_packet):
    _session_counters[self.uid] = _session_counters.get(self.uid, 0) + 1
    s_num = _session_counters[self.uid]
    label = f"[{self.uid}|S#{s_num}]"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    t0 = time.time()
    try:
        sock.connect((online_ip, int(online_port)))
        t_conn = time.time() - t0
        sock.send(bytes.fromhex(token_packet))

        #Đọc login response
        sock.settimeout(2)
        resp = b""
        try:
            resp = sock.recv(4096)
        except Exception:
            pass

        got_ff = bool(resp and resp[0] == 0xFF)
        logging.warning(
            f"{label} LOGIN_RESP | "
            f"tcp={t_conn:.3f}s | "
            f"resp={len(resp)}B | "
            f"hex={resp[:12].hex() if resp else 'EMPTY'} | "
            f"0xFF={got_ff}"
        )

        if got_ff:
            time.sleep(0.4)
            try:
                extra = sock.recv(4096)
                logging.warning(f"{label} 0xFF_EXTRA | {len(extra)}B: {extra[:12].hex()}")
            except Exception:
                logging.warning(f"{label} 0xFF_EXTRA | timeout (no extra)")
        elif not resp:
            logging.warning(f"{label} LOGIN_RESP | EMPTY → có thể bị blacklist hoặc token hết hạn")

        #Gửi join packet
        pkt_join = self.pkt_join_team(self.teamcode)
        if not pkt_join:
            logging.error(f"{label} pkt_join=None")
            sock.close()
            return None
        sock.send(pkt_join)

        #Đọc join response
        sock.settimeout(0.5)
        resp2 = b""
        try:
            resp2 = sock.recv(4096)
        except Exception:
            pass

        logging.warning(
            f"{label} JOIN_RESP | "
            f"resp={len(resp2)}B | "
            f"hex={resp2[:12].hex() if resp2 else 'EMPTY'} | "
            f"total_t={time.time()-t0:.3f}s"
        )

        # Phát hiện dấu hiệu bị reject/blacklist
        if resp2 and len(resp2) < 10:
            logging.warning(f"{label} JOIN_RESP quá ngắn ({len(resp2)}B) → có thể bị từ chối")

        sock.settimeout(None)
        return sock
    except Exception as e:
        logging.warning(f"{label} connect_once FAILED {time.time()-t0:.2f}s: {e}")
        try: sock.close()
        except: pass
        return None

def _run_reconnect_loop(self, whisper_ip, whisper_port, online_ip, online_port,
                         token_packet, stop_ev, n_workers=25, delay=0):
    try:
        ws = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ws.settimeout(5)
        ws.connect((whisper_ip, int(whisper_port)))
        ws.send(bytes.fromhex(token_packet))
        ws.close()
        logging.info(f"[{self.uid}] Whisper OK")
    except Exception as e:
        logging.warning(f"[{self.uid}] Whisper FAILED: {e}")

    # Build packets
    pkt_lag = self.pkt_squad()
    pkt_g = self.pkt_start()
    spam_pkts = [p for p in [pkt_lag, pkt_g] if p]

    session = 0
    next_sock_holder = [None]

    def _prefetch():
        next_sock_holder[0] = _connect_once(self, online_ip, online_port, token_packet)

    # Pre-connect
    t = threading.Thread(target=_prefetch, daemon=True)
    t.start(); t.join()

    while True:
        if stop_ev and stop_ev.is_set():
            break
        if not self.is_running:
            break

        session += 1
        sock = next_sock_holder[0]
        next_sock_holder[0] = None

        if not sock:
            logging.warning(f"[{self.uid}] S#{session} pre-connect failed, direct retry...")
            sock = _connect_once(self, online_ip, online_port, token_packet)
            if not sock:
                time.sleep(0.5)
                continue

        _t_session = time.time()
        if session <= 2 or session % 20 == 0:
            logging.warning(f"[{self.uid}] S#{session} start")

        # Pre-connect
        pre_t = threading.Thread(target=_prefetch, daemon=True)
        pre_t.start()

        sock_lock  = threading.Lock()
        is_running = [True]
        workers = [
            threading.Thread(
                target=_spam_worker,
                args=(sock, spam_pkts, sock_lock, stop_ev, is_running, delay, f"{self.uid}|S{session}W{i}"),
                daemon=True
            )
            for i in range(n_workers)
        ]
        for w in workers: w.start()
        for w in workers: w.join()

        is_running[0] = False
        _alive = time.time() - _t_session
        try: sock.close()
        except: pass

        logging.warning(f"[{self.uid}] S#{session} ended | alive={_alive:.2f}s")

        if stop_ev and stop_ev.is_set():
            if next_sock_holder[0]:
                try: next_sock_holder[0].close()
                except: pass
            break
        pre_t.join(timeout=1)

    logging.warning(f"[{self.uid}] loop done | sessions={session}")

FFClient.connect_and_spam    = lambda *a, **kw: None   # unused
FFClient._run_reconnect_loop = _run_reconnect_loop

#run

# Thêm vào main.py (hoặc các file tương ứng nếu tách module)


def _launch_bot_single(team_code, uid, pwd, stop_event):
    try:
        client = FFClient(uid, pwd, team_code)
        client._stop_event = stop_event
        client.is_running  = True
        client.start()
        client.join()
    except Exception as e:
        logging.error(f"[-] Bot error [{uid} - {team_code}]: {e}")
    finally:
        auto_reg_replacement(old_uid=uid)
        

def run_bot(team_code, uid, pwd, stop_event: threading.Event):
    global current_stop_event, current_thread
    run_n, log_file, fh = _get_run_label()
    try:
        logging.warning(f"[RUN#{run_n}] TC={team_code} | UID={uid} | acc_left={get_remaining_count()}")

        if stop_event.is_set():
            return

        client = FFClient(uid, pwd, team_code)
        client._stop_event = stop_event
        client.is_running  = True
        client.start()
        client.join()

        logging.info(f"[+] Hoàn thành Teamcode: {team_code}")

    except Exception as e:
        logging.error(f"[-] Lỗi run_bot [{team_code}]: {e}")
    finally:
        logging.warning(f"[RUN#{run_n}] Done — xem {log_file}")
        fh.close()
        logging.getLogger().removeHandler(fh)
        with thread_lock:
            current_stop_event = None
            current_thread     = None