from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import base64
import json
import os
import urllib.parse
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

# ============================================================
# HÀM LẤY THÔNG TIN NGƯỜI CHƠI
# ============================================================

def get_player_info(access_token):
    """Lấy UID, Nickname, Region từ access_token qua API Garena"""
    try:
        player_url = f"https://api-otrss.garena.com/support/callback/?access_token={access_token}"
        player_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        
        p_res = requests.get(player_url, headers=player_headers, timeout=15, allow_redirects=True)
        parsed_url = urllib.parse.urlparse(p_res.url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        uid = query_params.get("account_id", ["Unknown"])[0]
        nickname = query_params.get("nickname", ["Unknown"])[0]
        region = query_params.get("region", ["Unknown"])[0]
        
        return uid, nickname, region
    except Exception as e:
        print(f"Error getting player info: {e}")
        return "N/A", "Unknown", "N/A"

# ============================================================
# API 1: EAT → ACCESS TOKEN
# ============================================================

@app.route('/eat2token', methods=['GET'])
def api_eat_to_token():
    eat_token = request.args.get('eat')
    
    if not eat_token:
        return jsonify({
            "success": False,
            "error": "Missing eat token",
            "usage": "/eat2token?eat=YOUR_EAT_TOKEN"
        })
    
    try:
        api_url = f"https://api-otrss.garena.com/support/callback/?access_token={eat_token}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
        }
        
        response = requests.get(api_url, headers=headers, allow_redirects=True, timeout=15)
        parsed_final = urllib.parse.urlparse(response.url)
        final_params = urllib.parse.parse_qs(parsed_final.query)
        
        if 'access_token' in final_params:
            access_token = final_params['access_token'][0]
            account_id = final_params.get('account_id', ['Unknown'])[0]
            nickname = final_params.get('nickname', ['Unknown'])[0]
            region = final_params.get('region', ['Unknown'])[0]
            
            return jsonify({
                "success": True,
                "access_token": access_token,
                "account_id": account_id,
                "nickname": urllib.parse.unquote(nickname),
                "region": region
            })
        else:
            return jsonify({
                "success": False,
                "error": "Access token not found. Token might be expired or invalid."
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# ============================================================
# API 2: REVOKE ACCESS TOKEN
# ============================================================

@app.route('/revoke', methods=['GET'])
def api_revoke_token():
    access_token = request.args.get('token')
    
    if not access_token:
        return jsonify({
            "success": False,
            "error": "Missing token",
            "usage": "/revoke?token=YOUR_ACCESS_TOKEN"
        })
    
    # Kiểm tra token có hợp lệ không
    api_url = f"https://api-otrss.garena.com/support/callback/?access_token={access_token}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    nickname = "Unknown"
    account_id = "Unknown"
    region = "Unknown"
    is_valid = False
    
    try:
        res = requests.get(api_url, headers=headers, allow_redirects=True, timeout=15)
        parsed = urllib.parse.urlparse(res.url)
        params = urllib.parse.parse_qs(parsed.query)
        
        if 'access_token' in params:
            is_valid = True
            nickname = urllib.parse.unquote(params.get('nickname', ['Unknown'])[0])
            account_id = params.get('account_id', ['Unknown'])[0]
            region = params.get('region', ['Unknown'])[0]
    except Exception:
        pass
    
    if not is_valid:
        return jsonify({
            "success": False,
            "error": "Token is already invalid, expired, or revoked!"
        })
    
    # Revoke token
    refresh_token = "1380dcb63ab3a077dc05bdf0b25ba4497c403a5b4eae96d7203010eafa6c83a8"
    logout_url = f"https://100067.connect.garena.com/oauth/logout?access_token={access_token}&refresh_token={refresh_token}"
    
    try:
        logout_res = requests.get(logout_url, headers=headers, timeout=15)
        
        if logout_res.status_code == 200 and "error" not in logout_res.text:
            return jsonify({
                "success": True,
                "nickname": nickname,
                "account_id": account_id,
                "region": region,
                "message": "Successfully logged out & revoked!"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to revoke token! Server responded with an error."
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# ============================================================
# API 3: ACCESS TOKEN → JWT
# ============================================================

@app.route('/access2jwt', methods=['GET'])
def api_access_to_jwt():
    access_token = request.args.get('token')
    
    if not access_token:
        return jsonify({
            "success": False,
            "error": "Missing token",
            "usage": "/access2jwt?token=YOUR_ACCESS_TOKEN"
        })
    
    try:
        url = f"https://jwt-system-ff.vercel.app/access_to_jwt?access_token={access_token}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                return jsonify({
                    "success": True,
                    "uid": data.get('uid'),
                    "nickname": data.get('nickname'),
                    "region": data.get('lock_region'),
                    "platform": data.get('platform_name'),
                    "open_id": data.get('open_id'),
                    "jwt_token": data.get('jwt_token'),
                    "credits": data.get('credits', {})
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "API returned success=False"
                })
        else:
            return jsonify({
                "success": False,
                "error": f"Server error! HTTP Status: {response.status_code}"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# ============================================================
# API 4: BIND INFO (CŨ)
# ============================================================

@app.route('/bindinfo', methods=['GET'])
def api_bindinfo():
    access_token = request.args.get('token')
    show_raw = request.args.get('raw', 'false').lower() == 'true'
    
    if not access_token:
        return jsonify({
            "success": False,
            "error": "Missing token",
            "usage": "/bindinfo?token=YOUR_ACCESS_TOKEN"
        })
    
    uid, nickname, region = get_player_info(access_token)
    
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
            
            email = data.get("email", "")
            email_to_be = data.get("email_to_be", "")
            countdown = data.get("request_exec_countdown", 0)
            result_code = data.get("result", -1)
            
            if email == "" and email_to_be != "":
                status = f"Chờ xác nhận email: {email_to_be}"
            elif email != "" and email_to_be == "":
                status = f"Email đã xác nhận: {email}"
            elif email == "" and email_to_be == "":
                status = "Chưa có email khôi phục"
            else:
                status = f"Email: {email}, Chờ: {email_to_be}"
            
            response_data = {
                "success": True,
                "uid": uid,
                "nickname": nickname,
                "region": region,
                "data": {
                    "current_email": email if email else "Chưa có",
                    "pending_email": email_to_be if email_to_be else "Chưa có",
                    "countdown": countdown,
                    "result_code": result_code,
                    "result_text": "Thành công" if result_code == 0 else f"Thất bại (Code: {result_code})",
                    "status": status
                }
            }
            
            if show_raw:
                response_data["data"]["raw"] = data
            
            return jsonify(response_data)
        else:
            return jsonify({
                "success": False,
                "uid": uid,
                "nickname": nickname,
                "region": region,
                "error": f"API Error: {response.status_code}"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "uid": uid,
            "nickname": nickname,
            "region": region,
            "error": str(e)
        })

# ============================================================
# API 5: CHECK INFO UID
# ============================================================

@app.route('/checkinfo', methods=['GET'])
def api_checkinfo():
    uid = request.args.get('uid')
    
    if not uid:
        return jsonify({
            "success": False,
            "error": "Missing uid",
            "usage": "/checkinfo?uid=YOUR_UID"
        })
    
    if not uid.isdigit():
        return jsonify({
            "success": False,
            "error": "UID phải là số"
        })
    
    try:
        url = f"https://info-bb20.onrender.com/info?uid={uid}"
        resp = requests.get(url, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            basic = data.get('basicInfo', {})
            clan = data.get('clanBasicInfo', {})
            
            return jsonify({
                "success": True,
                "nickname": basic.get('nickname', 'N/A'),
                "uid": basic.get('accountId', uid),
                "level": basic.get('level', 'N/A'),
                "rank": basic.get('rank', 'N/A'),
                "clan": clan.get('clanName', 'Chưa có'),
                "data": data
            })
        else:
            return jsonify({
                "success": False,
                "error": "Không thể lấy thông tin"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# ============================================================
# API 6: TEST
# ============================================================

@app.route('/test', methods=['GET'])
def test():
    return jsonify({
        "status": "ok",
        "message": "API đang hoạt động!",
        "endpoints": {
            "eat2token": "/eat2token?eat=YOUR_EAT_TOKEN",
            "revoke": "/revoke?token=YOUR_ACCESS_TOKEN",
            "access2jwt": "/access2jwt?token=YOUR_ACCESS_TOKEN",
            "bindinfo": "/bindinfo?token=YOUR_ACCESS_TOKEN",
            "checkinfo": "/checkinfo?uid=YOUR_UID"
        }
    })

# ============================================================
# TRANG CHỦ
# ============================================================

@app.route('/')
def index():
    try:
        return send_file('index.html')
    except:
        return '''
        <h1>🔥 ZAN FULL API</h1>
        <p>API đang hoạt động!</p>
        <hr>
        <h3>📌 Các endpoint:</h3>
        <ul>
            <li><b>/eat2token?eat=YOUR_EAT</b> - Chuyển EAT → Access Token</li>
            <li><b>/revoke?token=YOUR_TOKEN</b> - Thu hồi Access Token</li>
            <li><b>/access2jwt?token=YOUR_TOKEN</b> - Access Token → JWT</li>
            <li><b>/bindinfo?token=YOUR_TOKEN</b> - Kiểm tra bind email</li>
            <li><b>/checkinfo?uid=YOUR_UID</b> - Tra cứu thông tin UID</li>
            <li><b>/test</b> - Kiểm tra API</li>
        </ul>
        <hr>
        <p>© 2026 Zan Full API</p>
        '''

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
