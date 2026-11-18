#!/usr/bin/env python3
"""
1.py — Chia N leader theo số lượng acc
- <500 acc: 1 leader, 1 code
- <1000: 2 leader, 2 code
- <1500: 3 leader, 3 code
- >=1500: 4 leader, 4 code
- Worker pick random code để lấy 2 số cuối, random 5 số đầu (00000 -> 99999) để dò join
"""
import asyncio
import json
import os
import random
import sys
import time

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


# ============ CONFIG ============
MAX_ACCOUNTS = 2000
MAX_CONCURRENT_LOGIN = 30
LOGIN_RETRY = 3

MEMBER_WAIT_AFTER_OUT = 3.0
LEAVE_WAIT = 5.0
HEARTBEAT_INTERVAL = 8.0
KA_BYTES = bytes.fromhex("0215")

ROTATOR_INTERVAL = 10.0
LEADER_SUPERVISOR_INTERVAL = 5.0
MAX_TRIES_PER_GEN = 5
MAX_FAILED_CACHE = 5000
STATS_INTERVAL = 60.0
WATCH_INTERVAL = 2.0

INSTANCE_ID = os.environ.get("INSTANCE_ID", "")
AC_FILENAME = os.environ.get("AC_FILE", "ac.json")
AC_FILE = os.path.join(BASE_DIR, AC_FILENAME)
CFG_FILE = os.path.join(BASE_DIR, "ttoan.txt")


# ============ COLORS ============
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[38;5;46m"
    RED = "\033[38;5;196m"
    CYAN = "\033[38;5;51m"
    MAGENTA = "\033[38;5;201m"
    YELLOW = "\033[38;5;226m"
    GRAY = "\033[38;5;245m"
    WHITE = "\033[38;5;255m"


# ============ STATE ============
class STATE:
    codes = {}                      # {leader_idx: code}
    codes_lock = asyncio.Lock()
    code_generation = 0
    failed_codes = set()
    failed_lock = asyncio.Lock()

    total_join_attempts = 0
    total_join_success = 0
    total_join_fail = 0
    total_spam_sent = 0
    total_ghost_sent = 0
    start_time = time.time()


stop_flag = None
file_lock = asyncio.Lock()


# ============ HELPER ============
def compute_leader_count(n_acc):
    """Tính số leader theo số acc: 500 acc = 1 leader"""
    if n_acc <= 0:
        return 0
    return min(4, (n_acc // 500) + 1)


# ============ LOG ============
def ts():
    return time.strftime("%H:%M:%S")


def log_rotator(leader_idx, code):
    suffix = code[-2:] if len(code) >= 2 else code
    print(f"{C.GRAY}{ts()}{C.RESET} {C.MAGENTA}[L{leader_idx+1}]{C.RESET} "
          f"→ {C.BOLD}{code}{C.RESET} (giữ 2 số cuối: {C.GREEN}{suffix}{C.RESET})", flush=True)


def log_login(uid, ok, nick_or_err=""):
    if ok:
        print(f"{C.GRAY}{ts()}{C.RESET} {C.GREEN}[LOGIN]{C.RESET} {uid} "
              f"{C.GREEN}✓{C.RESET} {nick_or_err}", flush=True)
    else:
        print(f"{C.GRAY}{ts()}{C.RESET} {C.RED}[LOGIN]{C.RESET} {uid} "
              f"{C.RED}✗ {nick_or_err}{C.RESET}", flush=True)


def log_join(worker_id, nick, code, ok, detail=""):
    wtag = f"[W{worker_id:03d}]"
    nk = nick[:10].ljust(10)
    if ok:
        print(f"{C.GRAY}{ts()}{C.RESET} {C.GREEN}{wtag} {nk} {code}  ✓  "
              f"{detail}{C.RESET}", flush=True)
    else:
        print(f"{C.GRAY}{ts()}{C.RESET} {C.RED}{wtag} {nk} {code}  ✗{C.RESET}",
              flush=True)


def print_stats():
    elapsed = time.time() - STATE.start_time
    h, rem = divmod(int(elapsed), 3600)
    m, s = divmod(rem, 60)
    rate = (STATE.total_join_success / STATE.total_join_attempts * 100) \
        if STATE.total_join_attempts > 0 else 0
    codes_str = ", ".join(STATE.codes[k] for k in sorted(STATE.codes)) or "-"
    suffixes_str = ", ".join(STATE.codes[k][-2:] for k in sorted(STATE.codes) if len(STATE.codes[k]) >= 2) or "-"
    print()
    print(f"{C.CYAN}{'='*58}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} Leaders: {len(STATE.codes)}   "
          f"Gen: {STATE.code_generation}")
    print(f"{C.CYAN}|{C.RESET} Codes: {codes_str} (2 số cuối: {suffixes_str})")
    print(f"{C.CYAN}|{C.RESET} Join: {C.GREEN}{STATE.total_join_success}{C.RESET}/"
          f"{STATE.total_join_attempts} ({rate:.0f}%)   "
          f"Fail: {C.RED}{STATE.total_join_fail}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET} Spam: {STATE.total_spam_sent}   "
          f"Ghost: {STATE.total_ghost_sent}   "
          f"Uptime: {h:02d}:{m:02d}:{s:02d}")
    print(f"{C.CYAN}{'='*58}{C.RESET}")
    print()


# ============ CONFIG READER ============
def load_config():
    if not os.path.exists(CFG_FILE):
        return {"chat": "Contact @Ph_rin", "ghost": "[C][FF0000]@ph_rin"}
    chat_lines, ghost_lines = [], []
    current = None
    with open(CFG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            s = line.rstrip("\n")
            if s.strip().upper() == "[CHAT]":
                current = "chat"; continue
            if s.strip().upper() == "[GHOST]":
                current = "ghost"; continue
            if current == "chat": chat_lines.append(s)
            elif current == "ghost": ghost_lines.append(s)
    return {
        "chat": "\n".join(chat_lines).strip() or "contact @ph_rin",
        "ghost": "\n".join(ghost_lines).strip() or "[C][FF0000]@ph_rin_",
    }


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


# ============ LOGIN ============
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
        await asyncio.sleep(0.4)
    except Exception:
        return None

    ch_r = ch_w = None
    try:
        ch_r, ch_w = await asyncio.open_connection(gs["chatip"], int(gs["chatport"]))
        ch_w.write(ttoan.build_chat_auth(acc_id, token, login_time, key, iv))
        await ch_w.drain()
        await asyncio.sleep(0.4)
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


# ============ READ 0500 ============
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


# ============ HEARTBEAT ============
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


# ============ ROTATOR (per leader) ============
async def rotate_team(acc):
    on_r, on_w = acc["on_r"], acc["on_w"]
    acc_id, rc, key, iv = acc["acc_id"], acc["rc"], acc["key"], acc["iv"]
    if not on_w or on_w.is_closing():
        return None

    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(LEAVE_WAIT)
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
        await asyncio.sleep(0.5)
    except Exception:
        pass

    return code


async def leader_rotator(leader_idx, accounts_ref, stop_evt):
    """1 task riêng cho mỗi leader — đổi code mỗi 10s"""
    while not stop_evt.is_set():
        # Pick acc free
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
    """Giám sát số leader cần thiết, spawn/kill rotator task"""
    tasks = {}   # {leader_idx: task}

    while not stop_evt.is_set():
        n_acc = len(accounts_ref)
        n_leader = compute_leader_count(n_acc)

        # Kill leader thừa
        for idx in list(tasks.keys()):
            if idx >= n_leader:
                tasks[idx].cancel()
                try: await tasks[idx]
                except: pass
                del tasks[idx]
                async with STATE.codes_lock:
                    STATE.codes.pop(idx, None)

        # Spawn leader mới
        for idx in range(n_leader):
            if idx not in tasks or tasks[idx].done():
                tasks[idx] = asyncio.create_task(
                    leader_rotator(idx, accounts_ref, stop_evt)
                )

        await asyncio.sleep(LEADER_SUPERVISOR_INTERVAL)

    # Cleanup
    for t in tasks.values():
        if not t.done():
            t.cancel()


# ============ WORKER ============
async def try_join_once(acc, candidate):
    on_r, on_w = acc["on_r"], acc["on_w"]
    acc_id, rc, key, iv = acc["acc_id"], acc["rc"], acc["key"], acc["iv"]
    if not on_w or on_w.is_closing():
        return False, None

    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(1.5)
    except Exception:
        return False, None

    try:
        on_w.write(ttoan.join_code(candidate, rc, key, iv))
        await on_w.drain()
    except Exception:
        return False, None

    info = await read_0500(on_r, timeout=8.0)
    if not info or not info.get("owner_uid"):
        return False, None
    if info.get("squad_code", "") != candidate:
        return False, None
    return True, info


async def do_spam(acc, info, cfg):
    on_w = acc["on_w"]
    ch_w = acc["ch_w"]
    acc_id, rc, key, iv = acc["acc_id"], acc["rc"], acc["key"], acc["iv"]
    owner = int(info.get("owner_uid"))
    chat_int = info.get("chat_code_int", 0)
    chat_channel = info.get("chat_channel", "")
    secret_code = info.get("secret_code", "")

    chat_ok = False
    ghost_ok = False

    auth_val = str(chat_int) if chat_int else chat_channel
    if ch_w and auth_val and owner:
        try:
            ch_w.write(ttoan.auth_chat(3, owner, auth_val, key, iv))
            await ch_w.drain()
            await asyncio.sleep(0.8)
            chat_pkt = ttoan.send_chat_squad(cfg["chat"], owner, 0, key, iv)
            if chat_pkt:
                ch_w.write(chat_pkt)
                await ch_w.drain()
                chat_ok = True
                await asyncio.sleep(1.0)
        except Exception:
            pass

    try:
        on_w.write(ttoan.leave_team(acc_id, rc, key, iv))
        await on_w.drain()
        await asyncio.sleep(0.5)
    except Exception:
        pass

    if ch_w and owner:
        try:
            ch_w.write(ttoan.quit_chat(owner, key, iv))
            await ch_w.drain()
            await asyncio.sleep(0.2)
        except Exception:
            pass

    if on_w and owner and secret_code:
        try:
            ghost_pkt = ttoan.ghost_name(owner, cfg["ghost"], secret_code, key, iv)
            on_w.write(ghost_pkt)
            await on_w.drain()
            ghost_ok = True
            await asyncio.sleep(0.2)
        except Exception:
            pass

    return chat_ok, ghost_ok


async def spam_cycle(acc, cfg, worker_id):
    """Pick random code từ STATE.codes, giữ 2 số cuối và random 5 số đầu để thử join"""
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

        # Random 5 số đầu (00000 -> 99999), giữ nguyên 2 số cuối
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
            log_join(worker_id, nick, candidate, False)
            continue

        STATE.total_join_success += 1
        chat_ok, ghost_ok = await do_spam(acc, info, cfg)
        if chat_ok:
            STATE.total_spam_sent += 1
        if ghost_ok:
            STATE.total_ghost_sent += 1
        detail = "+".join(
            [x for x, k in [("chat", chat_ok), ("ghost", ghost_ok)] if k]
        )
        log_join(worker_id, nick, candidate, True, detail or "join")
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
            await asyncio.sleep(0.3)
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


# ============ WATCHER ============
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
                log_login(uid, True, f"{acc['nickname'][:20]} → W{wid:03d}")
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


# ============ MAIN ============
async def main():
    global stop_flag

    cfg = load_config()

    accs = load_accounts()
    n = len(accs)
    if n > 0:
        print(f"{C.CYAN}[ACC]{C.RESET} {n} acc trong {AC_FILENAME} "
              f"(max {MAX_ACCOUNTS}, {compute_leader_count(n)} leader)")
    else:
        print(f"{C.CYAN}[ACC]{C.RESET} 0 acc trong {AC_FILENAME} (đang chờ gen.py tạo...)")

    print(f"{C.CYAN}[CFG]{C.RESET} Chat: {cfg['chat'][:50].replace(chr(10), ' | ')}...")
    print(f"{C.CYAN}[CFG]{C.RESET} Ghost: {cfg['ghost'][:50]}")
    print(f"{C.MAGENTA}[SYS]{C.RESET} Logic dò code: Random 5 số đầu + Giữ 2 số cuối")
    print(f"{C.MAGENTA}[SYS]{C.RESET} login={MAX_CONCURRENT_LOGIN} song song, "
          f"retry={LOGIN_RETRY}, rotator={ROTATOR_INTERVAL}s\n")

    stop_evt = asyncio.Event()
    stop_flag = stop_evt
    accounts_ref = []
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
            await close_acc(acc)
        print_stats()
        print(f"\n{C.YELLOW}[STOP]{C.RESET}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}[CTRL+C]{C.RESET}")
