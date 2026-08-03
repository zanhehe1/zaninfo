from flask import Flask, request, jsonify
import requests

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
# QUAN TRỌNG: Vercel/Render yêu cầu biến handler
# ============================================
handler = app
