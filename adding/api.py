from flask import Flask, request, jsonify
import requests
import json
import time
import urllib3
import ssl
import gzip
import http.client
import threading
from io import BytesIO
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from datetime import datetime
from protobuf_decoder.protobuf_decoder import Parser
from google.protobuf.timestamp_pb2 import Timestamp
from my_message_pb2 import MyMessage

# Import từ byte
from byte import Ua, CrEaTe_ProTo, Fix_PackEt, Encrypt_ID, Key, Iv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

VERSION = "1.130.1"
RELEASE_VERSION = "OB54"

token_cache = {}

def EnC_AEs(HeX):
    cipher = AES.new(Key, AES.MODE_CBC, Iv)
    return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()

def DeCode_PackEt(input_text):
    try:
        parsed = Parser().parse(input_text)
        return json.dumps(Fix_PackEt(parsed))
    except Exception as e:
        return None

def get_access_token(uid, password):
    cache_key = f"{uid}:{password}"
    if cache_key in token_cache and time.time() - token_cache[cache_key]['timestamp'] < 1800:
        return token_cache[cache_key]['access_token'], token_cache[cache_key]['open_id']
    
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": Ua(),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close",
        "X-Client-Version": VERSION,
    }
    data = {
        "uid": str(uid),
        "password": str(password),
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067",
    }
    try:
        response = requests.post(url, headers=headers, data=data, verify=False, timeout=15)
        if response.status_code == 200:
            result = response.json()
            token_cache[cache_key] = {
                'access_token': result['access_token'],
                'open_id': result['open_id'],
                'timestamp': time.time()
            }
            return result['access_token'], result['open_id']
    except Exception as e:
        print(f"Lỗi: {e}")
    return None, None

def do_major_login(payload):
    context = ssl._create_unverified_context()
    conn = http.client.HTTPSConnection("loginbp.ggpolarbear.com", context=context)
    headers = {
        "X-Unity-Version": "2018.4.11f1",
        "ReleaseVersion": RELEASE_VERSION,
        "Content-Type": "application/x-www-form-urlencoded",
        "X-GA": "v1 1",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)",
        "Host": "loginbp.ggpolarbear.com",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "X-Client-Version": VERSION,
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

def extract_key_iv(raw_data):
    my_message = MyMessage()
    my_message.ParseFromString(raw_data)
    timestamp = my_message.field21
    key = my_message.field22
    iv = my_message.field23
    
    timestamp_obj = Timestamp()
    timestamp_obj.FromNanoseconds(timestamp)
    timestamp_seconds = timestamp_obj.seconds
    timestamp_nanos = timestamp_obj.nanos
    combined_timestamp = timestamp_seconds * 1_000_000_000 + timestamp_nanos
    return combined_timestamp, key, iv

def generate_login_token(uid, password):
    try:
        access_token, open_id = get_access_token(uid, password)
        if not access_token:
            return None
        
        platform = 4
        
        payload = {
            3: str(datetime.now())[:-7], 4: "free fire", 5: 4, 7: VERSION,
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
            return jwt_token, key, iv, combined_timestamp, bot_uid
    except Exception as e:
        print(f"Lỗi: {e}")
    return None

def SendFriendRequest_HTTP(target_uid, uid, password):
    access_token, open_id = get_access_token(uid, password)
    if not access_token:
        return False, "Không thể lấy access token"
    
    headers = {
        'X-Unity-Version': '2018.4.11f1',
        'ReleaseVersion': RELEASE_VERSION,
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-GA': 'v1 1',
        'Authorization': f'Bearer {access_token}',
        'User-Agent': Ua(),
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip',
        'X-Client-Version': VERSION,
    }
    
    encrypted_id = Encrypt_ID(target_uid)
    if not encrypted_id:
        return False, f"Lỗi mã hóa UID: {target_uid}"
    
    payload = f'08a7c4839f1e10{encrypted_id}1801'
    data = bytes.fromhex(EnC_AEs(payload))
    
    domains = [
        'https://clientbp.ggpolarbear.com/RequestAddingFriend',
        'https://clientbp.ggwhitehawk.com/RequestAddingFriend',
        'https://clientbp.ggpbn.com/RequestAddingFriend',
    ]
    
    for url in domains:
        try:
            response = requests.post(url, headers=headers, data=data, verify=False, timeout=15)
            text = response.text
            
            if response.status_code == 200:
                if 'success' in text.lower() or 'ok' in text.lower():
                    return True, f"Gửi kết bạn thành công! (VERSION {VERSION})"
                elif 'BR_FRIEND_NOT_SAME_REGION' in text:
                    return False, "Khác khu vực!"
                elif 'BR_FRIEND_MAX_REQUEST' in text:
                    return False, "Đã đạt giới hạn yêu cầu!"
                elif 'BR_FRIEND_ALREADY_SENT_REQUEST' in text:
                    return False, "Đã gửi yêu cầu trước đó!"
                elif 'BR_FRIEND_ALREADY_FRIEND' in text:
                    return False, "Đã là bạn bè!"
            elif response.status_code == 401:
                return False, "Token hết hạn hoặc version không hợp lệ!"
        except Exception as e:
            continue
    
    return False, "Không kết nối được server"

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'name': 'Zan KB API',
        'version': VERSION,
        'release': RELEASE_VERSION,
        'endpoints': {
            '/kb': 'Gửi kết bạn (uid, password, target)',
            '/token': 'Lấy token (uid, password)',
        }
    })

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
            return jsonify({'status': 'error', 'message': 'Thiếu uid, password hoặc target'}), 400
        
        success, message = SendFriendRequest_HTTP(target, uid, password)
        return jsonify({'status': 'success' if success else 'error', 'message': message})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

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
            return jsonify({'status': 'error', 'message': 'Thiếu uid hoặc password'}), 400
        
        access_token, open_id = get_access_token(uid, password)
        if not access_token:
            return jsonify({'status': 'error', 'message': 'Sai UID hoặc mật khẩu'}), 400
        
        return jsonify({'status': 'success', 'access_token': access_token, 'open_id': open_id})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def keep_alive():
    while True:
        try:
            requests.get("https://zankb.onrender.com/", timeout=10)
        except: pass
        time.sleep(600)

if __name__ == '__main__':
    threading.Thread(target=keep_alive, daemon=True).start()
    print(f"✅ Server chạy tại http://0.0.0.0:2010")
    print(f"✅ Version: {VERSION} - {RELEASE_VERSION}")
    app.run(host='0.0.0.0', port=2010, debug=False)
