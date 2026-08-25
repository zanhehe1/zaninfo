from flask import Flask, request, jsonify
import requests
import json
import os
import time
import urllib3

# Import từ byte.py
from byte import EnC_AEs, Encrypt_ID, Ua, SendFriendRequest_HTTP

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8080))

# ==================== HÀM LẤY TOKEN ====================
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
    
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)
            if response.status_code == 200:
                return response.json().get("access_token"), response.json().get("open_id")
        except:
            time.sleep(1)
    return None, None

# ==================== API ====================

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "service": "Free Fire Friend Request API",
        "endpoints": {
            "/kb": "GET - Gửi kết bạn (dùng browser)",
            "/send": "POST - Gửi kết bạn",
            "/health": "GET - Kiểm tra"
        },
        "example": {
            "GET": "/kb?uid=123456789&password=abc&target=987654321",
            "POST": '{"uid":"123456789","password":"abc","target_uid":"987654321"}'
        }
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok", "timestamp": time.time()})

@app.route('/kb', methods=['GET'])
def kb_get():
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
        
        access_token, open_id = get_access_token(str(uid), str(password))
        if not access_token:
            return jsonify({
                "success": False,
                "error": "Sai UID hoặc Password"
            }), 400
        
        success, message = SendFriendRequest_HTTP(str(target), access_token, str(uid))
        
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
                "error": "Sai UID hoặc Password"
            }), 400
        
        success, message = SendFriendRequest_HTTP(str(target_uid), access_token, str(uid))
        
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

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 FREE FIRE FRIEND REQUEST API")
    print("=" * 50)
    print(f"📡 Port: {PORT}")
    print(f"📍 Endpoints:")
    print(f"   GET  /        - Home")
    print(f"   GET  /health  - Health check")
    print(f"   GET  /kb      - Gửi kết bạn (GET)")
    print(f"   POST /send    - Gửi kết bạn (POST)")
    print("=" * 50)
    print("📌 Ví dụ GET:")
    print("   /kb?uid=123456789&password=abc&target=987654321")
    print("=" * 50)
    
    app.run(host="0.0.0.0", port=PORT, debug=False)
