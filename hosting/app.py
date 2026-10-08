import os
import subprocess
import threading
import time
import json
import shutil
import signal
import io
import zipfile
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file

app = Flask(__name__)

BOTS_DIR = "bots"
LOGS_DIR = "logs"
META_FILE = "bots_meta.json"
os.makedirs(BOTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

PING_URL = "https://zanhostingz.onrender.com"
PING_INTERVAL = 600

ping_log = []
MAX_LOG = 50
processes = {}
start_times = {}


# ============ META ============
def load_meta():
    if not os.path.exists(META_FILE):
        return {}
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_meta(meta):
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ============ BOT ============
def start_bot(bot_id):
    if bot_id in processes and processes[bot_id].poll() is None:
        return {"status": "already_running"}

    meta = load_meta().get(bot_id, {})
    main_file = meta.get("main_file", "start.py")
    python_ver = meta.get("python_version", "python")

    script = os.path.join(BOTS_DIR, bot_id, main_file)
    if not os.path.exists(script):
        return {"status": "error", "message": f"Không tìm thấy {main_file}"}

    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    log_file = open(log_path, "a", encoding="utf-8")

    # Chọn python
    python_cmd = python_ver if python_ver != "default" else "python"

    try:
        p = subprocess.Popen(
            [python_cmd, main_file],
            stdout=log_file,
            stderr=log_file,
            cwd=os.path.join(BOTS_DIR, bot_id),
            preexec_fn=os.setsid
        )
        processes[bot_id] = p
        start_times[bot_id] = time.time()
        return {"status": "started", "pid": p.pid, "python": python_cmd, "main": main_file}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def stop_bot(bot_id):
    p = processes.get(bot_id)
    if not p or p.poll() is not None:
        return {"status": "not_running"}
    try:
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        time.sleep(1)
        if p.poll() is None:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except:
        pass
    processes.pop(bot_id, None)
    start_times.pop(bot_id, None)
    return {"status": "stopped"}


def restart_bot(bot_id):
    stop_bot(bot_id)
    time.sleep(2)
    return start_bot(bot_id)


def status_bot(bot_id):
    p = processes.get(bot_id)
    if not p:
        return {"status": "stopped"}
    if p.poll() is None:
        uptime = int(time.time() - start_times.get(bot_id, time.time()))
        return {"status": "running", "pid": p.pid, "uptime": uptime}
    return {"status": "stopped"}


def get_bot_log(bot_id, lines=200):
    path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return "\n".join(content.splitlines()[-lines:])
    except:
        return ""


def get_bot_files(bot_id):
    bot_dir = os.path.join(BOTS_DIR, bot_id)
    if not os.path.exists(bot_dir):
        return []
    files = []
    for root, dirs, fs in os.walk(bot_dir):
        for f in fs:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, bot_dir)
            size = os.path.getsize(full)
            files.append({"name": rel, "size": size})
    return files


def list_all_bots():
    meta = load_meta()
    bots = []
    if not os.path.exists(BOTS_DIR):
        return bots
    for name in os.listdir(BOTS_DIR):
        path = os.path.join(BOTS_DIR, name)
        if os.path.isdir(path):
            info = meta.get(name, {})
            bots.append({
                "id": name,
                "status": status_bot(name),
                "created": datetime.fromtimestamp(os.path.getctime(path)).strftime("%d/%m/%Y %H:%M"),
                "main_file": info.get("main_file", "start.py"),
                "python_version": info.get("python_version", "python"),
                "note": info.get("note", "")
            })
    return bots


# ============ PING ============
def ping_loop():
    import requests
    while True:
        try:
            start = time.time()
            r = requests.get(PING_URL, timeout=30)
            elapsed = round(time.time() - start, 2)
            entry = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "date": datetime.now().strftime("%d/%m/%Y"),
                "status": r.status_code,
                "elapsed": f"{elapsed}s",
                "ok": r.status_code == 200
            }
        except Exception as e:
            entry = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "date": datetime.now().strftime("%d/%m/%Y"),
                "status": "LỖI",
                "elapsed": "-",
                "ok": False,
                "error": str(e)
            }
        ping_log.insert(0, entry)
        if len(ping_log) > MAX_LOG:
            ping_log.pop()
        time.sleep(PING_INTERVAL)


# ============ ROUTES ============
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/bots")
def api_bots():
    return jsonify({"bots": list_all_bots()})


@app.route("/api/bots/create", methods=["POST"])
def api_create_bot():
    data = request.get_json() or {}
    bot_id = data.get("bot_id", "").strip()
    main_file = data.get("main_file", "start.py").strip()
    python_version = data.get("python_version", "python").strip()
    note = data.get("note", "").strip()

    if not bot_id:
        return jsonify({"status": "error", "message": "Thiếu ID bot"}), 400
    if not bot_id.replace("_", "").replace("-", "").isalnum():
        return jsonify({"status": "error", "message": "ID chỉ chữ + số + _ -"}), 400

    bot_dir = os.path.join(BOTS_DIR, bot_id)
    if os.path.exists(bot_dir):
        return jsonify({"status": "error", "message": "ID đã tồn tại"}), 400

    os.makedirs(bot_dir, exist_ok=True)

    meta = load_meta()
    meta[bot_id] = {
        "main_file": main_file,
        "python_version": python_version,
        "note": note,
        "created": datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    save_meta(meta)

    return jsonify({"status": "ok", "bot_id": bot_id})


@app.route("/api/bots/<bot_id>/delete", methods=["DELETE"])
def api_delete_bot(bot_id):
    stop_bot(bot_id)
    bot_dir = os.path.join(BOTS_DIR, bot_id)
    if os.path.exists(bot_dir):
        shutil.rmtree(bot_dir)
    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    if os.path.exists(log_path):
        os.remove(log_path)
    meta = load_meta()
    meta.pop(bot_id, None)
    save_meta(meta)
    return jsonify({"status": "ok"})


@app.route("/api/bots/<bot_id>/start", methods=["POST"])
def api_start(bot_id):
    return jsonify(start_bot(bot_id))


@app.route("/api/bots/<bot_id>/stop", methods=["POST"])
def api_stop(bot_id):
    return jsonify(stop_bot(bot_id))


@app.route("/api/bots/<bot_id>/restart", methods=["POST"])
def api_restart(bot_id):
    return jsonify(restart_bot(bot_id))


@app.route("/api/bots/<bot_id>/logs")
def api_logs(bot_id):
    lines = int(request.args.get("lines", 200))
    return jsonify({"logs": get_bot_log(bot_id, lines)})


@app.route("/api/bots/<bot_id>/clear-log", methods=["POST"])
def api_clear_log(bot_id):
    path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    if os.path.exists(path):
        open(path, "w").close()
    return jsonify({"status": "ok"})


@app.route("/api/bots/<bot_id>/files")
def api_files(bot_id):
    return jsonify({"files": get_bot_files(bot_id)})


@app.route("/api/bots/<bot_id>/upload", methods=["POST"])
def api_upload(bot_id):
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Không có file"}), 400

    bot_dir = os.path.join(BOTS_DIR, bot_id)
    os.makedirs(bot_dir, exist_ok=True)

    uploaded = []
    for f in request.files.getlist("file"):
        if not f.filename:
            continue
        # Giữ cấu trúc thư mục (webkitRelativePath)
        rel_path = f.filename
        save_path = os.path.join(bot_dir, rel_path)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        f.save(save_path)
        uploaded.append(rel_path)

    return jsonify({"status": "ok", "files": uploaded})


@app.route("/api/bots/<bot_id>/upload-zip", methods=["POST"])
def api_upload_zip(bot_id):
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Không có file"}), 400

    f = request.files["file"]
    if not f.filename.endswith(".zip"):
        return jsonify({"status": "error", "message": "Chỉ nhận .zip"}), 400

    bot_dir = os.path.join(BOTS_DIR, bot_id)
    os.makedirs(bot_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(io.BytesIO(f.read())) as z:
            z.extractall(bot_dir)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/bots/<bot_id>/file", methods=["GET", "DELETE", "PUT"])
def api_file(bot_id):
    path = request.args.get("path", "")
    if not path:
        return jsonify({"status": "error", "message": "Thiếu path"}), 400

    full = os.path.join(BOTS_DIR, bot_id, path)
    if not os.path.abspath(full).startswith(os.path.abspath(os.path.join(BOTS_DIR, bot_id))):
        return jsonify({"status": "error", "message": "Path không hợp lệ"}), 400

    if request.method == "GET":
        if not os.path.exists(full):
            return jsonify({"status": "error", "message": "File không tồn tại"}), 404
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                return jsonify({"status": "ok", "content": f.read()})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    elif request.method == "DELETE":
        if os.path.exists(full):
            os.remove(full)
        return jsonify({"status": "ok"})

    elif request.method == "PUT":
        data = request.get_json() or {}
        content = data.get("content", "")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"status": "ok"})


@app.route("/api/ping/status")
def api_ping_status():
    last = ping_log[0] if ping_log else None
    return jsonify({
        "target": PING_URL,
        "interval": PING_INTERVAL,
        "last": last,
        "total": len(ping_log),
        "server_time": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })


@app.route("/api/ping/logs")
def api_ping_logs():
    return jsonify({"logs": ping_log})


@app.route("/api/ping/now")
def api_ping_now():
    import requests
    try:
        start = time.time()
        r = requests.get(PING_URL, timeout=30)
        elapsed = round(time.time() - start, 2)
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%d/%m/%Y"),
            "status": r.status_code,
            "elapsed": f"{elapsed}s",
            "ok": r.status_code == 200
        }
        ping_log.insert(0, entry)
        return jsonify({"status": "ok", "result": entry})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


threading.Thread(target=ping_loop, daemon=True).start()
print(f"[PING] Khởi động ping {PING_URL} mỗi {PING_INTERVAL}s")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 2008))
    app.run(host="0.0.0.0", port=port)
