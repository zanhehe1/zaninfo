from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import base64
import json
import time
import os
import hashlib
import hmac
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

# ====== KEY ======
KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# ====== GIẢI MÃ ACCESS TOKEN ======
def decode_access_token(access_token):
    try:
        parts = access_token.split('.')
        if len(parts) >= 2:
            payload_b64 = parts[1]
            # Thêm padding nếu thiếu
            while len(payload_b64) % 4 != 0:
                payload_b64 += '='
            decoded = json.loads(base64.urlsafe_b64decode(payload_b64))
            return decoded
    except Exception as e:
        print(f"Decode token error: {e}")
    return None

# ====== LẤY NICKNAME TỪ ACCESS TOKEN ======
def get_nickname_from_token(access_token):
    try:
        decoded = decode_access_token(access_token)
        if decoded:
            # Lấy UID
            uid = decoded.get('account_id', 'N/A')
            if not uid or uid == 'N/A':
                uid = decoded.get('user_id', 'N/A')
            if not uid or uid == 'N/A':
                uid = decoded.get('sub', 'N/A')
            
            # Lấy nickname
            nickname = decoded.get('nickname', 'Unknown')
            if nickname and nickname != 'Unknown':
                try:
                    # Thử decode base64
                    nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                except:
                    pass
            
            # Nếu vẫn Unknown, thử lấy từ các field khác
            if nickname == 'Unknown' or not nickname:
                nickname = decoded.get('name', 'Unknown')
                if nickname and nickname != 'Unknown':
                    try:
                        nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                    except:
                        pass
            
            # Nếu vẫn Unknown, thử lấy từ email
            if nickname == 'Unknown' or not nickname:
                email = decoded.get('email', '')
                if email:
                    nickname = email.split('@')[0]
            
            return nickname, uid
    except Exception as e:
        print(f"Get nickname error: {e}")
    
    return 'Unknown', 'N/A'

# ====== LẤY THÔNG TIN TỪ TOKEN QUA API GARENA ======
def get_user_info_from_garena(access_token):
    try:
        url = f"https://100067.connect.garena.com/oauth/token/inspect?token={access_token}"
        headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "100067.connect.garena.com",
            "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if 'error' not in data:
                return data
    except:
        pass
    return None

# ====== MÃ HÓA ======
def aes_encrypt(data):
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    return cipher.encrypt(pad(data, AES.block_size))

def encode_varint(n):
    result = []
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            byte |= 0x80
        result.append(byte)
        if not n:
            break
    return bytes(result)

def build_bio_proto(bio_text):
    result = b''
    header = (2 << 3) | 0
    result += encode_varint(header)
    result += encode_varint(17)
    empty = b''
    header5 = (5 << 3) | 2
    result += encode_varint(header5)
    result += encode_varint(len(empty))
    result += empty
    header6 = (6 << 3) | 2
    result += encode_varint(header6)
    result += encode_varint(len(empty))
    result += empty
    bio_encoded = bio_text.encode('utf-8')
    header8 = (8 << 3) | 2
    result += encode_varint(header8)
    result += encode_varint(len(bio_encoded))
    result += bio_encoded
    header9 = (9 << 3) | 0
    result += encode_varint(header9)
    result += encode_varint(1)
    header11 = (11 << 3) | 2
    result += encode_varint(header11)
    result += encode_varint(len(empty))
    result += empty
    header12 = (12 << 3) | 2
    result += encode_varint(header12)
    result += encode_varint(len(empty))
    result += empty
    return result

# ====== ĐỔI BIO ======
def change_bio(jwt_token, bio_text):
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
    for url in endpoints:
        try:
            proto = build_bio_proto(bio_text)
            encrypted = aes_encrypt(proto)
            resp = requests.post(url, headers=headers, data=encrypted, verify=False, timeout=10)
            if resp.status_code == 200:
                return True, "✅ Thành công!"
        except:
            continue
    return False, "❌ Thất bại!"

# ====== BAN ACCOUNT (FIX LỖI) ======
def ban_account(access_token):
    try:
        # Bước 1: Lấy thông tin token
        user_info = get_user_info_from_garena(access_token)
        if not user_info:
            return False, "Token không hợp lệ hoặc đã hết hạn!"
        
        open_id = user_info.get('open_id')
        if not open_id:
            return False, "Không lấy được Open ID!"
        
        # Bước 2: Gửi request ban đến server Garena
        ban_url = "https://clientbp.ggpolarbear.com/AccountBan"
        
        # Headers cho request ban
        ban_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; SM-G998B Build/TP1A.220624.014)",
            "ReleaseVersion": "OB54",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1"
        }
        
        # Data cho request ban
        ban_data = {
            "open_id": open_id,
            "ban_type": 1,
            "reason": "Vi phạm điều khoản sử dụng",
            "duration": 3
        }
        
        # Thử gửi request ban
        try:
            resp = requests.post(ban_url, headers=ban_headers, json=ban_data, timeout=15)
            if resp.status_code == 200:
                result = resp.json()
                if result.get('code') == 0:
                    return True, "✅ Ban 3 ngày thành công!"
                else:
                    return False, f"Lỗi từ server: {result.get('message', 'Unknown error')}"
        except Exception as e:
            pass
        
        # Bước 3: Thử endpoint khác nếu thất bại
        ban_url2 = "https://clientbp.ggblueshark.com/AccountBan"
        try:
            resp2 = requests.post(ban_url2, headers=ban_headers, json=ban_data, timeout=15)
            if resp2.status_code == 200:
                result2 = resp2.json()
                if result2.get('code') == 0:
                    return True, "✅ Ban 3 ngày thành công!"
        except:
            pass
        
        return False, "Không thể ban tài khoản! Vui lòng thử lại sau."
        
    except Exception as e:
        return False, str(e)

# ====== BIND INFO ======
def get_bind_info(access_token):
    try:
        url = "https://100067.connect.garena.com/game/account_security/bind:get_bind_info"
        payload = {'app_id': "100067", 'access_token': access_token}
        headers = {
            'User-Agent': "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip"
        }
        response = requests.get(url, params=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return True, data
        return False, None
    except Exception as e:
        return False, None

# ====== GET TOKEN ======
def get_access_token(uid, password):
    try:
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        headers = {
            "Host": "100067.connect.garena.com",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 7.1.2)",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "uid": uid,
            "password": password,
            "response_type": "token",
            "client_type": "2",
            "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
            "client_id": "100067",
        }
        response = requests.post(url, headers=headers, data=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            access_token = result.get("access_token")
            open_id = result.get("open_id")
            if access_token:
                nickname, _ = get_nickname_from_token(access_token)
                return True, {
                    "access_token": access_token,
                    "open_id": open_id or "",
                    "uid": uid,
                    "nickname": nickname
                }
        return False, "Sai UID hoặc mật khẩu!"
    except Exception as e:
        return False, str(e)

# ====== CHECK INFO UID ======
def get_uid_info(uid):
    try:
        # Thử nhiều API khác nhau
        apis = [
            f"https://info-bb20.onrender.com/info?uid={uid}",
            f"https://ff.garena.com/api/anticheat/player_info?uid={uid}",
            f"https://api.ff.garena.com/player/info?uid={uid}"
        ]
        
        for url in apis:
            try:
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                if response.status_code == 200:
                    data = response.json()
                    if data and not data.get('error'):
                        return True, data
            except:
                continue
        
        return False, None
    except Exception as e:
        return False, None

# ====== API ENDPOINTS ======

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/ban', methods=['GET'])
def api_ban():
    access_token = request.args.get('access_token')
    ban_type = request.args.get('type', '3day')
    
    if not access_token:
        return jsonify({"success": False, "error": "Missing access_token"})
    
    # Lấy thông tin từ token
    nickname, uid = get_nickname_from_token(access_token)
    
    # Thử lấy thông tin từ Garena nếu chưa có
    if uid == 'N/A' or nickname == 'Unknown':
        user_info = get_user_info_from_garena(access_token)
        if user_info:
            uid = user_info.get('account_id', uid)
            nickname = user_info.get('nickname', nickname)
            if nickname and nickname != 'Unknown':
                try:
                    nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                except:
                    pass
    
    success, msg = ban_account(access_token)
    
    return jsonify({
        "success": success,
        "uid": uid,
        "nickname": nickname,
        "ban_type": ban_type,
        "message": msg
    })

@app.route('/bio', methods=['GET'])
def api_bio():
    jwt_token = request.args.get('jwt')
    bio_text = request.args.get('bio')
    
    if not jwt_token or not bio_text:
        return jsonify({"success": False, "error": "Missing jwt or bio"})
    
    # Lấy thông tin từ JWT
    nickname = "Unknown"
    uid = "N/A"
    try:
        info = decode_jwt(jwt_token)
        if info:
            uid = info.get('account_id', 'N/A')
            nickname = info.get('nickname', 'Unknown')
            try:
                nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
            except:
                pass
    except:
        pass
    
    success, msg = change_bio(jwt_token, bio_text)
    return jsonify({
        "success": success,
        "uid": uid,
        "nickname": nickname,
        "message": msg
    })

@app.route('/bindinfo', methods=['GET'])
def api_bindinfo():
    access_token = request.args.get('token')
    if not access_token:
        return jsonify({"success": False, "error": "Missing token"})
    
    # Lấy thông tin từ token
    nickname, uid = get_nickname_from_token(access_token)
    
    # Thử lấy thông tin từ Garena nếu chưa có
    if uid == 'N/A' or nickname == 'Unknown':
        user_info = get_user_info_from_garena(access_token)
        if user_info:
            uid = user_info.get('account_id', uid)
            nickname = user_info.get('nickname', nickname)
            if nickname and nickname != 'Unknown':
                try:
                    nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                except:
                    pass
    
    success, data = get_bind_info(access_token)
    if success and data:
        return jsonify({
            "success": True,
            "uid": uid,
            "nickname": nickname,
            "data": {
                "current_email": data.get("email", "Chưa có"),
                "pending_email": data.get("email_to_be", "Chưa có"),
                "countdown": data.get("request_exec_countdown", 0),
                "result": data.get("result", -1)
            }
        })
    else:
        return jsonify({"success": False, "error": "Failed to get bind info"})

@app.route('/gettoken', methods=['GET'])
def api_gettoken():
    uid = request.args.get('uid')
    password = request.args.get('pass')
    
    if not uid or not password:
        return jsonify({"success": False, "error": "Missing uid or pass"})
    if not uid.isdigit():
        return jsonify({"success": False, "error": "UID phải là số"})
    
    success, result = get_access_token(uid, password)
    if success:
        return jsonify({
            "success": True,
            "uid": uid,
            "nickname": result.get("nickname", "Unknown"),
            "access_token": result.get("access_token"),
            "open_id": result.get("open_id", "")
        })
    else:
        return jsonify({"success": False, "error": result})

@app.route('/checkinfo', methods=['GET'])
def api_checkinfo():
    uid = request.args.get('uid')
    if not uid:
        return jsonify({"success": False, "error": "Missing uid"})
    if not uid.isdigit():
        return jsonify({"success": False, "error": "UID phải là số"})
    
    success, data = get_uid_info(uid)
    if success and data:
        basic = data.get('basicInfo', {})
        clan = data.get('clanBasicInfo', {})
        return jsonify({
            "success": True,
            "nickname": basic.get('nickname', 'N/A'),
            "uid": basic.get('accountId', uid),
            "level": basic.get('level', 'N/A'),
            "rank": basic.get('rank', 'N/A'),
            "clan": clan.get('clanName', 'Chưa có quân đoàn'),
            "data": data
        })
    else:
        return jsonify({"success": False, "error": "Không tìm thấy thông tin!"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

