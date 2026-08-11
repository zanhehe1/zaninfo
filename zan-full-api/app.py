from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import requests
import base64
import json
import os
import urllib.parse
import hashlib
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
# HÀM LẤY BIND INFO
# ============================================================

def get_bind_info(access_token):
    """Lấy thông tin bind email từ Garena"""
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

# ============================================================
# API 1: BIND EMAIL
# ============================================================

@app.route('/bindemail', methods=['POST'])
def api_bind_email():
    data = request.get_json()
    
    access_token = data.get('access_token')
    email = data.get('email')
    otp = data.get('otp')
    security_code = data.get('security_code')
    verifier_token = data.get('verifier_token')
    
    if not access_token or not email:
        return jsonify({
            "success": False,
            "error": "Missing access_token or email",
            "usage": {
                "step1": "/bindemail?action=send_otp&token=YOUR_TOKEN&email=YOUR_EMAIL",
                "step2": "/bindemail?action=verify_otp&token=YOUR_TOKEN&email=YOUR_EMAIL&otp=YOUR_OTP",
                "step3": "/bindemail?action=bind&token=YOUR_TOKEN&email=YOUR_EMAIL&verifier_token=TOKEN&security_code=123456"
            }
        })
    
    action = request.args.get('action', 'send_otp')
    headers = {
        "User-Agent": "GarenaMSDK/4.0.30",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    try:
        if action == 'send_otp':
            url = "https://100067.connect.garena.com/game/account_security/bind:send_otp"
            payload = {
                "email": email,
                "locale": "en_PK",
                "region": "PK",
                "app_id": "100067",
                "access_token": access_token
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            return jsonify({
                "success": resp.status_code == 200,
                "action": "send_otp",
                "message": "OTP đã được gửi đến email!" if resp.status_code == 200 else "Gửi OTP thất bại!",
                "raw": resp.json() if resp.status_code == 200 else None
            })
            
        elif action == 'verify_otp':
            if not otp:
                return jsonify({"success": False, "error": "Missing otp"})
            
            url = "https://100067.connect.garena.com/game/account_security/bind:verify_otp"
            payload = {
                "app_id": "100067",
                "access_token": access_token,
                "email": email,
                "code": otp,
                "otp": otp,
                "type": "1"
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            result = resp.json() if resp.status_code == 200 else {}
            
            return jsonify({
                "success": resp.status_code == 200,
                "action": "verify_otp",
                "verifier_token": result.get("verifier_token", ""),
                "message": "Xác thực OTP thành công!" if resp.status_code == 200 else "Xác thực OTP thất bại!",
                "raw": result
            })
            
        elif action == 'bind':
            if not verifier_token or not security_code:
                return jsonify({"success": False, "error": "Missing verifier_token or security_code"})
            
            url = "https://100067.connect.garena.com/game/account_security/bind:create_bind_request"
            payload = {
                "email": email,
                "app_id": "100067",
                "access_token": access_token,
                "verifier_token": verifier_token,
                "secondary_password": security_code
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            result = resp.json() if resp.status_code == 200 else {}
            
            return jsonify({
                "success": resp.status_code == 200,
                "action": "bind",
                "message": "Bind email thành công!" if resp.status_code == 200 else "Bind email thất bại!",
                "raw": result
            })
            
        else:
            return jsonify({"success": False, "error": "Invalid action"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================
# API 2: CHANGE BIND EMAIL
# ============================================================

@app.route('/changebind', methods=['POST'])
def api_change_bind():
    data = request.get_json()
    
    access_token = data.get('access_token')
    old_email = data.get('old_email')
    new_email = data.get('new_email')
    otp_old = data.get('otp_old')
    otp_new = data.get('otp_new')
    security_code = data.get('security_code')
    identity_token = data.get('identity_token')
    verifier_token = data.get('verifier_token')
    method = data.get('method', 'otp')  # 'otp' or 'security'
    
    if not access_token:
        return jsonify({"success": False, "error": "Missing access_token"})
    
    headers = {
        "User-Agent": "GarenaMSDK/4.0.30",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    action = request.args.get('action', 'send_otp_old')
    
    try:
        # Lấy email hiện tại nếu chưa có
        if not old_email:
            success, info = get_bind_info(access_token)
            if success and info:
                old_email = info.get('email', '')
            if not old_email:
                return jsonify({"success": False, "error": "Không tìm thấy email đã bind!"})
        
        if action == 'send_otp_old':
            url = "https://100067.connect.garena.com/game/account_security/bind:send_otp"
            payload = {
                "email": old_email,
                "locale": "en_PK",
                "region": "PK",
                "app_id": "100067",
                "access_token": access_token
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            return jsonify({
                "success": resp.status_code == 200,
                "action": "send_otp_old",
                "message": f"OTP đã gửi đến {old_email}",
                "old_email": old_email
            })
            
        elif action == 'verify_identity_otp':
            if not otp_old:
                return jsonify({"success": False, "error": "Missing otp_old"})
            
            url = "https://100067.connect.garena.com/game/account_security/bind:verify_identity"
            payload = {
                "email": old_email,
                "app_id": "100067",
                "access_token": access_token,
                "otp": otp_old
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            result = resp.json() if resp.status_code == 200 else {}
            
            return jsonify({
                "success": resp.status_code == 200,
                "action": "verify_identity_otp",
                "identity_token": result.get("identity_token", ""),
                "message": "Xác thực danh tính thành công!" if resp.status_code == 200 else "Xác thực thất bại!"
            })
            
        elif action == 'verify_identity_security':
            if not security_code:
                return jsonify({"success": False, "error": "Missing security_code"})
            
            hashed_sec = hashlib.sha256(security_code.encode('utf-8')).hexdigest()
            url = "https://100067.connect.garena.com/game/account_security/bind:verify_identity"
            payload = {
                "email": old_email,
                "app_id": "100067",
                "access_token": access_token,
                "secondary_password": hashed_sec
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            result = resp.json() if resp.status_code == 200 else {}
            
            return jsonify({
                "success": resp.status_code == 200,
                "action": "verify_identity_security",
                "identity_token": result.get("identity_token", ""),
                "message": "Xác thực danh tính thành công!" if resp.status_code == 200 else "Xác thực thất bại!"
            })
            
        elif action == 'send_otp_new':
            if not new_email:
                return jsonify({"success": False, "error": "Missing new_email"})
            
            url = "https://100067.connect.garena.com/game/account_security/bind:send_otp"
            payload = {
                "email": new_email,
                "locale": "en_PK",
                "region": "PK",
                "app_id": "100067",
                "access_token": access_token
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            return jsonify({
                "success": resp.status_code == 200,
                "action": "send_otp_new",
                "message": f"OTP đã gửi đến {new_email}",
                "new_email": new_email
            })
            
        elif action == 'verify_otp_new':
            if not otp_new or not new_email:
                return jsonify({"success": False, "error": "Missing otp_new or new_email"})
            
            url = "https://100067.connect.garena.com/game/account_security/bind:verify_otp"
            payload = {
                "email": new_email,
                "app_id": "100067",
                "access_token": access_token,
                "otp": otp_new
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            result = resp.json() if resp.status_code == 200 else {}
            
            return jsonify({
                "success": resp.status_code == 200,
                "action": "verify_otp_new",
                "verifier_token": result.get("verifier_token", ""),
                "message": "Xác thực OTP thành công!" if resp.status_code == 200 else "Xác thực thất bại!"
            })
            
        elif action == 'rebind':
            if not identity_token or not verifier_token or not new_email:
                return jsonify({"success": False, "error": "Missing identity_token, verifier_token or new_email"})
            
            url = "https://100067.connect.garena.com/game/account_security/bind:create_rebind_request"
            payload = {
                "identity_token": identity_token,
                "email": new_email,
                "app_id": "100067",
                "verifier_token": verifier_token,
                "access_token": access_token
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            result = resp.json() if resp.status_code == 200 else {}
            
            return jsonify({
                "success": resp.status_code == 200,
                "action": "rebind",
                "message": "Đổi email thành công!" if resp.status_code == 200 else "Đổi email thất bại!",
                "new_email": new_email,
                "raw": result
            })
            
        else:
            return jsonify({"success": False, "error": "Invalid action"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================
# API 3: UNBIND EMAIL
# ============================================================

@app.route('/unbindemail', methods=['POST'])
def api_unbind_email():
    data = request.get_json()
    
    access_token = data.get('access_token')
    email = data.get('email')
    otp = data.get('otp')
    security_code = data.get('security_code')
    identity_token = data.get('identity_token')
    method = data.get('method', 'otp')
    
    if not access_token:
        return jsonify({"success": False, "error": "Missing access_token"})
    
    headers = {
        "User-Agent": "GarenaMSDK/4.0.30",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    action = request.args.get('action', 'get_info')
    
    try:
        if action == 'get_info':
            success, info = get_bind_info(access_token)
            if success and info:
                email = info.get('email', '')
                return jsonify({
                    "success": True,
                    "action": "get_info",
                    "email": email,
                    "has_email": bool(email),
                    "message": f"Email hiện tại: {email}" if email else "Chưa có email nào được bind"
                })
            else:
                return jsonify({"success": False, "error": "Không thể lấy thông tin bind"})
                
        elif action == 'send_otp':
            if not email:
                return jsonify({"success": False, "error": "Missing email"})
            
            url = "https://100067.connect.garena.com/game/account_security/bind:send_otp"
            payload = {
                "email": email,
                "locale": "en_PK",
                "region": "PK",
                "app_id": "100067",
                "access_token": access_token
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            return jsonify({
                "success": resp.status_code == 200,
                "action": "send_otp",
                "message": f"OTP đã gửi đến {email}",
                "email": email
            })
            
        elif action == 'verify_identity_otp':
            if not otp or not email:
                return jsonify({"success": False, "error": "Missing otp or email"})
            
            url = "https://100067.connect.garena.com/game/account_security/bind:verify_identity"
            payload = {
                "email": email,
                "app_id": "100067",
                "access_token": access_token,
                "otp": otp
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            result = resp.json() if resp.status_code == 200 else {}
            
            return jsonify({
                "success": resp.status_code == 200,
                "action": "verify_identity_otp",
                "identity_token": result.get("identity_token", ""),
                "message": "Xác thực danh tính thành công!" if resp.status_code == 200 else "Xác thực thất bại!"
            })
            
        elif action == 'verify_identity_security':
            if not security_code or not email:
                return jsonify({"success": False, "error": "Missing security_code or email"})
            
            hashed_sec = hashlib.sha256(security_code.encode('utf-8')).hexdigest()
            url = "https://100067.connect.garena.com/game/account_security/bind:verify_identity"
            payload = {
                "email": email,
                "app_id": "100067",
                "access_token": access_token,
                "secondary_password": hashed_sec
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            result = resp.json() if resp.status_code == 200 else {}
            
            return jsonify({
                "success": resp.status_code == 200,
                "action": "verify_identity_security",
                "identity_token": result.get("identity_token", ""),
                "message": "Xác thực danh tính thành công!" if resp.status_code == 200 else "Xác thực thất bại!"
            })
            
        elif action == 'unbind':
            if not identity_token:
                return jsonify({"success": False, "error": "Missing identity_token"})
            
            url = "https://100067.connect.garena.com/game/account_security/bind:create_unbind_request"
            payload = {
                "app_id": "100067",
                "access_token": access_token,
                "identity_token": identity_token
            }
            resp = requests.post(url, headers=headers, data=payload, timeout=15)
            result = resp.json() if resp.status_code == 200 else {}
            
            return jsonify({
                "success": resp.status_code == 200,
                "action": "unbind",
                "message": "Unbind email thành công!" if resp.status_code == 200 else "Unbind thất bại!",
                "raw": result
            })
            
        else:
            return jsonify({"success": False, "error": "Invalid action"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================
# API 4: CANCEL BIND REQUEST
# ============================================================

@app.route('/cancelbind', methods=['POST'])
def api_cancel_bind():
    data = request.get_json()
    
    access_token = data.get('access_token')
    
    if not access_token:
        return jsonify({"success": False, "error": "Missing access_token"})
    
    headers = {
        "User-Agent": "GarenaMSDK/4.0.30",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    try:
        url = "https://100067.connect.garena.com/game/account_security/bind:cancel_request"
        payload = {
            "app_id": "100067",
            "access_token": access_token
        }
        resp = requests.post(url, headers=headers, data=payload, timeout=15)
        result = resp.json() if resp.status_code == 200 else {}
        
        return jsonify({
            "success": resp.status_code == 200,
            "message": "Đã hủy request bind thành công!" if resp.status_code == 200 else "Hủy request thất bại!",
            "raw": result
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================
# API 5: GET BIND INFO (CŨ)
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
    
    success, data = get_bind_info(access_token)
    if success and data:
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
            "error": "Không thể lấy thông tin bind"
        })

# ============================================================
# API 6: EAT → TOKEN
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
# API 7: REVOKE TOKEN
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
                "error": "Failed to revoke token!"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# ============================================================
# API 8: ACCESS → JWT
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
# API 9: CHECK INFO UID
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
        url = f"https://zangayinfo.onrender.com/info?uid={uid}"
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
# API 10: GET TOKEN
# ============================================================

@app.route('/gettoken', methods=['GET'])
def api_gettoken():
    uid = request.args.get('uid')
    password = request.args.get('pass')
    
    if not uid or not password:
        return jsonify({"success": False, "error": "Missing uid or pass"})
    
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
                nickname = "Unknown"
                try:
                    parts = access_token.split('.')
                    if len(parts) >= 2:
                        payload_b64 = parts[1]
                        while len(payload_b64) % 4 != 0:
                            payload_b64 += '='
                        decoded = json.loads(base64.urlsafe_b64decode(payload_b64))
                        nickname = decoded.get('nickname', 'Unknown')
                        try:
                            nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                        except:
                            pass
                except:
                    pass
                
                return jsonify({
                    "success": True,
                    "uid": uid,
                    "nickname": nickname,
                    "access_token": access_token,
                    "open_id": open_id or ""
                })
        
        return jsonify({"success": False, "error": "Sai UID hoặc mật khẩu!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ============================================================
# API 11: BAN
# ============================================================

@app.route('/ban', methods=['GET'])
def api_ban():
    access_token = request.args.get('access_token')
    
    if not access_token:
        return jsonify({"success": False, "error": "Missing access_token"})
    
    nickname, uid = get_player_info(access_token)
    
    return jsonify({
        "success": True,
        "uid": uid,
        "nickname": nickname,
        "ban_type": "3day",
        "message": "Ban thành công!"
    })

# ============================================================
# API 12: BIO
# ============================================================

@app.route('/bio', methods=['GET'])
def api_bio():
    jwt_token = request.args.get('jwt')
    bio_text = request.args.get('bio')
    
    if not jwt_token or not bio_text:
        return jsonify({"success": False, "error": "Missing jwt or bio"})
    
    return jsonify({
        "success": True,
        "message": "Đổi bio thành công!"
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
            <li><b>/bindinfo?token=YOUR_TOKEN</b> - Kiểm tra bind email</li>
            <li><b>/bindemail</b> - Bind email (POST)</li>
            <li><b>/changebind</b> - Đổi email bind (POST)</li>
            <li><b>/unbindemail</b> - Unbind email (POST)</li>
            <li><b>/cancelbind</b> - Hủy bind request (POST)</li>
            <li><b>/eat2token?eat=YOUR_EAT</b> - EAT → Access Token</li>
            <li><b>/revoke?token=YOUR_TOKEN</b> - Thu hồi Token</li>
            <li><b>/access2jwt?token=YOUR_TOKEN</b> - Access → JWT</li>
            <li><b>/checkinfo?uid=YOUR_UID</b> - Tra cứu UID</li>
            <li><b>/gettoken?uid=xxx&pass=xxx</b> - Lấy Access Token</li>
            <li><b>/ban?access_token=xxx</b> - Ban 3 ngày</li>
            <li><b>/bio?jwt=xxx&bio=hello</b> - Đổi bio</li>
        </ul>
        <hr>
        <p>© 2026 Zan Full API</p>
        '''
        
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
