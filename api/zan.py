from flask import Flask, request, jsonify
import requests
import base64
import json

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
                "likes": data.get("likes", 0),
                "is_banned": data.get("is_banned", 0)
            })
        return jsonify({"success": False, "error": "Cannot fetch"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# API 2: /gettoken - Lấy Access Token chi tiết
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
        # ====== 1. LOGIN LẤY TOKEN ======
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
        
        if response.status_code != 200:
            return jsonify({
                "success": False,
                "error": f"Login failed: {response.status_code}"
            }), response.status_code
        
        result = response.json()
        access_token = result.get("access_token")
        open_id = result.get("open_id")
        uid_return = result.get("uid", uid)
        
        if not access_token:
            return jsonify({
                "success": False,
                "error": "Sai UID hoặc mật khẩu"
            }), 401
        
        # ====== 2. DECODE JWT LẤY THÔNG TIN ======
        jwt_info = {}
        nickname = "N/A"
        
        try:
            parts = access_token.split('.')
            if len(parts) >= 2:
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                jwt_data = json.loads(decoded)
                
                nickname = jwt_data.get("nickname", "N/A")
                if nickname and nickname != "N/A":
                    try:
                        nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                    except:
                        pass
                
                jwt_info = {
                    "nickname": nickname,
                    "account_id": jwt_data.get("account_id", uid_return),
                    "region": jwt_data.get("lock_region", "VN"),
                    "client_version": jwt_data.get("client_version", "N/A"),
                    "create_time": jwt_data.get("create_time", "N/A"),
                    "expiry_time": jwt_data.get("expiry_time", "N/A"),
                }
        except Exception as e:
            jwt_info = {"error": f"Cannot decode JWT: {str(e)}"}
        
        # ====== 3. LẤY THÔNG TIN BỔ SUNG ======
        extra_info = {}
        try:
            url_info = f"https://ff.garena.com/api/antihack/check_banned?lang=vi&uid={uid_return}"
            r = requests.get(url_info, headers={"Accept": "application/json"}, timeout=10)
            if r.status_code == 200:
                data_info = r.json().get("data", {})
                extra_info = {
                    "level": data_info.get("level", "N/A"),
                    "rank": data_info.get("rank", "N/A"),
                    "likes": data_info.get("likes", 0),
                    "is_banned": data_info.get("is_banned", 0)
                }
        except:
            pass
        
        # ====== 4. TRẢ VỀ JSON ĐẦY ĐỦ ======
        return jsonify({
            "success": True,
            "data": {
                "uid": uid_return,
                "open_id": open_id,
                "access_token": access_token,
                "jwt_decoded": jwt_info,
                "player_info": extra_info
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================
# QUAN TRỌNG: Vercel/Render yêu cầu biến handler
# ============================================
handler = app
