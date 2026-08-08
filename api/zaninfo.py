from flask import Flask, request, jsonify
import requests
import base64
import json
import time
import urllib.parse
from datetime import datetime

app = Flask(__name__)

# ============================================
# API 1: /zaninfo - Lấy thông tin Free Fire
# ============================================
@app.route('/zaninfo')
def zan_info():
    uid = request.args.get('uid')
    if not uid or not uid.isdigit():
        return jsonify({"success": False, "error": "Invalid uid"}), 400
    
    try:
        url = f"https://ff.garena.com/api/antihack/check_banned?lang=vi&uid={uid}"
        headers = {
            "Accept": "application/json",
            "x-requested-with": "B6FksShzIgjfrYImLpTsadjS86sddhFH"
        }
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json().get("data", {})
            return jsonify({
                "success": True,
                "uid": uid,
                "nickname": data.get("nickname", "N/A"),
                "level": data.get("level", "N/A"),
                "rank": data.get("rank", "N/A"),
                "region": data.get("region", "VN"),
                "is_banned": data.get("is_banned", 0)
            })
        return jsonify({"success": False, "error": "Cannot fetch"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# API 2: /gettoken - Lấy Access Token
# ============================================
@app.route('/gettoken')
def get_token():
    uid = request.args.get('uid')
    password = request.args.get('pass')
    
    if not uid or not password:
        return jsonify({
            "success": False,
            "error": "Missing uid or password"
        }), 400
    
    if not uid.isdigit():
        return jsonify({
            "success": False,
            "error": "UID phải là số"
        }), 400
    
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
                return jsonify({
                    "success": True,
                    "uid": uid,
                    "access_token": access_token,
                    "open_id": open_id
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Sai UID hoặc mật khẩu"
                }), 401
        else:
            return jsonify({
                "success": False,
                "error": f"Login failed: {response.status_code}"
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================
# API 3: /bindinfo - Check bind info
# ============================================
@app.route('/bindinfo')
def bind_info():
    access_token = request.args.get('token')
    if not access_token:
        return jsonify({"success": False, "error": "Missing token"}), 400
    
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
            return jsonify({
                "success": True,
                "data": {
                    "current_email": data.get("email", ""),
                    "pending_email": data.get("email_to_be", ""),
                    "countdown": data.get("request_exec_countdown", 0),
                    "result": data.get("result", -1)
                }
            })
        else:
            return jsonify({"success": False, "error": f"HTTP {response.status_code}"}), response.status_code
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# API 4: /eattotoken - EAT to Access Token
# ============================================
@app.route('/eattotoken')
def eat_to_token():
    eat = request.args.get('eat')
    if not eat:
        return jsonify({"success": False, "error": "Missing eat token"}), 400
    
    try:
        url = f"https://api-otrss.garena.com/support/callback/?access_token={eat}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        parsed = urllib.parse.urlparse(response.url)
        params = urllib.parse.parse_qs(parsed.query)
        
        if 'access_token' in params:
            return jsonify({
                "success": True,
                "access_token": params['access_token'][0],
                "account_id": params.get('account_id', ['Unknown'])[0],
                "nickname": urllib.parse.unquote(params.get('nickname', ['Unknown'])[0]),
                "region": params.get('region', ['Unknown'])[0]
            })
        else:
            return jsonify({"success": False, "error": "No access_token found"}), 400
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# API 5: /loginhistory - Get login history
# ============================================
@app.route('/loginhistory')
def login_history():
    token = request.args.get('token')
    if not token:
        return jsonify({"success": False, "error": "Missing token"}), 400
    
    try:
        # Gọi API GetLoginHistory trực tiếp
        headers = {
            "Expect": "100-continue",
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Host": "client.ind.freefiremobile.com",
            "Connection": "close"
        }
        
        resp = requests.post("https://client.ind.freefiremobile.com/GetLoginHistory", headers=headers, data=b"", timeout=15)
        
        if resp.status_code == 200:
            # Parse history (raw hex)
            return jsonify({
                "success": True,
                "data": {
                    "raw_hex": resp.content.hex(),
                    "raw_base64": base64.b64encode(resp.content).decode()
                }
            })
        else:
            return jsonify({"success": False, "error": f"History failed: {resp.status_code}"}), resp.status_code
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/chui', methods=['GET', 'POST'])
def chui_ai():
    # Lấy msg từ request (GET, POST JSON, POST Form)
    if request.method == 'GET':
        msg = request.args.get('msg')
    else:
        msg = request.json.get('msg') if request.json else request.form.get('msg')
    
    if not msg:
        return jsonify({"error": "Mày nhập gì vô coi"}), 400
    
    try:
        # URL chứa danh sách các câu chửi
        url_chui = "https://raw.githubusercontent.com/ehvuebe-png/Cailontaone/main/chui.txt"
        
        # Gửi request để lấy nội dung file
        response_chui = requests.get(url_chui, timeout=15)
        
        # Kiểm tra xem tải thành công không
        if response_chui.status_code == 200:
            # Tách nội dung thành các dòng, bỏ qua dòng trống
            danh_sach_chui = [line.strip() for line in response_chui.text.splitlines() if line.strip()]
            
            if danh_sach_chui:
                # Chọn ngẫu nhiên 1 câu
                ai_chui_lai = random.choice(danh_sach_chui)
            else:
                # Fallback nếu file rỗng
                ai_chui_lai = "Mày hỏi ngu vãi! 😡"
        else:
            # Fallback nếu không tải được file
            fallback = [
                "Mày hỏi ngu vãi! 😡",
                "Địt mẹ mày, câu hỏi gì thế? 🤬",
                "Đi chỗ khác chơi đi ku! 😤",
                "Tao đang bận chửi đứa khác! 😒"
            ]
            ai_chui_lai = random.choice(fallback)

        # Trả về kết quả
        return jsonify({
            "success": True,
            "may_chui": msg,
            "ai_chui_lai": ai_chui_lai
        })
        
    except Exception as e:
        return jsonify({"error": f"Lỗi server: {str(e)}"}), 500
        
# ============================================
# API 6: /band - Ban account
# ============================================
@app.route('/band', methods=['GET'])
def band_account():
    access_token = request.args.get('access_token')
    
    if not access_token:
        return jsonify({
            "success": False,
            "error": "Missing access_token",
            "example": "/band?access_token=xxx"
        }), 400
    
    result = ban_account(access_token)
    return jsonify(result)


# ============================================
# API 7: /band3day - Ban 3 days
# ============================================
@app.route('/band3day', methods=['GET'])
def band_3day():
    access_token = request.args.get('access_token')
    
    if not access_token:
        return jsonify({
            "success": False,
            "error": "Missing access_token",
            "example": "/band3day?access_token=xxx"
        }), 400
    
    result = ban_account(access_token)
    
    if result.get('success'):
        result['ban_duration'] = '3 days'
        result['message'] = 'Ban 3 days Successfully!'
    
    return jsonify(result)


# ============================================
# HÀM BAN ACCOUNT
# ============================================
def ban_account(access_token):
    try:
        # ====== CHECK TOKEN ======
        inspect_url = f"https://100067.connect.garena.com/oauth/token/inspect?token={access_token}"
        inspect_headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "100067.connect.garena.com",
            "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)"
        }
        
        resp = requests.get(inspect_url, headers=inspect_headers, timeout=10)
        data = resp.json()
        if 'error' in data:
            return {"success": False, "error": f"Token error: {data.get('error')}"}
        
        NEW_OPEN_ID = data.get('open_id')
        platform_ = data.get('platform')
        
        # ====== MAJOR LOGIN ======
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        
        MajorLogin_url = "https://loginbp.ggpolarbear.com/MajorLogin"
        MajorLogin_headers = {
            "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-GA": "v1 1",
            "X-Unity-Version": "2022.3.47f1",
            "ReleaseVersion": "OB54"
        }
        
        # Tạo payload login
        payload = bytearray()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Encode string fields
        def encode_string(field_num, value):
            if isinstance(value, str):
                value = value.encode('utf-8')
            result = bytearray()
            # Simple protobuf encoding (tag + length + value)
            result.append((field_num << 3) | 2)
            # Length
            length = len(value)
            if length < 128:
                result.append(length)
            else:
                while length > 0:
                    result.append((length & 0x7F) | 0x80)
                    length >>= 7
            result.extend(value)
            return bytes(result)
        
        def encode_int(field_num, value):
            result = bytearray()
            result.append((field_num << 3) | 0)
            # Varint encoding
            while value > 0x7F:
                result.append((value & 0x7F) | 0x80)
                value >>= 7
            result.append(value & 0x7F)
            return bytes(result)
        
        # Build payload
        payload.extend(encode_string(3, current_time))
        payload.extend(encode_string(4, 'free fire'))
        payload.extend(encode_int(5, 1))
        payload.extend(encode_string(7, '1.128.9'))
        payload.extend(encode_string(8, 'Android OS 12 / API-31'))
        payload.extend(encode_string(9, 'Handheld'))
        payload.extend(encode_string(10, 'O2'))
        payload.extend(encode_string(11, 'WIFI'))
        payload.extend(encode_int(12, 1666))
        payload.extend(encode_int(13, 750))
        payload.extend(encode_string(14, '440'))
        payload.extend(encode_string(15, 'ARM64 FP ASIMD AES | 2600 | 8'))
        payload.extend(encode_int(16, 5479))
        payload.extend(encode_string(17, 'Mali-G57 MC5'))
        payload.extend(encode_string(18, 'OpenGL ES 3.2'))
        payload.extend(encode_string(19, 'Google|21cd1993-491c-45f0-9aee-f4bf86b9245b'))
        payload.extend(encode_string(20, '192.168.1.100'))
        payload.extend(encode_string(21, 'vi'))
        payload.extend(encode_string(22, NEW_OPEN_ID))
        payload.extend(encode_string(23, str(platform_)))
        payload.extend(encode_string(24, 'Handheld'))
        payload.extend(encode_string(25, 'Xiaomi M2004J7AC'))
        payload.extend(encode_string(29, access_token))
        payload.extend(encode_int(30, 1))
        payload.extend(encode_string(41, 'O2'))
        payload.extend(encode_string(42, 'WIFI'))
        payload.extend(encode_string(57, '7428b253defc164018c604a1ebbfebdf'))
        payload.extend(encode_int(60, 48520))
        payload.extend(encode_int(61, 28119))
        payload.extend(encode_int(62, 4498))
        payload.extend(encode_int(63, 0))
        payload.extend(encode_int(64, 28263))
        payload.extend(encode_int(65, 48520))
        payload.extend(encode_int(66, 28263))
        payload.extend(encode_int(67, 48520))
        payload.extend(encode_int(73, 2))
        payload.extend(encode_string(74, '/data/app/~~iMOsnrV6G19kswoTGJGYgQ==/lib/arm64'))
        payload.extend(encode_int(76, 1))
        payload.extend(encode_string(77, '17e6a447803a17e4f59e3fd734efc5ae|/base.apk'))
        payload.extend(encode_int(78, 3))
        payload.extend(encode_int(79, 2))
        payload.extend(encode_string(81, '64'))
        payload.extend(encode_string(83, '2019120270'))
        payload.extend(encode_int(85, 3))
        payload.extend(encode_string(86, 'OpenGLES2'))
        payload.extend(encode_int(87, 255))
        payload.extend(encode_int(88, 4))
        payload.extend(encode_string(90, 'Ha Noi'))
        payload.extend(encode_string(91, '22'))
        payload.extend(encode_int(92, 4275))
        payload.extend(encode_string(93, 'android'))
        payload.extend(encode_string(94, 'KqsHT2CnbP+CILeOnb+OUB8t2RSH3z76xfxPgY7My2napifnqTdAvVbbxUjA1J8kEj6yUng+sn/m+Bl6rX6Gv+tto7A='))
        payload.extend(encode_int(95, 111207))
        payload.extend(encode_int(97, 1))
        payload.extend(encode_int(98, 1))
        payload.extend(encode_string(99, str(platform_)))
        payload.extend(encode_string(100, str(platform_)))
        payload.extend(encode_int(101, 1))
        payload.extend(encode_string(102, 'GLAVY\x09\x04N\x01\x0c\x13\x0f\x04@^A9YS\x0fP[=\x0fQ[nR\t<\nT2'))
        payload.extend(encode_int(103, 1))
        payload.extend(encode_int(104, 0))
        
        # Encrypt payload
        from Crypto.Util.Padding import pad
        cipher = AES.new(key, AES.MODE_CBC, iv)
        enc_data = cipher.encrypt(pad(bytes(payload), AES.block_size))
        
        response = requests.post(MajorLogin_url, headers=MajorLogin_headers, data=enc_data, timeout=15)
        if response.status_code != 200:
            return {"success": False, "error": f"MajorLogin error: {response.status_code}"}
        
        # Parse response
        from Crypto.Util.Padding import unpad
        cipher_resp = AES.new(key, AES.MODE_CBC, iv)
        try:
            resp_dec = unpad(cipher_resp.decrypt(response.content), 16)
        except:
            resp_dec = response.content
        
        # Extract JWT
        import re
        jwt_match = re.search(rb'account_jwt:\s*"([^"]+)"', resp_dec)
        if not jwt_match:
            return {"success": False, "error": "No JWT found"}
        
        account_jwt = jwt_match.group(1).decode()
        
        # Extract key and iv
        key_match = re.search(rb'key:\s*"([^"]+)"', resp_dec)
        iv_match = re.search(rb'iv:\s*"([^"]+)"', resp_dec)
        
        if not key_match or not iv_match:
            return {"success": False, "error": "No key/iv found"}
        
        aes_key = bytes.fromhex(key_match.group(1).decode())
        aes_iv = bytes.fromhex(iv_match.group(1).decode())
        
        # ====== GET LOGIN DATA ======
        GetLoginData_resURL = "https://clientbp.ggpolarbear.com/GetLoginData"
        GetLoginData_res_headers = {
            'Authorization': f'Bearer {account_jwt}',
            'X-Unity-Version': '2018.4.11f1',
            'X-GA': 'v1 1',
            'ReleaseVersion': 'OB54',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Accept-Encoding': 'gzip, deflate, br',
        }
        
        r2 = requests.post(GetLoginData_resURL, headers=GetLoginData_res_headers, data=enc_data, timeout=12, verify=False)
        if r2.status_code != 200:
            return {"success": False, "error": f"GetLoginData error: {r2.status_code}"}
        
        # ====== GET IP:PORT ======
        x = r2.content.hex()
        online_ip = None
        online_port = None
        
        # Tìm ip:port trong hex
        import re
        ip_port_match = re.search(r'([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})([0-9]{5})', x)
        if ip_port_match:
            online_ip = ip_port_match.group(1)
            online_port = int(ip_port_match.group(2))
        else:
            return {"success": False, "error": "Could not find server address"}
        
        # ====== BUILD BAN PACKET ======
        def encrypt_packet(hex_string: str, aes_key, aes_iv) -> str:
            if isinstance(aes_key, str):
                aes_key = bytes.fromhex(aes_key)
            if isinstance(aes_iv, str):
                aes_iv = bytes.fromhex(aes_iv)   
            data = bytes.fromhex(hex_string)
            cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
            encrypted = cipher.encrypt(pad(data, AES.block_size))
            return encrypted.hex()
        
        def build_start_packet(account_id: int, timestamp: int, jwt: str, key, iv) -> str:
            try:
                encrypted = encrypt_packet(jwt.encode().hex(), key, iv)
                head_len = hex(len(encrypted) // 2)[2:]
                ide_hex = hex(int(account_id))[2:]
                zeros = "0" * (16 - len(ide_hex))
                timestamp_hex = hex(timestamp)[2:].zfill(2)
                head = f"0115{zeros}{ide_hex}{timestamp_hex}00000{head_len}"
                start_packet = head + encrypted        
                return start_packet
            except Exception as e:
                return None
        
        def send_once(remote_ip, remote_port, payload_bytes, recv_timeout=3.0):
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(recv_timeout)
            try:
                s.connect((remote_ip, remote_port))
                s.sendall(payload_bytes)        
                chunks = []
                try:
                    while True:
                        chunk = s.recv(4096)
                        if not chunk:
                            break
                        chunks.append(chunk)
                except socket.timeout:
                    pass
                return b"".join(chunks)
            finally:
                s.close()
        
        # Decode JWT payload
        jwt_parts = account_jwt.split('.')
        if len(jwt_parts) < 2:
            return {"success": False, "error": "Invalid JWT"}
        
        payload_b64 = jwt_parts[1]
        rem = len(payload_b64) % 4
        if rem:
            payload_b64 += '=' * (4 - rem)
        jwt_payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode('utf-8', errors='ignore'))
        
        account_id = int(jwt_payload.get("account_id", 0))
        timestamp = int(time.time())
        
        final_token_hex = build_start_packet(
            account_id=account_id,
            timestamp=timestamp,
            jwt=account_jwt,
            key=aes_key,
            iv=aes_iv
        )
        
        if not final_token_hex:
            return {"success": False, "error": "Failed to build packet"}
        
        # ====== SEND BAN ======
        payload_bytes = bytes.fromhex(final_token_hex)
        response = send_once(online_ip, online_port, payload_bytes, recv_timeout=5.0)
        
        if response:
            return {"success": True, "message": "Ban Successfully!"}
        else:
            return {"success": False, "error": "No response from server"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================
# QUAN TRỌNG: Vercel/Render yêu cầu biến handler
# ============================================
handler = app
