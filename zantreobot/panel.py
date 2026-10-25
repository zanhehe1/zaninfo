# -*- coding: utf-8 -*-
"""
ZAN BOT MANAGER - backend của web dashboard (Flask Blueprint, chạy chung start.py)

Mở:  http://localhost:2009/panel

Bảo mật
  * Đăng nhập bằng cookie phiên ký số (HttpOnly, SameSite=Strict) + CSRF token.
  * 2 vai trò: admin (toàn quyền) và viewer (chỉ xem).
  * Mật khẩu lưu dạng PBKDF2 trong panel_data/auth.json, KHÔNG lưu plain-text
    (mặc định admin123 nếu chưa đặt/đổi).
  * Token bot không bao giờ gửi xuống trình duyệt (chỉ gửi bản đã che).
  * Các route quản trị cũ của start.py (/check, /addbot, /delbot, /addid, ...)
    được khoá: cần phiên admin, hoặc header X-API-Key, hoặc gọi trực tiếp từ localhost.

Biến môi trường (đều tuỳ chọn)
  PANEL_ADMIN_PASSWORD   mật khẩu admin (nếu không đặt: mặc định admin123)
  PANEL_VIEWER_PASSWORD  mật khẩu tài khoản viewer (chỉ xem)
  PANEL_API_KEY          khoá cho các script gọi API cũ từ máy khác
  PANEL_DATA_DIR         thư mục lưu dữ liệu panel (mặc định ./panel_data)
  PANEL_REMOTE_URL       (tuỳ chọn) địa chỉ máy đang chạy bot, để web hiện log của bot ở máy khác
  PANEL_REMOTE_KEY       khoá = PANEL_API_KEY đặt ở máy chạy bot
"""
import os, re, json, time, hmac, base64, hashlib, secrets, threading, sys, platform
import datetime as _dt
from flask import Blueprint, jsonify, request, send_file, make_response, abort, g
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("PANEL_DATA_DIR") or os.path.join(os.getcwd(), "panel_data")
HTML_PATH = os.path.join(BASE, "panel.html")
FMT = "%Y-%m-%d %H:%M:%S"
FOREVER = "2099-12-31 23:59:59"
SESSION_TTL = 12 * 3600
STARTED = time.time()

bp = Blueprint("zan_panel", __name__)
_mng = None
_lock = threading.RLock()
_fails = {}  # ip -> [count, locked_until]

LEGACY_GUARDED = {"/check", "/addid", "/delid", "/addbot", "/delbot", "/addadmin",
                  "/resetbot", "/online", "/offline"}


# ───────────────────────── lưu trữ nhỏ ─────────────────────────
def _p(name):
    return os.path.join(DATA_DIR, name)


def _read_json(name, default):
    try:
        with open(_p(name), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(name, data):
    tmp = _p(name) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _p(name))


def _hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()
    return {"salt": salt, "hash": h}


def _check_pw(pw, rec):
    if not rec:
        return False
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(rec["salt"]), 200_000).hex()
    return hmac.compare_digest(h, rec["hash"])


_auth = {}      # {"admin": rec, "viewer": rec|None}
_env_locked = set()
_serializer = None


def _setup_storage():
    global _serializer
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        os.chmod(DATA_DIR, 0o700)
    except Exception:
        pass
    # khoá ký cookie
    kp = _p("secret.key")
    if not os.path.exists(kp):
        with open(kp, "w") as f:
            f.write(secrets.token_hex(32))
        try:
            os.chmod(kp, 0o600)
        except Exception:
            pass
    _serializer = URLSafeTimedSerializer(open(kp).read().strip(), salt="zan-panel-session")
    _con_file[0] = _p("console.log")

    stored = _read_json("auth.json", {})
    env_admin = os.environ.get("PANEL_ADMIN_PASSWORD", "").strip()
    env_viewer = os.environ.get("PANEL_VIEWER_PASSWORD", "").strip()
    if env_admin:
        _auth["admin"] = _hash_pw(env_admin)
        _env_locked.add("admin")
    elif stored.get("admin"):
        _auth["admin"] = stored["admin"]
    else:
        _auth["admin"] = _hash_pw("admin123")
        print("[PANEL] 🔑 Mật khẩu admin mặc định: admin123 (hãy đổi trong Cài đặt hoặc đặt PANEL_ADMIN_PASSWORD)")
    if env_viewer:
        _auth["viewer"] = _hash_pw(env_viewer)
        _env_locked.add("viewer")
    else:
        _auth["viewer"] = stored.get("viewer")


def _persist_auth():
    _write_json("auth.json", {
        "admin": None if "admin" in _env_locked else _auth.get("admin"),
        "viewer": None if "viewer" in _env_locked else _auth.get("viewer"),
    })


# ───────────────────────── bắt log console (stdout/stderr) ─────────────────────────
from collections import deque

_CON = deque(maxlen=3000)      # (seq, "HH:MM:SS", text)
_con_seq = [0]
_con_lock = threading.Lock()
_con_file = [None]
_TOKEN_RE = re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}")
_DROP_RE = re.compile(r'"(GET|POST|PATCH|DELETE) /panel[/ ]')   # bỏ log polling của chính panel


class _Tee:
    """Ghi đè sys.stdout/sys.stderr: vẫn in ra màn hình như cũ, đồng thời lưu vào bộ nhớ cho web."""
    def __init__(self, orig):
        self.orig, self.buf = orig, ""

    def write(self, s):
        try:
            n = self.orig.write(s)
        except Exception:
            n = len(s)
        try:
            self.buf += s
            while "\n" in self.buf:
                line, self.buf = self.buf.split("\n", 1)
                _con_add(line)
            if len(self.buf) > 4000:
                _con_add(self.buf); self.buf = ""
        except Exception:
            pass
        return n

    def flush(self):
        try:
            self.orig.flush()
        except Exception:
            pass

    def __getattr__(self, k):
        return getattr(self.orig, k)


def _con_add(line):
    line = line.rstrip("\r")
    if not line.strip() or _DROP_RE.search(line):
        return
    line = _TOKEN_RE.sub("***", line)[:1200]
    with _con_lock:
        _con_seq[0] += 1
        t = _dt.datetime.now().strftime("%H:%M:%S")
        _CON.append((_con_seq[0], t, line))
        try:
            fp = _con_file[0]
            if fp:
                with open(fp, "a", encoding="utf-8") as f:
                    f.write(f"{_dt.datetime.now().strftime(FMT)} {line}\n")
                if _con_seq[0] % 500 == 0 and os.path.getsize(fp) > 2_000_000:
                    keep = open(fp, encoding="utf-8").read().splitlines()[-5000:]
                    open(fp, "w", encoding="utf-8").write("\n".join(keep) + "\n")
        except Exception:
            pass


def _install_capture():
    if isinstance(sys.stdout, _Tee):
        return
    sys.stdout = _Tee(sys.stdout)
    sys.stderr = _Tee(sys.stderr)


_install_capture()   # chạy ngay khi `import panel` (đặt ở đầu start.py để bắt log từ lúc khởi động)


# ───────────────────────── nhật ký ─────────────────────────
_SECRET_RE = re.compile(r"\d{6,}:[A-Za-z0-9_-]{20,}")


def _clean(s):
    return _SECRET_RE.sub("***", str(s))[:300]


def log(typ, action, status="ok", detail="", actor=None):
    rec = {"t": _dt.datetime.now().strftime(FMT), "type": typ, "action": action,
           "status": status, "detail": _clean(detail),
           "actor": actor or getattr(g, "role", None) or "system"}
    try:
        with _lock:
            fp = _p("activity.jsonl")
            with open(fp, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if os.path.getsize(fp) > 600_000:  # cắt bớt, giữ 1500 dòng cuối
                lines = open(fp, encoding="utf-8").read().splitlines()[-1500:]
                with open(fp, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
    except Exception as e:
        print("[PANEL] log lỗi:", e)


def _read_log():
    out = []
    try:
        with open(_p("activity.jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    except FileNotFoundError:
        pass
    return out


def _sample_loop():
    """Ghi số bot online mỗi 5 phút để vẽ biểu đồ hoạt động thật."""
    while True:
        try:
            with _mng.config_lock:
                bots = [_serialize(b["bot_id"], b) for b in _mng.config["bots"]]
            rec = {"t": _dt.datetime.now().strftime(FMT),
                   "online": sum(1 for b in bots if b["online"]),
                   "total": len(bots)}
            hist = _read_json("history.json", [])
            hist.append(rec)
            _write_json("history.json", hist[-288:])
        except Exception as e:
            print("[PANEL] sample lỗi:", e)
        time.sleep(300)


# ───────────────────────── xác thực ─────────────────────────
def _loopback_direct():
    return request.remote_addr in ("127.0.0.1", "::1") and not request.headers.get("X-Forwarded-For")


def _session():
    tok = request.cookies.get("zp_session")
    if not tok:
        return None
    try:
        return _serializer.loads(tok, max_age=SESSION_TTL)
    except (BadSignature, SignatureExpired):
        return None


@bp.before_request
def _before():
    p = request.path
    if p == "/panel" or p == "/panel/":
        return None
    if p in ("/panel/api/login",):
        return None
    if not p.startswith("/panel/api/"):
        return None
    if p == "/panel/api/console" and request.method == "GET":
        key = os.environ.get("PANEL_API_KEY", "").strip()
        if key and hmac.compare_digest(request.headers.get("X-API-Key", ""), key):
            g.role, g.csrf = "remote", ""      # chỉ đọc log, dành cho panel đặt ở máy khác
            return None
    s = _session()
    if not s:
        return jsonify({"ok": False, "msg": "Chưa đăng nhập", "auth": False}), 401
    g.role, g.csrf = s["r"], s["c"]
    if request.method not in ("GET", "HEAD"):
        if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), g.csrf):
            return jsonify({"ok": False, "msg": "CSRF token không hợp lệ"}), 403
        if p != "/panel/api/logout" and g.role != "admin":
            return jsonify({"ok": False, "msg": "Tài khoản chỉ-xem không có quyền thay đổi"}), 403
    return None


def _need_admin():
    if getattr(g, "role", None) != "admin":
        abort(403)


@bp.errorhandler(403)
def _e403(e):
    return jsonify({"ok": False, "msg": "Không đủ quyền"}), 403


def guard_legacy():
    """Khoá các route quản trị cũ của start.py."""
    if request.path not in LEGACY_GUARDED:
        return None
    s = _session()
    if s and s.get("r") == "admin":
        return None
    key = os.environ.get("PANEL_API_KEY", "").strip()
    if key and hmac.compare_digest(request.headers.get("X-API-Key", ""), key):
        return None
    if _loopback_direct():
        return None
    return ("Unauthorized", 401)


# ───────────────────────── helper dữ liệu ─────────────────────────
def _parse_expire(v):
    try:
        if isinstance(v, (int, float)):
            return _dt.datetime.fromtimestamp(v)
        return _dt.datetime.strptime(str(v), FMT)
    except Exception:
        return None


def _delta(s):
    s = (s or "").strip().lower()
    if s in ("vv", "forever"):
        return None, True
    m = re.match(r"^(\d{1,4})([hdwmy])$", s)
    if not m:
        raise ValueError("Thời hạn không hợp lệ (vd: 12h, 7d, 4w, 3m, 1y, vv)")
    n, u = int(m.group(1)), m.group(2)
    if n <= 0:
        raise ValueError("Thời hạn phải lớn hơn 0")
    days = {"h": n / 24, "d": n, "w": n * 7, "m": n * 30, "y": n * 365}[u]
    return _dt.timedelta(days=days), False


def _mask(t):
    t = t or ""
    return (t[:4] + "••••••••" + t[-4:]) if len(t) > 12 else "••••••••"


def _bot_cfg(bid):
    for b in _mng.config["bots"]:
        if b["bot_id"] == bid:
            return b
    return None


def _user_row(u, now):
    exp = _parse_expire(u.get("expire"))
    return {"uid": u.get("uid"), "expire": u.get("expire"),
            "forever": bool(exp and exp.year >= 2050),
            "expired": bool(exp and exp < now),
            "left_sec": int((exp - now).total_seconds()) if exp else None}


def _serialize(bid, cfg):
    inst = _mng.bots.get(bid)
    now = _dt.datetime.now()
    users = [_user_row(u, now) for u in cfg.get("access_bot", [])]
    users.sort(key=lambda x: (x["expired"], x["left_sec"] if x["left_sec"] is not None else 0))
    ev = getattr(inst, "running_event", None) if inst else None
    return {
        "id": bid,
        "botid": getattr(inst, "botid", None) or cfg.get("botid"),
        "nickname": getattr(inst, "nickname", None) or cfg.get("nickname") or "",
        "label": cfg.get("label", ""),
        "token_masked": _mask(cfg.get("auth_bot_login", {}).get("access_token", "")),
        "online": bool(ev is not None and ev.is_set()),
        "guild": cfg.get("active-clan", True),
        "in_guild": bool(getattr(inst, "GuildIds", None)) if inst else False,
        "users": users,
    }


def _save():
    _mng.save_config()


def _body():
    return request.get_json(silent=True) or {}


def _int(v, name="giá trị"):
    try:
        return int(str(v).strip())
    except Exception:
        raise ValueError(f"{name} phải là số")


def _err(msg, code=400):
    return jsonify({"ok": False, "msg": msg}), code


def _apply_time(cfg, uid, time_s, mode="extend"):
    """Cấp / gia hạn 1 UID trên 1 bot. Trả (hành động, hạn mới)."""
    delta, forever = _delta(time_s)
    lst = cfg.setdefault("access_bot", [])
    cur = next((u for u in lst if u.get("uid") == uid), None)
    now = _dt.datetime.now()
    if forever:
        new = FOREVER
    else:
        base = now
        if cur and mode == "extend":
            old = _parse_expire(cur.get("expire"))
            if old and old > now:
                base = old
        new = (base + delta).strftime(FMT)
    if cur:
        cur["expire"] = new
        return "gia hạn", new
    lst.append({"uid": uid, "expire": new})
    return "cấp quyền", new


# ───────────────────────── routes: trang & auth ─────────────────────────
@bp.route("/panel")
@bp.route("/panel/")
def page():
    r = make_response(send_file(HTML_PATH))
    r.headers["Cache-Control"] = "no-store"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "no-referrer"
    return r


@bp.route("/panel/api/login", methods=["POST"])
def login():
    ip = request.remote_addr or "?"
    st = _fails.get(ip, [0, 0])
    if st[1] > time.time():
        return _err(f"Sai quá nhiều lần, thử lại sau {int(st[1] - time.time())}s", 429)
    b = _body()
    user, pw = str(b.get("username", "")).strip().lower(), str(b.get("password", ""))
    ok = user in ("admin", "viewer") and _check_pw(pw, _auth.get(user))
    if not ok:
        st[0] += 1
        if st[0] >= 5:
            st = [0, time.time() + 300]
        _fails[ip] = st
        log("auth", "đăng nhập", "fail", f"tài khoản {user[:20]} từ {ip}", actor=user[:20] or "?")
        time.sleep(0.6)
        return _err("Sai tài khoản hoặc mật khẩu", 401)
    _fails.pop(ip, None)
    csrf = secrets.token_urlsafe(24)
    tok = _serializer.dumps({"r": user, "c": csrf})
    resp = jsonify({"ok": True, "role": user, "csrf": csrf})
    resp.set_cookie("zp_session", tok, max_age=SESSION_TTL, httponly=True,
                    samesite="Strict", secure=request.is_secure)
    log("auth", "đăng nhập", "ok", f"từ {ip}", actor=user)
    return resp


@bp.route("/panel/api/logout", methods=["POST"])
def logout():
    resp = jsonify({"ok": True})
    resp.delete_cookie("zp_session")
    log("auth", "đăng xuất")
    return resp


@bp.route("/panel/api/me")
def me():
    return jsonify({"ok": True, "role": g.role, "csrf": g.csrf})


@bp.route("/panel/api/password", methods=["POST"])
def change_password():
    _need_admin()
    b = _body()
    target = b.get("account", "admin")
    new = str(b.get("new", ""))
    if target not in ("admin", "viewer"):
        return _err("Tài khoản không hợp lệ")
    if target in _env_locked:
        return _err("Mật khẩu này đang đặt bằng biến môi trường, hãy đổi ở đó")
    if target == "admin" and not _check_pw(str(b.get("current", "")), _auth["admin"]):
        return _err("Mật khẩu hiện tại không đúng")
    if not new and target == "viewer":
        _auth["viewer"] = None
        _persist_auth()
        log("settings", "tắt tài khoản viewer")
        return jsonify({"ok": True, "msg": "Đã tắt tài khoản viewer"})
    if len(new) < 8:
        return _err("Mật khẩu mới tối thiểu 8 ký tự")
    _auth[target] = _hash_pw(new)
    _persist_auth()
    log("settings", f"đổi mật khẩu {target}")
    return jsonify({"ok": True, "msg": f"Đã đổi mật khẩu {target}"})


# ───────────────────────── routes: dữ liệu ─────────────────────────
@bp.route("/panel/api/overview")
def overview():
    with _mng.config_lock:
        bots = [_serialize(b["bot_id"], b) for b in _mng.config["bots"]]
    now_users = {u["uid"] for b in bots for u in b["users"] if not u["expired"]}
    logs = _read_log()
    hist = _read_json("history.json", [])
    # hoạt động quản trị theo giờ (24h gần nhất) từ nhật ký thật
    buckets = {}
    cutoff = _dt.datetime.now() - _dt.timedelta(hours=24)
    for r in logs:
        try:
            t = _dt.datetime.strptime(r["t"], FMT)
        except Exception:
            continue
        if t >= cutoff and r["type"] in ("bot", "user"):
            k = t.strftime("%Y-%m-%d %H:00")
            buckets[k] = buckets.get(k, 0) + 1
    return jsonify({
        "ok": True,
        "total": len(bots),
        "online": sum(1 for b in bots if b["online"]),
        "offline": sum(1 for b in bots if not b["online"]),
        "users": len(now_users),
        "grants": sum(len(b["users"]) for b in bots),
        "expired": sum(1 for b in bots for u in b["users"] if u["expired"]),
        "recent": sorted(bots, key=lambda b: -b["id"])[:5],
        "history": hist[-96:],
        "actions24h": buckets,
        "events": logs[-8:][::-1],
        "backend": {
            "api": True,
            "uptime_sec": int(time.time() - STARTED),
            "python": platform.python_version(),
            "bot_json": os.path.exists(getattr(_mng, "filename", "bot.json")),
            "data_dir_ok": os.access(DATA_DIR, os.W_OK),
            "threads": threading.active_count(),
        },
    })


@bp.route("/panel/api/bots", methods=["GET"])
def list_bots():
    with _mng.config_lock:
        return jsonify({"ok": True, "bots": [_serialize(b["bot_id"], b) for b in _mng.config["bots"]]})


@bp.route("/panel/api/bots", methods=["POST"])
def add_bot():
    b = _body()
    token = str(b.get("token", "")).strip()
    if not token or len(token) < 20 or len(token) > 300 or re.search(r"\s", token):
        return _err("Access token không hợp lệ")
    res = _mng.add_bot(token)
    if not res.get("status"):
        log("bot", "thêm bot", "fail", res.get("message", ""))
        return _err(res.get("message", "Không thêm được bot"))
    bid = res["bot_id"]
    label = str(b.get("label", "")).strip()[:60]
    if label:
        with _mng.config_lock:
            _bot_cfg(bid)["label"] = label
            _save()
    try:
        _mng.bots[bid].start()
    except Exception as e:
        log("bot", "thêm bot", "warn", f"bot #{bid} chưa chạy được: {e}")
        return jsonify({"ok": True, "id": bid, "msg": f"Đã thêm bot #{bid} nhưng chưa khởi động được"})
    log("bot", "thêm bot", "ok", f"bot #{bid}")
    return jsonify({"ok": True, "id": bid, "msg": f"Đã thêm bot #{bid} và đang khởi động"})


@bp.route("/panel/api/bots/<int:bid>", methods=["PATCH"])
def edit_bot(bid):
    b = _body()
    changed = []
    restart = False
    with _mng.config_lock:
        cfg = _bot_cfg(bid)
        if not cfg:
            return _err("Không tìm thấy bot", 404)
        if "label" in b:
            cfg["label"] = str(b["label"]).strip()[:60]
            changed.append("ghi chú")
        if b.get("token"):
            t = str(b["token"]).strip()
            if len(t) < 20 or len(t) > 300 or re.search(r"\s", t):
                return _err("Access token không hợp lệ")
            ex, other = _mng.check_token_exists(t)
            if ex and other != bid:
                return _err("Token này đã được dùng cho bot khác")
            cfg["auth_bot_login"]["access_token"] = t
            changed.append("token")
            restart = True
        _save()
    if "guild" in b:
        res = _mng.toggle_guild_activation(bid, "on" if b["guild"] else "off")
        if res in ("error", "Bot is not in guild"):
            log("bot", "đổi chế độ guild", "fail", f"bot #{bid}: {res}")
            return _err("Bot chưa vào guild nên chưa đổi được chế độ guild" if res != "error" else "Không đổi được")
        changed.append("guild")
    if restart:
        _restart(bid)
    if not changed:
        return _err("Không có gì để cập nhật")
    log("bot", "sửa bot", "ok", f"bot #{bid}: {', '.join(changed)}")
    return jsonify({"ok": True, "msg": f"Đã cập nhật bot #{bid} ({', '.join(changed)})"})


@bp.route("/panel/api/bots/<int:bid>", methods=["DELETE"])
def delete_bot(bid):
    with _mng.config_lock:
        cfg = _bot_cfg(bid)
        if not cfg and bid not in _mng.bots:
            return _err("Không tìm thấy bot", 404)
        inst = _mng.bots.pop(bid, None)
        if inst:
            try:
                inst.cleanup()
            except Exception:
                pass
        _mng.config["bots"] = [x for x in _mng.config["bots"] if x["bot_id"] != bid]
        _save()
    log("bot", "xoá bot", "ok", f"bot #{bid}")
    return jsonify({"ok": True, "msg": f"Đã xoá bot #{bid}"})


def _restart(bid):
    inst = _mng.bots.get(bid)
    if not inst:
        return False

    def work():
        try:
            inst.cleanup()
            time.sleep(0.5)
            inst.running_event.set()
            inst.started = False
            inst.start()
        except Exception as e:
            log("bot", "restart", "fail", f"bot #{bid}: {e}", actor="system")

    threading.Thread(target=work, daemon=True).start()
    return True


@bp.route("/panel/api/bots/<int:bid>/restart", methods=["POST"])
def restart_bot(bid):
    if not _restart(bid):
        return _err("Không tìm thấy bot", 404)
    log("bot", "restart", "ok", f"bot #{bid}")
    return jsonify({"ok": True, "msg": f"Đang khởi động lại bot #{bid}"})


@bp.route("/panel/api/bots/<int:bid>/access", methods=["POST"])
def add_access(bid):
    b = _body()
    try:
        uid = _int(b.get("uid"), "UID")
        with _mng.config_lock:
            cfg = _bot_cfg(bid)
            if not cfg:
                return _err("Không tìm thấy bot", 404)
            act, exp = _apply_time(cfg, uid, b.get("time", ""), b.get("mode", "extend"))
            _save()
    except ValueError as e:
        return _err(str(e))
    log("user", act, "ok", f"UID {uid} • bot #{bid} • hạn {exp}")
    return jsonify({"ok": True, "msg": f"Đã {act} UID {uid} → {exp}"})


@bp.route("/panel/api/bots/<int:bid>/access/<int:uid>", methods=["DELETE"])
def del_access(bid, uid):
    with _mng.config_lock:
        cfg = _bot_cfg(bid)
        if not cfg:
            return _err("Không tìm thấy bot", 404)
        before = cfg.get("access_bot", [])
        after = [u for u in before if u.get("uid") != uid]
        if len(after) == len(before):
            return _err("UID không có trong danh sách", 404)
        cfg["access_bot"] = after
        _save()
    log("user", "thu hồi quyền", "ok", f"UID {uid} • bot #{bid}")
    return jsonify({"ok": True, "msg": f"Đã thu hồi quyền UID {uid}"})


# ───── user (gộp theo UID trên tất cả bot) ─────
@bp.route("/panel/api/users")
def list_users():
    now = _dt.datetime.now()
    users = {}
    with _mng.config_lock:
        for cfg in _mng.config["bots"]:
            inst = _mng.bots.get(cfg["bot_id"])
            name = (getattr(inst, "nickname", None) if inst else None) or cfg.get("nickname") or ""
            for u in cfg.get("access_bot", []):
                row = _user_row(u, now)
                row.update({"bot_id": cfg["bot_id"], "bot_name": cfg.get("label") or name})
                users.setdefault(u["uid"], []).append(row)
    out = []
    for uid, grants in users.items():
        active = [x for x in grants if not x["expired"]]
        out.append({"uid": uid, "grants": grants, "active": len(active),
                    "forever": any(x["forever"] for x in grants)})
    out.sort(key=lambda x: (-x["active"], x["uid"]))
    return jsonify({"ok": True, "users": out})


@bp.route("/panel/api/users", methods=["POST"])
def create_user():
    b = _body()
    try:
        uid = _int(b.get("uid"), "UID")
        ids = b.get("bots")
        with _mng.config_lock:
            if ids == "all":
                ids = [c["bot_id"] for c in _mng.config["bots"]]
            if not isinstance(ids, list) or not ids:
                return _err("Chọn ít nhất 1 bot")
            done = 0
            for bid in ids:
                cfg = _bot_cfg(_int(bid, "ID bot"))
                if cfg:
                    _apply_time(cfg, uid, b.get("time", ""), "extend")
                    done += 1
            if not done:
                return _err("Không tìm thấy bot nào")
            _save()
    except ValueError as e:
        return _err(str(e))
    log("user", "cấp quyền", "ok", f"UID {uid} • {done} bot • {b.get('time')}")
    return jsonify({"ok": True, "msg": f"Đã cấp quyền UID {uid} trên {done} bot"})


@bp.route("/panel/api/users/<int:uid>", methods=["PATCH"])
def edit_user(uid):
    """Sửa quyền của 1 user: grant (cấp/đặt lại hạn trên các bot) và/hoặc revoke."""
    b = _body()
    n_grant = n_rev = 0
    try:
        with _mng.config_lock:
            for bid in b.get("grant", []) or []:
                cfg = _bot_cfg(_int(bid, "ID bot"))
                if cfg:
                    _apply_time(cfg, uid, b.get("time", ""), b.get("mode", "set"))
                    n_grant += 1
            for bid in b.get("revoke", []) or []:
                cfg = _bot_cfg(_int(bid, "ID bot"))
                if cfg:
                    old = cfg.get("access_bot", [])
                    cfg["access_bot"] = [u for u in old if u.get("uid") != uid]
                    n_rev += len(old) - len(cfg["access_bot"])
            if not (n_grant or n_rev):
                return _err("Không có thay đổi nào")
            _save()
    except ValueError as e:
        return _err(str(e))
    log("user", "sửa quyền", "ok", f"UID {uid}: +{n_grant} / -{n_rev}")
    return jsonify({"ok": True, "msg": f"Đã cập nhật UID {uid} (+{n_grant} / -{n_rev})"})


@bp.route("/panel/api/users/<int:uid>", methods=["DELETE"])
def delete_user(uid):
    n = 0
    with _mng.config_lock:
        for cfg in _mng.config["bots"]:
            old = cfg.get("access_bot", [])
            new = [u for u in old if u.get("uid") != uid]
            if len(new) != len(old):
                cfg["access_bot"] = new
                n += 1
        if not n:
            return _err("Không tìm thấy user", 404)
        _save()
    log("user", "xoá user", "ok", f"UID {uid} khỏi {n} bot")
    return jsonify({"ok": True, "msg": f"Đã xoá UID {uid} khỏi {n} bot"})


# ───── console log ─────
@bp.route("/panel/api/console")
def console():
    try:
        since = int(request.args.get("since", "0"))
    except ValueError:
        since = 0
    limit = min(max(int(request.args.get("limit", "600") or 600), 1), 2000)
    remote = os.environ.get("PANEL_REMOTE_URL", "").strip().rstrip("/")
    if remote and getattr(g, "role", "") != "remote":
        # panel này chỉ là "màn hình": lấy log từ nơi bot đang chạy
        try:
            import requests
            r = requests.get(remote + "/panel/api/console", params={"since": since, "limit": limit},
                             headers={"X-API-Key": os.environ.get("PANEL_REMOTE_KEY", "")}, timeout=6)
            if r.status_code != 200:
                raise RuntimeError(f"máy bot trả về HTTP {r.status_code} (kiểm tra PANEL_REMOTE_KEY / PANEL_API_KEY)")
            d = r.json()
            d["source"] = "remote"
            return jsonify(d)
        except Exception as e:
            return jsonify({"ok": True, "lines": [], "last": since, "reset": False, "source": "remote",
                            "error": "Không lấy được log từ máy bot: " + _clean(e)})
    with _con_lock:
        data = list(_CON)
    last = _con_seq[0]
    reset = since > last          # bot vừa khởi động lại → web nạp lại từ đầu
    if reset:
        since = 0
    lines = [{"n": n, "t": t, "s": txt} for n, t, txt in data if n > since]
    if not since:
        lines = lines[-limit:]
    else:
        lines = lines[:limit]
    return jsonify({"ok": True, "lines": lines, "last": last, "reset": reset, "source": "local"})


# ───── log & settings ─────
@bp.route("/panel/api/logs")
def get_logs():
    typ = request.args.get("type", "")
    st = request.args.get("status", "")
    q = request.args.get("q", "").lower()
    hours = request.args.get("hours", "")
    rows = _read_log()
    if hours.isdigit():
        cut = _dt.datetime.now() - _dt.timedelta(hours=int(hours))
        rows = [r for r in rows if (_parse_expire(r.get("t")) or cut) >= cut]
    if typ:
        rows = [r for r in rows if r.get("type") == typ]
    if st:
        rows = [r for r in rows if r.get("status") == st]
    if q:
        rows = [r for r in rows if q in json.dumps(r, ensure_ascii=False).lower()]
    return jsonify({"ok": True, "logs": rows[-300:][::-1], "total": len(rows)})


@bp.route("/panel/api/logs", methods=["DELETE"])
def clear_logs():
    _need_admin()
    with _lock:
        open(_p("activity.jsonl"), "w").close()
    log("settings", "xoá nhật ký")
    return jsonify({"ok": True, "msg": "Đã xoá nhật ký"})


@bp.route("/panel/api/settings")
def get_settings():
    return jsonify({"ok": True, "info": {
        "admin_pw_env": "admin" in _env_locked,
        "viewer_enabled": bool(_auth.get("viewer")),
        "viewer_pw_env": "viewer" in _env_locked,
        "api_key_set": bool(os.environ.get("PANEL_API_KEY", "").strip()),
        "remote": os.environ.get("PANEL_REMOTE_URL", "").strip(),
        "data_dir": DATA_DIR,
        "session_hours": SESSION_TTL // 3600,
        "python": platform.python_version(),
    }})


# ───────────────────────── khởi tạo ─────────────────────────
def init_panel(app, manager):
    global _mng
    _mng = manager
    _setup_storage()
    app.register_blueprint(bp)
    app.before_request(guard_legacy)
    threading.Thread(target=_sample_loop, daemon=True).start()
    print("[PANEL] ✅ Dashboard quản lý bot: http://localhost:2009/panel")
