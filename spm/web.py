import os
import time
import requests
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)
app.secret_key = "zanspm_secret_key_cyberpunk"

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
PORT = int(os.environ.get("PORT", 10000))
BOT_API_URL = "http://127.0.0.1:2026"

HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ZansPM Control</title>
<style>
    :root { --bg:#050711; --panel:#0c1426; --border:rgba(0,245,255,.2); --text:#eafaff; --cyan:#00f5ff; --green:#00ffad; --red:#ff386c; }
    * { box-sizing:border-box; margin:0; padding:0; }
    body { background:var(--bg); color:var(--text); font-family:sans-serif; min-height:100vh; }
    .hidden { display:none !important; }
    .login-wrap { display:flex; align-items:center; justify-content:center; height:100vh; }
    .login-box { width:100%; max-width:380px; padding:40px; background:var(--panel); border:1px solid var(--border); border-radius:15px; text-align:center; }
    .login-box h1 { color:var(--cyan); margin-bottom:10px; }
    .login-box input { width:100%; padding:14px; margin:15px 0; border-radius:8px; border:1px solid var(--border); background:#050b19; color:white; }
    .login-box button { width:100%; padding:14px; border:none; border-radius:8px; background:var(--cyan); color:#000; font-weight:bold; cursor:pointer; }
    .err { color:var(--red); font-size:13px; margin-top:10px; height:15px; }
    
    .header { padding:20px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; }
    .btn-logout { color:var(--red); border:1px solid var(--red); padding:8px 15px; border-radius:8px; background:transparent; cursor:pointer; }
    .container { max-width:1200px; margin:20px auto; padding:0 20px; }
    .stats { display:grid; grid-template-columns:repeat(4,1fr); gap:15px; margin-bottom:20px; }
    .stat-card { background:var(--panel); padding:20px; border-radius:12px; border:1px solid var(--border); }
    .stat-title { font-size:12px; color:#8fa3c0; text-transform:uppercase; }
    .stat-val { font-size:28px; font-weight:bold; color:var(--cyan); margin-top:10px; }
    .grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
    .panel { background:var(--panel); border:1px solid var(--border); border-radius:12px; height:500px; display:flex; flex-direction:column; }
    .panel-head { padding:15px; border-bottom:1px solid var(--border); font-weight:bold; display:flex; justify-content:space-between; }
    .terminal { flex:1; overflow-y:auto; padding:15px; background:#000; font-family:monospace; font-size:12px; }
    .log-line { color:#c9d6ec; margin-bottom:4px; }
    .log-line.error { color:var(--red); }
    .log-line.ok { color:var(--green); }
    .log-line.info { color:var(--cyan); }
    .bot-list { flex:1; overflow-y:auto; list-style:none; }
    .bot-item { padding:12px 15px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; }
</style>
</head>
<body>

<div id="login-screen" class="login-wrap">
    <div class="login-box">
        <h1>ZansPM Admin</h1>
        <form id="login-form">
            <input type="password" id="password" placeholder="Nhập mật khẩu..." required>
            <button type="submit" id="login-btn">Đăng nhập</button>
        </form>
        <div class="err" id="login-err"></div>
    </div>
</div>

<div id="dashboard-screen" class="hidden">
    <div class="header">
        <h1>ZansPM Dashboard</h1>
        <button class="btn-logout" onclick="location.reload()">Thoát / Làm mới</button>
    </div>
    <div class="container">
        <div class="stats">
            <div class="stat-card"><div class="stat-title">Bot Đang Chạy</div><div class="stat-val" id="stat-running">0</div></div>
            <div class="stat-card"><div class="stat-title">Tổng Bot</div><div class="stat-val" id="stat-total">0</div></div>
            <div class="stat-card"><div class="stat-title">Đã Tham Gia</div><div class="stat-val" id="stat-joined">0</div></div>
            <div class="stat-card"><div class="stat-title">Lỗi</div><div class="stat-val" id="stat-failed" style="color:var(--red)">0</div></div>
        </div>
        <div class="grid">
            <div class="panel">
                <div class="panel-head"><span>System Terminal</span><span id="log-count">0</span></div>
                <div class="terminal" id="terminal"></div>
            </div>
            <div class="panel">
                <div class="panel-head"><span>Bot List</span><span id="bot-count">0 bots</span></div>
                <ul class="bot-list" id="bot-list"></ul>
            </div>
        </div>
    </div>
</div>

<script>
    let lastLogId = 0;
    let intervals = [];

    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('login-btn');
        const err = document.getElementById('login-err');
        
        btn.disabled = true;
        btn.innerText = "Đang kiểm tra...";
        
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: document.getElementById('password').value })
            });
            const data = await res.json();

            if (data.success) {
                document.getElementById('login-screen').classList.add('hidden');
                document.getElementById('dashboard-screen').classList.remove('hidden');
                startDashboard();
            } else {
                err.innerText = data.error || "Sai mật khẩu!";
                btn.disabled = false;
                btn.innerText = "Đăng nhập";
            }
        } catch (error) {
            err.innerText = "Lỗi kết nối đến máy chủ!";
            btn.disabled = false;
            btn.innerText = "Đăng nhập";
        }
    });

    function startDashboard() {
        fetchStats(); fetchLogs(); fetchBots();
        intervals.push(setInterval(fetchStats, 3000));
        intervals.push(setInterval(fetchLogs, 1500));
        intervals.push(setInterval(fetchBots, 5000));
    }

    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.getElementById('stat-running').innerText = data.running || 0;
            document.getElementById('stat-total').innerText = data.total_bots || 0;
            document.getElementById('stat-joined').innerText = data.joined || 0;
            document.getElementById('stat-failed').innerText = data.failed || 0;
        } catch (e) {}
    }

    async function fetchLogs() {
        try {
            const res = await fetch('/api/logs?after=' + lastLogId);
            const data = await res.json();
            if (data.lines && data.lines.length > 0) {
                const term = document.getElementById('terminal');
                data.lines.forEach(line => {
                    const cleanLine = line.replace(/\\x1b\\[[0-9;]*m/g, '');
                    const div = document.createElement('div');
                    div.className = 'log-line';
                    if (cleanLine.includes('[ERROR]') || cleanLine.includes('✗')) div.classList.add('error');
                    else if (cleanLine.includes('[OK]') || cleanLine.includes('[LOGIN]') || cleanLine.includes('✓')) div.classList.add('ok');
                    else if (cleanLine.includes('[API]') || cleanLine.includes('[SYS]')) div.classList.add('info');
                    div.innerText = cleanLine;
                    term.appendChild(div);
                });
                lastLogId = data.total;
                while (term.children.length > 1000) term.removeChild(term.firstChild);
                term.scrollTop = term.scrollHeight;
                document.getElementById('log-count').innerText = data.total;
            }
        } catch (e) {}
    }

    async function fetchBots() {
        try {
            const res = await fetch('/api/bots');
            const data = await res.json();
            const bots = Array.isArray(data) ? data : (data.bots || []);
            const list = document.getElementById('bot-list');
            list.innerHTML = ''; 
            document.getElementById('bot-count').innerText = bots.length + " bots";
            
            bots.slice(0, 100).forEach(bot => {
                const li = document.createElement('li');
                li.className = 'bot-item';
                li.innerHTML = `<div><div><b>${bot.nickname || 'Unknown'}</b></div><div style="font-size:11px;color:#8fa3c0">${bot.uid}</div></div><div style="color:var(--green);font-size:12px">RUNNING</div>`;
                list.appendChild(li);
            });
        } catch (e) {}
    }
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if data.get("password") == ADMIN_PASSWORD:
        resp = jsonify({"success": True})
        resp.set_cookie("auth", "1", httponly=True, samesite='Lax', max_age=86400)
        return resp
    return jsonify({"success": False, "error": "Mật khẩu không chính xác!"})

@app.route('/api/stats')
def stats():
    try:
        r = requests.get(f"{BOT_API_URL}/api/stats", timeout=2)
        return jsonify(r.json())
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
