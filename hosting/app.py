from flask import Flask, render_template_string, request, jsonify, send_file
import os, zipfile, subprocess, shutil, time, signal, json

app = Flask(__name__)
BOT_DIR = 'bot_workspace'
BOT_PID = None
UPLOAD_STATUS = "Chưa upload"

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Bot Treo</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:#0d0d1a; color:#c8d0e0; font-family: 'Segoe UI', Arial, sans-serif; padding:30px 20px; }
        .container { max-width:1200px; margin:0 auto; }
        .card { background:#14142a; border:1px solid #2a2a4a; border-radius:16px; padding:35px; margin-bottom:25px; }
        .card h2 { font-size:32px; color:#e0e8f0; }
        .card h3 { font-size:20px; color:#8a9aba; margin-bottom:15px; }
        .upload-area {
            border: 2px dashed #3a3a5a;
            border-radius: 14px;
            padding: 60px 20px;
            text-align: center;
            cursor: pointer;
            transition: 0.3s;
        }
        .upload-area:hover { border-color:#5a7aff; background:#1a1a3a; }
        .upload-area .icon { font-size:56px; color:#3a3a5a; }
        .upload-area .title { font-size:22px; color:#5a7aaa; margin:15px 0 5px; }
        .upload-area .file-name { color:#7a8aaa; font-size:18px; margin-top:10px; }
        .upload-area input[type="file"] { display:none; }
        .status-box {
            display: flex;
            align-items: center;
            gap: 20px;
            padding: 20px 25px;
            background: #0a0a18;
            border-radius: 12px;
            margin-top: 15px;
        }
        .status-box .dot {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            display: inline-block;
        }
        .dot.online { background:#4ade80; box-shadow:0 0 20px #4ade8055; }
        .dot.offline { background:#f87171; box-shadow:0 0 20px #f8717155; }
        .status-box .value { font-size:20px; color:#e0e8f0; font-weight:600; }
        .btn-group { display:flex; gap:15px; flex-wrap:wrap; margin:20px 0; }
        .btn {
            padding: 14px 35px;
            border: none;
            border-radius: 10px;
            font-size: 17px;
            cursor: pointer;
            font-weight: 600;
            transition: 0.2s;
        }
        .btn:hover { transform: scale(1.03); }
        .btn-success { background:#22c55e; color:#fff; }
        .btn-success:hover { background:#16a34a; }
        .btn-danger { background:#ef4444; color:#fff; }
        .btn-danger:hover { background:#dc2626; }
        .btn-gray { background:#2a2a4a; color:#aaa; }
        .btn-gray:hover { background:#3a3a5a; }
        .link-group { display:flex; gap:20px; flex-wrap:wrap; margin-top:15px; }
        .link-group a { color:#5a7aff; cursor:pointer; font-size:16px; text-decoration:none; }
        .link-group a:hover { text-decoration:underline; }
        .log-box {
            background:#0a0a18;
            border-radius:12px;
            padding:20px;
            max-height:400px;
            overflow-y:auto;
            font-family:monospace;
            font-size:15px;
            white-space:pre-wrap;
            color:#7a8aaa;
            line-height:1.8;
        }
        .log-box::-webkit-scrollbar { width:6px; }
        .log-box::-webkit-scrollbar-thumb { background:#3a3a5a; border-radius:3px; }
        .file-item {
            display:flex;
            justify-content:space-between;
            padding:12px 18px;
            background:#0a0a18;
            border-radius:8px;
            margin-bottom:6px;
            font-size:16px;
        }
        .file-item .name { color:#a0b0d0; }
        .file-item .size { color:#6a7a9a; }
        #uploadStatus { color:#4ade80; font-size:17px; margin-top:12px; }
        #uploadError { color:#f87171; font-size:17px; margin-top:12px; }
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 30px;
            border-radius: 10px;
            color: #fff;
            font-weight: bold;
            z-index: 999;
            display: none;
            animation: slideIn 0.3s ease;
        }
        .toast.success { background:#22c55e; }
        .toast.error { background:#ef4444; }
        @keyframes slideIn {
            from { transform: translateX(100px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @media (max-width:600px) {
            .card { padding:20px; }
            .btn { padding:12px 20px; font-size:15px; width:100%; }
            .btn-group { flex-direction:column; }
        }
    </style>
</head>
<body>
<div class="container">

    <!-- Toast notification -->
    <div id="toast" class="toast"></div>

    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
            <h2>🤖 Treo Bot</h2>
            <div style="display:flex; align-items:center; gap:15px;">
                <span class="status-box" style="margin:0; padding:10px 20px;">
                    <span class="dot {{ 'online' if status=='online' else 'offline' }}"></span>
                    <span class="value">{{ status }}</span>
                </span>
            </div>
        </div>
    </div>

    <div class="card">
        <h3>📤 Upload ZIP</h3>
        <div class="upload-area" id="uploadArea" onclick="document.getElementById('fileInput').click()">
            <div class="icon">📁</div>
            <div class="title">Chọn file ZIP</div>
            <div class="file-name" id="fileName">Chưa chọn file</div>
            <input type="file" id="fileInput" accept=".zip" onchange="uploadFile(this)">
        </div>
        <div id="uploadStatus"></div>
        <div id="uploadError"></div>
    </div>

    <div class="card">
        <div class="btn-group">
            <button class="btn btn-success" onclick="runBot()">▶ Run</button>
            <button class="btn btn-danger" onclick="stopBot()">⏹ Stop</button>
            <button class="btn btn-gray" onclick="viewLogs()">📄 Logs</button>
            <button class="btn btn-gray" onclick="viewFiles()">📂 Files</button>
        </div>
        <div class="link-group">
            <a onclick="downloadBot()">⬇ Download</a>
            <a onclick="deleteBot()">🗑 Delete</a>
        </div>
    </div>

    <div class="card">
        <h3>📄 Logs</h3>
        <div class="log-box" id="logBox">Chưa có log...</div>
    </div>

    <div class="card" id="filesCard" style="display:none;">
        <h3>📂 Files</h3>
        <div id="fileList"></div>
    </div>

</div>

<script>
function showToast(msg, type) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast ' + type;
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 4000);
}

function uploadFile(input) {
    const file = input.files[0];
    if (!file) return;
    document.getElementById('fileName').textContent = file.name + ' (Đang upload...)';
    document.getElementById('uploadStatus').textContent = '';
    document.getElementById('uploadError').textContent = '';
    
    const formData = new FormData();
    formData.append('file', file);
    
    fetch('/upload', {method:'POST', body:formData})
        .then(res => res.text())
        .then(msg => {
            if (msg.includes('thành công') || msg.includes('success')) {
                document.getElementById('uploadStatus').textContent = '✅ ' + msg;
                document.getElementById('fileName').textContent = file.name + ' ✅';
                showToast('✅ Upload thành công!', 'success');
                updateStatus();
            } else {
                document.getElementById('uploadError').textContent = '❌ ' + msg;
                document.getElementById('fileName').textContent = file.name + ' ❌';
                showToast('❌ Upload thất bại!', 'error');
            }
        })
        .catch(err => {
            document.getElementById('uploadError').textContent = '❌ Lỗi kết nối: ' + err;
            showToast('❌ Lỗi kết nối!', 'error');
        });
}

function runBot() { 
    fetch('/run')
        .then(r=>r.text())
        .then(msg => {
            if (msg.includes('started')) {
                showToast('✅ Bot đã chạy!', 'success');
            } else {
                showToast('❌ ' + msg, 'error');
            }
            updateStatus();
        });
}
function stopBot() { 
    fetch('/stop')
        .then(r=>r.text())
        .then(msg => {
            if (msg.includes('stopped')) {
                showToast('⏹ Bot đã dừng!', 'success');
            }
            updateStatus();
        });
}
function viewLogs() { 
    fetch('/logs').then(r=>r.text()).then(d=>document.getElementById('logBox').textContent=d); 
}
function viewFiles() {
    const card = document.getElementById('filesCard');
    if (card.style.display === 'block') { card.style.display = 'none'; return; }
    fetch('/files').then(r=>r.json()).then(data => {
        let html = '';
        if (data.length === 0) {
            html = '<div style="color:#6a7a9a; padding:20px; text-align:center;">📭 Chưa có file nào</div>';
        } else {
            data.forEach(f => html += `<div class="file-item"><span class="name">📄 ${f.name}</span><span class="size">${(f.size/1024).toFixed(1)} KB</span></div>`);
        }
        document.getElementById('fileList').innerHTML = html;
        card.style.display = 'block';
    });
}
function downloadBot() { window.location.href = '/download'; }
function deleteBot() { 
    if(confirm('Xóa tất cả file và bot?')) {
        fetch('/delete').then(() => {
            showToast('🗑 Đã xóa toàn bộ!', 'success');
            location.reload();
        });
    }
}
function updateStatus() { 
    fetch('/status').then(r=>r.json()).then(d => { location.reload(); }); 
}
setInterval(viewLogs, 5000);
setInterval(updateStatus, 10000);
viewLogs();
</script>
</body>
</html>
'''

def get_status():
    global BOT_PID
    if BOT_PID:
        try:
            os.kill(BOT_PID, 0)
            return 'online'
        except:
            BOT_PID = None
    return 'offline'

@app.route('/')
def index():
    return render_template_string(HTML, status=get_status())

@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return 'Không có file', 400
        f = request.files['file']
        if f.filename == '':
            return 'Chưa chọn file', 400
        if not f.filename.endswith('.zip'):
            return 'Chỉ chấp nhận file ZIP', 400
        os.makedirs(BOT_DIR, exist_ok=True)
        zip_path = os.path.join(BOT_DIR, f.filename)
        f.save(zip_path)
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(BOT_DIR)
        os.remove(zip_path)
        return 'Upload thành công! Giải nén xong.'
    except Exception as e:
        return f'Lỗi: {str(e)}', 400

@app.route('/run')
def run():
    global BOT_PID
    if get_status() == 'online':
        return 'Bot đang chạy!'
    os.makedirs(BOT_DIR, exist_ok=True)
    
    # ====== TÌM start.py TRONG TẤT CẢ THƯ MỤC CON (KHÔNG GIỚI HẠN ĐỘ SÂU) ======
    start_file = None
    for root, dirs, files in os.walk(BOT_DIR):
        if 'start.py' in files:
            start_file = os.path.join(root, 'start.py')
            break
    
    if not start_file:
        return '❌ Không tìm thấy start.py trong file ZIP'
    
    # ====== CHẠY BOT TỪ ĐÚNG THƯ MỤC CHỨA start.py ======
    log_path = os.path.join(BOT_DIR, 'bot.log')
    with open(log_path, 'w') as f:
        f.write(f'✅ Bot started at {time.ctime()}\n')
        f.write(f'📁 File path: {start_file}\n')
        f.write(f'📁 Working dir: {os.path.dirname(start_file)}\n')
    
    proc = subprocess.Popen(
        ['python', start_file], 
        cwd=os.path.dirname(start_file),  # 👈 CHẠY TỪ THƯ MỤC CHỨA start.py
        stdout=open(log_path, 'a'), 
        stderr=subprocess.STDOUT
    )
    BOT_PID = proc.pid
    return f'✅ Bot started! (found: {start_file})'

@app.route('/stop')
def stop():
    global BOT_PID
    if get_status() == 'offline':
        return 'Bot đã offline'
    try:
        os.kill(BOT_PID, signal.SIGTERM)
        BOT_PID = None
        return '✅ Bot stopped!'
    except:
        return '❌ Lỗi khi dừng bot'

@app.route('/logs')
def logs():
    log_path = os.path.join(BOT_DIR, 'bot.log')
    if not os.path.exists(log_path):
        return 'Chưa có log...'
    with open(log_path, 'r') as f:
        return f.read()[-5000:]

@app.route('/status')
def status():
    return jsonify({'status': get_status()})

@app.route('/files')
def files():
    if not os.path.exists(BOT_DIR):
        return jsonify([])
    result = []
    for root, dirs, files in os.walk(BOT_DIR):
        for f in files:
            path = os.path.join(root, f)
            result.append({'name': f, 'size': os.path.getsize(path)})
    return jsonify(result)

@app.route('/download')
def download():
    zip_path = os.path.join(BOT_DIR, 'backup.zip')
    with zipfile.ZipFile(zip_path, 'w') as z:
        for root, dirs, files in os.walk(BOT_DIR):
            for f in files:
                if f != 'backup.zip':
                    z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), BOT_DIR))
    return send_file(zip_path, as_attachment=True, download_name='bot_backup.zip')

@app.route('/delete')
def delete():
    global BOT_PID
    if get_status() == 'online':
        os.kill(BOT_PID, signal.SIGTERM)
        BOT_PID = None
    shutil.rmtree(BOT_DIR, ignore_errors=True)
    return 'Đã xóa!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
