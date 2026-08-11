from flask import Flask, request, jsonify, render_template_string
import requests
import threading
import time
import os
import subprocess
import sys

app = Flask(__name__)

# ====== HTML WEB TREO BOT ======
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web Treo Bot 24/7</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: #0a0e1a;
            color: #fff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            width: 100%;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        h1 {
            text-align: center;
            color: #00b4ff;
            margin-bottom: 5px;
            font-size: 24px;
        }
        .sub-title {
            text-align: center;
            color: #888;
            font-size: 13px;
            margin-bottom: 20px;
        }
        .status-box {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 18px;
            border-radius: 12px;
            background: rgba(0,180,255,0.08);
            border: 1px solid rgba(0,180,255,0.15);
            margin-bottom: 18px;
        }
        .status-box .dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #00ff00;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.2; }
        }
        .upload-area {
            border: 2px dashed rgba(255,255,255,0.15);
            border-radius: 14px;
            padding: 30px 20px;
            text-align: center;
            cursor: pointer;
            transition: 0.3s;
            margin-bottom: 12px;
        }
        .upload-area:hover {
            border-color: #00b4ff;
            background: rgba(0,180,255,0.05);
        }
        .upload-area i {
            font-size: 36px;
            color: #00b4ff;
            margin-bottom: 6px;
        }
        .upload-area p { color: #888; font-size: 14px; }
        .upload-area .filename {
            color: #00b4ff;
            font-weight: bold;
            margin-top: 6px;
            font-size: 13px;
        }
        #fileInput { display: none; }
        .btn-group {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
            margin: 10px 0;
        }
        .btn {
            padding: 11px;
            border: none;
            border-radius: 10px;
            font-size: 13px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.3s;
        }
        .btn-start { background: linear-gradient(135deg, #00c853, #009624); color: #fff; }
        .btn-start:hover { opacity: 0.85; transform: scale(1.02); }
        .btn-stop { background: linear-gradient(135deg, #ff4444, #cc0000); color: #fff; }
        .btn-stop:hover { opacity: 0.85; transform: scale(1.02); }
        .btn-ping { background: linear-gradient(135deg, #f59e0b, #d97706); color: #fff; }
        .btn-ping:hover { opacity: 0.85; transform: scale(1.02); }
        .file-list {
            margin-top: 12px;
            padding: 10px;
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            max-height: 180px;
            overflow-y: auto;
        }
        .file-list .file-item {
            display: flex;
            justify-content: space-between;
            padding: 5px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 13px;
        }
        .file-list .file-item .name { color: #00b4ff; }
        .file-list .file-item .size { color: #888; font-size: 12px; }
        .file-list .file-item .del {
            color: #ff4444;
            cursor: pointer;
            font-size: 12px;
        }
        .file-list .file-item .del:hover { opacity: 0.7; }
        .log-box {
            margin-top: 12px;
            padding: 12px;
            background: rgba(0,0,0,0.4);
            border-radius: 12px;
            max-height: 150px;
            overflow-y: auto;
            font-size: 12px;
            color: #00ff00;
            font-family: monospace;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .log-box .log-error { color: #ff4444; }
        .log-box .log-info { color: #00b4ff; }
        .log-box .log-success { color: #00ff00; }
        .footer {
            text-align: center;
            margin-top: 14px;
            color: #555;
            font-size: 12px;
        }
        .footer a { color: #00b4ff; text-decoration: none; }
        .bot-url {
            margin-top: 10px;
            padding: 10px;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            font-size: 13px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .bot-url input {
            width: 100%;
            padding: 8px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.3);
            color: #00b4ff;
            font-size: 13px;
            margin-top: 5px;
            text-align: center;
        }
        .bot-url input:focus { outline: none; border-color: #00b4ff; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 WEB TREO BOT</h1>
        <div class="sub-title">Upload bot lên và giữ 24/7 không ngủ</div>

        <div class="status-box">
            <span><span class="dot"></span> <span style="margin-left:8px;">Bot đang hoạt động</span></span>
            <span id="pingTime" style="color:#888;font-size:12px;">Ping: 5 phút</span>
        </div>

        <div class="bot-url">
            <span style="color:#888;">🔗 Link bot của bạn:</span>
            <input type="text" id="botUrl" placeholder="https://ten-bot.onrender.com" value="">
        </div>

        <div class="upload-area" onclick="document.getElementById('fileInput').click()">
            <i class="fas fa-cloud-upload-alt"></i>
            <p>Click để upload file bot (.py, .json, .txt)</p>
            <div class="filename" id="fileName">Chưa chọn file</div>
        </div>
        <input type="file" id="fileInput" multiple onchange="uploadFiles()">

        <div class="btn-group">
            <button class="btn btn-start" onclick="startBot()"><i class="fas fa-play"></i> Start</button>
            <button class="btn btn-stop" onclick="stopBot()"><i class="fas fa-stop"></i> Stop</button>
            <button class="btn btn-ping" onclick="pingNow()"><i class="fas fa-sync"></i> Ping</button>
        </div>

        <div class="file-list" id="fileList">
            <div style="color:#666;text-align:center;padding:10px;">📁 Danh sách file</div>
        </div>

        <div class="log-box" id="logBox">
            <div style="color:#666;">[ Log ] Đang kết nối...</div>
        </div>

        <div class="footer">
            <span id="pingStatus">🔄 Ping bot mỗi 5 phút</span>
        </div>
    </div>

    <script>
        function addLog(msg, type='info') {
            const box = document.getElementById('logBox');
            const colors = { info: '#00b4ff', success: '#00ff00', error: '#ff4444' };
            const time = new Date().toLocaleTimeString();
            box.innerHTML += `<div style="color:${colors[type] || '#fff'}">[${time}] ${msg}</div>`;
            box.scrollTop = box.scrollHeight;
        }

        async function uploadFiles() {
            const input = document.getElementById('fileInput');
            const files = input.files;
            if (!files.length) return;

            const formData = new FormData();
            for (let f of files) formData.append('files', f);

            document.getElementById('fileName').textContent = `⏳ Đang upload ${files.length} file...`;

            try {
                const res = await fetch('/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.success) {
                    addLog(`✅ Upload ${data.count} file thành công!`, 'success');
                    document.getElementById('fileName').textContent = `✅ ${data.count} file đã upload`;
                    loadFiles();
                } else {
                    addLog(`❌ Upload thất bại: ${data.error}`, 'error');
                }
            } catch (e) {
                addLog(`❌ Lỗi: ${e}`, 'error');
            }
        }

        async function loadFiles() {
            try {
                const res = await fetch('/files');
                const data = await res.json();
                const list = document.getElementById('fileList');
                if (data.files && data.files.length) {
                    list.innerHTML = data.files.map(f => 
                        `<div class="file-item">
                            <span class="name">📄 ${f.name}</span>
                            <span class="size">${(f.size/1024).toFixed(1)} KB</span>
                            <span class="del" onclick="deleteFile('${f.name}')">✕</span>
                        </div>`
                    ).join('');
                } else {
                    list.innerHTML = '<div style="color:#666;text-align:center;padding:10px;">📭 Chưa có file nào</div>';
                }
            } catch (e) { console.error(e); }
        }

        async function deleteFile(name) {
            if (!confirm(`Xóa file ${name}?`)) return;
            try {
                const res = await fetch(`/delete?file=${encodeURIComponent(name)}`, { method: 'DELETE' });
                const data = await res.json();
                if (data.success) {
                    addLog(`🗑️ Đã xóa ${name}`, 'info');
                    loadFiles();
                }
            } catch (e) { addLog(`❌ Lỗi xóa: ${e}`, 'error'); }
        }

        async function startBot() {
            addLog('🔄 Đang start bot...', 'info');
            try {
                const res = await fetch('/start', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    addLog('✅ Bot đã start!', 'success');
                } else {
                    addLog(`❌ Start thất bại: ${data.error}`, 'error');
                }
            } catch (e) {
                addLog(`❌ Lỗi: ${e}`, 'error');
            }
        }

        async function stopBot() {
            addLog('🔄 Đang stop bot...', 'info');
            try {
                const res = await fetch('/stop', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    addLog('✅ Bot đã stop!', 'success');
                } else {
                    addLog(`❌ Stop thất bại: ${data.error}`, 'error');
                }
            } catch (e) {
                addLog(`❌ Lỗi: ${e}`, 'error');
            }
        }

        async function pingNow() {
            const botUrl = document.getElementById('botUrl').value.trim();
            if (!botUrl) {
                addLog('❌ Chưa nhập link bot!', 'error');
                return;
            }
            addLog(`🔄 Đang ping ${botUrl}...`, 'info');
            try {
                const res = await fetch(`/ping?url=${encodeURIComponent(botUrl)}`);
                const data = await res.json();
                if (data.success) {
                    addLog(`✅ Ping thành công! Status: ${data.status}`, 'success');
                } else {
                    addLog(`❌ Ping thất bại: ${data.error}`, 'error');
                }
            } catch (e) {
                addLog(`❌ Lỗi: ${e}`, 'error');
            }
        }

        loadFiles();
        setInterval(loadFiles, 10000);
        addLog('✅ Web treo bot sẵn sàng!', 'success');
    </script>
</body>
</html>
"""

# ====== ROUTE ======
@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        files = request.files.getlist('files')
        saved = []
        for f in files:
            if f.filename:
                path = os.path.join('/tmp', f.filename)
                f.save(path)
                saved.append(f.filename)
        return jsonify({"success": True, "count": len(saved)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/files')
def list_files():
    try:
        files = []
        for f in os.listdir('/tmp'):
            path = os.path.join('/tmp', f)
            if os.path.isfile(path):
                files.append({"name": f, "size": os.path.getsize(path)})
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"files": [], "error": str(e)})

@app.route('/delete', methods=['DELETE'])
def delete_file():
    try:
        name = request.args.get('file')
        if not name:
            return jsonify({"success": False, "error": "Missing file"})
        path = os.path.join('/tmp', name)
        if os.path.exists(path):
            os.remove(path)
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "File not found"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/start', methods=['POST'])
def start_bot():
    try:
        if os.path.exists('/tmp/start.py'):
            subprocess.Popen(['python3', '/tmp/start.py'], cwd='/tmp', 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Không tìm thấy start.py"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/stop', methods=['POST'])
def stop_bot():
    try:
        subprocess.Popen(['pkill', '-f', 'start.py'])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/ping')
def ping_now():
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({"success": False, "error": "Missing url"})
        resp = requests.get(url, timeout=10)
        return jsonify({"success": True, "status": resp.status_code})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
