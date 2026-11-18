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
HTTP_PORT = int(os.environ.get("PORT", 2026))

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

# ================== HELPERS ==================
def compute_leader_count(n_acc):
    if n_acc <= 0:
        return 0
    if n_acc < 50:
        return 1
    return min(8, (n_acc // 1000) + 1)

def ts():
    return time.strftime("%H:%M:%S")

def log_rotator(leader_idx, code):
    suffix = code[-2:] if len(code) >= 2 else code
    print(f"{C.GRAY}{ts()}{C.RESET} {C.MAGENTA}[L{leader_idx+1}]{C.RESET} "
          f"→ {C.BOLD}{code}{C.RESET} (giữ 2 số cuối: {C.GREEN}{suffix}{C.RESET})", flush=True)

def log_login(uid, ok, nick=""):
    if ok:
        total = len(accounts_ref_global)
        print(f"{C.GRAY}{ts()}{C.RESET} {C.GREEN}[LOGIN]{C.RESET} {uid} "
              f"{C.GREEN}✓{C.RESET} {nick} {C.CYAN}| BOT [{total}]{C.RESET}", flush=True)
    else:
        print(f"{C.GRAY}{ts()}{C.RESET} {C.RED}[LOGIN]{C.RESET} {uid} "
              f"{C.RED}✗ {nick}{C.RESET}", flush=True)

def log_join(worker_id, nick, code, ok, detail=""):
    if not ok:
        return
    wtag = f"[W{worker_id:03d}]"
    nk = nick[:10].ljust(10)
    print(f"{C.GRAY}{ts()}{C.RESET} {C.GREEN}{wtag} {nk} {code}  ✓  "
          f"{detail}{C.RESET}", flush=True)

def print_stats():
    elapsed = time.time() - STATE.start_time
    h, rem = divmod(int(elapsed), 3600)
    m, s = divmod(rem, 60)
    rate = (STATE.total_join_success / STATE.total_join_attempts * 100) \
        if STATE.total_join_attempts > 0 else 0
    codes_str = ", ".join(STATE.codes[k] for k in sorted(STATE.codes)) or "-"
    suffixes_str = ", ".join(STATE.codes[k][-2:] for k in sorted(STATE.codes) if len(STATE.codes[k]) >= 2) or "-"
    code_per_hour = STATE.total_join_success / max(elapsed, 1) * 3600
    print()
    print(f"{C.CYAN}{'='*58}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} BOT online: {C.GREEN}{len(accounts_ref_global)}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} Leaders: {len(STATE.codes)}   Gen: {STATE.code_generation}")
    print(f"{C.CYAN}|{C.RESET} Codes: {codes_str} (2 số cuối: {suffixes_str})")
    print(f"{C.CYAN}|{C.RESET} Join: {C.GREEN}{STATE.total_join_success}{C.RESET}/"
          f"{STATE.total_join_attempts} ({rate:.0f}%)   "
          f"Fail: {C.RED}{STATE.total_join_fail}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} Spam: {STATE.total_spam_sent}   "
          f"Code/giờ: {C.YELLOW}{code_per_hour:.0f}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} Uptime: {h:02d}:{m:02d}:{s:02d}")
    print(f"{C.CYAN}{'='*58}{C.RESET}")
    print()

def load_config():
    if not os.path.exists(CFG_FILE):
        return {"chat": "Contact @zanxgay"}
    chat_lines = []
    current = None
    with open(CFG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            s = line.rstrip("\n")
            st = s.strip()
            if st.upper() == "[CHAT]":
                current = "chat"; continue
            if st.upper() == "[GHOST]":
                current = "ghost"; continue
            if st.startswith("#"):
                continue
            if current == "chat":
                chat_lines.append(s)
    chat_text = "\n".join(chat_lines).strip()
    return {"chat": chat_text or "Contact @zanxgay"}

def load_accounts():
    if not os.path.exists(AC_FILE):
        return {}
    try:
        with open(AC_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

async def remove_from_json(uid):
    async with file_lock:
        try:
            with open(AC_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if uid in data:
                del data[uid]
                tmp = AC_FILE + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                os.replace(tmp, AC_FILE)
                return True
        except Exception:
            pass
    return False

async def login_one(uid, password):
    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(
            None, lambda: FreeFireAPI().get(f"{uid}:{password}")
        )
    except Exception:
        return None
    if not data or 'account not found' in str(data):
        return None
    return data

async def setup_acc(uid, password):
    data = await login_one(uid, password)
    if not data:
        return None

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
    except Exception:
        return None

    ch_r = ch_w = None
    try:
        ch_r, ch_w = await asyncio.open_connection(gs["chatip"], int(gs["chatport"]))
        ch_w.write(ttoan.build_chat_auth(acc_id, token, login_time, key, iv))
        await ch_w.drain()
        await asyncio.sleep(0.3)
        ch_w.write(KA_BYTES)
        await ch_w.drain()
    except Exception:
        ch_r = ch_w = None

    return {
        "uid": uid, "acc_id": acc_id, "nickname": nickname,
        "key": key, "iv": iv, "rc": rc, "region": region,
        "on_r": on_r, "on_w": on_w,
        "ch_r": ch_r, "ch_w": ch_w,
        "lock": asyncio.Lock(),
        "busy": False,
    }

async def login_with_retry(uid, password):
    for attempt in range(1, LOGIN_RETRY + 1):
        try:
            acc = await setup_acc(uid, password)
            if acc:
                return acc
        except Exception:
            pass
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
            if best.get("squad_code"):
                return best
            continue
        except Exception:
            break
        if not chunk:
            break
        buf += chunk
        while len(buf) >= 5:
            plen = int.from_bytes(buf[2:5], 'big')
            if plen <= 0 or plen > 1000000:
                buf = b""; break
            total = 5 + plen
            if len(buf) < total: break
            pkt = buf[:total]; buf = buf[total:]
            if pkt[:2].hex() == "0500" and len(pkt) > 100:
                info = ttoan.parse_0500(pkt)
                if info.get("squad_code"):
                    return info
                if info.get("owner_uid") and not best.get("owner_uid"):
                    best = info
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
                    except Exception:
                        pass
        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=HEARTBEAT_INTERVAL)
        except asyncio.TimeoutError:
            pass

async def rotate_team(acc):
    on_r, on_w = acc["on_r"], acc["on_w"]
    acc_id, rc, key, iv = acc["acc_id"], acc["rc"], acc["key"], acc["iv"]
    if not on_w or on_w.is_closing():
        return None

    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(T_LEAVE_OLD)
    except Exception:
        return None

    try:
        idc = ttoan.get_idc(acc["region"])
        create_pkt = ttoan.create_team(4, rc, idc, acc["region"], key, iv)
        on_w.write(create_pkt)
        await on_w.drain()
    except Exception:
        return None

    info = await read_0500(on_r, timeout=15.0)
    if not info or not info.get("squad_code"):
        return None

    code = info["squad_code"]

    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(0.2)
    except Exception:
        pass

    return code

async def leader_rotator(leader_idx, accounts_ref, stop_evt):
    while not stop_evt.is_set():
        candidates = [a for a in accounts_ref
                      if not a.get("busy") and not a["lock"].locked()]
        if not candidates:
            await asyncio.sleep(1.0)
            continue

        acc = random.choice(candidates)

        try:
            acc["busy"] = True
            async with acc["lock"]:
                code = await rotate_team(acc)
            if code:
                async with STATE.codes_lock:
                    STATE.codes[leader_idx] = code
                STATE.code_generation += 1
                log_rotator(leader_idx, code)
        except Exception:
            pass
        finally:
            acc["busy"] = False

        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=ROTATOR_INTERVAL)
            return
        except asyncio.TimeoutError:
            pass

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
                async with STATE.codes_lock:
                    STATE.codes.pop(idx, None)

        for idx in range(n_leader):
            if idx not in tasks or tasks[idx].done():
                tasks[idx] = asyncio.create_task(
                    leader_rotator(idx, accounts_ref, stop_evt)
                )

        await asyncio.sleep(LEADER_SUPERVISOR_INTERVAL)

    for t in tasks.values():
        if not t.done():
            t.cancel()

async def try_join_once(acc, candidate):
    on_r, on_w = acc["on_r"], acc["on_w"]
    acc_id, rc, key, iv = acc["acc_id"], acc["rc"], acc["key"], acc["iv"]
    if not on_w or on_w.is_closing():
        return False, None

    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(T_LEAVE_OLD)
    except Exception:
        return False, None

    try:
        on_w.write(ttoan.join_code(candidate, rc, key, iv))
        await on_w.drain()
    except Exception:
        return False, None

    info = await read_0500(on_r, timeout=3.0)
    if not info or not info.get("owner_uid"):
        return False, None
    if info.get("squad_code", "") != candidate:
        return False, None
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
        except Exception:
            pass

    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(T_EXIT)
    except Exception:
        pass

    if ch_w and owner:
        try:
            ch_w.write(ttoan.quit_chat(owner, key, iv))
            await ch_w.drain()
            await asyncio.sleep(T_QUIT)
        except Exception:
            pass

    return chat_ok

async def spam_cycle(acc, cfg, worker_id):
    async with STATE.codes_lock:
        codes = list(STATE.codes.values())

    if not codes:
        return "no_code"

    code_base = random.choice(codes)
    my_gen = STATE.code_generation
    suffix = code_base[-2:]
    nick = acc.get("nickname", acc["uid"][:10])

    for _ in range(MAX_TRIES_PER_GEN):
        if STATE.code_generation != my_gen:
            return "gen_changed"

        first5 = f"{random.randint(0, 99999):05d}"
        candidate = f"{first5}{suffix}"

        if candidate == code_base or candidate in codes:
            continue

        async with STATE.failed_lock:
            if candidate in STATE.failed_codes:
                continue

        STATE.total_join_attempts += 1
        ok, info = await try_join_once(acc, candidate)

        if not ok:
            STATE.total_join_fail += 1
            async with STATE.failed_lock:
                if len(STATE.failed_codes) >= MAX_FAILED_CACHE:
                    STATE.failed_codes.clear()
                STATE.failed_codes.add(candidate)
            continue

        STATE.total_join_success += 1
        chat_ok = await do_chat(acc, info, cfg)
        if chat_ok:
            STATE.total_spam_sent += 1
        log_join(worker_id, nick, candidate, True, "chat" if chat_ok else "join")
        return "success"

    return "exhausted"

async def worker_loop(acc, worker_id, cfg, stop_evt):
    while not stop_evt.is_set():
        async with STATE.codes_lock:
            has_codes = bool(STATE.codes)

        if not has_codes:
            await asyncio.sleep(0.5)
            continue

        if acc.get("busy"):
            await asyncio.sleep(0.05)
            continue

        acc["busy"] = True
        try:
            async with acc["lock"]:
                await spam_cycle(acc, cfg, worker_id)
        except Exception as e:
            print(f"{C.GRAY}{ts()}{C.RESET} {C.RED}[W{worker_id:03d}] "
                  f"err: {type(e).__name__}{C.RESET}", flush=True)
        finally:
            acc["busy"] = False

        await asyncio.sleep(MEMBER_WAIT_AFTER_OUT)

async def stats_loop(stop_evt):
    while not stop_evt.is_set():
        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=STATS_INTERVAL)
            return
        except asyncio.TimeoutError:
            print_stats()

async def file_watcher(accounts_ref, spawn_worker, login_sem, stop_evt):
    known_uids = set()
    last_mtime = 0
    first_load = True
    worker_counter = [0]
    pending_logins = set()

    async def login_and_spawn(uid, pwd):
        try:
            async with login_sem:
                acc = await login_with_retry(uid, pwd)
            if acc and not stop_evt.is_set():
                accounts_ref.append(acc)
                worker_counter[0] += 1
                wid = worker_counter[0]
                log_login(uid, True, acc['nickname'][:20])
                spawn_worker(acc, wid)
        finally:
            pending_logins.discard(uid)

    while not stop_evt.is_set():
        try:
            mtime = os.path.getmtime(AC_FILE)
        except Exception:
            await asyncio.sleep(WATCH_INTERVAL)
            continue

        if mtime == last_mtime:
            await asyncio.sleep(WATCH_INTERVAL)
            continue
        last_mtime = mtime

        try:
            with open(AC_FILE, "r", encoding="utf-8") as f:
                accs = json.load(f)
        except Exception:
            await asyncio.sleep(WATCH_INTERVAL)
            continue

        slots = MAX_ACCOUNTS - len(accounts_ref) - len(pending_logins)
        if slots <= 0:
            await asyncio.sleep(WATCH_INTERVAL)
            continue

        new_accs = [(u, p) for u, p in accs.items()
                    if u not in known_uids and u not in pending_logins][:slots]

        if not new_accs:
            await asyncio.sleep(WATCH_INTERVAL)
            continue

        if first_load:
            print(f"{C.GRAY}{ts()}{C.RESET} {C.CYAN}[WATCH]{C.RESET} "
                  f"load {len(new_accs)} acc từ {AC_FILENAME} → login song song", flush=True)
            first_load = False
        else:
            print(f"{C.GRAY}{ts()}{C.RESET} {C.YELLOW}[WATCH]{C.RESET} "
                  f"+{len(new_accs)} acc mới từ {AC_FILENAME} → login", flush=True)

        for uid, pwd in new_accs:
            known_uids.add(uid)
            pending_logins.add(uid)
            asyncio.create_task(login_and_spawn(uid, pwd))

        await asyncio.sleep(WATCH_INTERVAL)

# ================== CORE HTTP ROUTES ==================
async def handle_stats(request):
    return web.json_response({
        "ok": True,
        "bot_online": len(accounts_ref_global),
        "leaders": len(STATE.codes),
        "codes": STATE.codes,
        "gen": STATE.code_generation,
        "join_success": STATE.total_join_success,
        "join_fail": STATE.total_join_fail,
        "join_attempts": STATE.total_join_attempts,
        "spam_sent": STATE.total_spam_sent,
    })

async def handle_status(request):
    return web.json_response({
        "ok": True,
        "bot_online": len(accounts_ref_global),
        "count": len(accounts_ref_global),
        "codes": STATE.codes,
        "gen": STATE.code_generation,
    })

async def handle_chat(request):
    tc = request.query.get("tc", "").strip()
    if not tc or not tc.isdigit():
        return web.json_response({"ok": False, "msg": "Format: /chat?tc=1234567"})

    async with CHAT_LOCK:
        candidates = [a for a in accounts_ref_global
                      if not a.get("busy") and not a["lock"].locked()]
        if not candidates:
            return web.json_response({"ok": False, "msg": "no free bot"})
        acc = random.choice(candidates)

        cfg = load_config()
        acc["busy"] = True
        try:
            async with acc["lock"]:
                on_r, on_w = acc["on_r"], acc["on_w"]
                ch_w = acc["ch_w"]
                acc_id, rc, key, iv = acc["acc_id"], acc["rc"], acc["key"], acc["iv"]

                try:
                    on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
                    await on_w.drain()
                    await asyncio.sleep(T_LEAVE_OLD)
                except Exception:
                    pass

                try:
                    on_w.write(ttoan.join_code(tc, rc, key, iv))
                    await on_w.drain()
                except Exception as e:
                    return web.json_response({"ok": False, "msg": f"join err: {e}"})

                info = await read_0500(on_r, timeout=8.0)
                if not info or not info.get("owner_uid"):
                    try:
                        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
                        await on_w.drain()
                    except Exception:
                        pass
                    return web.json_response({"ok": False, "msg": "không bắt được owner"})

                owner = int(info.get("owner_uid"))
                chat_int = info.get("chat_code_int", 0)
                chat_channel = info.get("chat_channel", "")
                squad_code = info.get("squad_code", "")

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
                    except Exception:
                        pass

                try:
                    on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
                    await on_w.drain()
                    await asyncio.sleep(T_EXIT)
                except Exception:
                    pass

                if ch_w and owner:
                    try:
                        ch_w.write(ttoan.quit_chat(owner, key, iv))
                        await ch_w.drain()
                        await asyncio.sleep(T_QUIT)
                    except Exception:
                        pass

                if chat_ok:
                    STATE.total_spam_sent += 1

                return web.json_response({
                    "ok": True,
                    "uid": str(acc_id),
                    "nickname": acc.get("nickname", ""),
                    "teamcode": tc,
                    "owner_uid": owner,
                    "squad_code": squad_code,
                    "chat_sent": chat_ok,
                })
        finally:
            acc["busy"] = False

# ================== DASHBOARD ROUTES ==================
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

# ================== API PING ==================
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
async def start_http_server():
    global HTTP_PORT
    app = web.Application()
    # core
    app.router.add_get("/stats", handle_stats)
    app.router.add_get("/status", handle_status)
    app.router.add_get("/chat", handle_chat)
    # dashboard
    app.router.add_get("/login", handle_login)
    app.router.add_post("/login", handle_login)
    app.router.add_get("/logout", handle_logout)
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/stats", handle_api_stats)
    app.router.add_get("/api/logs", handle_api_logs)

    runner = web.AppRunner(app)
    await runner.setup()
    for port in range(HTTP_PORT, HTTP_PORT + 20):
        try:
            site = web.TCPSite(runner, HTTP_HOST, port)
            await site.start()
            HTTP_PORT = port
            _log("info", f"Dashboard http://{HTTP_HOST}:{port}")
            _log("info", f"Chat API: http://127.0.0.1:{port}/chat?tc=TEAMCODE")
            print(f"{C.GREEN}[HTTP]{C.RESET} Dashboard → http://{HTTP_HOST}:{port}", flush=True)
            print(f"{C.GREEN}[HTTP]{C.RESET} Chat: http://127.0.0.1:{port}/chat?tc=TEAMCODE", flush=True)
            return
        except OSError as e:
            if "address already in use" in str(e).lower():
                _log("warn", f"port {port} bận, thử port khác...")
                continue
            raise
    _log("error", "Không tìm được port trống")
    print(f"{C.RED}[HTTP] Không tìm được port trống{C.RESET}", flush=True)

# ================== MAIN ==================
async def main():
    global stop_flag, accounts_ref_global

    cfg = load_config()

    accs = load_accounts()
    n = len(accs)
    if n > 0:
        print(f"{C.CYAN}[ACC]{C.RESET} {n} acc trong {AC_FILENAME} "
              f"(max {MAX_ACCOUNTS}, {compute_leader_count(n)} leader)")
    else:
        print(f"{C.CYAN}[ACC]{C.RESET} 0 acc trong {AC_FILENAME} (đang chờ gen.py tạo...)")

    print(f"{C.CYAN}[CFG]{C.RESET} Chat: {cfg['chat'][:80].replace(chr(10), ' | ')}...")
    print(f"{C.MAGENTA}[SYS]{C.RESET} Logic dò code: xxxxx[suffix] (1/100000)")
    print(f"{C.MAGENTA}[SYS]{C.RESET} Đổi code mỗi {ROTATOR_INTERVAL}s")
    print(f"{C.MAGENTA}[SYS]{C.RESET} Timing: leave={T_LEAVE_OLD}s auth={T_AUTH_CHAT}s "
          f"chat={T_CHAT_SEND}s exit={T_EXIT}s")
    print(f"{C.MAGENTA}[SYS]{C.RESET} login={MAX_CONCURRENT_LOGIN} song song, "
          f"retry={LOGIN_RETRY}, tries={MAX_TRIES_PER_GEN}\n")

    stop_evt = asyncio.Event()
    stop_flag = stop_evt
    accounts_ref = []
    accounts_ref_global = accounts_ref
    login_sem = asyncio.Semaphore(MAX_CONCURRENT_LOGIN)
    worker_tasks = []

    def spawn_worker(acc, wid):
        t = asyncio.create_task(worker_loop(acc, wid, cfg, stop_evt))
        worker_tasks.append(t)

    watcher_task = asyncio.create_task(
        file_watcher(accounts_ref, spawn_worker, login_sem, stop_evt)
    )
    supervisor_task = asyncio.create_task(leader_supervisor(accounts_ref, stop_evt))
    hb_task = asyncio.create_task(heartbeat_loop(accounts_ref, stop_evt))
    stats_task = asyncio.create_task(stats_loop(stop_evt))

    # ping API 5 phút (thread riêng)
    threading.Thread(target=api_pinger, daemon=True).start()

    try:
        await start_http_server()
    except Exception as e:
        print(f"{C.RED}[HTTP] Không start được: {e}{C.RESET}", flush=True)

    try:
        await asyncio.gather(
            watcher_task, supervisor_task, hb_task, stats_task,
            return_exceptions=True
        )
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
        print(f"\n{C.YELLOW}[STOP]{C.RESET}")

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
