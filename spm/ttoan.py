"""
ttoan.py — Proto/packet builders tự chứa
- Bỏ hoàn toàn decorate_chat / con mắt 👁️
- Chat gửi nguyên văn text từ ttoan.txt
- Fix parse_0500 chuẩn (f11=team_code, f14=chat_channel, f17=chat_int, f31=secret_code)
"""
import time
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from protobuf_decoder.protobuf_decoder import Parser

# ============ CONST ============
AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV  = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

REGION_CODE_MAP = {
    "VN": "01", "IND": "14", "BD": "19", "ME": "15",
    "PK": "17", "ID": "15", "TH": "15", "SG": "15",
    "BR": "15", "US": "15",
}

REGION_IDC_MAP = {
    "VN": "IDC1", "BD": "IDC3", "IND": "IDC3", "ME": "IDC3",
}


# ============ HELPERS ============
def _vr(n):
    if n < 0: n &= 0xFFFFFFFFFFFFFFFF
    out = []
    while True:
        b = n & 0x7F
        n >>= 7
        if n: b |= 0x80
        out.append(b)
        if not n: break
    return bytes(out)


def _proto(fields):
    packet = bytearray()
    for f, v in fields.items():
        if isinstance(v, dict):
            nested = _proto(v)
            packet.extend(_vr((f << 3) | 2) + _vr(len(nested)) + nested)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    nested = _proto(item)
                    packet.extend(_vr((f << 3) | 2) + _vr(len(nested)) + nested)
                elif isinstance(item, int):
                    packet.extend(_vr((f << 3) | 0) + _vr(item))
                elif isinstance(item, (str, bytes)):
                    enc = item.encode() if isinstance(item, str) else item
                    packet.extend(_vr((f << 3) | 2) + _vr(len(enc)) + enc)
        elif isinstance(v, int):
            packet.extend(_vr((f << 3) | 0) + _vr(v))
        elif isinstance(v, (str, bytes)):
            enc = v.encode() if isinstance(v, str) else v
            packet.extend(_vr((f << 3) | 2) + _vr(len(enc)) + enc)
    return bytes(packet)


def _gene_pk(pk_hex, pkt_type, key, iv):
    enc_hex = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(bytes.fromhex(pk_hex), 16)).hex()
    h = hex(len(enc_hex) // 2)[2:]
    if len(h) == 1: h = "0" + h
    head = {2: "000000", 3: "00000", 4: "0000", 5: "000"}.get(len(h), "")
    return bytes.fromhex(pkt_type + head + h + enc_hex)


def _gp_build(fields, region_code, key, iv):
    header_type = fields[0][1]
    payload = _proto(dict(fields[1:]))
    enc = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(payload, 16)).hex()
    length = hex(len(enc) // 2)[2:]
    zeros = '0' * (8 - len(length)) if len(length) < 8 else ''
    return bytes.fromhex("%02x%s%s%s%s" % (header_type, region_code, zeros, length, enc))


# ============ 1. MỞ TEAM (CMD 1) ============
def create_team(team_size, region_code, idc, region, key, iv, game_version="1.132.9"):
    f2_map = bytes.fromhex("011d")
    proto_team_size = 3 if team_size >= 3 else team_size
    sub2 = {
        2: f2_map, 3: 15, 4: proto_team_size, 5: "en",
        8: {1: idc, 2: 123, 3: region}, 9: 1,
        10: bytes.fromhex("011d"),
        11: 1, 13: 1,
        14: {
            1: "08FBA33B4BABE2790205390333330000009700050092005F72697EB2134DCBB2467625142201040e38e848dc0e748c3f6aa04d81000000ff1113090dcacfa16d",
            2: 478, 3: "7e585d55", 4: "y[Z]", 6: 12,
            7: "15686677735a7506101c",
            8: game_version, 9: 3, 10: 1,
            11: "03626253513637754174",
        },
        19: 324,
        21: bytes.fromhex("374f521955"),
        24: {1: 21},
    }
    if proto_team_size > 1:
        sub2[27] = "a_6534489873065906362"
    return _gp_build([(0, 5), (1, 1), (2, sub2)], region_code, key, iv)


# ============ 2. LEAVE TEAM (CMD 7) ============
def leave_team(uid, region_code, key, iv):
    return _gp_build([(0, 5), (1, 7), (2, {1: int(uid)})], region_code, key, iv)


# ============ 3. JOIN CODE (CMD 4) ============
def join_code(team_code, region_code, key, iv):
    fields = [(0, 5), (1, 4), (2, {
        11: {1: b'IDC1', 2: 3000, 3: b'VN'},
        13: b'vn', 16: b'O\x19',
        20: [{1: 3, 2: 391}, {1: 4, 2: 385}, {1: 5, 2: 192},
             {1: 29, 2: 204}, {1: 22, 2: 120}, {1: 14, 2: 175}, {1: 21}],
        23: b'a_2045012438551707759',
        24: b'https://dl-sg-production.freefiremobile.com/D5A73B5E05EC88BB7181_7104104913_107_1767710870_0',
        27: {1: 55, 2: 8},
        4: b"\x01\x07\t\n\x0b\x12\x19\x1a ')",
        5: str(team_code).encode(),
        6: 6, 8: 1,
        9: {
            1: b'080380301ABA279402010000000000000005000100040000F1FA740A0F0000004676251400000000000000000000000000000000000000ff00000000cacfa16d',
            10: 2,
            11: b'\x03bbSQ67nzZ/J0AdV2KyoVlYRIvdLC0ggc1SIsxSJO8MXrgUkvxAkmhEqpVCVKdh4a7LxqKFYvy+y5zjI+1dGPHOuVubJoKDp0pr/Yq6MttgXgfYtvMrbAt6vRoRLEEpda3wLewWn00dRBgYY9M3nZVWmaVaxLsI8erqaJNKudc8L0KcKhQy5gzD9xT+PhpDNC4aENmAzy0dZwlIpf4CAwzXcRGS2UsDipni8CqiTrFh/JkipNOLxUAr4lTLoDMBBLocusy/+u8+MgrgO4PETOy0fVThcf4XbHbbKbob06z0LKcYCtK3kPYs+wUJzZHvDmMTNQG56raMMKlvbfBfyw/Ch3MkoOsBK/VwFbSseEQFyqBNBfVov55UCK6ggZQNcYX5TeVXWUYe8QYadeLelsF1IXmWxj/sqlUdz6BT6qfhcDrWXT1grfKjmntvHTdCbJzut57sbsuTk5yBvPYN2eahhpeWJoG3JUGEqKeLBCyLcIO1+KBm1PqV9iRrY5yYWCXFlVnowSZySFSZPkh220l/L2tYlPFGxWWcunSBGkpJ7HwiTxekah+4J7OskqQL7bUHMbC8aQCzHBwHe3aoZLCA==',
            2: 33,
            3: b'uZ_T\x10\x08\x08O\x06\x03\x0b\nU\x02\x02\x01\x0e\x0e\x03\x06Q\x02\n\x04P\x06\x02\\Y\x03PQWU\x05QR\x02\rZ\x10\x02\x02Ov^CEJ\x11\x08\x1f\x02\x1a\x10\x02\x01O\x1aAir_TCwr]UHfzH\x18Z\\K\x06QDBiUib\x0e\x10\x02O\x18\x06^t\x16j\x02Az\x06PdDcq\x16UVAFIDQ`\x01\x02\r\x05\x10\x02\x00OPK\n\x02\x01sK\x0bP\x06x\x07U\x05\x1aKM\x0eqG\x03\x03`zyWb\x04\x1b\x0bO\\Kk\n|G\n{\nfbXU[\x04vXCPRIB{IfX@\x0c\x10\x0bDeaDu\x06{q_\x05\x12ZAZ_\\`YpR_\x16sCt[w\x0b\x0e\x10\x08O\x0cMJRKZg\x04\x7f\tqky\x18^UPJdYGE`lf^~\x0e\x10\x02\x0bMR\x0eyu|BPKByT\x06jB{\\]ZX_R\x04\x7f\x16i]D\x0e\x10\x00Op\x1e\x7f_rKx|{G_riw~YJvbg[rrgv|_\x0e\x10\x07O\x02\x7f\x1cgXir|JDg{e[W\x7ftN\x18@\x01q\x03j\x1ch\\\x04\x1b\x01\x03O\x07a\x03\x0bpfn\x7ff@rwgp}\x7f@\tyEazI\x07YZx\x0e\x1a\rOQ\x02|APtu@Pig\x04t^fJ_\x01gOupFf\x03\x06v\x0e',
            4: b'}\\]V', 6: 11,
            7: b'\x17\rydRQ\x00w\x17\x17',
            8: b'1.130.20', 9: 3,
        },
    })]
    return _gp_build(fields, region_code, key, iv)


# ============ 4. AUTH CHAT (CMD 3) ============
def auth_chat(auth_type, uid, code, key, iv):
    fields = {1: auth_type, 2: {1: int(uid), 3: "en", 4: str(code)}}
    return _gene_pk(_proto(fields).hex(), '1215', key, iv)


# ============ 4b. QUIT CHAT (CMD 4) ============
def quit_chat(owner, key, iv):
    fields = {1: 4, 2: {1: int(owner), 3: "en"}}
    return _gene_pk(_proto(fields).hex(), '1215', key, iv)


# ============ 5. CHAT SQUAD (text thuần, không mắt) ============
def send_chat_squad(msg, uid, msg_type=0, key=None, iv=None):
    """Gửi chat squad — text thuần, không chèn icon"""
    fields = {
        1: int(uid), 2: int(uid), 3: int(msg_type), 4: str(msg),
        5: 1710537479, 7: 2,
        9: {1: "Josh1X5c9y", 2: 902000074, 4: 330, 7: 2},
        10: "ar", 11: 1, 12: 1,
        13: {
            1: "https://lh3.googleusercontent.com/a/ACg8ocJSmS1omtLmOqTlRqfY7Kpt2xPqBZYYULNE7uoWSHyG=s96-c",
            2: 1, 3: 1,
        },
        14: {},
    }
    body = _proto(fields)
    protobuf = "080112" + _vr(len(body)).hex() + body.hex()
    return _gene_pk(protobuf, '1201', key, iv)


# ============ 6. GHOST NAME (CMD 61) ============
def ghost_name(owner_uid, ghost_text, secret_code, key, iv):
    fields = {
        1: 61,
        2: {
            1: int(owner_uid),
            2: {
                1: int(owner_uid),
                2: int(time.time()),
                3: str(ghost_text),
                5: 12, 6: 9999999, 7: 1,
                8: {2: 1, 3: 1}, 9: 3,
            },
            3: str(secret_code or ''),
        },
    }
    return _gene_pk(_proto(fields).hex(), '0501', key, iv)


# ============ 7. AUTH SOCKET ============
def build_online_auth(acc_id, token, kts, key, iv):
    enc = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(token.encode("utf-8"), 16))
    return (bytes.fromhex("830c")
            + int(acc_id).to_bytes(8, "big")
            + int(kts).to_bytes(4, "big")
            + len(enc).to_bytes(8, "big") + enc)


def build_chat_auth(acc_id, token, kts, key, iv):
    enc = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(token.encode("utf-8"), 16))
    return (bytes.fromhex("6d19")
            + int(acc_id).to_bytes(8, "big")
            + int(kts).to_bytes(4, "big")
            + len(enc).to_bytes(4, "big") + enc)


# ============ 8. PARSE 0500 ============
def parse_0500(pkt):
    if not pkt or len(pkt) < 6 or pkt[:2].hex() != "0500":
        return {}
    res = {"all_uids": set()}
    try:
        for f in Parser().parse(pkt[5:].hex()):
            if f.field != 5 or f.wire_type != "length_delimited":
                continue
            for sf in f.data.results:
                if sf.field == 1 and sf.wire_type == "varint":
                    res["owner_uid"] = int(sf.data)
                    res["all_uids"].add(int(sf.data))
                elif sf.field == 11:  # team_code 7 số
                    sc = sf.data
                    if isinstance(sc, bytes): sc = sc.decode("utf-8", errors="ignore")
                    if sc: res["squad_code"] = str(sc)
                elif sf.field == 14:  # chat_channel string {ts}_{rand}
                    sc = sf.data
                    if isinstance(sc, bytes): sc = sc.decode("utf-8", errors="ignore")
                    if sc: res["chat_channel"] = str(sc)
                elif sf.field == 17 and sf.wire_type == "varint":  # chat int
                    res["chat_code_int"] = int(sf.data)
                elif sf.field == 31:  # secret_code cho ghost
                    sc = sf.data
                    if isinstance(sc, bytes): sc = sc.decode("utf-8", errors="ignore")
                    if sc: res["secret_code"] = str(sc)
                elif sf.field == 6 and sf.wire_type == "length_delimited":
                    for mf in sf.data.results:
                        if mf.field == 1 and mf.wire_type == "varint":
                            v = int(mf.data)
                            if v > 10000: res["all_uids"].add(v)
    except Exception:
        pass
    return res


# ============ 9. UTILS ============
def get_region_code(logindata, region):
    up = (region or "VN").upper()
    raw = logindata.get("19", logindata.get(19))
    if isinstance(raw, dict) and "data" in raw and len(raw) <= 2:
        raw = raw["data"]
    if isinstance(raw, dict) and ("1" in raw or 1 in raw):
        raw = [raw]
    rmap = {}
    if isinstance(raw, list):
        for it in raw:
            if not isinstance(it, dict): continue
            k1, k2 = it.get("1", it.get(1)), it.get("2", it.get(2))
            if isinstance(k1, dict) and "data" in k1: k1 = k1["data"]
            if isinstance(k2, dict) and "data" in k2: k2 = k2["data"]
            if k1 is None or k2 is None: continue
            try: rmap[str(k2).upper()] = "%02X" % int(k1)
            except Exception: pass
    return rmap.get(up) or REGION_CODE_MAP.get(up, "15")


def get_idc(region):
    return REGION_IDC_MAP.get((region or "VN").upper(), "IDC3")