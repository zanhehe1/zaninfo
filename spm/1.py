#!/usr/bin/env python3
import asyncio
import json
import os
import random
import sys
import time
import threading
from collections import deque
from datetime import datetime

try:
    from aiohttp import web
except ImportError:
    os.system("pip install aiohttp -q")
    from aiohttp import web

try:
    import requests
except ImportError:
    os.system("pip install requests -q")
    import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import ttoan
from ReQAPI import FreeFireAPI

# ================== CONFIG ==================
MAX_ACCOUNTS = 10000
MAX_CONCURRENT_LOGIN = 50
LOGIN_RETRY = 3

MEMBER_WAIT_AFTER_OUT = 0.05
LEAVE_WAIT = 1.0
HEARTBEAT_INTERVAL = 8.0
KA_BYTES = bytes.fromhex("0215")

ROTATOR_INTERVAL = 15.0
LEADER_SUPERVISOR_INTERVAL = 5.0
MAX_TRIES_PER_GEN = 50
MAX_FAILED_CACHE = 5000
STATS_INTERVAL = 60.0
WATCH_INTERVAL = 0.5

T_LEAVE_OLD = 0.2
T_AUTH_CHAT = 0.1
T_CHAT_SEND = 0.15
T_EXIT = 0.05
T_QUIT = 0.03

HTTP_HOST = "0.0.0.0"
HTTP_PORT = int(os.environ.get("PORT", 2026))  # Render set $PORT

INSTANCE_ID = os.environ.get("INSTANCE_ID", "")
AC_FILENAME = os.environ.get("AC_FILE", "ac.json")
AC_FILE = os.path.join(BASE_DIR, AC_FILENAME)
CFG_FILE = os.path.join(BASE_DIR, "ttoan.txt")
INDEX_FILE = os.path.join(BASE_DIR, "index.html")

API_URL = "https://zanspm.onrender.com"
API_INTERVAL = 300
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# ================== COLORS ==================
class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    GREEN = "\033[38;5;46m"; RED = "\033[38;5;196m"; CYAN = "\033[38;5;51m"
    MAGENTA = "\033[38;5;201m"; YELLOW = "\033[38;5;226m"; GRAY = "\033[38;5;245m"
    WHITE = "\033[38;5;255m"

# ================== STATE ==================
class STATE:
    codes = {}
    codes_lock = asyncio.Lock()
    code_generation = 0
    failed_codes = set()
    failed_lock = asyncio.Lock()

    total_join_attempts = 0
    total_join_success = 0
    total_join_fail = 0
    total_spam_sent = 0
    start_time = time.time()

stop_flag = None
file_lock = asyncio.Lock()
accounts_ref_global = []
CHAT_LOCK = asyncio.Lock()

# ================== DASHBOARD STATE ==================
LOG_BUFFER = deque(maxlen=3000)
LOG_LOCK = threading.Lock()
API_STATE = {
    "api_last_ok": None, "api_last_ms": None, "api_last_error": None,
    "started_at": datetime.now().isoformat(timespec="seconds"),
}

_orig_print = print
def _log(level, msg):
    line = f"[{time.strftime('%H:%M:%S')}] [{level.upper()}] {msg}"
    with LOG_LOCK:
        LOG_BUFFER.append(line)

def log_hook(*args, **kwargs):
    try:
        s = " ".join(str(a) for a in args)
        low = s.lower()
        if "✗" in s or "err:" in low or "error" in low:
            lvl = "error"
        elif "✓" in s:
            lvl = "ok"
        elif "[http]" in low:
            lvl = "info"
        elif "[watch]" in low or "[sys]" in low:
            lvl = "info"
        elif "[login]" in low:
            lvl = "ok" if "✓" in s else "error"
        elif "[stop]" in low or "ctrl+c" in low:
            lvl = "warn"
        else:
            lvl = "info"
        _log(lvl, s)
    except Exception:
        pass
    return _orig_print(*args, **kwargs)

print = log_hook

# ================== (GIỮ NGUYÊN TOÀN BỘ LOGIC BOT CỦA 1.py GỐC) ==================
# ... dán nguyên phần compute_leader_count, ts, log_rotator, log_login, log_join,
# print_stats, load_config, load_accounts, remove_from_json, login_one, setup_acc,
# login_with_retry, close_acc, read_0500, heartbeat_loop, rotate_team,
# leader_rotator, leader_supervisor, try_join_once, do_chat, spam_cycle,
# worker_loop, stats_loop, file_watcher ở đây (giữ y nguyên) ...

# ================== HTTP ROUTES (DASHBOARD) ==================
LOGIN_HTML = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>Login</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
    background:radial-gradient(1200px 600px at 20% 0%,#1b2a4a,#0b1020 60%);
    font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial;color:#e6edf3}
  .card{width:min(420px,92vw);padding:32px 28px;border-radius:18px;
    background:rgba(20,28,46,.85);border:1px solid rgba(120,170,255,.15);
    box-shadow:0 20px 60px rgba(0,0,0,.5);backdrop-filter:blur(10px)}
  h1{margin:0 0 6px;font-size:22px}p.sub{margin:0 0 22px;color:#8fa3c0;font-size:14px}
  label{display:block;font-size:13px;color:#9fb2cc;margin-bottom:6px}
  input{width:100%;padding:12px 14px;border-radius:10px;border:1px solid rgba(120,170,255,.2);
    background:#0d1527;color:#e6edf3;font-size:15px;outline:none;box-sizing:border-box}
  button{width:100%;margin-top:18px;padding:12px;border:none;border-radius:10px;
    background:linear-gradient(135deg,#4f8cff,#2f6bff);color:#fff;font-weight:600;font-size:15px;cursor:pointer}
  .err{margin-top:14px;color:#ff8080;font-size:13px}
</style></head><body>
<form class="card" method="POST" action="/login">
  <h1>ZansPM Dashboard</h1>
  <p class="sub">Vui lòng đăng nhập để sử dụng</p>
  <label for="pw">Mật khẩu</label>
  <input id="pw" name="password" type="password" autofocus required>
  <button type="submit">Đăng nhập</button>
  <div class="err">{error}</div>
</form></body></html>"""

def _cookie_auth(request):
    return request.cookies.get("auth") == "1"

async def handle_login(request):
    if request.method == "POST":
        form = await request.post()
        if form.get("password") == ADMIN_PASSWORD:
            resp = web.HTTPFound("/")
            resp.set_cookie("auth", "1", httponly=True, max_age=86400)
            return resp
        return web.Response(text=LOGIN_HTML.replace("{error}", "Sai mật khẩu"), content_type="text/html")
    return web.Response(text=LOGIN_HTML.replace("{error}", ""), content_type="text/html")

async def handle_logout(request):
    resp = web.HTTPFound("/login")
    resp.del_cookie("auth")
    return resp

async def handle_index(request):
    if not _cookie_auth(request):
        raise web.HTTPFound("/login")
    if not os.path.exists(INDEX_FILE):
        return web.Response(text="index.html not found", status=404)
    return web.FileResponse(INDEX_FILE)

async def handle_api_stats(request):
    if not _cookie_auth(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    return web.json_response({
        "total_bots": len(accounts_ref_global),
        "running": len(accounts_ref_global),
        "joined": STATE.total_join_success,
        "failed": STATE.total_join_fail,
        "api_last_ok": API_STATE["api_last_ok"],
        "api_last_ms": API_STATE["api_last_ms"],
        "api_last_error": API_STATE["api_last_error"],
        "started_at": API_STATE["started_at"],
    })

async def handle_api_logs(request):
    if not _cookie_auth(request):
        return web.json_response({"error": "unauthorized"}, status=401)
    after = int(request.query.get("after", 0))
    with LOG_LOCK:
        logs = list(LOG_BUFFER)
    return web.json_response({"total": len(logs), "lines": logs[after:]})

# ================== API PING 5 PHÚT ==================
def api_pinger():
    while True:
        try:
            t0 = time.time()
            r = requests.get(API_URL, timeout=15)
            ms = int((time.time() - t0) * 1000)
            API_STATE["api_last_ok"] = datetime.now().isoformat(timespec="seconds")
            API_STATE["api_last_ms"] = ms
            API_STATE["api_last_error"] = None
            _log("api", f"Ping {API_URL} → {r.status_code} ({ms}ms)")
        except Exception as e:
            API_STATE["api_last_error"] = str(e)
            _log("api", f"Ping {API_URL} lỗi: {e}")
        time.sleep(API_INTERVAL)

# ================== HTTP SERVER ==================
async def start_dashboard():
    app = web.Application()
    app.router.add_get("/login", handle_login)
    app.router.add_post("/login", handle_login)
    app.router.add_get("/logout", handle_logout)
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/stats", handle_api_stats)
    app.router.add_get("/api/logs", handle_api_logs)
    # giữ endpoint cũ /stats /status /chat
    app.router.add_get("/stats", handle_stats)
    app.router.add_get("/status", handle_status)
    app.router.add_get("/chat", handle_chat)
    runner = web.AppRunner(app)
    await runner.setup()
    for port in range(HTTP_PORT, HTTP_PORT + 20):
        try:
            site = web.TCPSite(runner, HTTP_HOST, port)
            await site.start()
            _log("info", f"Dashboard http://{HTTP_HOST}:{port}")
            _log("info", f"Chat API: http://127.0.0.1:{port}/chat?tc=TEAMCODE")
            print(f"{C.GREEN}[HTTP]{C.RESET} Dashboard → http://{HTTP_HOST}:{port}", flush=True)
            return
        except OSError:
            continue
    _log("error", "Không tìm được port trống")

# ================== MAIN ==================
async def main():
    global stop_flag, accounts_ref_global

    # ghi đè start_http_server cũ bằng dashboard
    globals()["start_http_server"] = start_dashboard

    cfg = load_config()
    accs = load_accounts()
    n = len(accs)
    if n > 0:
        print(f"{C.CYAN}[ACC]{C.RESET} {n} acc trong {AC_FILENAME}")
    else:
        print(f"{C.CYAN}[ACC]{C.RESET} 0 acc trong {AC_FILENAME}")

    print(f"{C.CYAN}[CFG]{C.RESET} Chat: {cfg['chat'][:80]}")
    print(f"{C.MAGENTA}[SYS]{C.RESET} Đổi code mỗi {ROTATOR_INTERVAL}s")

    stop_evt = asyncio.Event()
    stop_flag = stop_evt
    accounts_ref = []
    accounts_ref_global = accounts_ref
    login_sem = asyncio.Semaphore(MAX_CONCURRENT_LOGIN)
    worker_tasks = []

    def spawn_worker(acc, wid):
        worker_tasks.append(asyncio.create_task(worker_loop(acc, wid, cfg, stop_evt)))

    watcher_task = asyncio.create_task(file_watcher(accounts_ref, spawn_worker, login_sem, stop_evt))
    supervisor_task = asyncio.create_task(leader_supervisor(accounts_ref, stop_evt))
    hb_task = asyncio.create_task(heartbeat_loop(accounts_ref, stop_evt))
    stats_task = asyncio.create_task(stats_loop(stop_evt))

    # ping API 5 phút (thread riêng)
    threading.Thread(target=api_pinger, daemon=True).start()

    try:
        await start_dashboard()
    except Exception as e:
        print(f"{C.RED}[HTTP] Không start được: {e}{C.RESET}", flush=True)

    try:
        await asyncio.gather(watcher_task, supervisor_task, hb_task, stats_task, return_exceptions=True)
    except asyncio.CancelledError:
        pass
    finally:
        stop_evt.set()
        for t in [watcher_task, supervisor_task, hb_task, stats_task] + worker_tasks:
            if not t.done():
                t.cancel()
        for acc in accounts_ref:
            close_acc_sync(acc)
        print_stats()

def close_acc_sync(acc):
    for w_key in ("on_w", "ch_w"):
        w = acc.get(w_key)
        if w:
            try: w.close()
            except: pass

if __name__ == "__main__":
    print(f"{C.MAGENTA}[SYS]{C.RESET} Chạy: python 1.py")
    print(f"{C.MAGENTA}[SYS]{C.RESET} Dashboard: mở http://localhost:{HTTP_PORT} — mật khẩu admin123")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}[CTRL+C]{C.RESET}")
