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
FILES_DIR = RUNTIME_DIR / 'files'
FILES_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = RUNTIME_DIR / 'bot.log'
ENTRY_PATH = RUNTIME_DIR / 'entry.txt'
MAX_UPLOAD = 2 * 1024 * 1024          # tối đa 2 MB mỗi tệp
MAX_REQUEST = 20 * 1024 * 1024        # tối đa 20 MB mỗi lần tải lên
MAX_FILES = 100

# Chuyển main.py cũ (bản trước) sang thư mục files nếu có
_old_main = RUNTIME_DIR / 'main.py'
if _old_main.exists() and not (FILES_DIR / 'main.py').exists():
    try:
        _old_main.replace(FILES_DIR / 'main.py')
    except OSError:
        pass

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-this-secret-before-deploying')
app.config['MAX_CONTENT_LENGTH'] = MAX_REQUEST
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
process = None
running_script = None
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
        return 'Chưa có nhật ký. Hãy tải tệp .py lên rồi nhấn Start.'


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


def safe_path(name):
    """Trả về đường dẫn an toàn bên trong FILES_DIR hoặc None."""
    clean = secure_filename(name or '')
    if not clean or clean != (name or ''):
        return None
    return FILES_DIR / clean


def list_files():
    items = []
    for f in sorted(FILES_DIR.iterdir(), key=lambda x: x.name.lower()):
        if f.is_file():
            st = f.stat()
            items.append({
                'name': f.name,
                'size': st.st_size,
                'mtime': int(st.st_mtime),
                'is_py': f.suffix.lower() == '.py',
            })
    return items


def get_entry(files=None):
    """Tệp .py sẽ được chạy: ưu tiên tệp đã chọn, rồi main.py, rồi tệp .py duy nhất."""
    files = files if files is not None else list_files()
    pys = [f['name'] for f in files if f['is_py']]
    try:
        chosen = ENTRY_PATH.read_text(encoding='utf-8').strip()
    except OSError:
        chosen = ''
    if chosen in pys:
        return chosen
    if 'main.py' in pys:
        return 'main.py'
    return pys[0] if pys else None


def get_status():
    global process, running_script
    with process_lock:
        p = process
        running = p is not None and p.poll() is None
        if p is not None and not running:
            process = None
            running_script = None
        files = list_files()
        return {
            'running': running,
            'running_script': running_script if running else None,
            'uploaded': any(f['is_py'] for f in files),
            'file_count': len(files),
            'entry': get_entry(files),
            'filename': get_entry(files),
        }


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


@app.get('/api/files')
@login_required
def api_files():
    files = list_files()
    return jsonify({'ok': True, 'files': files, 'entry': get_entry(files), **{k: v for k, v in get_status().items() if k in ('running', 'running_script')}})


@app.post('/api/upload')
@login_required
def api_upload():
    uploads = [f for f in request.files.getlist('file') if f and f.filename]
    if not uploads:
        return jsonify({'ok': False, 'error': 'Chưa chọn tệp.'}), 400
    status = get_status()
    saved, errors = [], []
    existing = {f['name'] for f in list_files()}
    for f in uploads:
        name = secure_filename(f.filename or '')
        if not name:
            errors.append(f'“{f.filename}”: tên tệp không hợp lệ (hãy đặt tên chữ/số, ví dụ bot.json).')
            continue
        data = f.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            errors.append(f'{name}: vượt quá giới hạn 2 MB.')
            continue
        if status['running'] and name == status['running_script']:
            errors.append(f'{name}: đang chạy, hãy Stop bot trước khi thay tệp này.')
            continue
        if name not in existing and len(existing) >= MAX_FILES:
            errors.append(f'{name}: đã đạt tối đa {MAX_FILES} tệp.')
            continue
        (FILES_DIR / name).write_bytes(data)
        existing.add(name)
        saved.append(name)
        with LOG_PATH.open('a', encoding='utf-8') as out:
            out.write(f'\n[Zan Hosting] Đã tải lên {name} ({len(data)} bytes).\n')
    if not saved:
        return jsonify({'ok': False, 'error': ' '.join(errors)}), 400
    msg = 'Đã tải lên: ' + ', '.join(saved) + '.'
    if errors:
        msg += ' Bỏ qua: ' + ' '.join(errors)
    return jsonify({'ok': True, 'message': msg, 'saved': saved})


@app.post('/api/delete')
@login_required
def api_delete():
    data = request.get_json(silent=True) or {}
    path = safe_path(data.get('name'))
    if path is None or not path.is_file():
        return jsonify({'ok': False, 'error': 'Không tìm thấy tệp.'}), 404
    status = get_status()
    if status['running'] and path.name == status['running_script']:
        return jsonify({'ok': False, 'error': 'Tệp này đang chạy, hãy Stop bot trước khi xóa.'}), 409
    path.unlink()
    with LOG_PATH.open('a', encoding='utf-8') as out:
        out.write(f'\n[Zan Hosting] Đã xóa {path.name}.\n')
    return jsonify({'ok': True, 'message': f'Đã xóa {path.name}.'})


@app.post('/api/entry')
@login_required
def api_entry():
    data = request.get_json(silent=True) or {}
    path = safe_path(data.get('name'))
    if path is None or not path.is_file() or path.suffix.lower() != '.py':
        return jsonify({'ok': False, 'error': 'Chỉ chọn được tệp .py đã tải lên.'}), 400
    ENTRY_PATH.write_text(path.name, encoding='utf-8')
    return jsonify({'ok': True, 'message': f'Sẽ chạy {path.name} khi Start.'})


@app.post('/api/start')
@login_required
def api_start():
    global process, running_script
    data = request.get_json(silent=True) or {}
    name = data.get('name') or get_entry()
    script = safe_path(name) if name else None
    if script is None or not script.is_file() or script.suffix.lower() != '.py':
        return jsonify({'ok': False, 'error': 'Bạn cần tải tệp .py lên và chọn tệp để chạy.'}), 400
    with process_lock:
        if process is not None and process.poll() is None:
            return jsonify({'ok': False, 'error': 'Bot đang chạy rồi.'}), 409
        with LOG_PATH.open('a', encoding='utf-8') as out:
            out.write(f'\n[Zan Hosting] Start {script.name} lúc {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        try:
            process = subprocess.Popen(
                [sys.executable, '-u', str(script)],
                cwd=str(FILES_DIR),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}
            )
            running_script = script.name
            threading.Thread(target=pump_output, args=(process.stdout,), daemon=True).start()
        except Exception as exc:
            process = None
            running_script = None
            return jsonify({'ok': False, 'error': f'Không khởi chạy được: {exc}'}), 500
    return jsonify({'ok': True, 'message': f'Đã gửi lệnh chạy {script.name}.'})


@app.post('/api/stop')
@login_required
def api_stop():
    global process, running_script
    with process_lock:
        p = process
        if p is None or p.poll() is not None:
            process = None
            running_script = None
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
        running_script = None
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
        return jsonify({'ok': False, 'error': 'Tổng dung lượng tải lên quá lớn (tối đa 20 MB mỗi lần, 2 MB mỗi tệp).'}), 413
    return 'Tệp quá lớn.', 413



@app.get('/healthz')
def healthz():
    return jsonify({'ok': True, 'service': 'zan-python-host'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '10000'))
    app.run(host='0.0.0.0', port=port)
