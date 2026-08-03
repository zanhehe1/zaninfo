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


# ============================================
# QUAN TRỌNG: Vercel/Render yêu cầu biến handler
# ============================================
handler = app
