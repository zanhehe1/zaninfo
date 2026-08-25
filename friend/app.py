from flask import Flask, request, jsonify
import requests
import json
import os
import time
import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ==================== CẤU HÌNH ====================
PORT = int(os.environ.get("PORT", 8080))

# ==================== AES KEY ====================
Key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
Iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# ==================== HÀM MÃ HÓA ====================
def EnC_AEs(HeX):
    cipher = AES.new(Key, AES.MODE_CBC, Iv)
    return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()

def EnC_Vr(N):
    if N < 0: return b''
    H = []
    while True:
        BesTo = N & 0x7F
        N >>= 7
        if N: BesTo |= 0x80
        H.append(BesTo)
        if not N: break
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
    if len(F) == 1: F = "0" + F
    return F

def Encrypt_ID(x):
    dec = ['80','81','82','83','84','85','86','87','88','89','8a','8b','8c','8d','8e','8f','90','91',
           '92','93','94','95','96','97','98','99','9a','9b','9c','9d','9e','9f','a0','a1','a2','a3',
           'a4','a5','a6','a7','a8','a9','aa','ab','ac','ad','ae','af','b0','b1','b2','b3','b4','b5',
           'b6','b7','b8','b9','ba','bb','bc','bd','be','bf','c0','c1','c2','c3','c4','c5','c6','c7',
           'c8','c9','ca','cb','cc','cd','ce','cf','d0','d1','d2','d3','d4','d5','d6','d7','d8','d9',
           'da','db','dc','dd','de','df','e0','e1','e2','e3','e4','e5','e6','e7','e8','e9','ea','eb',
           'ec','ed','ee','ef','f0','f1','f2','f3','f4','f5','f6','f7','f8','f9','fa','fb','fc','fd',
           'fe','ff']
    xxx = ['1','01','02','03','04','05','06','07','08','09','0a','0b','0c','0d','0e','0f','10','11',
           '12','13','14','15','16','17','18','19','1a','1b','1c','1d','1e','1f','20','21','22','23',
           '24','25','26','27','28','29','2a','2b','2c','2d','2e','2f','30','31','32','33','34','35',
           '36','37','38','39','3a','3b','3c','3d','3e','3f','40','41','42','43','44','45','46','47',
           '48','49','4a','4b','4c','4d','4e','4f','50','51','52','53','54','55','56','57','58','59',
           '5a','5b','5c','5d','5e','5f','60','61','62','63','64','65','66','67','68','69','6a','6b',
           '6c','6d','6e','6f','70','71','72','73','74','75','76','77','78','79','7a','7b','7c','7d',
           '7e','7f']
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
    except:
        return None

# ==================== HÀM LẤY TOKEN ====================
def get_access_token(uid, password):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": "GarenaMSDK/4.0.19P9(SM-S908E; Android 13; en; VN)",
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
        response = requests.post(url, headers=headers, data=data, timeout=10)
        if response.status_code == 200:
            return response.json().get("access_token"), response.json().get("open_id")
    except:
        pass
    return None, None

# ==================== HÀM GỬI KẾT BẠN ====================
def send_friend_request(target_uid, token):
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
        return False, "Mã hóa UID thất bại"
    
    plain_text_payload = f'08a7c4839f1e10{encrypted_id}1801'
    data = bytes.fromhex(EnC_AEs(plain_text_payload))
    
    domains = [
        'https://clientbp.ggpolarbear.com/RequestAddingFriend',
        'https://clientbp.ggwhitehawk.com/RequestAddingFriend',
        'https://clientbp.ggpbn.com/RequestAddingFriend',
    ]
    
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
            elif 'BR_FRIEND_ALREADY_FRIEND' in text:
                return False, "Đã là bạn bè!"
        except:
            continue
    
    return False, "Không kết nối được server"

# ==================== API ====================

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Free Fire Friend Request API",
        "endpoints": {
            "/kb": "GET - Gửi kết bạn (dùng trên browser)",
            "/send": "POST - Gửi kết bạn",
            "/send_bulk": "POST - Gửi hàng loạt",
            "/health": "GET - Kiểm tra",
            "/login": "POST - Kiểm tra đăng nhập"
        },
        "example": {
            "GET": "/kb?uid=123456789&password=abc&target=987654321",
            "POST": {"uid": "123456789", "password": "abc", "target_uid": "987654321"}
        }
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})

# ==================== API /kb (GET - DÙNG TRÊN CHROME) ====================
@app.route('/kb', methods=['GET'])
def kb_get():
    """Gửi kết bạn qua GET request (dùng trên Chrome)"""
    try:
        uid = request.args.get('uid')
        password = request.args.get('password')
        target = request.args.get('target')
        
        if not uid:
            return jsonify({"success": False, "error": "Thiếu uid"}), 400
        if not password:
            return jsonify({"success": False, "error": "Thiếu password"}), 400
        if not target:
            return jsonify({"success": False, "error": "Thiếu target"}), 400
        
        # Lấy token
        access_token, open_id = get_access_token(str(uid), str(password))
        if not access_token:
            return jsonify({
                "success": False,
                "error": "Sai UID hoặc Password"
            }), 400
        
        # Gửi kết bạn
        success, message = send_friend_request(str(target), access_token)
        
        return jsonify({
            "success": success,
            "message": message,
            "data": {
                "from_uid": str(uid),
                "target_uid": str(target)
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== API /send (POST) ====================
@app.route('/send', methods=['POST'])
def send_friend():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "Vui lòng gửi JSON"}), 400
        
        uid = data.get('uid')
        password = data.get('password')
        target_uid = data.get('target_uid')
        
        if not uid:
            return jsonify({"success": False, "error": "Thiếu uid"}), 400
        if not password:
            return jsonify({"success": False, "error": "Thiếu password"}), 400
        if not target_uid:
            return jsonify({"success": False, "error": "Thiếu target_uid"}), 400
        
        access_token, open_id = get_access_token(str(uid), str(password))
        if not access_token:
            return jsonify({
                "success": False,
                "error": "Không lấy được token, kiểm tra lại UID/PASSWORD"
            }), 400
        
        success, message = send_friend_request(str(target_uid), access_token)
        
        return jsonify({
            "success": success,
            "message": message,
            "data": {
                "from_uid": str(uid),
                "target_uid": str(target_uid)
            }
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== API /send_bulk (POST) ====================
@app.route('/send_bulk', methods=['POST'])
def send_friend_bulk():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "Vui lòng gửi JSON"}), 400
        
        accounts = data.get('accounts', [])
        target_uid = data.get('target_uid')
        
        if not accounts:
            return jsonify({"success": False, "error": "Thiếu danh sách accounts"}), 400
        if not target_uid:
            return jsonify({"success": False, "error": "Thiếu target_uid"}), 400
        
        results = []
        success_count = 0
        fail_count = 0
        
        for acc in accounts:
            uid = acc.get('uid')
            password = acc.get('password')
            
            if not uid or not password:
                results.append({
                    "uid": uid or "unknown",
                    "success": False,
                    "message": "Thiếu uid hoặc password"
                })
                fail_count += 1
                continue
            
            access_token, open_id = get_access_token(str(uid), str(password))
            if not access_token:
                results.append({
                    "uid": str(uid),
                    "success": False,
                    "message": "Không lấy được token"
                })
                fail_count += 1
                continue
            
            success, message = send_friend_request(str(target_uid), access_token)
            
            results.append({
                "uid": str(uid),
                "success": success,
                "message": message
            })
            
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            time.sleep(0.5)
        
        return jsonify({
            "success": True,
            "summary": {
                "total": len(accounts),
                "success": success_count,
                "fail": fail_count
            },
            "results": results
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== API /login (POST) ====================
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        uid = data.get('uid')
        password = data.get('password')
        
        if not uid or not password:
            return jsonify({"success": False, "error": "Thiếu uid hoặc password"}), 400
        
        access_token, open_id = get_access_token(str(uid), str(password))
        
        if access_token:
            return jsonify({
                "success": True,
                "message": "Đăng nhập thành công",
                "data": {
                    "uid": str(uid),
                    "access_token": access_token[:20] + "...",
                    "open_id": open_id
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": "Đăng nhập thất bại, sai UID hoặc password"
            }), 401
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== CHẠY APP ====================
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 FREE FIRE FRIEND REQUEST API")
    print("=" * 50)
    print(f"📡 Port: {PORT}")
    print(f"📍 Endpoints:")
    print(f"   GET  /        - Home")
    print(f"   GET  /health  - Health check")
    print(f"   GET  /kb      - Gửi kết bạn (GET - dùng browser)")
    print(f"   POST /send    - Gửi kết bạn")
    print(f"   POST /send_bulk - Gửi hàng loạt")
    print(f"   POST /login   - Kiểm tra đăng nhập")
    print("=" * 50)
    print("📌 Ví dụ GET:")
    print("   /kb?uid=123456789&password=abc&target=987654321")
    print("=" * 50)
    
    app.run(host="0.0.0.0", port=PORT, debug=False)
