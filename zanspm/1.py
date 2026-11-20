#!/usr/bin/env python3
import asyncio
from collections import deque
import json
import os
import random
import re
import sys
import time

try:
    from aiohttp import web, ClientSession, ClientTimeout
except ImportError:
    os.system("pip install aiohttp -q")
    from aiohttp import web, ClientSession, ClientTimeout

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
MAX_WEB_LOGS = 2000  # Tăng bộ nhớ đệm lên 2000 dòng
STATS_INTERVAL = 60.0
WATCH_INTERVAL = 0.5

# API gọi mỗi 5 phút
API_PING_URL = "https://zancutespm.onrender.com/stats"
API_PING_INTERVAL = 300.0  # 5 phút

T_LEAVE_OLD = 0.2
T_AUTH_CHAT = 0.1
T_CHAT_SEND = 0.15
T_EXIT = 0.05
T_QUIT = 0.03

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 2026

INSTANCE_ID = os.environ.get("INSTANCE_ID", "")
AC_FILENAME = os.environ.get("AC_FILE", "ac.json")
AC_FILE = os.path.join(BASE_DIR, AC_FILENAME)
CFG_FILE = os.path.join(BASE_DIR, "ttoan.txt")
INDEX_FILE = os.path.join(BASE_DIR, "index.html")

class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"
    GREEN = "\033[38;5;46m"; RED = "\033[38;5;196m"; CYAN = "\033[38;5;51m"
    MAGENTA = "\033[38;5;201m"; YELLOW = "\033[38;5;226m"; GRAY = "\033[38;5;245m"
    WHITE = "\033[38;5;255m"

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

    logs = deque(maxlen=MAX_WEB_LOGS)
    log_seq = 0

stop_flag = None
file_lock = asyncio.Lock()
accounts_ref_global = []
CHAT_LOCK = asyncio.Lock()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text or "")

def push_log(tag: str, message: str, level: str = "info"):
    STATE.log_seq += 1
    STATE.logs.append({
        "id": STATE.log_seq,
        "time": time.strftime("%H:%M:%S"),
        "tag": tag,
        "level": level,
        "message": strip_ansi(message).strip(),
    })

def termux_print(ansi_line: str, tag: str = "SYS", level: str = "info"):
    print(ansi_line, flush=True)
    push_log(tag, ansi_line, level)

def format_uptime(seconds: float) -> str:
    sec = max(0, int(seconds))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def compute_leader_count(n_acc):
    if n_acc <= 0: return 0
    if n_acc < 50: return 1
    return min(8, (n_acc // 1000) + 1)

def ts(): return time.strftime("%H:%M:%S")

def log_rotator(leader_idx, code):
    suffix = code[-2:] if len(code) >= 2 else code
    termux_print(f"{C.GRAY}{ts()}{C.RESET} {C.MAGENTA}[L{leader_idx+1}]{C.RESET} → {C.BOLD}{code}{C.RESET} (giữ 2 số cuối: {C.GREEN}{suffix}{C.RESET})", tag=f"L{leader_idx+1}", level="rotator")

def log_login(uid, ok, nick=""):
    if ok:
        total = len(accounts_ref_global)
        termux_print(f"{C.GRAY}{ts()}{C.RESET} {C.GREEN}[LOGIN]{C.RESET} {uid} {C.GREEN}✓{C.RESET} {nick} {C.CYAN}| BOT [{total}]{C.RESET}", tag="LOGIN", level="ok")
    else:
        termux_print(f"{C.GRAY}{ts()}{C.RESET} {C.RED}[LOGIN]{C.RESET} {uid} {C.RED}✗ {nick}{C.RESET}", tag="LOGIN", level="err")

def log_join(worker_id, nick, code, ok, detail=""):
    if not ok: return
    wtag = f"[W{worker_id:03d}]"
    nk = nick[:10].ljust(10)
    termux_print(f"{C.GRAY}{ts()}{C.RESET} {C.GREEN}{wtag} {nk} {code}  ✓  {detail}{C.RESET}", tag=f"W{worker_id:03d}", level="ok")

def print_stats():
    elapsed = time.time() - STATE.start_time
    uptime_str = format_uptime(elapsed)
    rate = (STATE.total_join_success / STATE.total_join_attempts * 100) if STATE.total_join_attempts > 0 else 0
    codes_str = ", ".join(STATE.codes[k] for k in sorted(STATE.codes)) or "-"
    suffixes_str = ", ".join(STATE.codes[k][-2:] for k in sorted(STATE.codes) if len(STATE.codes[k]) >= 2) or "-"
    code_per_hour = STATE.total_join_success / max(elapsed, 1) * 3600
    print()
    print(f"{C.CYAN}{'='*58}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} BOT online: {C.GREEN}{len(accounts_ref_global)}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} Leaders: {len(STATE.codes)}   Gen: {STATE.code_generation}")
    print(f"{C.CYAN}|{C.RESET} Codes: {codes_str} (2 số cuối: {suffixes_str})")
    print(f"{C.CYAN}|{C.RESET} Join: {C.GREEN}{STATE.total_join_success}{C.RESET}/{STATE.total_join_attempts} ({rate:.0f}%)   Fail: {C.RED}{STATE.total_join_fail}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} Spam: {STATE.total_spam_sent}   Code/giờ: {C.YELLOW}{code_per_hour:.0f}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} Uptime: {uptime_str}")
    print(f"{C.CYAN}{'='*58}{C.RESET}")
    print()
    push_log("STATS", f"BOT={len(accounts_ref_global)} | Join={STATE.total_join_success}/{STATE.total_join_attempts} ({rate:.0f}%) | Fail={STATE.total_join_fail} | Uptime={uptime_str}", level="info")

def load_config():
    if not os.path.exists(CFG_FILE): return {"chat": "Contact @zanxgay"}
    chat_lines = []
    current = None
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
    except Exception: return {}

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
        except Exception: pass
    return False

async def login_one(uid, password):
    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, lambda: FreeFireAPI().get(f"{uid}:{password}"))
    except Exception: return None
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
    except Exception: return None

    ch_r = ch_w = None
    try:
        ch_r, ch_w = await asyncio.open_connection(gs["chatip"], int(gs["chatport"]))
        ch_w.write(ttoan.build_chat_auth(acc_id, token, login_time, key, iv))
        await ch_w.drain()
        await asyncio.sleep(0.3)
        ch_w.write(KA_BYTES)
        await ch_w.drain()
    except Exception: ch_r = ch_w = None

    return {"uid": uid, "acc_id": acc_id, "nickname": nickname, "key": key, "iv": iv, "rc": rc, "region": region, "on_r": on_r, "on_w": on_w, "ch_r": ch_r, "ch_w": ch_w, "lock": asyncio.Lock(), "busy": False}

async def login_with_retry(uid, password):
    for attempt in range(1, LOGIN_RETRY + 1):
        try:
            acc = await setup_acc(uid, password)
            if acc: return acc
        except Exception: pass
        await asyncio.sleep(1.0)

    removed = await remove_from_json(uid)
    log_login(uid, False, f"fail {LOGIN_RETRY}x → {'removed' if removed else 'keep'}")
    return None

async def close_acc(acc):
    for w_key in ("on_w", "ch_w"):
        w = acc.get(w_key)
        if w:
            try: w.close()
            except: pass

async def read_0500(reader, timeout=8.0):
    buf = b""
    start = time.time()
    best = {}
    while time.time() - start < timeout:
        try:
            chunk = await asyncio.wait_for(reader.read(8192), timeout=1.0)
        except asyncio.TimeoutError:
            if best.get("squad_code"): return best
            continue
        except Exception: break
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
                    try:
                        w.write(KA_BYTES)
                        await w.drain()
                    except Exception: pass
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
    except Exception: return None

    try:
        idc = ttoan.get_idc(acc["region"])
        create_pkt = ttoan.create_team(4, rc, idc, acc["region"], key, iv)
        on_w.write(create_pkt)
        await on_w.drain()
    except Exception: return None

    info = await read_0500(on_r, timeout=15.0)
    if not info or not info.get("squad_code"): return None

    code = info["squad_code"]
    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(0.2)
    except Exception: pass
    return code

async def leader_rotator(leader_idx, accounts_ref, stop_evt):
    while not stop_evt.is_set():
        candidates = [a for a in accounts_ref if not a.get("busy") and not a["lock"].locked()]
        if not candidates:
            await asyncio.sleep(1.0)
            continue

        acc = random.choice(candidates)
        try:
            acc["busy"] = True
            async with acc["lock"]: code = await rotate_team(acc)
            if code:
                async with STATE.codes_lock: STATE.codes[leader_idx] = code
                STATE.code_generation += 1
                log_rotator(leader_idx, code)
        except Exception: pass
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
    except Exception: return False, None

    try:
        on_w.write(ttoan.join_code(candidate, rc, key, iv))
        await on_w.drain()
    except Exception: return False, None

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
        except Exception: pass

    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(T_EXIT)
    except Exception: pass

    if ch_w and owner:
        try:
            ch_w.write(ttoan.quit_chat(owner, key, iv))
            await ch_w.drain()
            await asyncio.sleep(T_QUIT)
        except Exception: pass
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
            termux_print(f"{C.GRAY}{ts()}{C.RESET} {C.RED}[W{worker_id:03d}] err: {type(e).__name__}{C.RESET}", tag=f"W{worker_id:03d}", level="err")
        finally: acc["busy"] = False
        await asyncio.sleep(MEMBER_WAIT_AFTER_OUT)

async def stats_loop(stop_evt):
    while not stop_evt.is_set():
        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=STATS_INTERVAL)
            return
        except asyncio.TimeoutError: print_stats()

async def api_ping_loop(stop_evt):
    """Gọi API zanspm.onrender.com/stats mỗi 5 phút."""
    timeout = ClientTimeout(total=20.0)
    async with ClientSession(timeout=timeout) as session:
        while not stop_evt.is_set():
            try:
                async with session.get(API_PING_URL) as resp:
                    status = resp.status
                    body = await resp.text()
                    preview = body[:180].replace("\n", " ")
                    if 200 <= status < 300:
                        termux_print(
                            f"{C.GRAY}{ts()}{C.RESET} {C.CYAN}[API]{C.RESET} GET {API_PING_URL} → {C.GREEN}{status}{C.RESET} {preview}",
                            tag="API", level="ok"
                        )
                    else:
                        termux_print(
                            f"{C.GRAY}{ts()}{C.RESET} {C.YELLOW}[API]{C.RESET} GET {API_PING_URL} → {C.YELLOW}{status}{C.RESET}",
                            tag="API", level="warn"
                        )
            except asyncio.CancelledError:
                return
            except Exception as e:
                termux_print(
                    f"{C.GRAY}{ts()}{C.RESET} {C.RED}[API]{C.RESET} GET {API_PING_URL} err: {type(e).__name__}: {e}",
                    tag="API", level="err"
                )

            try:
                await asyncio.wait_for(stop_evt.wait(), timeout=API_PING_INTERVAL)
                return
            except asyncio.TimeoutError:
                pass

async def file_watcher(accounts_ref, spawn_worker, login_sem, stop_evt):
    known_uids = set()
    last_mtime = 0
    first_load = True
    worker_counter = [0]
    pending_logins = set()

    async def login_and_spawn(uid, pwd):
        try:
            async with login_sem: acc = await login_with_retry(uid, pwd)
            if acc and not stop_evt.is_set():
                accounts_ref.append(acc)
                worker_counter[0] += 1
                wid = worker_counter[0]
                log_login(uid, True, acc['nickname'][:20])
                spawn_worker(acc, wid)
        finally: pending_logins.discard(uid)

    while not stop_evt.is_set():
        try: mtime = os.path.getmtime(AC_FILE)
        except Exception:
            await asyncio.sleep(WATCH_INTERVAL)
            continue

        if mtime == last_mtime:
            await asyncio.sleep(WATCH_INTERVAL)
            continue
        last_mtime = mtime

        try:
            with open(AC_FILE, "r", encoding="utf-8") as f: accs = json.load(f)
        except Exception:
            await asyncio.sleep(WATCH_INTERVAL)
            continue

        slots = MAX_ACCOUNTS - len(accounts_ref) - len(pending_logins)
        if slots <= 0:
            await asyncio.sleep(WATCH_INTERVAL)
            continue

        new_accs = [(u, p) for u, p in accs.items() if u not in known_uids and u not in pending_logins][:slots]
        if not new_accs:
            await asyncio.sleep(WATCH_INTERVAL)
            continue

        if first_load:
            termux_print(f"{C.GRAY}{ts()}{C.RESET} {C.CYAN}[WATCH]{C.RESET} load {len(new_accs)} acc từ {AC_FILENAME} → login song song", tag="WATCH", level="info")
            first_load = False
        else:
            termux_print(f"{C.GRAY}{ts()}{C.RESET} {C.YELLOW}[WATCH]{C.RESET} +{len(new_accs)} acc mới từ {AC_FILENAME} → login", tag="WATCH", level="warn")

        for uid, pwd in new_accs:
            known_uids.add(uid)
            pending_logins.add(uid)
            asyncio.create_task(login_and_spawn(uid, pwd))

        await asyncio.sleep(WATCH_INTERVAL)

# ==========================================
# API NỘI BỘ
# ==========================================
async def handle_index_or_panel(request):
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html", charset="utf-8")
    return web.Response(text="<h1>Thiếu file index.html</h1>", status=404, content_type="text/html")

async def handle_stats(request):
    elapsed = time.time() - STATE.start_time
    return web.json_response({
        "ok": True, "bot_online": len(accounts_ref_global), "leaders": len(STATE.codes), "codes": STATE.codes,
        "gen": STATE.code_generation, "join_success": STATE.total_join_success, "join_fail": STATE.total_join_fail,
        "join_attempts": STATE.total_join_attempts, "spam_sent": STATE.total_spam_sent,
        "uptime": format_uptime(elapsed), "uptime_sec": int(elapsed), "logs": list(STATE.logs)
    })

async def start_http_server():
    global HTTP_PORT
    app = web.Application()
    app.router.add_get("/", handle_index_or_panel)
    app.router.add_get("/panel", handle_index_or_panel)
    app.router.add_get("/index.html", handle_index_or_panel)
    app.router.add_get("/stats", handle_stats)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HTTP_HOST, HTTP_PORT)
    await site.start()
    termux_print(f"{C.GREEN}[HTTP]{C.RESET} Panel: http://127.0.0.1:{HTTP_PORT}/", tag="HTTP", level="ok")

async def main():
    global stop_flag, accounts_ref_global
    cfg = load_config()

    accs = load_accounts()
    if len(accs) > 0:
        termux_print(f"{C.CYAN}[ACC]{C.RESET} {len(accs)} acc trong {AC_FILENAME}", tag="ACC", level="info")
    else:
        termux_print(f"{C.CYAN}[ACC]{C.RESET} 0 acc trong {AC_FILENAME}", tag="ACC", level="info")

    termux_print(f"{C.MAGENTA}[SYS]{C.RESET} Logic dò code: xxxxx[suffix] (1/100000)", tag="SYS", level="rotator")
    termux_print(f"{C.MAGENTA}[SYS]{C.RESET} Đổi code mỗi {ROTATOR_INTERVAL}s", tag="SYS", level="rotator")
    termux_print(f"{C.MAGENTA}[SYS]{C.RESET} API ping: {API_PING_URL} mỗi {int(API_PING_INTERVAL)}s", tag="SYS", level="info")

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
    api_task = asyncio.create_task(api_ping_loop(stop_evt))

    try:
        await start_http_server()
    except Exception as e:
        termux_print(f"{C.RED}[HTTP] Không start được: {e}{C.RESET}", tag="HTTP", level="err")

    try:
        await asyncio.gather(watcher_task, supervisor_task, hb_task, stats_task, api_task, return_exceptions=True)
    except asyncio.CancelledError: pass
    finally:
        stop_evt.set()
        for t in [watcher_task, supervisor_task, hb_task, stats_task, api_task] + worker_tasks:
            if not t.done(): t.cancel()
        for acc in accounts_ref: close_acc_sync(acc)
        print_stats()

def close_acc_sync(acc):
    for w_key in ("on_w", "ch_w"):
        w = acc.get(w_key)
        if w:
            try: w.close()
            except: pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}[CTRL+C]{C.RESET}")
