import requests, json, base64, time, struct, datetime, re, hmac, hashlib, random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from protobuf_decoder.protobuf_decoder import Parser
from typing import Dict, Any, Optional, Tuple, Union, TypedDict, List
from dataclasses import dataclass
from enum import IntEnum

class ProtoBuf:
    def __init__(self, data):
        self.data = data

    def varint(self, buffer: bytes, pos: int = 0) -> Tuple[int, int]:
        result, shift = 0, 0
        while shift < 64 and pos < len(buffer):
            byte = buffer[pos]
            pos += 1
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                return result, pos
            shift += 7
        return result, pos

    def repeated(self, data: bytes) -> List[int]:
        pos, out = 0, []
        while pos < len(data):
            val, pos = self.varint(data, pos)
            out.append(val)
        return out

    def string(self, buffer: bytes, pos: int) -> Tuple[str, int]:
        length, pos = self.varint(buffer, pos)
        newpos = min(pos + length, len(buffer))
        value = buffer[pos:newpos]
        try: value = value.decode("utf-8")
        except: pass
        return value, newpos

    def fixed32(self, buffer: bytes, pos: int) -> Tuple[int, int]:
        return (struct.unpack("<I", buffer[pos:pos + 4])[0], pos + 4) if pos + 4 <= len(buffer) else (0, pos)

    def fixed64(self, buffer: bytes, pos: int) -> Tuple[int, int]:
        return (struct.unpack("<Q", buffer[pos:pos + 8])[0], pos + 8) if pos + 8 <= len(buffer) else (0, pos)

    def parse_field(self, buffer: bytes, pos: int) -> Tuple[int, Any, int]:
        if pos >= len(buffer): return 0, None, pos
        key, pos = self.varint(buffer, pos)
        field_number, wire_type = key >> 3, key & 0x7
        try:
            if wire_type == 0: value, pos = self.varint(buffer, pos)
            elif wire_type == 1: value, pos = self.fixed64(buffer, pos)
            elif wire_type == 2: value, pos = self.string(buffer, pos)
            elif wire_type == 5: value, pos = self.fixed32(buffer, pos)
            else: return field_number, None, pos
        except (struct.error, IndexError):
            return field_number, None, pos
        return field_number, value, pos

    def protobuf(self, buffer: Optional[bytes] = None, offset: int = 0) -> Dict[str, Any]:
        if buffer is None:
            buffer = self.data
        result = {}
        while offset < len(buffer):
            field_number, value, offset = self.parse_field(buffer, offset)
            if isinstance(value, bytes) and value:
                try:
                    nested = self.protobuf(value)
                    if nested: value = nested
                except: pass
            key = str(field_number)
            result.setdefault(key, []).append(value)
        return {k: v[0] if len(v) == 1 else v for k, v in result.items()}

    def fieldsRaw(self, buf: bytes, pos: int) -> Tuple[int, int, bytes, int, int]:
        start = pos
        key, pos = self.varint(buf, pos)
        num, wt = key >> 3, key & 0x7
        if wt == 0: _, end = self.varint(buf, pos)
        elif wt == 1: end = pos + 8
        elif wt == 2:
            length, lp = self.varint(buf, pos)
            end = lp + length
        elif wt == 5: end = pos + 4
        else: return num, wt, b'', pos, pos
        return num, wt, buf[start:end], pos, end

    def EXTRACT_FIELDS(self, fields: List[int], mode: str = "repeated") -> List:
        cur = self.data
        for depth, target in enumerate(fields):
            pos = 0; found = False
            if depth == len(fields) - 1:
                results = []
                while pos < len(cur):
                    num, wt, raw, val_start, val_end = self.fieldsRaw(cur, pos)
                    if num == target:
                        if mode == "repeated":
                            if wt == 0:
                                val, _ = self.varint(cur, val_start)
                                results.append(val)
                            elif wt == 2:
                                _, lp = self.varint(cur, val_start)
                                packed = cur[lp:val_end]
                                results += self.repeated(packed)
                        elif mode == "bytes":
                            if wt == 2:
                                _, lp = self.varint(cur, val_start)
                                results.append(cur[lp:val_end])
                            else:
                                results.append(cur[val_start:val_end])
                    pos = val_end
                if len(results) == 0: return []
                if len(results) == 1: return results[0]
                return results
            else:
                while pos < len(cur):
                    num, wt, raw, val_start, val_end = self.fieldsRaw(cur, pos)
                    if num == target and wt == 2:
                        _, lp = self.varint(cur, val_start)
                        cur = cur[lp:val_end]
                        found = True; break
                    pos = val_end
                if not found: return []
        return []


def Encrypt(value):
    value = int(value)
    result = []
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value)
    return bytes(result)

def Decrypt(value):
    result, shift = 0, 0
    for byte in bytes.fromhex(value):
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result

def parse_results(parsed_results):
    result_dict = {}
    for result in parsed_results:
        if result.field not in result_dict:
            result_dict[result.field] = []
        field_data = {}
        if result.wire_type in ["varint", "string", "bytes"]:
            field_data = result.data
        elif result.wire_type == "length_delimited":
            field_data = parse_results(result.data.results)
        result_dict[result.field].append(field_data)
    return {
        key: value[0] if len(value) == 1
        else value for key, value in result_dict.items()
    }

protobuf_dec = lambda data: json.dumps(parse_results(
    Parser().parse(data)
), ensure_ascii=False)

def AES_CBC128(data, key, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, 0x10))

def _scalar(v):
    while isinstance(v, (list, tuple)) and v:
        v = v[0]
    return v

def _as_bytes(v):
    v = _scalar(v)
    if v is None: return None
    if isinstance(v, bytes): return v
    if isinstance(v, bytearray): return bytes(v)
    if isinstance(v, str): return v.encode("latin-1")
    if isinstance(v, (list, tuple)):
        try: return bytes(v)
        except Exception: return None
    return None

def create_varint_field(field_number, value):
    field_header = (field_number << 3) | 0
    return Encrypt(field_header) + Encrypt(value)

def create_length_delimited_field(field_number, value):
    field_header = (field_number << 3) | 2
    encoded_value = value.encode() if isinstance(value, str) else value
    return Encrypt(field_header) + Encrypt(len(encoded_value)) + encoded_value

def pb_encode(fields):
    packet = bytearray()
    for field, value in fields.items():
        field = int(field)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    packet.extend(create_length_delimited_field(field, pb_encode(item)))
        elif isinstance(value, dict):
            nested_packet = pb_encode(value)
            packet.extend(create_length_delimited_field(field, nested_packet))
        elif isinstance(value, int):
            packet.extend(create_varint_field(field, value))
        elif isinstance(value, str) or isinstance(value, bytes):
            packet.extend(create_length_delimited_field(field, value))
    return bytes(packet)


class gayerr(Exception): pass

@dataclass
class account_data:
    access_token = ""
    open_id = ""
    platform = 0x4
    login_platform = 0x4
    main_active_platform = 0x4
    chat_ip = chat_port = online_ip = online_port = ""
    create_time = None
    expiry_time = None
    guild_id = None
    guild_code = None
    login_token = None
    account_id = None
    server = None
    base_url = None
    login_time = None
    key = None
    iv = None


class gringay:
    @staticmethod
    def tokendecode(token):
        try:
            parts = token.split(".")
            if len(parts) != 3: raise gayerr("Invalid token format")
            payload = parts[1]
            payload += "=" * (0x4 - len(payload) % 0x4)
            return json.loads(base64.urlsafe_b64decode(payload).decode('utf-8'))
        except (ValueError, json.JSONDecodeError) as e: pass

    @staticmethod
    def format_timestamp(timestamp):
        if timestamp is None: return ""
        return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp))

def storeApps(package):
    I = requests.get(f"https://play.google.com/store/apps/%s" % package)
    I = re.search(r'\[\[\["(\d+\.\d+\.\d+)"\]\]', I.text)
    if I: return I.group(1)
    return None

def bdversion(ver: str = None):
    try:
        if not ver:
            try:
                from google_play_scraper import app as play_store_app
                result = play_store_app('com.dts.freefireth', lang="fr", country='fr')
                ver = result['version']
            except Exception:
                ver = "1.132.9"
        r = requests.get(f'https://version.ggwhitehawk.com/live/ver.php?version={ver}&lang=en&device=android&channel=android&appsttore=googleplay&region=ME&whitelist_version=1.3.0&whitelist_sp_version=1.0.0&device_name=google%20G011A&device_CPU=ARMv7%20VFPv3%20NEON%20VMH&device_GPU=Adreno%20(TM)%20640&device_mem=1993', verify=False, timeout=10).json()
        data = {
            "server_url": r['server_url'],
            "latest_release_version": r.get('latest_release_version') or "OB55",
            "remote_version": ver
        }
        return data
    except Exception as e:
        return {
            "server_url": "https://loginbp.ppmainecoonghj.com/",
            "latest_release_version": "OB55",
            "remote_version": "1.132.9"
        }

# Details: https://api.freefireservice.dnc.su/ff.status
# Telegram: @gringo_modz

class APIClient:
    def __init__(self):
        self._data = account_data()
        self.logindata = {}
        detail_vers = bdversion()
        self.is_emulator = False
        self.language = "en"
        self.base_url = detail_vers["server_url"]
        self.client_version = "1.132.9"
        self.release_version = detail_vers.get("latest_release_version") or "OB55"
        self.key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
        self.iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
        from urllib.parse import urlparse
        host_name = "loginbp.ppmainecoonghj.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
            "X-GA": "v1 1", "X-GA-SV": str(int(time.time())),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "deflate, gzip", "Accept": "*/*",
            "X-Unity-Version": "2018.4.12f1",
            "Host": host_name, "ReleaseVersion": self.release_version
        })

    def auth_guest_token(self, uid, password):
        try:
            password_hash = hashlib.sha256(str(password).encode()).hexdigest()
            data = requests.post(
                "https://100067.connect.garena.com/api/v2/oauth/guest/token:grant",
                headers={
                    "Host": "100067.connect.garena.com",
                    "User-Agent": "GarenaMSDK/4.0.44(Pixel ;Android 10;en;US;app 1.132.1 2019121229;)",
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json",
                },
                json={
                    "client_id": 100067,
                    "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
                    "client_type": 2,
                    "device_id": "",
                    "password": password_hash,
                    "response_type": "token",
                    "uid": int(uid)
                },
                verify=False, timeout=30
            ).json()
            if data.get("code") == 0 and "data" in data:
                d = data["data"]
                self._data.access_token = d.get("access_token")
                self._data.open_id = d.get("open_id")
                self._data.platform = int(d.get("platform", 4))
                self._data.login_platform = self._data.platform
                self._data.main_active_platform = self._data.platform
                self._data.create_time = d.get("create_time")
                self._data.expiry_time = d.get("expiry_time")
                return
            print("[auth_guest_token] fail:", data)
        except Exception as e:
            print("[auth_guest_token]", e)

    def auth_token_inspect(self, access_token):
        try:
            data = requests.get(
                "https://auth.garena.com/oauth/token/inspect",
                params={"token": access_token}
            ).json()
            if "open_id" not in data:
                print("[auth_token_inspect] token không hợp lệ:", data)
                return
            self._data.access_token = access_token
            self._data.open_id = data["open_id"]
            self._data.platform = int(data.get("platform", 4))
            self._data.login_platform = self._data.platform
            self._data.main_active_platform = self._data.platform
            self._data.create_time = data.get("create_time")
            self._data.expiry_time = data.get("expiry_time")
            print(f"[auth_token_inspect] platform={self._data.platform}")
        except Exception as e:
            print("[auth_token_inspect]", e)

    def MajorLogin(self):
        try:
            fields = {}
            fields[3] = str(datetime.datetime.now())[:-7]
            fields[4] = "free fire"
            fields[5] = 1
            fields[7] = "1.132.9"
            fields[8] = "Android OS 10 / API-29 (NHG47O/eng.build.20231013.013027)"
            fields[9] = "Handheld"
            fields[10] = "TelKila"
            fields[11] = "WIFI"
            fields[12] = 1708
            fields[13] = 750
            fields[14] = "440"
            fields[15] = "ARM64 FP ASIMD AES | 2850 | 8"
            fields[16] = 3968
            fields[17] = "Mali-G610 MC6"
            fields[18] = "OpenGL ES 3.2 v1.r32p1-01eac0.54329dee8f160f288c574caaf67bbe3f"
            fields[19] = "Google|0ecc7b3b-6c41-462e-9050-26d835e84c53"
            fields[20] = "116.97.105.60"
            fields[21] = "en"
            fields[22] = str(self._data.open_id)
            fields[23] = "4"
            fields[24] = "Handheld"
            fields[25] = "Google Pixel"
            fields[26] = "SG"
            fields[29] = str(self._data.access_token)
            fields[30] = 1
            fields[41] = "TelKila"
            fields[42] = "WIFI"
            fields[57] = "7428b253defc164018c604a1ebbfebdf"
            fields[60] = 109029
            fields[61] = 37616
            fields[62] = 2048
            fields[63] = 804
            fields[64] = 37616
            fields[65] = 109029
            fields[66] = 37616
            fields[67] = 109029
            fields[70] = 2
            fields[73] = 3
            fields[74] = "/data/app/com.dts.freefireth-oiglMJkEoNJlsRci10280Q==/lib/arm64"
            fields[76] = 1
            fields[77] = "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/com.dts.freefireth-oiglMJkEoNJlsRci10280Q==/base.apk"
            fields[78] = 3
            fields[79] = 2
            fields[81] = "64"
            fields[83] = "2019121229"
            fields[85] = 3
            fields[86] = "OpenGLES2"
            fields[87] = 511
            fields[88] = 4
            fields[90] = "Hà Nội"
            fields[91] = "01"
            fields[92] = 4231
            fields[93] = "android"
            fields[94] = "KqsHT8at0g7Na/G7iOeF1IpesHMf+HoePFMFFE8Tq/dSk4fIbJ1j8TdV8OAyWIVnSmD2rM6vfFMtCD8Ig7iROgDJmIMrdtcB6orwuNRpMr4MVu3D7FoTcuQdq/8EyOkRQiUrbg=="
            fields[95] = 111207
            fields[96] = '{"cur_rate":null,"support_etc2":false}'
            fields[97] = 1
            fields[98] = 1
            fields[99] = "4"
            fields[100] = "4"
            fields[102] = bytes.fromhex('4000434f07555f0637')
            fields[103] = 1
            fields[104] = 1797
            fields[105] = 1
            fields[106] = "https://dl.cdn.freefiremobile.com/live/ABHotUpdates/|https://dl-core.cdn.freefiremobile.com/live/ABHotUpdates/|4a0070ac356973792f002e0b25b96c3b"
            fields[107] = "c8e41b7a93f02d56e1a94c7b8203f5d1"

            payload = AES_CBC128(pb_encode(fields), self.key, self.iv)
            url = "https://loginbp.ppmainecoonghj.com/MajorLogin"
            headers = {
                "X-Unity-Version": "2018.4.12f1",
                "ReleaseVersion": "OB55",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Bearer",
                "Accept": "*/*",
                "Expect": "100-continue",
                "X-GA": "v1 1",
                "X-GA-SV": str(int(time.time())),
                "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                "Host": "loginbp.ppmainecoonghj.com",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "deflate, gzip",
            }
            r = requests.post(url, headers=headers, data=payload, verify=False, timeout=30)
            print(f"[MajorLogin] HTTP {r.status_code}")
            if r.status_code != 200:
                print(f"[MajorLogin] ❌ {r.text[:200]}")
                return

            raw = r.content
            print(f"[MajorLogin] RESPONSE LEN: {len(raw)}")

            # ⚠️ THỬ DECRYPT RESPONSE BẰNG KEY/IV HARDCODE
            decrypted = None
            try:
                decrypted = unpad(AES.new(self.key, AES.MODE_CBC, self.iv).decrypt(raw), 16)
                print(f"[MajorLogin] ✅ Response decrypted OK (len={len(decrypted)})")
            except Exception as e:
                print(f"[MajorLogin] ⚠️ Response NOT encrypted (hoặc key/iv khác): {e}")
                decrypted = raw

            # ⚠️ EXTRACT KEY/IV TỪ DECRYPTED (hoặc raw)
            pb = ProtoBuf(decrypted)
            key_extracted = _as_bytes(pb.EXTRACT_FIELDS([22], mode="bytes"))
            iv_extracted = _as_bytes(pb.EXTRACT_FIELDS([23], mode="bytes"))

            # ⚠️ FALLBACK: thử offset 64
            if (not key_extracted or not iv_extracted) and len(decrypted) > 64:
                pb2 = ProtoBuf(decrypted[64:])
                key_extracted = _as_bytes(pb2.EXTRACT_FIELDS([22], mode="bytes"))
                iv_extracted = _as_bytes(pb2.EXTRACT_FIELDS([23], mode="bytes"))

            if key_extracted and iv_extracted:
                self._data.key = key_extracted
                self._data.iv = iv_extracted
                print(f"[MajorLogin] ✅ key={key_extracted.hex()}")
                print(f"[MajorLogin] ✅ iv ={iv_extracted.hex()}")
            else:
                self._data.key = self.key
                self._data.iv = self.iv
                print(f"[MajorLogin] ⚠️ key/iv hardcode (extract fail)")
                print(f"[MajorLogin] key_extracted={key_extracted.hex() if key_extracted else None}")
                print(f"[MajorLogin] iv_extracted ={iv_extracted.hex() if iv_extracted else None}")

            # ⚠️ FIND JWT
            jwt_bytes = None
            o = 0
            while o < len(decrypted) - 1:
                idx = decrypted.find(b"\x42", o)
                if idx < 0:
                    idx = decrypted.find(b"eyJ", o)
                    if idx >= 0:
                        jwt_bytes = decrypted[idx:idx + 500]
                        break
                    break
                length, after = 0, idx + 1
                shift = 0
                while after < len(decrypted):
                    b = decrypted[after]; after += 1
                    length |= (b & 0x7F) << shift
                    if not (b & 0x80): break
                    shift += 7
                end = after + length
                if end <= len(decrypted) and decrypted[after:after + 3] == b"eyJ":
                    jwt_bytes = decrypted[after:end]
                    break
                o = idx + 1

            if not jwt_bytes:
                print(f"[MajorLogin] ❌ Không tìm thấy JWT")
                return

            login_token = jwt_bytes.decode('utf-8', 'replace')
            account_id = ""
            try:
                parts = login_token.split('.')
                if len(parts) >= 2:
                    p = parts[1] + '=' * ((4 - len(parts[1]) % 4) % 4)
                    jd = json.loads(base64.urlsafe_b64decode(p))
                    account_id = str(jd.get('account_id', ''))
            except: pass

            self._data.login_token = login_token
            self._data.account_id = account_id
            self._data.server = "VN"
            self._data.base_url = "https://clientbp.ppmainecoonghj.com"
            self._data.login_time = int(time.time())

            print(f"[MajorLogin] ✅ OK account_id={account_id}")
        except Exception as e:
            print("[MajorLogin]", e)

    def GetLoginData(self):
        try:
            if not self._data.login_token:
                print("[GetLoginData] ❌ login_token rỗng")
                return

            fields = {}
            fields[3] = str(datetime.datetime.now())[:-7]
            fields[4] = "free fire"
            fields[5] = 1
            fields[7] = "1.132.9"
            fields[8] = "Android OS 10 / API-29 (NHG47O/eng.build.20231013.013027)"
            fields[9] = "Handheld"
            fields[10] = "TelKila"
            fields[11] = "WIFI"
            fields[12] = 1708
            fields[13] = 750
            fields[14] = "440"
            fields[15] = "ARM64 FP ASIMD AES | 2850 | 8"
            fields[16] = 3968
            fields[17] = "Mali-G610 MC6"
            fields[18] = "OpenGL ES 3.2 v1.r32p1-01eac0.54329dee8f160f288c574caaf67bbe3f"
            fields[19] = "Google|0ecc7b3b-6c41-462e-9050-26d835e84c53"
            fields[20] = "116.97.105.60"
            fields[21] = "en"
            fields[22] = str(self._data.open_id)
            fields[23] = "4"
            fields[24] = "Handheld"
            fields[25] = "Google Pixel"
            fields[26] = "SG"
            fields[29] = str(self._data.access_token)
            fields[30] = 1
            fields[41] = "TelKila"
            fields[42] = "WIFI"
            fields[57] = "7428b253defc164018c604a1ebbfebdf"
            fields[60] = 109029
            fields[61] = 37616
            fields[62] = 2048
            fields[63] = 804
            fields[64] = 37616
            fields[65] = 109029
            fields[66] = 37616
            fields[67] = 109029
            fields[70] = 2
            fields[73] = 3
            fields[74] = "/data/app/com.dts.freefireth-oiglMJkEoNJlsRci10280Q==/lib/arm64"
            fields[76] = 1
            fields[77] = "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/com.dts.freefireth-oiglMJkEoNJlsRci10280Q==/base.apk"
            fields[78] = 3
            fields[79] = 2
            fields[81] = "64"
            fields[83] = "2019121229"
            fields[85] = 3
            fields[86] = "OpenGLES2"
            fields[87] = 511
            fields[88] = 4
            fields[90] = "Hà Nội"
            fields[91] = "01"
            fields[92] = 4231
            fields[93] = "android"
            fields[94] = "KqsHT8at0g7Na/G7iOeF1IpesHMf+HoePFMFFE8Tq/dSk4fIbJ1j8TdV8OAyWIVnSmD2rM6vfFMtCD8Ig7iROgDJmIMrdtcB6orwuNRpMr4MVu3D7FoTcuQdq/8EyOkRQiUrbg=="
            fields[95] = 111207
            fields[96] = '{"cur_rate":null,"support_etc2":false}'
            fields[97] = 1
            fields[98] = 1
            fields[99] = "4"
            fields[100] = "4"
            fields[102] = bytes.fromhex('4000434f07555f0637')
            fields[103] = 1
            fields[104] = 1797
            fields[105] = 1
            fields[106] = "https://dl.cdn.freefiremobile.com/live/ABHotUpdates/|https://dl-core.cdn.freefiremobile.com/live/ABHotUpdates/|4a0070ac356973792f002e0b25b96c3b"
            fields[107] = "c8e41b7a93f02d56e1a94c7b8203f5d1"

            payload = AES_CBC128(pb_encode(fields), self.key, self.iv)
            url = f"{self._data.base_url}/GetLoginData"
            headers = {
                "X-Unity-Version": "2018.4.12f1",
                "ReleaseVersion": "OB55",
                "Content-Type": "application/x-www-form-urlencoded",
                "X-GA": "v1 1",
                "X-GA-SV": str(int(time.time())),
                "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
                "Host": "clientbp.ppmainecoonghj.com",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
                "Authorization": f"Bearer {self._data.login_token}",
            }
            r = requests.post(url, headers=headers, data=payload, verify=False, timeout=30)
            print(f"[GetLoginData] HTTP {r.status_code}")
            if r.status_code != 200:
                print(f"[GetLoginData] ❌ {r.text[:200]}")
                return

            # ⚠️ THỬ DECRYPT RESPONSE
            raw = r.content
            try:
                dec = unpad(AES.new(self.key, AES.MODE_CBC, self.iv).decrypt(raw), 16)
                data = json.loads(protobuf_dec(dec.hex()))
            except:
                data = json.loads(protobuf_dec(raw.hex()))

            self.logindata = data
            self._data.guild_id = data.get("20")
            self._data.guild_code = data.get("55")
            sv = _scalar(data.get("14"))
            chat = _scalar(data.get("32"))
            sv = str(sv) if sv else ""
            chat = str(chat) if chat else ""
            if len(chat) > 6:
                self._data.chat_port, self._data.chat_ip = chat[-5:], chat[:-6]
            if len(sv) > 6:
                self._data.online_port, self._data.online_ip = sv[-5:], sv[:-6]
            print(f"[GetLoginData] ✅ OK online={self._data.online_ip}:{self._data.online_port}")
        except Exception as e:
            print("[GetLoginData]", e)

    def _auth_packet(self, fox=True):
        regions = self.logindata.get("19") or []
        if isinstance(regions, dict):
            regions = [regions]
        esid = lambda rec: (
            lambda s: s[str(rec).upper()] if str(rec).upper() in s else None)(
            {str(x["2"]).upper(): x["1"] for x in regions if isinstance(x, dict) and "1" in x and "2" in x}
        )
        tok = self._data.login_token
        if isinstance(tok, bytes):
            tok = tok.decode("utf-8", "replace")
        encrypts = AES_CBC128(str(tok).encode(), self._data.key, self._data.iv)
        region = int(_scalar(esid(self._data.server)) or 1)
        aid = int(_scalar(self._data.account_id) or 0)
        kts = int(_scalar(self._data.login_time) or 0)
        cmd = 1 if fox else (101 + (aid % 50))
        hdr = (
            bytes([cmd & 0xFF, region & 0xFF])
            + struct.pack(">Q", aid)
            + struct.pack(">I", kts & 0xFFFFFFFF)
        )
        if fox:
            return hdr + struct.pack(">I", len(encrypts)) + encrypts
        return hdr + struct.pack(">Q", len(encrypts)) + encrypts

    def TAO_PACKET_XT(self) -> str:
        try:
            return self._auth_packet(True)
        except Exception as e: print(e)

    def TAO_PACKET_LOBBY(self):
        try:
            return self._auth_packet(False)
        except Exception as e: print(e)

    def auth(self, access_token, is_emulator=False):
        try:
            self.is_emulator = is_emulator
            print(f"[auth] Bắt đầu — token={'guest' if ':' in access_token else 'access_token'}")

            if ":" in access_token:
                uid, password = access_token.split(":")
                self.auth_guest_token(int(uid), password)
            else:
                self.auth_token_inspect(access_token)

            if not self._data.access_token:
                print("[auth] ❌ Không có access_token")
                return "account not found"
            print(f"[auth] ✅ open_id={self._data.open_id}")

            self.MajorLogin()
            if not self._data.login_token:
                print("[auth] ❌ MajorLogin thất bại")
                return "account not found"

            self.GetLoginData()
            if not self.logindata:
                print("[auth] ❌ GetLoginData thất bại")
                return "account not found"

            pkt = self.TAO_PACKET_XT()
            if not pkt:
                print("[auth] ❌ TAO_PACKET_XT rỗng")
                return "account not found"

            return self._build_api_response(pkt)
        except Exception as e:
            print("[auth]", e)

    def _build_api_response(self, authpacket):
        if not self._data.login_token or not authpacket: return "account not found"
        if not self._data.key or not self._data.iv: return "account not found"
        tok = self._data.login_token
        if isinstance(tok, bytes):
            tok = tok.decode("utf-8", "replace")
        data = gringay.tokendecode(tok)
        if self._data.guild_id:
            guild = {}
            guild["id"] = self._data.guild_id
            guild["secret_code"] = self._data.guild_code
        else:
            guild = False

        saddress = {}
        saddress["chatip"] = self._data.chat_ip
        saddress["chatport"] = self._data.chat_port
        saddress["onlineip"] = self._data.online_ip
        saddress["onlineport"] = self._data.online_port
        response = {}
        response["CreateTime"] = gringay.format_timestamp(self._data.create_time)
        response["ExpiryTime"] = gringay.format_timestamp(self._data.expiry_time)
        response["UserAuthPacket"] = list(authpacket)
        lobby_pkt = self.TAO_PACKET_LOBBY()
        response["UserAuthPacketLobby"] = list(lobby_pkt) if lobby_pkt else list(authpacket)
        response["UserAuthToken"] = tok
        response["UserNickName"] = data.get("nickname") if data else None
        response["UserAccountUID"] = data.get("account_id") if data else None
        response["LockRegion"] = data.get("lock_region") if data else None
        response["ClientVersion"] = data.get("client_version") if data else None
        response["IsEmulator"] = data.get("is_emulator") if data else None
        response["GuildData"] = guild
        response["BaseUrl"] = self._data.base_url or ""
        response["key"] = list(self._data.key)
        response["iv"] = list(self._data.iv)
        response["logindata"] = self.logindata
        response["GameServerAddress"] = saddress
        return response

class FreeFireAPI:
    def __init__(self):
        self.client = APIClient()

    def get(self, target: str, is_emulator: bool = False):
        return self.client.auth(target, is_emulator)