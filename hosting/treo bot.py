from flask import Flask, render_template_string, request, jsonify, send_file
import subprocess
import os
import json
import time

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Bot Manager</title>
    <style>
        body { background: #1a1a2e; color: #eee; font-family: Arial; padding: 20px; }
        .card { background: #16213e; padding: 20px; border-radius: 10px; margin: 10px 0; }
        button { background: #0f3460; color: #fff; border: none; padding: 10px 20px; cursor: pointer; border-radius: 5px; }
        button:hover { background: #1a4a7a; }
        .log { background: #0d0d1a; padding: 10px; border-radius: 5px; max-height: 300px; overflow-y: auto; white-space: pre-wrap; font-family: monospace; font-size: 12px; }
    </style>
</head>
<body>
    <h1>🤖 Bot Manager</h1>
    <div class="card">
        <button onclick="runBot()">▶ Run</button>
        <button onclick="stopBot()">⏹ Stop</button>
        <button onclick="viewLogs()">📄 Logs</button>
    </div>
    <div class="card">
        <h3>Upload file</h3>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file">
            <button type="submit">Upload</button>
        </form>
    </div>
    <div class="card">
        <h3>Logs</h3>
        <div class="log" id="log">Chưa có log...</div>
    </div>
    <script>
        function runBot() {
            fetch('/run').then(() => alert('Bot started!'));
        }
        function stopBot() {
            fetch('/stop').then(() => alert('Bot stopped!'));
        }
        function viewLogs() {
            fetch('/logs').then(r => r.text()).then(d => document.getElementById('log').textContent = d);
        }
        setInterval(viewLogs, 5000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/run')
def run():
    subprocess.Popen(['python', 'start.py'], shell=True)
    return 'ok'

@app.route('/stop')
def stop():
    os.system('taskkill /f /im python.exe' if os.name == 'nt' else 'pkill -f start.py')
    return 'ok'

@app.route('/logs')
def logs():
    try:
        with open('bot.log', 'r') as f:
            return f.read()[-5000:]
    except:
        return 'Chưa có log...'

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    file.save(file.filename)
    return 'Upload thành công!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
