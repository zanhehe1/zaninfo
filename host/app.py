import os
import sys
import time
import signal
import threading
import subprocess
import urllib.request
from pathlib import Path
from functools import wraps
from flask import Flask, request, session, redirect, url_for, render_template, jsonify, abort
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = Path(os.environ.get('RUNTIME_DIR', '/tmp/zan-python-runtime'))
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
SCRIPT_PATH = RUNTIME_DIR / 'main.py'
LOG_PATH = RUNTIME_DIR / 'bot.log'
MAX_UPLOAD = 2 * 1024 * 1024

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-this-secret-before-deploying')
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')
process = None
process_lock = threading.Lock()


def logged_in():
    return bool(session.get('logged_in'))


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not logged_in():
            if request.path.startswith('/api/'):
                return jsonify({'ok': False, 'error': 'Bạn cần đăng nhập trước.'}), 401
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper


def read_logs():
    try:
        text = LOG_PATH.read_text(encoding='utf-8', errors='replace')
        return text[-30000:]
    except FileNotFoundError:
        return 'Chưa có nhật ký. Hãy tải tệp Python lên rồi nhấn Start.'


def pump_output(pipe):
    try:
        with LOG_PATH.open('a', encoding='utf-8', errors='replace') as out:
            for line in iter(pipe.readline, ''):
                out.write(line)
                out.flush()
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def get_status():
    global process
    with process_lock:
        p = process
        running = p is not None and p.poll() is None
        if p is not None and not running:
            process = None
        return {'running': running, 'uploaded': SCRIPT_PATH.exists(), 'filename': 'main.py' if SCRIPT_PATH.exists() else None}


@app.route('/')
def index():
    if not logged_in():
        return redirect(url_for('login'))
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ''
    if request.method == 'POST':
        if not ADMIN_PASSWORD:
            error = 'Chưa cấu hình ADMIN_PASSWORD trên Render. Hãy thêm Environment Variable trước.'
        elif request.form.get('password', '') == ADMIN_PASSWORD:
            session.clear()
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('index'))
        else:
            error = 'Mật khẩu không đúng.'
    return render_template('login.html', error=error)


@app.post('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.get('/api/status')
@login_required
def api_status():
    return jsonify({'ok': True, **get_status()})


@app.post('/api/upload')
@login_required
def api_upload():
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'Chưa chọn tệp.'}), 400
    f = request.files['file']
    safe_name = secure_filename(f.filename or '')
    if not safe_name.lower().endswith('.py'):
        return jsonify({'ok': False, 'error': 'Chỉ chấp nhận tệp .py.'}), 400
    data = f.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        return jsonify({'ok': False, 'error': 'Tệp vượt quá giới hạn 2 MB.'}), 413
    status = get_status()
    if status['running']:
        return jsonify({'ok': False, 'error': 'Hãy Stop bot trước khi thay tệp.'}), 409
    SCRIPT_PATH.write_bytes(data)
    with LOG_PATH.open('a', encoding='utf-8') as out:
        out.write(f'\n[Zan Hosting] Đã tải lên {safe_name} ({len(data)} bytes).\n')
    return jsonify({'ok': True, 'message': f'Đã tải {safe_name} lên máy chủ.'})


@app.post('/api/start')
@login_required
def api_start():
    global process
    if not SCRIPT_PATH.exists():
        return jsonify({'ok': False, 'error': 'Bạn cần tải tệp .py lên trước.'}), 400
    with process_lock:
        if process is not None and process.poll() is None:
            return jsonify({'ok': False, 'error': 'Bot đang chạy rồi.'}), 409
        with LOG_PATH.open('a', encoding='utf-8') as out:
            out.write(f'\n[Zan Hosting] Start lúc {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        try:
            process = subprocess.Popen(
                [sys.executable, '-u', str(SCRIPT_PATH)],
                cwd=str(RUNTIME_DIR),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}
            )
            threading.Thread(target=pump_output, args=(process.stdout,), daemon=True).start()
        except Exception as exc:
            process = None
            return jsonify({'ok': False, 'error': f'Không khởi chạy được: {exc}'}), 500
    return jsonify({'ok': True, 'message': 'Đã gửi lệnh chạy bot.'})


@app.post('/api/stop')
@login_required
def api_stop():
    global process
    with process_lock:
        p = process
        if p is None or p.poll() is not None:
            process = None
            return jsonify({'ok': True, 'message': 'Bot hiện không chạy.'})
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                p.wait(timeout=2)
        except ProcessLookupError:
            pass
        process = None
        with LOG_PATH.open('a', encoding='utf-8') as out:
            out.write('[Zan Hosting] Đã dừng bot.\n')
    return jsonify({'ok': True, 'message': 'Đã dừng bot.'})


@app.get('/api/logs')
@login_required
def api_logs():
    return jsonify({'ok': True, 'logs': read_logs(), **get_status()})


@app.errorhandler(413)
def too_large(_):
    if request.path.startswith('/api/'):
        return jsonify({'ok': False, 'error': 'Tệp vượt quá giới hạn 2 MB.'}), 413
    return 'Tệp quá lớn (giới hạn 2 MB).', 413



@app.get('/healthz')
def healthz():
    return jsonify({'ok': True, 'service': 'zan-python-host'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '10000'))
    app.run(host='0.0.0.0', port=port)
