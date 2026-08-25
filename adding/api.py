from flask import Flask, request, jsonify
import requests
import json
import binascii
import time
import urllib3
import base64
import datetime
import re
import socket
import threading
import random
import os
import sys
import ssl
import gzip
import http.client
from io import BytesIO
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from datetime import datetime
from protobuf_decoder.protobuf_decoder import Parser
from google.protobuf.timestamp_pb2 import Timestamp

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ====== MÀU SẮC ======
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
WHITE = "\033[97m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ====== KEY AES ======
Key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
Iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# ====== HÀM CƠ BẢN ======
def Ua():
    versions = [
        '4.0.18P6', '4.0.19P7', '4.0.20P1', '4.1.0P3', '4.1.5P2', '4.2.1P8',
        '4.2.3P1', '5.0.1B2', '5.0.2P4', '5.1.0P1', '5.2.0B1', '5.2.5P3',
        '5.3.0B1', '5.3.2P2', '5.4.0P1', '5.4.3B2', '5.5.0P1', '5.5.2P3'
    ]
    models = [
        'SM-A125F', 'SM-A225F', 'SM-A325M', 'SM-A515F', 'SM-A725F', 'SM-M215F', 'SM-M325FV',
        'Redmi 9A', 'Redmi 9C', 'POCO M3', 'POCO M4 Pro', 'RMX2185', 'RMX3085',
        'moto g(9) play', 'CPH2239', 'V2027', 'OnePlus Nord', 'ASUS_Z01QD',
    ]
    android_versions = ['9', '10', '11', '12', '13', '14']
    languages = ['en-US', 'es-MX', 'pt-BR', 'id-ID', 'ru-RU', 'hi-IN', 'en-BD']
    countries = ['USA', 'MEX', 'BRA', 'IDN', 'RUS', 'BD', 'IND']
    version = random.choice(versions)
    model = random.choice(models)
    android = random.choice(android_versions)
    lang = random.choice(languages)
    country = random.choice(countries)
    return f"GarenaMSDK/{version}({model};Android {android};{lang};{country};)"

def EnC_AEs(HeX):
    cipher = AES.new(Key, AES.MODE_CBC, Iv)
    return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()

def DEc_AEs(HeX):
    cipher = AES.new(Key, AES.MODE_CBC, Iv)
    return unpad(cipher.decrypt(bytes.fromhex(HeX)), AES.block_size).hex()

def EnC_PacKeT(HeX, K, V):
    return AES.new(K, AES.MODE_CBC, V).encrypt(pad(bytes.fromhex(HeX), 16)).hex()

def DEc_PacKeT(HeX, K, V):
    return unpad(AES.new(K, AES.MODE_CBC, V).decrypt(bytes.fromhex(HeX)), 16).hex()

def EnC_Vr(N):
    if N < 0:
        return ''
    H = []
    while True:
        BesTo = N & 0x7F
        N >>= 7
        if N:
            BesTo |= 0x80
        H.append(BesTo)
        if not N:
            break
    return bytes(H)

def CrEaTe_VarianT(field_number, value):
    field_header = (field_number << 3) | 0
    return EnC_Vr(field_header) + EnC_Vr(value)

def CrEaTe_LenGTh(field_number, value):
    field_header = (field_number << 3) | 2
    encoded_value = value.encode() if isinstance(value, str) else value
    return EnC_Vr(field_header) + EnC_Vr(len(encoded_value)) + encoded_value

def CrEaTe_ProTo(fields):
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, dict):
            nested_packet = CrEaTe_ProTo(value)
            packet.extend(CrEaTe_LenGTh(field, nested_packet))
        elif isinstance(value, int):
            packet.extend(CrEaTe_VarianT(field, value))
        elif isinstance(value, str) or isinstance(value, bytes):
            packet.extend(CrEaTe_LenGTh(field, value))
    return packet

def DecodE_HeX(H):
    R = hex(H)
    F = str(R)[2:]
    if len(F) == 1:
        F = "0" + F
        return F
    else:
        return F

def Fix_PackEt(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data['wire_type'] = result.wire_type
        if result.wire_type == "varint":
            field_data['data'] = result.data
        if result.wire_type == "string":
            field_data['data'] = result.data
        if result.wire_type == "bytes":
            field_data['data'] = result.data
        elif result.wire_type == 'length_delimited':
            field_data["data"] = Fix_PackEt(result.data.results)
        result_dict[result.field] = field_data
    return result_dict

def DeCode_PackEt(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        parsed_results_objects = parsed_results
        parsed_results_dict = Fix_PackEt(parsed_results_objects)
        json_data = json.dumps(parsed_results_dict)
        return json_data
    except Exception as e:
        print(f"error {e}")
        return None

def GeneRaTePk(Pk, N, K, V):
    PkEnc = EnC_PacKeT(Pk, K, V)
    _ = DecodE_HeX(int(len(PkEnc) // 2))
    if len(_) == 2:
        HeadEr = N + "000000"
    elif len(_) == 3:
        HeadEr = N + "00000"
    elif len(_) == 4:
        HeadEr = N + "0000"
    elif len(_) == 5:
        HeadEr = N + "000"
    return bytes.fromhex(HeadEr + _ + PkEnc)

def xBunnEr():
    avatar_list = [
        '902000016', '902000031', '902000011', '902000065',
        '902000204', '902000192', '902000191', '902000179',
        '902000133', '902045001', '902038023', '902048004',
        '902039014', '902000063', '902000306', '902047009'
    ]
    return int(random.choice(avatar_list))

# ====== MÃ HÓA ID ======
def Encrypt_ID(x):
    dec = ['80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '8a', '8b', '8c', '8d', '8e', '8f', '90', '91', 
     '92', '93', '94', '95', '96', '97', '98', '99', '9a', '9b', '9c', '9d', '9e', '9f', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8', 'a9', 'aa', 'ab', 'ac', 'ad', 'ae', 'af', 'b0', 'b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b8', 'b9', 'ba', 'bb', 'bc', 'bd', 'be', 'bf', 'c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'ca', 'cb', 'cc', 'cd', 'ce', 'cf', 'd0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8', 'd9', 'da', 'db', 'dc', 'dd', 'de', 'df', 'e0', 'e1', 'e2', 'e3', 'e4', 'e5', 'e6', 'e7', 'e8', 'e9', 'ea', 'eb', 'ec', 'ed', 'ee', 'ef', 'f0', 'f1', 'f2', 'f3', 'f4', 
     'f5', 'f6', 'f7', 'f8', 'f9', 'fa', 'fb', 'fc', 'fd', 'fe', 'ff']
    xxx = ['1', '01', '02', '03', '04', '05', '06', '07', '08', '09', '0a', '0b', '0c', '0d', '0e', '0f', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '1a', '1b', '1c', '1d', '1e', '1f', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '2a', '2b', '2c', '2d', '2e', '2f', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '3a', '3b', '3c', '3d', '3e', '3f', '40', '41', '42', '43', '44', '45', '46', '47', '48', '49', '4a', '4b', '4c', '4d', '4e', '4f', '50', '51', '52', 
     '53', '54', '55', '56', '57', '58', '59', '5a', '5b', '5c', '5d', '5e', '5f', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '6a', '6b', '6c', '6d', '6e', '6f', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '7a', '7b', '7c', '7d', '7e', '7f']
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
    except Exception: 
        return None

# ====== LẤY ACCESS TOKEN ======
def get_access_token(uid, password):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": Ua(),
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
    try:
        response = requests.post(url, headers=headers, data=data, verify=False)
        if response.status_code == 200:
            return response.json()["access_token"], response.json()["open_id"]
    except Exception as e:
        print(f"{RED}Lỗi: {e}{RESET}")
    return None, None

# ====== DO MAJOR LOGIN ======
def do_major_login(payload):
    context = ssl._create_unverified_context()
    conn = http.client.HTTPSConnection("loginbp.ggpolarbear.com", context=context)
    headers = {
        "X-Unity-Version": "2018.4.11f1",
        "ReleaseVersion": "OB54",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-GA": "v1 1",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)",
        "Host": "loginbp.ggpolarbear.com",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
    }
    try:
        conn.request("POST", "/MajorLogin", body=payload, headers=headers)
        response = conn.getresponse()
        raw_data = response.read()
        if response.getheader("Content-Encoding") == "gzip":
            with gzip.GzipFile(fileobj=BytesIO(raw_data)) as f:
                raw_data = f.read()
        text = raw_data.decode(errors="ignore")
        if "BR_PLATFORM_INVALID_OPENID" in text or "BR_GOP_TOKEN_AUTH_FAILED" in text:
            return None
        return raw_data.hex() if response.status in [200, 201] else None
    finally:
        conn.close()

# ====== EXTRACT KEY IV ======
def extract_key_iv(raw_data):
    # Tạo class MyMessage đơn giản
    class MyMessage:
        def ParseFromString(self, data):
            # Parse protobuf đơn giản
            parsed = json.loads(DeCode_PackEt(data.hex()))
            self.field21 = int(parsed.get("21", {}).get("data", 0))
            self.field22 = bytes.fromhex(parsed.get("22", {}).get("data", ""))
            self.field23 = bytes.fromhex(parsed.get("23", {}).get("data", ""))
    
    my_message = MyMessage()
    my_message.ParseFromString(raw_data)
    timestamp, key, iv = my_message.field21, my_message.field22, my_message.field23
    timestamp_obj = Timestamp()
    timestamp_obj.FromNanoseconds(timestamp)
    timestamp_seconds = timestamp_obj.seconds
    timestamp_nanos = timestamp_obj.nanos
    combined_timestamp = timestamp_seconds * 1_000_000_000 + timestamp_nanos
    return combined_timestamp, key, iv

# ====== GET GAME SERVERS ======
def get_game_servers(jwt_token, payload):
    url = "https://clientbp.ggpolarbear.com/GetLoginData"
    headers = {
        "Expect": "100-continue",
        "Authorization": f"Bearer {jwt_token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB54",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dalvik/2.1.0 (Linux; Android 9; G011A Build/PI)",
        "Host": "clientbp.ggpolarbear.com",
        "Connection": "close",
        "Accept-Encoding": "gzip, deflate, br",
    }
    try:
        response = requests.post(url, headers=headers, data=payload, verify=False)
        parsed_data = json.loads(DeCode_PackEt(response.content.hex()))
        chat_addr = parsed_data["32"]["data"]
        online_addr = parsed_data["14"]["data"]
        chat_ip = chat_addr[: len(chat_addr) - 6]
        online_ip = online_addr[: len(online_addr) - 6]
        chat_port = chat_addr[len(chat_addr) - 5 :]
        online_port = online_addr[len(online_addr) - 5 :]
        return chat_ip, chat_port, online_ip, online_port
    except Exception:
        return None, None, None, None

# ====== GENERATE LOGIN TOKEN ======
def generate_login_token(uid, password):
    try:
        access_token, open_id = get_access_token(uid, password)
        if not access_token:
            return None
        
        platform = 4
        version = "1.123.1"
        
        payload = {
            3: str(datetime.now())[:-7], 4: "free fire", 5: 4, 7: version,
            8: "Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)",
            9: "Handheld", 10: "Verizon Wireless", 11: "WIFI", 12: 1280, 13: 960,
            14: "240", 15: "x86-64 SSE3 SSE4.1 SSE4.2 AVX AVX2 | 2400 | 4",
            16: 5951, 17: "Adreno (TM) 640", 18: "OpenGL ES 3.0",
            19: "Google|0fc0e446-ca27-4faa-824a-d40d77767de9",
            20: "20.171.73.202", 21: "fr", 22: open_id, 23: platform,
            24: "Handheld", 25: "google G011A", 29: access_token, 30: 1,
            41: "Verizon Wireless", 42: "WIFI", 57: "1ac4b80ecf0478a44203bf8fac6120f5",
            60: 32966, 61: 29779, 62: 2479, 63: 914, 64: 31176,
            65: 32966, 66: 31176, 67: 32966, 70: 4, 73: 2,
            74: "/data/app/com.dts.freefireth-g8eDE0T268FtFmnFZ2UpmA==/lib/arm",
            76: 1, 77: "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-g8eDE0T268FtFmnFZ2UpmA==/base.apk",
            78: 6, 79: 1, 81: "32", 83: "2019120270", 86: "OpenGLES2",
            87: 255, 88: platform, 89: "J\u0003FD\u0004\r_UH\u0003\u000b\u0016_\u0003D^J>\u000fWT\u0000\\=\nQ_;\u0000\r;Z\u0005a",
            90: "Phoenix", 91: "AZ", 92: 10214, 93: "3rd_party",
            94: "KqsHT7gtKWkK0gY/HwmdwXIhSiz4fQldX3YjZeK86XBTthKAf1bW4Vsz6Di0S8vqr0Jc4HX3TMQ8KaUU3GeVvYzWF9I=",
            95: 111207, 97: 1, 98: 1, 99: f"{platform}", 100: f"{platform}",
        }
        
        payload_hex = CrEaTe_ProTo(payload).hex()
        encrypted = bytes.fromhex(EnC_AEs(payload_hex))
        response = do_major_login(encrypted)
        
        if response:
            parsed = json.loads(DeCode_PackEt(response))
            bot_uid = parsed["1"]["data"]
            jwt_token = parsed["8"]["data"]
            combined_timestamp, key, iv = extract_key_iv(bytes.fromhex(response))
            chat_ip, chat_port, online_ip, online_port = get_game_servers(jwt_token, encrypted)
            return jwt_token, key, iv, combined_timestamp, chat_ip, chat_port, online_ip, online_port, bot_uid
    except Exception as e:
        print(f"{RED}Lỗi: {e}{RESET}")
    return None

# ====== GỬI KẾT BẠN ======
def SendFriendRequest_HTTP(target_uid, token, bot_uid=""):
    domains = [
        'https://clientbp.ggpolarbear.com/RequestAddingFriend',
        'https://clientbp.ggwhitehawk.com/RequestAddingFriend',
        'https://clientbp.ggpbn.com/RequestAddingFriend',
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
    
    encrypted_id = Encrypt_ID(target_uid)
    if not encrypted_id:
        return False, f"Lỗi mã hóa UID: {target_uid}"
    
    plain_text_payload = f'08a7c4839f1e10{encrypted_id}1801'
    data = bytes.fromhex(EnC_AEs(plain_text_payload))
    
    for url in domains:
        try:
            response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
            text = response.text
            
            if response.status_code == 200:
                return True, "Gửi kết bạn thành công!"
            elif 'BR_FRIEND_NOT_SAME_REGION' in text:
                return False, "Khác khu vực!"
            elif 'BR_FRIEND_MAX_REQUEST' in text:
                return False, "Đã đạt giới hạn yêu cầu!"
            elif 'BR_FRIEND_ALREADY_SENT_REQUEST' in text:
                return False, "Đã gửi yêu cầu trước đó!"
            else:
                continue
        except Exception as e:
            continue
    
    return False, "Không kết nối được đến server (thử hết các domain)"

# ====== API: HOME ======
@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'name': 'Zan KB API',
        'version': '2.0.0',
        'endpoints': {
            '/kb': 'Gửi kết bạn (uid, password, target)',
            '/token': 'Lấy token (uid, password)',
            '/info': 'Thông tin tài khoản (uid, password)'
        }
    })

# ====== API: GỬI KẾT BẠN ======
@app.route('/kb', methods=['GET', 'POST'])
def api_kb():
    try:
        if request.method == 'GET':
            uid = request.args.get('uid')
            password = request.args.get('password')
            target = request.args.get('target')
        else:
            data = request.get_json() or {}
            uid = data.get('uid')
            password = data.get('password')
            target = data.get('target')
        
        if not uid or not password or not target:
            return jsonify({
                'status': 'error',
                'message': 'Thiếu tham số: uid, password, target'
            }), 400
        
        # Lấy token
        access_token, open_id = get_access_token(uid, password)
        if not access_token:
            return jsonify({
                'status': 'error',
                'message': 'Sai UID hoặc mật khẩu'
            }), 400
        
        # Gửi kết bạn trực tiếp không cần login phức tạp
        success, message = SendFriendRequest_HTTP(target, access_token)
        
        return jsonify({
            'status': 'success' if success else 'error',
            'message': message,
            'uid': uid,
            'target': target
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ====== API: LẤY TOKEN ======
@app.route('/token', methods=['GET', 'POST'])
def api_token():
    try:
        if request.method == 'GET':
            uid = request.args.get('uid')
            password = request.args.get('password')
        else:
            data = request.get_json() or {}
            uid = data.get('uid')
            password = data.get('password')
        
        if not uid or not password:
            return jsonify({
                'status': 'error',
                'message': 'Thiếu uid hoặc password'
            }), 400
        
        access_token, open_id = get_access_token(uid, password)
        if not access_token:
            return jsonify({
                'status': 'error',
                'message': 'Sai UID hoặc mật khẩu'
            }), 400
        
        return jsonify({
            'status': 'success',
            'access_token': access_token,
            'open_id': open_id,
            'uid': uid
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ====== API: THÔNG TIN TÀI KHOẢN ======
@app.route('/info', methods=['GET', 'POST'])
def api_info():
    try:
        if request.method == 'GET':
            uid = request.args.get('uid')
            password = request.args.get('password')
        else:
            data = request.get_json() or {}
            uid = data.get('uid')
            password = data.get('password')
        
        if not uid or not password:
            return jsonify({
                'status': 'error',
                'message': 'Thiếu uid hoặc password'
            }), 400
        
        # Login để lấy thông tin
        login_data = generate_login_token(uid, password)
        if not login_data:
            return jsonify({
                'status': 'error',
                'message': 'Login thất bại'
            }), 400
        
        jwt_token, key, iv, timestamp, chat_ip, chat_port, online_ip, online_port, bot_uid = login_data
        
        return jsonify({
            'status': 'success',
            'uid': uid,
            'bot_uid': bot_uid,
            'jwt_token': jwt_token,
            'chat_server': f"{chat_ip}:{chat_port}",
            'online_server': f"{online_ip}:{online_port}"
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ====== KEEP ALIVE (GỌI MỖI 10 PHÚT) ======
def keep_alive():
    url = "https://zankb.onrender.com/"
    while True:
        try:
            response = requests.get(url, timeout=10)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Keep-alive: {response.status_code}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Keep-alive error: {e}")
        time.sleep(600)  # 10 phút

# ====== KHỞI CHẠY ======
if __name__ == '__main__':
    # Chạy keep-alive trong thread riêng
    threading.Thread(target=keep_alive, daemon=True).start()
    
    print(f"{CYAN}╔═══════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║  {WHITE}ZAN KB API - FREE FIRE{RESET}{CYAN}                  ║{RESET}")
    print(f"{CYAN}║  {WHITE}Version 2.0.0{RESET}{CYAN}                           ║{RESET}")
    print(f"{CYAN}╚═══════════════════════════════════════════════╝{RESET}")
    print(f"\n{GREEN}✓ Server đang chạy tại http://0.0.0.0:2010{RESET}")
    print(f"{GREEN}✓ Keep-alive: https://zankb.onrender.com/ (mỗi 10 phút){RESET}")
    print(f"\n{CYAN}Endpoints:{RESET}")
    print(f"  • GET /kb?uid=...&password=...&target=...")
    print(f"  • GET /token?uid=...&password=...")
    print(f"  • GET /info?uid=...&password=...")
    print(f"\n{CYAN}DEV: @zanbackj | TIKTOK: @zanbackj{RESET}\n")
    
    app.run(host='0.0.0.0', port=2010, debug=False)
