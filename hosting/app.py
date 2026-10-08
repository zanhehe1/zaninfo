
import os
import subprocess
import threading
import time
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file
import io

app = Flask(__name__)

# ============ CẤU HÌNH ============
BOTS_DIR = "bots"
LOGS_DIR = "logs"
os.makedirs(BOTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

PING_URL = "https://zanhostingz.onrender.com"
PING_INTERVAL = 600

ping_log = []
MAX_LOG = 50
processes = {}


# ============ QUẢN LÝ BOT ============
def start_bot(bot_id):
    if bot_id in processes and processes[bot_id].poll() is None:
        return {"status": "already_running"}

    script = os.path.join(BOTS_DIR, bot_id, "start.py")
    if not os.path.exists(script):
        return {"status": "error", "message": "Không tìm thấy start.py"}

    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    log_file = open(log_path, "a", encoding="utf-8")

    p = subprocess.Popen(
        ["python", "start.py"],
        stdout=log_file,
        stderr=log_file,
        cwd=os.path.join(BOTS_DIR, bot_id),
        preexec_fn=os.setsid
    )
    processes[bot_id] = p
    return {"status": "started", "pid": p.pid}


def stop_bot(bot_id):
    p = processes.get(bot_id)
    if not p or p.poll() is not None:
        return {"status": "not_running"}
    try:
        import signal
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        time.sleep(1)
        if p.poll() is None:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except:
        pass
    processes.pop(bot_id, None)
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
        return {"status": "running", "pid": p.pid}
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


def list_all_bots():
    bots = []
    if not os.path.exists(BOTS_DIR):
        return bots
    for name in os.listdir(BOTS_DIR):
        path = os.path.join(BOTS_DIR, name)
        if os.path.isdir(path):
            bots.append({
                "id": name,
                "status": status_bot(name),
                "created": datetime.fromtimestamp(os.path.getctime(path)).strftime("%d/%m/%Y %H:%M")
            })
    return bots


# ============ PING LOOP ============
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
            print(f"[PING] {entry['time']} - {r.status_code} - {elapsed}s")
        except Exception as e:
            entry = {
                "time": datetime.now().strftime("%H:%M:%S"),
                "date": datetime.now().strftime("%d/%m/%Y"),
                "status": "LỖI",
                "elapsed": "-",
                "ok": False,
                "error": str(e)
            }
            print(f"[PING] {entry['time']} - LỖI: {e}")

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


@app.route("/api/bots/<bot_id>/upload", methods=["POST"])
def api_upload(bot_id):
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Không có file"}), 400

    f = request.files["file"]
    bot_dir = os.path.join(BOTS_DIR, bot_id)
    os.makedirs(bot_dir, exist_ok=True)
    save_path = os.path.join(bot_dir, f.filename)
    f.save(save_path)
    return jsonify({"status": "ok", "filename": f.filename})


@app.route("/api/bots/create", methods=["POST"])
def api_create_bot():
    data = request.get_json() or {}
    bot_id = data.get("bot_id", "").strip()
    if not bot_id:
        return jsonify({"status": "error", "message": "Thiếu ID"}), 400
    if not bot_id.replace("_", "").replace("-", "").isalnum():
        return jsonify({"status": "error", "message": "ID không hợp lệ"}), 400

    bot_dir = os.path.join(BOTS_DIR, bot_id)
    if os.path.exists(bot_dir):
        return jsonify({"status": "error", "message": "ID đã tồn tại"}), 400

    os.makedirs(bot_dir, exist_ok=True)
    return jsonify({"status": "ok", "bot_id": bot_id})


@app.route("/api/bots/<bot_id>/delete", methods=["DELETE"])
def api_delete_bot(bot_id):
    import shutil
    stop_bot(bot_id)
    bot_dir = os.path.join(BOTS_DIR, bot_id)
    if os.path.exists(bot_dir):
        shutil.rmtree(bot_dir)
    log_path = os.path.join(LOGS_DIR, f"{bot_id}.log")
    if os.path.exists(log_path):
        os.remove(log_path)
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


# ============ START ============
threading.Thread(target=ping_loop, daemon=True).start()
print(f"[PING] Khởi động ping {PING_URL} mỗi {PING_INTERVAL}s")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 2008))
    app.run(host="0.0.0.0", port=port)
