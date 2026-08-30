from flask import Flask, request, jsonify
import requests
import json
import base64

app = Flask(__name__)

def get_jwt(uid, password):
    """
    Lấy JWT token từ UID và Password (request trực tiếp Garena)
    """
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-G998B Build/RP1A.200720.012)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close"
    }
    
    data = {
        "uid": uid,
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067"
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            jwt_token = result.get("access_token")
            
            if jwt_token:
                # Decode JWT để lấy thông tin
                try:
                    parts = jwt_token.split('.')
                    if len(parts) >= 2:
                        payload = parts[1]
                        payload += '=' * (4 - len(payload) % 4)
                        decoded = json.loads(base64.urlsafe_b64decode(payload))
                        nickname = decoded.get('nickname', '')
                        if nickname:
                            try:
                                nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                            except:
                                pass
                    else:
                        nickname = ''
                except:
                    nickname = ''
                
                return {
                    "success": True,
                    "jwt": jwt_token,
                    "uid": result.get("uid"),
                    "open_id": result.get("open_id"),
                    "account_id": result.get("accountId"),
                    "nickname": nickname
                }
            else:
                return {
                    "success": False,
                    "error": "Không lấy được JWT",
                    "data": result
                }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "data": response.text
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.route('/', methods=['GET', 'POST'])
def home():
    return '''
    <h1>🔑 API LẤY JWT FREE FIRE</h1>
    <p>Dùng:</p>
    <code>/gettoken?uid=UID&password=PASSWORD</code>
    <br><br>
    <b>Ví dụ:</b>
    <br>
    <code>/gettoken?uid=4295974131&password=06_QBEKVPVOQ39</code>
    '''

@app.route('/gettoken', methods=['GET', 'POST'])
def api_get_jwt():
    if request.method == 'POST':
        uid = request.form.get('uid')
        password = request.form.get('password')
    else:
        uid = request.args.get('uid')
        password = request.args.get('password')
    
    if not uid or not password:
        return jsonify({
            "success": False,
            "error": "Missing uid or password",
            "usage": "/gettoken?uid=UID&password=PASSWORD"
        }), 400
    
    result = get_jwt(uid, password)
    return jsonify(result)

@app.route('/info', methods=['GET', 'POST'])
def api_info():
    """Lấy info bằng UID + Password"""
    if request.method == 'POST':
        uid = request.form.get('uid')
        password = request.form.get('password')
    else:
        uid = request.args.get('uid')
        password = request.args.get('password')
    
    if not uid or not password:
        return jsonify({
            "success": False,
            "error": "Missing uid or password",
            "usage": "/info?uid=UID&password=PASSWORD"
        }), 400
    
    # Lấy JWT
    jwt_result = get_jwt(uid, password)
    
    if not jwt_result["success"]:
        return jsonify(jwt_result)
    
    jwt = jwt_result["jwt"]
    
    # Từ JWT decode ra thông tin
    try:
        parts = jwt.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            
            # Decode nickname
            nickname = decoded.get('nickname', '')
            if nickname:
                try:
                    nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                except:
                    pass
            
            region = decoded.get('lock_region', 'VN')
            uid = decoded.get('account_id', uid)
            
            return jsonify({
                "success": True,
                "jwt": jwt,
                "uid": uid,
                "nickname": nickname,
                "region": region,
                "account_id": decoded.get('account_id'),
                "exp": decoded.get('exp')
            })
        else:
            return jsonify({
                "success": False,
                "error": "Invalid JWT format",
                "jwt": jwt
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "jwt": jwt
        })

# API lấy thông tin từ JWT (không cần uid/pass)
@app.route('/decode', methods=['GET', 'POST'])
def api_decode():
    """Decode JWT lấy thông tin"""
    if request.method == 'POST':
        jwt = request.form.get('jwt')
    else:
        jwt = request.args.get('jwt')
    
    if not jwt:
        return jsonify({
            "success": False,
            "error": "Missing jwt",
            "usage": "/decode?jwt=JWT_TOKEN"
        }), 400
    
    try:
        parts = jwt.split('.')
        if len(parts) >= 2:
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            
            nickname = decoded.get('nickname', '')
            if nickname:
                try:
                    nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                except:
                    pass
            
            return jsonify({
                "success": True,
                "uid": decoded.get('account_id'),
                "nickname": nickname,
                "region": decoded.get('lock_region'),
                "exp": decoded.get('exp'),
                "raw": decoded
            })
        else:
            return jsonify({
                "success": False,
                "error": "Invalid JWT format"
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
