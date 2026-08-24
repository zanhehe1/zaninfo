from flask import Flask, render_template_string, request, jsonify, send_file
import os, zipfile, subprocess, shutil, time, signal

app = Flask(__name__)
BOT_DIR = 'bot_workspace'
BOT_PID = None

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Bot Treo</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:#0d0d1a; color:#c8d0e0; font-family: Arial; padding:20px; }
        .container { max-width:900px; margin:0 auto; }
        .card { background:#14142a; border:1px solid #2a2a4a; border-radius:12px; padding:25px; margin-bottom:20px; }
        .upload-area { border:2px dashed #3a3a5a; border-radius:10px; padding:40px; text-align:center; cursor:pointer; }
        .upload-area:hover { border-color:#5a7aff; background:#1a1a3a; }
        .upload-area input[type="file"] { display:none; }
        .btn { padding:10px 25px; border:none; border-radius:6px; cursor:pointer; font-weight:bold; margin:5px; }
        .btn-success { background:#22c55e; color:#fff; }
        .btn-danger { background:#ef4444; color:#fff; }
        .btn-gray { background:#2a2a4a; color:#aaa; }
        .btn-primary { background:#3b5eff; color:#fff; }
        .log-box { background:#0a0a18; border-radius:8px; padding:15px; max-height:300px; overflow-y:auto; font-family:monospace; font-size:12px; white-space:pre-wrap; color:#7a8aaa; }
        .status { display:inline-block; padding:5px 15px; border-radius:20px; font-weight:bold; }
        .online { background:#22c55e33; color:#4ade80; }
        .offline { background:#ef444433; color:#f87171; }
        .file-item { display:flex; justify-content:space-between; padding:5px 10px; background:#0a0a18; border-radius:4px; margin:3px 0; }
        a { color:#5a7aff; cursor:pointer; text-decoration:none; margin:0 10px; }
        a:hover { text-decoration:underline; }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <h2>🤖 Treo Bot</h2>
        <span class="status {{ 'online' if status=='online' else 'offline' }}">{{ status }}</span>
    </div>

    <div class="card">
        <h3>📤 Upload ZIP</h3>
        <div class="upload-area" onclick="document.getElementById('fileInput').click()">
            <div style="font-size:40px;">📁</div>
            <div>Chọn file ZIP</div>
            <div id="fileName" style="color:#6a7a9a;">Chưa chọn file</div>
            <input type="file" id="fileInput" accept=".zip" onchange="uploadFile(this)">
        </div>
        <div id="uploadStatus" style="color:#4ade80; margin-top:10px;"></div>
    </div>

    <div class="card">
        <button class="btn btn-success" onclick="runBot()">▶ Run</button>
        <button class="btn btn-danger" onclick="stopBot()">⏹ Stop</button>
        <button class="btn btn-gray" onclick="viewLogs()">📄 Logs</button>
        <button class="btn btn-gray" onclick="viewFiles()">📂 Files</button>
        <a onclick="downloadBot()">⬇ Download</a>
        <a onclick="deleteBot()">🗑 Delete</a>
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
function uploadFile(input) {
    const file = input.files[0];
    if (!file) return;
    document.getElementById('fileName').textContent = file.name;
    const formData = new FormData();
    formData.append('file', file);
    fetch('/upload', {method:'POST', body:formData})
        .then(r=>r.text())
        .then(msg => {
            document.getElementById('uploadStatus').textContent = '✅ ' + msg;
            updateStatus();
        });
}
function runBot() { fetch('/run').then(()=>updateStatus()); }
function stopBot() { fetch('/stop').then(()=>updateStatus()); }
function viewLogs() { fetch('/logs').then(r=>r.text()).then(d=>document.getElementById('logBox').textContent=d); }
function viewFiles() {
    const card = document.getElementById('filesCard');
    if (card.style.display === 'block') { card.style.display = 'none'; return; }
    fetch('/files').then(r=>r.json()).then(data => {
        let html = '';
        data.forEach(f => html += `<div class="file-item"><span>📄 ${f.name}</span><span>${(f.size/1024).toFixed(1)} KB</span></div>`);
        document.getElementById('fileList').innerHTML = html || '📭 Trống';
        card.style.display = 'block';
    });
}
function downloadBot() { window.location.href = '/download'; }
function deleteBot() { if(confirm('Xóa tất cả?')) fetch('/delete').then(()=>location.reload()); }
function updateStatus() { fetch('/status').then(r=>r.json()).then(d => { location.reload(); }); }
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
    if 'file' not in request.files:
        return 'Không có file', 400
    f = request.files['file']
    if f.filename == '':
        return 'Chưa chọn file', 400
    os.makedirs(BOT_DIR, exist_ok=True)
    zip_path = os.path.join(BOT_DIR, f.filename)
    f.save(zip_path)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(BOT_DIR)
    os.remove(zip_path)
    return 'Upload thành công!'

@app.route('/run')
def run():
    global BOT_PID
    if get_status() == 'online':
        return 'Bot đang chạy!'
    os.makedirs(BOT_DIR, exist_ok=True)
    start_file = None
    for root, dirs, files in os.walk(BOT_DIR):
        if 'start.py' in files:
            start_file = os.path.join(root, 'start.py')
            break
    if not start_file:
        return '❌ Không tìm thấy start.py'
    log_path = os.path.join(BOT_DIR, 'bot.log')
    with open(log_path, 'w') as f:
        f.write(f'✅ Bot started at {time.ctime()}\n')
    proc = subprocess.Popen(['python', start_file], cwd=os.path.dirname(start_file),
                            stdout=open(log_path, 'a'), stderr=subprocess.STDOUT)
    BOT_PID = proc.pid
    return '✅ Bot started!'

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
