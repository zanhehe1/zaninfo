from flask import Flask, request, jsonify
import requests
import json
import time
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

app = Flask(__name__)

# ====== KEY AES ======
KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# ====== MÃ HÓA ======
def aes_encrypt(data):
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    return cipher.encrypt(pad(data, 16))

def encrypt_id(uid):
    dec = ['80','81','82','83','84','85','86','87','88','89','8a','8b','8c','8d','8e','8f','90','91','92','93','94','95','96','97','98','99','9a','9b','9c','9d','9e','9f','a0','a1','a2','a3','a4','a5','a6','a7','a8','a9','aa','ab','ac','ad','ae','af','b0','b1','b2','b3','b4','b5','b6','b7','b8','b9','ba','bb','bc','bd','be','bf','c0','c1','c2','c3','c4','c5','c6','c7','c8','c9','ca','cb','cc','cd','ce','cf','d0','d1','d2','d3','d4','d5','d6','d7','d8','d9','da','db','dc','dd','de','df','e0','e1','e2','e3','e4','e5','e6','e7','e8','e9','ea','eb','ec','ed','ee','ef','f0','f1','f2','f3','f4','f5','f6','f7','f8','f9','fa','fb','fc','fd','fe','ff']
    xxx = ['1','01','02','03','04','05','06','07','08','09','0a','0b','0c','0d','0e','0f','10','11','12','13','14','15','16','17','18','19','1a','1b','1c','1d','1e','1f','20','21','22','23','24','25','26','27','28','29','2a','2b','2c','2d','2e','2f','30','31','32','33','34','35','36','37','38','39','3a','3b','3c','3d','3e','3f','40','41','42','43','44','45','46','47','48','49','4a','4b','4c','4d','4e','4f','50','51','52','53','54','55','56','57','58','59','5a','5b','5c','5d','5e','5f','60','61','62','63','64','65','66','67','68','69','6a','6b','6c','6d','6e','6f','70','71','72','73','74','75','76','77','78','79','7a','7b','7c','7d','7e','7f']
    try:
        x = int(uid)
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

def encrypt_payload(plain_text):
    plain_text = bytes.fromhex(plain_text)
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    return cipher.encrypt(pad(plain_text, 16))

# ====== LẤY TOKEN ======
def get_access_token(uid, password):
    try:
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        headers = {
            "User-Agent": "GarenaMSDK/4.0.19P9(SM-S908E; Android 13; en; VN)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close",
        }
        data = {
            "uid": str(uid),
            "password": str(password),
            "response_type": "token",
            "client_type": "2",
            "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
            "client_id": "100067",
        }
        resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
        if resp.status_code == 200:
            return resp.json().get('access_token')
        return None
    except:
        return None

# ====== GỬI KẾT BẠN ======
def send_friend_request(token, target_uid):
    encrypted_id = encrypt_id(target_uid)
    if not encrypted_id:
        return {'status': 'error', 'message': 'Mã hóa UID thất bại'}
    
    payload = f"08a7c4839f1e10{encrypted_id}1801"
    encrypted_payload = encrypt_payload(payload)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB54",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dalvik/2.1.0"
    }
    
    response = requests.post(
        "https://clientbp.ggpolarbear.com/RequestAddingFriend",
        data=encrypted_payload,
        headers=headers,
        timeout=10,
        verify=False
    )
    
    if response.status_code == 200:
        return {'status': 'success', 'message': 'Gửi kết bạn thành công!'}
    elif "already friends" in response.text.lower():
        return {'status': 'error', 'message': 'Đã là bạn bè!'}
    elif "blocked" in response.text.lower():
        return {'status': 'error', 'message': 'Bạn đã bị chặn!'}
    else:
        return {'status': 'error', 'message': f'Lỗi: {response.status_code}'}

# ====== XÓA KẾT BẠN ======
def remove_friend_request(token, target_uid):
    encrypted_id = encrypt_id(target_uid)
    if not encrypted_id:
        return {'status': 'error', 'message': 'Mã hóa UID thất bại'}
    
    payload = f"08a7c4839f1e10{encrypted_id}1802"
    encrypted_payload = encrypt_payload(payload)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Unity-Version": "2018.4.11f1",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB54",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Dalvik/2.1.0"
    }
    
    response = requests.post(
        "https://clientbp.ggpolarbear.com/RemoveFriend",
        data=encrypted_payload,
        headers=headers,
        timeout=10,
        verify=False
    )
    
    if response.status_code == 200:
        return {'status': 'success', 'message': 'Xóa kết bạn thành công!'}
    elif "not friend" in response.text.lower():
        return {'status': 'error', 'message': 'Không phải bạn bè!'}
    else:
        return {'status': 'error', 'message': f'Lỗi: {response.status_code}'}

# ====== API HOME ======
@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'name': 'FF Friend API',
        'version': '1.0.0',
        'endpoints': {
            '/add': 'Gửi kết bạn (dùng token)',
            '/remove': 'Xóa kết bạn (dùng token)',
            '/add/uid': 'Gửi kết bạn (dùng UID + Password)',
            '/remove/uid': 'Xóa kết bạn (dùng UID + Password)',
            '/token': 'Lấy token từ UID + Password'
        }
    })

# ====== API: KẾT BẠN BẰNG TOKEN ======
@app.route('/add', methods=['GET'])
def add_friend():
    try:
        token = request.args.get('token')
        target_uid = request.args.get('uid')
        
        if not token or not target_uid:
            return jsonify({'status': 'error', 'message': 'Thiếu token hoặc uid'}), 400
        
        result = send_friend_request(token, target_uid)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ====== API: XÓA KẾT BẠN BẰNG TOKEN ======
@app.route('/remove', methods=['GET'])
def remove_friend():
    try:
        token = request.args.get('token')
        target_uid = request.args.get('uid')
        
        if not token or not target_uid:
            return jsonify({'status': 'error', 'message': 'Thiếu token hoặc uid'}), 400
        
        result = remove_friend_request(token, target_uid)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ====== API: KẾT BẠN BẰNG UID + PASS ======
@app.route('/add/uid', methods=['GET'])
def add_friend_by_uid():
    try:
        uid = request.args.get('uid')
        password = request.args.get('password')
        target_uid = request.args.get('target')
        
        if not uid or not password or not target_uid:
            return jsonify({'status': 'error', 'message': 'Thiếu uid, password hoặc target'}), 400
        
        token = get_access_token(uid, password)
        if not token:
            return jsonify({'status': 'error', 'message': 'Sai UID hoặc mật khẩu'}), 400
        
        result = send_friend_request(token, target_uid)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ====== API: XÓA KẾT BẠN BẰNG UID + PASS ======
@app.route('/remove/uid', methods=['GET'])
def remove_friend_by_uid():
    try:
        uid = request.args.get('uid')
        password = request.args.get('password')
        target_uid = request.args.get('target')
        
        if not uid or not password or not target_uid:
            return jsonify({'status': 'error', 'message': 'Thiếu uid, password hoặc target'}), 400
        
        token = get_access_token(uid, password)
        if not token:
            return jsonify({'status': 'error', 'message': 'Sai UID hoặc mật khẩu'}), 400
        
        result = remove_friend_request(token, target_uid)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ====== API: LẤY TOKEN ======
@app.route('/token', methods=['GET'])
def get_token_api():
    try:
        uid = request.args.get('uid')
        password = request.args.get('password')
        
        if not uid or not password:
            return jsonify({'status': 'error', 'message': 'Thiếu uid hoặc password'}), 400
        
        token = get_access_token(uid, password)
        if not token:
            return jsonify({'status': 'error', 'message': 'Sai UID hoặc mật khẩu'}), 400
        
        return jsonify({'status': 'success', 'access_token': token})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Vercel cần biến app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2010)
