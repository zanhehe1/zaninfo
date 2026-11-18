import os
import requests
from flask import Flask, send_file, request, jsonify

app = Flask(__name__)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
PORT = int(os.environ.get("PORT", 10000))
BOT_API_URL = "http://127.0.0.1:2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(BASE_DIR, "index.html")

@app.route('/')
def index():
    if not os.path.isfile(INDEX_FILE):
        return "Lỗi: Không tìm thấy file index.html", 404
    return send_file(INDEX_FILE, mimetype='text/html')

# Hỗ trợ cả 2 kiểu gửi form (URL-encoded) và JSON
@app.route('/login', methods=['POST'])
def login():
    if request.is_json:
        data = request.json
    else:
        data = request.form
        
    if data.get("password") == ADMIN_PASSWORD:
        resp = jsonify({"success": True})
        resp.set_cookie("auth", "1", httponly=True, samesite='Lax', max_age=86400)
        return resp
    return jsonify({"success": False, "error": "Mật khẩu không chính xác!"})

@app.route('/api/stats')
def stats():
    try:
        r = requests.get(f"{BOT_API_URL}/api/stats", timeout=2)
        data = r.json()
        # Bổ sung các trường còn thiếu để giao diện không bị lỗi "--"
        data["cpu"] = None
        data["memory"] = None
        data["api_last_ok"] = True
        data["api_last_ms"] = 10
        data["api_last_error"] = None
        data["started_at"] = None
        return jsonify(data)
    except:
        return jsonify({"running": 0, "total_bots": 0, "joined": 0, "failed": 0})

@app.route('/api/logs')
def logs():
    after = request.args.get('after', 0)
    try:
        r = requests.get(f"{BOT_API_URL}/api/logs?after={after}", timeout=2)
        return jsonify(r.json())
    except:
        return jsonify({"total": 0, "lines": []})

@app.route('/api/bots')
def bots():
    try:
        r = requests.get(f"{BOT_API_URL}/api/bots", timeout=2)
        return jsonify(r.json())
    except:
        return jsonify({"bots": []})
