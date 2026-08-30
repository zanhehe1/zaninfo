from flask import Flask, request, jsonify
import requests
import json
import time
import os
import base64
from concurrent.futures import ThreadPoolExecutor
import asyncio
import aiohttp
import threading
import binascii

app = Flask(__name__)

# ====== CẤU HÌNH ======
ACC_FILE = "acc.json"
TOKEN_FILE = "token_bd.json"
REGION = "BD"
TOKEN_REFRESH_INTERVAL = 8 * 60 * 60  # 8 giờ
_executor = ThreadPoolExecutor(max_workers=20)

# ====== PING KEEP ALIVE ======
def ping_keep_alive():
    url = "https://zanapilike.onrender.com"
    while True:
        try:
            r = requests.get(url, timeout=10)
            print(f"[PING] ✅ {url} - Status: {r.status_code}")
        except Exception as e:
            print(f"[PING] ❌ Lỗi: {e}")
        time.sleep(600)  # 10 phút

# Chạy thread ping khi khởi động
threading.Thread(target=ping_keep_alive, daemon=True).start()

# ====== LẤY JWT ======
def get_jwt(uid, password):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-G998B Build/RP1A.200720.012)",
        "Content-Type": "application/x-www-form-urlencoded",
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
        r = requests.post(url, headers=headers, data=data, timeout=30)
        if r.status_code == 200:
            result = r.json()
            token = result.get("access_token")
            if token:
                return {"success": True, "token": token, "uid": result.get("uid")}
        return {"success": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ====== LOAD ACCOUNTS ======
def load_accounts():
    if not os.path.exists(ACC_FILE):
        return []
    try:
        with open(ACC_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return [{"uid": str(k), "password": str(v)} for k, v in data.items()]
        return []
    except:
        return []

# ====== SAVE TOKEN ======
def save_tokens(token_list):
    with open(TOKEN_FILE, "w") as f:
        json.dump({"created_at": time.time(), "tokens": token_list}, f, indent=2)

# ====== LOAD TOKEN ======
def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        return []
    try:
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            return data.get("tokens", [])
    except:
        return []

# ====== REFRESH TOKENS ======
def refresh_tokens():
    accounts = load_accounts()
    if not accounts:
        return {"success": False, "error": "No accounts"}
    
    tokens = []
    success = 0
    fail = 0
    
    for acc in accounts:
        result = get_jwt(acc["uid"], acc["password"])
        if result.get("success"):
            tokens.append({"uid": acc["uid"], "token": result["token"]})
            success += 1
        else:
            fail += 1
        time.sleep(0.5)
    
    if tokens:
        save_tokens(tokens)
    
    return {"success": True, "total": len(accounts), "ok": success, "fail": fail}

# ====== GET TOKEN ======
def get_next_token():
    tokens = load_tokens()
    if not tokens:
        refresh_tokens()
        tokens = load_tokens()
    if tokens:
        return tokens[0]["token"]
    return None

# ====== BUFF LIKE ======
async def send_request(session, edata, token, url):
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Dalvik/2.1.0',
        'ReleaseVersion': 'OB54'
    }
    try:
        async with session.post(url, data=edata, headers=headers, timeout=10) as r:
            return await r.text()
    except:
        return None

async def send_likes(uid, region, tokens, count=200):
    url = {
        "IND": "https://client.ind.freefiremobile.com/LikeProfile",
        "BR": "https://client.us.freefiremobile.com/LikeProfile",
        "US": "https://client.us.freefiremobile.com/LikeProfile",
        "VN": "https://clientbp.ggpolarbear.com/LikeProfile",
        "BD": "https://clientbp.ggpolarbear.com/LikeProfile"
    }.get(region, "https://clientbp.ggpolarbear.com/LikeProfile")
    
    edata = bytes.fromhex(encrypt_uid(uid))
    
    async with aiohttp.ClientSession() as session:
        tasks = [
            send_request(session, edata, tokens[i % len(tokens)], url)
            for i in range(count)
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

def encrypt_uid(uid):
    import binascii
    return binascii.hexlify(str(uid).encode()).decode()

def get_info(uid, region):
    token = get_next_token()
    if not token:
        return None
    url = {
        "IND": "https://client.ind.freefiremobile.com/GetPlayerPersonalShow",
        "BR": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
        "VN": "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow"
    }.get(region, "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow")
    
    headers = {'Authorization': f'Bearer {token}'}
    try:
        r = requests.get(url, params={"uid": uid}, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

# ====== API ======
@app.route('/')
def home():
    return '''
    <h1>🔥 API BUFF LIKE FREE FIRE</h1>
    <p>Dùng:</p>
    <code>/like?uid=UID&region=VN</code>
    <br>
    <code>/tokens</code> - Xem số token
    <br>
    <code>/refresh</code> - Refresh token
    <br>
    <code>/reset</code> - Reset token
    '''

@app.route('/like', methods=['GET'])
def api_like():
    uid = request.args.get('uid')
    region = request.args.get('region', 'BD').upper()
    
    if not uid:
        return jsonify({"error": "Missing uid"}), 400
    
    tokens = load_tokens()
    if not tokens:
        return jsonify({"error": "No tokens, run /refresh first"}), 500
    
    # Get before
    before = get_info(uid, region)
    before_like = before.get('likes', 0) if before else 0
    
    # Send likes
    asyncio.run(send_likes(uid, region, [t["token"] for t in tokens], 200))
    time.sleep(2)
    
    # Get after
    after = get_info(uid, region)
    after_like = after.get('likes', 0) if after else 0
    
    return jsonify({
        "success": True,
        "uid": uid,
        "region": region,
        "before": before_like,
        "after": after_like,
        "added": after_like - before_like
    })

@app.route('/refresh', methods=['GET'])
def api_refresh():
    result = refresh_tokens()
    return jsonify(result)

@app.route('/reset', methods=['GET'])
def api_reset():
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        result = refresh_tokens()
        return jsonify({
            "success": True,
            "message": "Reset thành công",
            "data": result
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/tokens', methods=['GET'])
def api_tokens():
    tokens = load_tokens()
    return jsonify({"total": len(tokens), "tokens": [t["uid"] for t in tokens]})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 API chạy tại port {port}")
    print(f"🔄 Ping API https://zanapilike.onrender.com mỗi 10 phút")
    app.run(host='0.0.0.0', port=port, debug=True)
