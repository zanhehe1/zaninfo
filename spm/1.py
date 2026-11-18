#!/usr/bin/env python3
import asyncio
import json
import os
import random
import re
import sys
import time
import threading
from collections import deque

try:
    import aiohttp
    from aiohttp import web
except ImportError:
    os.system("pip install aiohttp -q")
    import aiohttp
    from aiohttp import web

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

# ================== CONFIG BOT ==================
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

BOT_API_PORT = 2026
API_PING_URL = os.environ.get("API_PING_URL", "https://zanspm.onrender.com")
API_PING_INTERVAL = 300

AC_FILENAME = os.environ.get("AC_FILE", "ac.json")
AC_FILE = os.path.join(BASE_DIR, AC_FILENAME)
CFG_FILE = os.path.join(BASE_DIR, "ttoan.txt")

class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    GREEN = "\033[38;5;46m"; RED = "\033[38;5;196m"; CYAN = "\033[38;5;51m"
    MAGENTA = "\033[38;5;201m"; YELLOW = "\033[38;5;226m"; GRAY = "\033[38;5;245m"

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
API_STATE = {"api_last_ok": None, "api_last_ms": None, "api_last_error": None}

LOG_BUFFER = deque(maxlen=2000)
LOG_SEQ = 0
LOG_LOCK = threading.Lock()

class LogTee:
    def __init__(self, stream):
        self.stream = stream
        self.pending = ""
    def write(self, value):
        global LOG_SEQ
        if not isinstance(value, str): value = str(value)
        result = self.stream.write(value)
        self.stream.flush()
        self.pending += value
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            if line.strip():
                with LOG_LOCK:
                    LOG_SEQ += 1
                    LOG_BUFFER.append({"id": LOG_SEQ, "line": line.rstrip("\r")})
        return result
    def flush(self): self.stream.flush()
    def isatty(self): return getattr(self.stream, "isatty", lambda: False)()
    @property
    def encoding(self): return getattr(self.stream, "encoding", "utf-8")

# ================== HELPERS BOT ==================
def compute_leader_count(n_acc):
    if n_acc <= 0: return 0
    if n_acc < 50: return 1
    return min(8, (n_acc // 1000) + 1)

def ts(): return time.strftime("%H:%M:%S")

def log_rotator(leader_idx, code):
    print(f"{C.GRAY}{ts()}{C.RESET} {C.MAGENTA}[L{leader_idx+1}]{C.RESET} → {C.BOLD}{code}{C.RESET}", flush=True)

def log_login(uid, ok, nick=""):
    if ok:
        print(f"{C.GRAY}{ts()}{C.RESET} {C.GREEN}[LOGIN]{C.RESET} {uid} ✓ {nick} | BOT [{len(accounts_ref_global)}]", flush=True)
    else:
        print(f"{C.GRAY}{ts()}{C.RESET} {C.RED}[LOGIN]{C.RESET} {uid} ✗ {nick}", flush=True)

def log_join(worker_id, nick, code, ok, detail=""):
    if not ok: return
    print(f"{C.GRAY}{ts()}{C.RESET} {C.GREEN}[W{worker_id:03d}] {nick[:10].ljust(10)} {code} ✓ {detail}{C.RESET}", flush=True)

def print_stats():
    elapsed = time.time() - STATE.start_time
    h, rem = divmod(int(elapsed), 3600)
    m, s = divmod(rem, 60)
    rate = (STATE.total_join_success / STATE.total_join_attempts * 100) if STATE.total_join_attempts > 0 else 0
    codes_str = ", ".join(STATE.codes[k] for k in sorted(STATE.codes)) or "-"
    code_per_hour = STATE.total_join_success / max(elapsed, 1) * 3600
    print()
    print(f"{C.CYAN}{'='*58}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} BOT online: {C.GREEN}{len(accounts_ref_global)}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} Leaders: {len(STATE.codes)}   Gen: {STATE.code_generation}")
    print(f"{C.CYAN}|{C.RESET} Codes: {codes_str}")
    print(f"{C.CYAN}|{C.RESET} Join: {C.GREEN}{STATE.total_join_success}{C.RESET}/{STATE.total_join_attempts} ({rate:.0f}%)   Fail: {C.RED}{STATE.total_join_fail}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} Spam: {STATE.total_spam_sent}   Code/giờ: {C.YELLOW}{code_per_hour:.0f}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} Uptime: {h:02d}:{m:02d}:{s:02d}")
    print(f"{C.CYAN}{'='*58}{C.RESET}")
    print()

def load_config():
    if not os.path.exists(CFG_FILE): return {"chat": "Contact @zanxgay"}
    chat_lines, current = [], None
    with open(CFG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            s = line.rstrip("\n")
            st = s.strip()
            if st.upper() == "[CHAT]": current = "chat"; continue
            if st.upper() == "[GHOST]": current = "ghost"; continue
            if st.startswith("#"): continue
            if current == "chat": chat_lines.append(s)
    return {"chat": "\n".join(chat_lines).strip() or "Contact @zanxgay"}

def load_accounts():
    if not os.path.exists(AC_FILE): return {}
    try:
        with open(AC_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

async def remove_from_json(uid):
    async with file_lock:
        try:
            with open(AC_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            if uid in data:
                del data[uid]
                tmp = AC_FILE + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
                os.replace(tmp, AC_FILE)
                return True
        except: pass
    return False

async def login_one(uid, password):
    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, lambda: FreeFireAPI().get(f"{uid}:{password}"))
    except: return None
    if not data or 'account not found' in str(data): return None
    return data

async def setup_acc(uid, password):
    data = await login_one(uid, password)
    if not data: return None

    acc_id = int(data["UserAccountUID"])
    token = data["UserAuthToken"]
    key = bytes(data["key"])
    iv = bytes(data["iv"])
    login_time = int(data.get("LoginTime", 0) or 0) or int(time.time())
    nickname = data.get("logindata", {}).get("4", str(acc_id))
    gs = data.get("GameServerAddress", {})
    logindata = data.get("logindata", {})
    region = data.get("LockRegion", "VN")
    rc = ttoan.get_region_code(logindata, region)

    try:
        on_r, on_w = await asyncio.open_connection(gs["onlineip"], int(gs["onlineport"]))
        on_w.write(ttoan.build_online_auth(acc_id, token, login_time, key, iv))
        await on_w.drain()
        await asyncio.sleep(0.3)
    except: return None

    ch_r = ch_w = None
    try:
        ch_r, ch_w = await asyncio.open_connection(gs["chatip"], int(gs["chatport"]))
        ch_w.write(ttoan.build_chat_auth(acc_id, token, login_time, key, iv))
        await ch_w.drain()
        await asyncio.sleep(0.3)
        ch_w.write(KA_BYTES)
        await ch_w.drain()
    except: ch_r = ch_w = None

    return {"uid": uid, "acc_id": acc_id, "nickname": nickname, "key": key, "iv": iv, "rc": rc, "region": region, "on_r": on_r, "on_w": on_w, "ch_r": ch_r, "ch_w": ch_w, "lock": asyncio.Lock(), "busy": False}

async def login_with_retry(uid, password):
    for attempt in range(1, LOGIN_RETRY + 1):
        try:
            acc = await setup_acc(uid, password)
            if acc: return acc
        except: pass
        await asyncio.sleep(1.0)
    removed = await remove_from_json(uid)
    log_login(uid, False, f"fail {LOGIN_RETRY}x → {'removed' if removed else 'keep'}")
    return None

async def read_0500(reader, timeout=8.0):
    buf, start, best = b"", time.time(), {}
    while time.time() - start < timeout:
        try: chunk = await asyncio.wait_for(reader.read(8192), timeout=1.0)
        except asyncio.TimeoutError:
            if best.get("squad_code"): return best
            continue
        except: break
        if not chunk: break
        buf += chunk
        while len(buf) >= 5:
            plen = int.from_bytes(buf[2:5], 'big')
            if plen <= 0 or plen > 1000000: buf = b""; break
            total = 5 + plen
            if len(buf) < total: break
            pkt = buf[:total]; buf = buf[total:]
            if pkt[:2].hex() == "0500" and len(pkt) > 100:
                info = ttoan.parse_0500(pkt)
                if info.get("squad_code"): return info
                if info.get("owner_uid") and not best.get("owner_uid"): best = info
    return best

async def heartbeat_loop(accounts_ref, stop_evt):
    while not stop_evt.is_set():
        for acc in list(accounts_ref):
            for w_key in ("on_w", "ch_w"):
                w = acc.get(w_key)
                if w and not w.is_closing():
                    try: w.write(KA_BYTES); await w.drain()
                    except: pass
        try: await asyncio.wait_for(stop_evt.wait(), timeout=HEARTBEAT_INTERVAL)
        except asyncio.TimeoutError: pass

async def rotate_team(acc):
    on_r, on_w = acc["on_r"], acc["on_w"]
    acc_id, rc, key, iv = acc["acc_id"], acc["rc"], acc["key"], acc["iv"]
    if not on_w or on_w.is_closing(): return None
    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(T_LEAVE_OLD)
    except: return None
    try:
        idc = ttoan.get_idc(acc["region"])
        create_pkt = ttoan.create_team(4, rc, idc, acc["region"], key, iv)
        on_w.write(create_pkt)
        await on_w.drain()
    except: return None
    info = await read_0500(on_r, timeout=15.0)
    if not info or not info.get("squad_code"): return None
    code = info["squad_code"]
    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(0.2)
    except: pass
    return code

async def leader_rotator(leader_idx, accounts_ref, stop_evt):
    while not stop_evt.is_set():
        candidates = [a for a in accounts_ref if not a.get("busy") and not a["lock"].locked()]
        if not candidates: await asyncio.sleep(1.0); continue
        acc = random.choice(candidates)
        try:
            acc["busy"] = True
            async with acc["lock"]: code = await rotate_team(acc)
            if code:
                async with STATE.codes_lock: STATE.codes[leader_idx] = code
                STATE.code_generation += 1
                log_rotator(leader_idx, code)
        except: pass
        finally: acc["busy"] = False
        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=ROTATOR_INTERVAL)
            return
        except asyncio.TimeoutError: pass

async def leader_supervisor(accounts_ref, stop_evt):
    tasks = {}
    while not stop_evt.is_set():
        n_acc = len(accounts_ref)
        n_leader = compute_leader_count(n_acc)
        for idx in list(tasks.keys()):
            if idx >= n_leader:
                tasks[idx].cancel()
                try: await tasks[idx]
                except: pass
                del tasks[idx]
                async with STATE.codes_lock: STATE.codes.pop(idx, None)
        for idx in range(n_leader):
            if idx not in tasks or tasks[idx].done():
                tasks[idx] = asyncio.create_task(leader_rotator(idx, accounts_ref, stop_evt))
        await asyncio.sleep(LEADER_SUPERVISOR_INTERVAL)
    for t in tasks.values():
        if not t.done(): t.cancel()

async def try_join_once(acc, candidate):
    on_r, on_w = acc["on_r"], acc["on_w"]
    acc_id, rc, key, iv = acc["acc_id"], acc["rc"], acc["key"], acc["iv"]
    if not on_w or on_w.is_closing(): return False, None
    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(T_LEAVE_OLD)
    except: return False, None
    try:
        on_w.write(ttoan.join_code(candidate, rc, key, iv))
        await on_w.drain()
    except: return False, None
    info = await read_0500(on_r, timeout=3.0)
    if not info or not info.get("owner_uid"): return False, None
    if info.get("squad_code", "") != candidate: return False, None
    return True, info

async def do_chat(acc, info, cfg):
    on_w = acc["on_w"]
    ch_w = acc["ch_w"]
    acc_id, rc, key, iv = acc["acc_id"], acc["rc"], acc["key"], acc["iv"]
    owner = int(info.get("owner_uid"))
    chat_int = info.get("chat_code_int", 0)
    chat_channel = info.get("chat_channel", "")
    chat_ok = False
    auth_val = str(chat_int) if chat_int else chat_channel
    if ch_w and auth_val and owner:
        try:
            ch_w.write(ttoan.auth_chat(3, owner, auth_val, key, iv))
            await ch_w.drain()
            await asyncio.sleep(T_AUTH_CHAT)
            chat_pkt = ttoan.send_chat_squad(cfg["chat"], owner, 0, key, iv)
            if chat_pkt:
                ch_w.write(chat_pkt)
                await ch_w.drain()
                chat_ok = True
                await asyncio.sleep(T_CHAT_SEND)
        except: pass
    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(T_EXIT)
    except: pass
    if ch_w and owner:
        try:
            ch_w.write(ttoan.quit_chat(owner, key, iv))
            await ch_w.drain()
            await asyncio.sleep(T_QUIT)
        except: pass
    return chat_ok

async def spam_cycle(acc, cfg, worker_id):
    async with STATE.codes_lock: codes = list(STATE.codes.values())
    if not codes: return "no_code"
    code_base = random.choice(codes)
    my_gen = STATE.code_generation
    suffix = code_base[-2:]
    nick = acc.get("nickname", acc["uid"][:10])

    for _ in range(MAX_TRIES_PER_GEN):
        if STATE.code_generation != my_gen: return "gen_changed"
        first5 = f"{random.randint(0, 99999):05d}"
        candidate = f"{first5}{suffix}"
        if candidate == code_base or candidate in codes: continue
        async with STATE.failed_lock:
            if candidate in STATE.failed_codes: continue

        STATE.total_join_attempts += 1
        ok, info = await try_join_once(acc, candidate)

        if not ok:
            STATE.total_join_fail += 1
            async with STATE.failed_lock:
                if len(STATE.failed_codes) >= MAX_FAILED_CACHE: STATE.failed_codes.clear()
                STATE.failed_codes.add(candidate)
            continue

        STATE.total_join_success += 1
        chat_ok = await do_chat(acc, info, cfg)
        if chat_ok: STATE.total_spam_sent += 1
        log_join(worker_id, nick, candidate, True, "chat" if chat_ok else "join")
        return "success"
    return "exhausted"

async def worker_loop(acc, worker_id, cfg, stop_evt):
    while not stop_evt.is_set():
        async with STATE.codes_lock: has_codes = bool(STATE.codes)
        if not has_codes: await asyncio.sleep(0.5); continue
        if acc.get("busy"): await asyncio.sleep(0.05); continue
        acc["busy"] = True
        try:
            async with acc["lock"]: await spam_cycle(acc, cfg, worker_id)
        except Exception as e:
            print(f"{C.GRAY}{ts()}{C.RESET} {C.RED}[W{worker_id:03d}] err: {type(e).__name__}{C.RESET}", flush=True)
        finally: acc["busy"] = False
        await asyncio.sleep(MEMBER_WAIT_AFTER_OUT)

async def stats_loop(stop_evt):
    while not stop_evt.is_set():
        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=STATS_INTERVAL)
            return
        except asyncio.TimeoutError: print_stats()

async def api_pinger_loop(stop_evt):
    while not stop_evt.is_set():
        t0 = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(API_PING_URL) as resp:
                    await resp.read()
                    ms = int((time.time() - t0) * 1000)
                    API_STATE["api_last_ok"] = time.strftime("%H:%M:%S")
                    API_STATE["api_last_ms"] = ms
                    API_STATE["api_last_error"] = None
        except Exception as e: API_STATE["api_last_error"] = str(e)
        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=API_PING_INTERVAL)
            return
        except asyncio.TimeoutError: pass

async def file_watcher(accounts_ref, spawn_worker, login_sem, stop_evt):
    known_uids, last_mtime, first_load, worker_counter, pending_logins = set(), 0, True, [0], set()

    async def login_and_spawn(uid, pwd):
        try:
            async with login_sem: acc = await login_with_retry(uid, pwd)
            if acc and not stop_evt.is_set():
                accounts_ref.append(acc)
                worker_counter[0] += 1
                log_login(uid, True, acc['nickname'][:20])
                spawn_worker(acc, worker_counter[0])
        finally: pending_logins.discard(uid)

    while not stop_evt.is_set():
        try: mtime = os.path.getmtime(AC_FILE)
        except: await asyncio.sleep(WATCH_INTERVAL); continue
        if mtime == last_mtime: await asyncio.sleep(WATCH_INTERVAL); continue
        last_mtime = mtime
        try:
            with open(AC_FILE, "r", encoding="utf-8") as f: accs = json.load(f)
        except: await asyncio.sleep(WATCH_INTERVAL); continue

        slots = MAX_ACCOUNTS - len(accounts_ref) - len(pending_logins)
        if slots <= 0: await asyncio.sleep(WATCH_INTERVAL); continue

        new_accs = [(u, p) for u, p in accs.items() if u not in known_uids and u not in pending_logins][:slots]
        if not new_accs: await asyncio.sleep(WATCH_INTERVAL); continue

        if first_load:
            print(f"{C.GRAY}{ts()}{C.RESET} {C.CYAN}[WATCH]{C.RESET} load {len(new_accs)} acc từ {AC_FILENAME} → login song song", flush=True)
            first_load = False
        else:
            print(f"{C.GRAY}{ts()}{C.RESET} {C.YELLOW}[WATCH]{C.RESET} +{len(new_accs)} acc mới từ {AC_FILENAME} → login", flush=True)

        for uid, pwd in new_accs:
            known_uids.add(uid)
            pending_logins.add(uid)
            asyncio.create_task(login_and_spawn(uid, pwd))

        await asyncio.sleep(WATCH_INTERVAL)

# ==========================================
# API NỘI BỘ DÀNH CHO FLASK (WEB.PY) GỌI SANG
# ==========================================
async def handle_stats(request):
    return web.json_response({
        "running": len(accounts_ref_global),
        "total_bots": len(accounts_ref_global),
        "joined": STATE.total_join_success,
        "failed": STATE.total_join_fail,
        "uptime": int(time.time() - STATE.start_time)
    })

async def handle_logs(request):
    try: after = max(0, int(request.query.get("after", "0")))
    except: after = 0
    with LOG_LOCK:
        entries = [item for item in LOG_BUFFER if item["id"] > after]
        return web.json_response({"total": LOG_SEQ, "lines": [item["line"] for item in entries]})

async def handle_bots(request):
    bots = [{"uid": str(acc.get("acc_id", "")), "nickname": str(acc.get("nickname", "Unknown")), "status": "running"} for acc in accounts_ref_global]
    return web.json_response({"bots": bots})

async def start_internal_api():
    app = web.Application()
    app.router.add_get("/api/stats", handle_stats)
    app.router.add_get("/api/logs", handle_logs)
    app.router.add_get("/api/bots", handle_bots)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", BOT_API_PORT)
    await site.start()
    print(f"\033[92m[BOT] Internal API chạy ngầm tại http://127.0.0.1:{BOT_API_PORT}\033[0m", flush=True)

async def main():
    global stop_flag, accounts_ref_global
    if not isinstance(sys.stdout, LogTee): sys.stdout = LogTee(sys.stdout)

    cfg = load_config()
    await start_internal_api()

    accs = load_accounts()
    n = len(accs)
    if n > 0: print(f"{C.CYAN}[ACC]{C.RESET} {n} acc trong {AC_FILENAME}")
    else: print(f"{C.CYAN}[ACC]{C.RESET} 0 acc trong {AC_FILENAME}")

    stop_evt = asyncio.Event()
    stop_flag = stop_evt
    accounts_ref = []
    accounts_ref_global = accounts_ref
    login_sem = asyncio.Semaphore(MAX_CONCURRENT_LOGIN)
    worker_tasks = []

    def spawn_worker(acc, wid):
        t = asyncio.create_task(worker_loop(acc, wid, cfg, stop_evt))
        worker_tasks.append(t)

    watcher_task = asyncio.create_task(file_watcher(accounts_ref, spawn_worker, login_sem, stop_evt))
    supervisor_task = asyncio.create_task(leader_supervisor(accounts_ref, stop_evt))
    hb_task = asyncio.create_task(heartbeat_loop(accounts_ref, stop_evt))
    stats_task = asyncio.create_task(stats_loop(stop_evt))
    api_task = asyncio.create_task(api_pinger_loop(stop_evt))

    try:
        await asyncio.gather(watcher_task, supervisor_task, hb_task, stats_task, api_task, return_exceptions=True)
    except asyncio.CancelledError: pass
    finally:
        stop_evt.set()
        for t in [watcher_task, supervisor_task, hb_task, stats_task, api_task] + worker_tasks:
            if not t.done(): t.cancel()
        for acc in accounts_ref: close_acc_sync(acc)

def close_acc_sync(acc):
    for w_key in ("on_w", "ch_w"):
        w = acc.get(w_key)
        if w:
            try: w.close()
            except: pass

# ==========================================
# TỰ ĐỘNG CHẠY WEB.PY KHI CHẠY 1.PY
# ==========================================
def run_flask_web():
    try:
        print(f"\033[92m[WEB] Đang khởi động web.py (Flask)...\033[0m", flush=True)
        import web as web_module
        web_module.app.run(host='0.0.0.0', port=web_module.PORT, debug=False, use_reloader=False)
    except Exception as e:
        print(f"\033[91m[WEB] Lỗi khởi động web.py: {e}\033[0m", flush=True)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask_web, daemon=True)
    flask_thread.start()
    time.sleep(1)

    try: 
        asyncio.run(main())
    except KeyboardInterrupt: 
        print(f"\n{C.YELLOW}[CTRL+C]{C.RESET}")
