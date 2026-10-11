import os
import sys
import time
import signal
import threading
import subprocess
import io
import re
import shutil
import zipfile
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
LIBS_DIR = RUNTIME_DIR / 'libs'
LIBS_DIR.mkdir(parents=True, exist_ok=True)
PKG_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*(\[[A-Za-z0-9,._-]+\])?([<>=!~]=?[A-Za-z0-9.*]+(,[<>=!~]=?[A-Za-z0-9.*]+)*)?$')
MAX_UPLOAD = 2 * 1024 * 1024          # tối đa 2 MB mỗi tệp
MAX_ZIP = 15 * 1024 * 1024            # tối đa 15 MB cho một tệp .zip
MAX_UNZIPPED = 60 * 1024 * 1024       # tổng dung lượng sau khi giải nén
MAX_REQUEST = 30 * 1024 * 1024        # tối đa 30 MB mỗi lần tải lên
MAX_FILES = 300
HIDDEN_DIRS = {'__pycache__'}

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
pip_proc = None
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
    """Đường dẫn tương đối (có thể có thư mục con) -> Path an toàn trong FILES_DIR, hoặc None."""
    if not name or not isinstance(name, str) or '\x00' in name or '\\' in name:
        return None
    parts = name.split('/')
    if any(p in ('', '.', '..') for p in parts):
        return None
    target = (FILES_DIR / Path(*parts)).resolve()
    try:
        target.relative_to(FILES_DIR.resolve())
    except ValueError:
        return None
    return target


def rel(path):
    return path.resolve().relative_to(FILES_DIR.resolve()).as_posix()


def list_files():
    """Danh sách tệp + thư mục (đệ quy), bỏ qua __pycache__."""
    items = []
    base = FILES_DIR.resolve()
    for f in sorted(base.rglob('*'), key=lambda x: x.relative_to(base).as_posix().lower()):
        r = f.relative_to(base)
        if any(part in HIDDEN_DIRS for part in r.parts):
            continue
        if f.is_symlink():
            continue
        if f.is_dir():
            n = sum(1 for x in f.rglob('*') if x.is_file() and not any(p in HIDDEN_DIRS for p in x.relative_to(base).parts))
            items.append({'name': r.as_posix(), 'is_dir': True, 'size': n, 'mtime': int(f.stat().st_mtime), 'is_py': False})
        elif f.is_file():
            st = f.stat()
            items.append({'name': r.as_posix(), 'is_dir': False, 'size': st.st_size, 'mtime': int(st.st_mtime), 'is_py': f.suffix.lower() == '.py'})
    return items


def get_entry(files=None):
    """Tệp .py sẽ được chạy: ưu tiên tệp đã chọn, rồi start.py/main.py, rồi tệp .py duy nhất."""
    files = files if files is not None else list_files()
    pys = [f['name'] for f in files if f['is_py']]
    try:
        chosen = ENTRY_PATH.read_text(encoding='utf-8').strip()
    except OSError:
        chosen = ''
    if chosen in pys:
        return chosen
    for pref in ('main.py', 'start.py'):
        if pref in pys:
            return pref
    return pys[0] if pys else None


def extract_zip(data, zip_name, status):
    """Giải nén .zip vào FILES_DIR (giữ thư mục con). Trả về (số tệp, danh sách cảnh báo)."""
    warnings = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError(f'{zip_name}: không phải tệp zip hợp lệ.')
    members = [m for m in zf.infolist() if not m.is_dir()]
    clean = []
    for m in members:
        name = m.filename.replace('\\', '/')
        parts = [x for x in name.split('/') if x not in ('', '.')]
        if not parts or any(x == '..' for x in parts) or name.startswith('/') or ':' in parts[0]:
            warnings.append(f'bỏ qua đường dẫn không an toàn “{m.filename}”')
            continue
        if any(x in HIDDEN_DIRS for x in parts) or parts[-1].lower().endswith('.pyc') or parts[0] == '__MACOSX' or parts[-1] == '.DS_Store':
            continue
        clean.append((m, parts))
    if sum(m.file_size for m, _ in clean) > MAX_UNZIPPED:
        raise ValueError(f'{zip_name}: sau khi giải nén vượt {MAX_UNZIPPED // 1024 // 1024} MB.')
    # Nếu tất cả nằm trong đúng 1 thư mục bọc ngoài (vd "99(Copy)/") thì bỏ thư mục đó
    if clean and all(len(p) > 1 for _, p in clean) and len({p[0] for _, p in clean}) == 1:
        clean = [(m, p[1:]) for m, p in clean]
    count = 0
    existing = sum(1 for f in list_files() if not f['is_dir'])
    for m, parts in clean:
        target = safe_path('/'.join(parts))
        if target is None:
            warnings.append(f'bỏ qua “{"/".join(parts)}”')
            continue
        if m.file_size > MAX_UPLOAD:
            warnings.append(f'bỏ qua {"/".join(parts)} (quá 2 MB)')
            continue
        r = '/'.join(parts)
        if status['running'] and r == status['running_script']:
            warnings.append(f'bỏ qua {r} (đang chạy)')
            continue
        if not target.exists():
            if existing >= MAX_FILES:
                warnings.append(f'bỏ qua {r} (đã đạt tối đa {MAX_FILES} tệp)')
                continue
            existing += 1
        if target.is_dir():
            warnings.append(f'bỏ qua {r} (trùng tên thư mục)')
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(zf.read(m))
        count += 1
    return count, warnings


def get_status():
    global process, running_script
    with process_lock:
        p = process
        running = p is not None and p.poll() is None
        if p is not None and not running:
            process = None
            running_script = None
        files = list_files()
        installing = pip_proc is not None and pip_proc.poll() is None
        return {
            'installing': installing,
            'running': running,
            'running_script': running_script if running else None,
            'uploaded': any(f['is_py'] for f in files),
            'file_count': sum(1 for f in files if not f['is_dir']),
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
    existing = {f['name'] for f in list_files() if not f['is_dir']}
    for f in uploads:
        name = secure_filename(f.filename or '')
        if not name:
            errors.append(f'“{f.filename}”: tên tệp không hợp lệ (hãy đặt tên chữ/số, ví dụ bot.json).')
            continue
        is_zip = name.lower().endswith('.zip')
        limit = MAX_ZIP if is_zip else MAX_UPLOAD
        data = f.read(limit + 1)
        if len(data) > limit:
            errors.append(f'{name}: vượt quá giới hạn {limit // 1024 // 1024} MB.')
            continue
        if is_zip and zipfile.is_zipfile(io.BytesIO(data)):
            try:
                n, warns = extract_zip(data, name, status)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            saved.append(f'{name} (giải nén {n} tệp)')
            if warns:
                errors.append(f'{name}: ' + '; '.join(warns[:5]) + ('…' if len(warns) > 5 else '') + '.')
            with LOG_PATH.open('a', encoding='utf-8') as out:
                out.write(f'\n[Zan Hosting] Đã tải lên {name} và giải nén {n} tệp.\n')
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
        msg += ' Lưu ý: ' + ' '.join(errors)
    return jsonify({'ok': True, 'message': msg, 'saved': saved})


@app.post('/api/delete')
@login_required
def api_delete():
    data = request.get_json(silent=True) or {}
    path = safe_path(data.get('name'))
    if path is None or not path.exists() or path == FILES_DIR.resolve():
        return jsonify({'ok': False, 'error': 'Không tìm thấy tệp.'}), 404
    r = rel(path)
    status = get_status()
    run = status['running_script']
    if status['running'] and run and (r == run or (path.is_dir() and run.startswith(r + '/'))):
        return jsonify({'ok': False, 'error': 'Tệp này đang chạy, hãy Stop bot trước khi xóa.'}), 409
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    with LOG_PATH.open('a', encoding='utf-8') as out:
        out.write(f'\n[Zan Hosting] Đã xóa {r}.\n')
    return jsonify({'ok': True, 'message': f'Đã xóa {r}.'})


@app.post('/api/entry')
@login_required
def api_entry():
    data = request.get_json(silent=True) or {}
    path = safe_path(data.get('name'))
    if path is None or not path.is_file() or path.suffix.lower() != '.py':
        return jsonify({'ok': False, 'error': 'Chỉ chọn được tệp .py đã tải lên.'}), 400
    ENTRY_PATH.write_text(rel(path), encoding='utf-8')
    return jsonify({'ok': True, 'message': f'Sẽ chạy {rel(path)} khi Start.'})


def _pip_worker(proc):
    global pip_proc
    try:
        with LOG_PATH.open('a', encoding='utf-8', errors='replace') as out:
            for line in iter(proc.stdout.readline, ''):
                out.write(line)
                out.flush()
            code = proc.wait()
            out.write(f'[Zan Hosting] pip kết thúc (mã {code}). ' + ('Cài xong, bấm Start lại bot.' if code == 0 else 'Có lỗi, xem log ở trên.') + '\n')
    finally:
        with process_lock:
            if pip_proc is proc:
                pip_proc = None


@app.post('/api/pip')
@login_required
def api_pip():
    """Cài thư viện: từ requirements.txt đã upload, hoặc danh sách gói gửi lên."""
    global pip_proc
    data = request.get_json(silent=True) or {}
    raw = str(data.get('packages') or '').split()
    pkgs = [x for x in raw if x]
    if pkgs:
        bad = [x for x in pkgs if not PKG_RE.match(x)]
        if bad:
            return jsonify({'ok': False, 'error': 'Tên gói không hợp lệ: ' + ', '.join(bad[:3])}), 400
        if len(pkgs) > 30:
            return jsonify({'ok': False, 'error': 'Tối đa 30 gói mỗi lần.'}), 400
        target = pkgs
        label = ', '.join(pkgs)
    else:
        req = FILES_DIR / 'requirements.txt'
        if not req.is_file():
            return jsonify({'ok': False, 'error': 'Chưa có requirements.txt. Hãy upload nó hoặc nhập tên gói.'}), 400
        target = ['-r', str(req)]
        label = 'requirements.txt'
    with process_lock:
        if pip_proc is not None and pip_proc.poll() is None:
            return jsonify({'ok': False, 'error': 'Đang cài thư viện rồi, vui lòng chờ.'}), 409
        with LOG_PATH.open('a', encoding='utf-8') as out:
            out.write(f'\n[Zan Hosting] Bắt đầu cài thư viện ({label}) lúc {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        try:
            pip_proc = subprocess.Popen(
                [sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-input',
                 '--target', str(LIBS_DIR), '--upgrade'] + target,
                cwd=str(FILES_DIR), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
        except Exception as exc:
            pip_proc = None
            return jsonify({'ok': False, 'error': f'Không chạy được pip: {exc}'}), 500
        threading.Thread(target=_pip_worker, args=(pip_proc,), daemon=True).start()
    return jsonify({'ok': True, 'message': f'Đang cài {label}… xem tiến trình ở nhật ký.'})


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
        if pip_proc is not None and pip_proc.poll() is None:
            return jsonify({'ok': False, 'error': 'Đang cài thư viện, chờ cài xong rồi Start.'}), 409
        with LOG_PATH.open('a', encoding='utf-8') as out:
            out.write(f'\n[Zan Hosting] Start {rel(script)} lúc {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
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
                env={**os.environ, 'PYTHONUNBUFFERED': '1', 'PYTHONPATH': os.pathsep.join(x for x in (str(FILES_DIR), str(LIBS_DIR), os.environ.get('PYTHONPATH', '')) if x)}
            )
            running_script = rel(script)
            threading.Thread(target=pump_output, args=(process.stdout,), daemon=True).start()
        except Exception as exc:
            process = None
            running_script = None
            return jsonify({'ok': False, 'error': f'Không khởi chạy được: {exc}'}), 500
    return jsonify({'ok': True, 'message': f'Đã gửi lệnh chạy {rel(script)}.'})


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
        return jsonify({'ok': False, 'error': 'Tổng dung lượng tải lên quá lớn (tối đa 30 MB mỗi lần).'}), 413
    return 'Tệp quá lớn.', 413



@app.get('/healthz')
def healthz():
    return jsonify({'ok': True, 'service': 'zan-python-host'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '10000'))
    app.run(host='0.0.0.0', port=port)
