import requests, json, base64, time, struct, datetime, re, hmac, hashlib, random, uuid
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from protobuf_decoder.protobuf_decoder import Parser
from typing import Dict, Any, Optional, Tuple, Union, TypedDict, List
from dataclasses import dataclass
from enum import IntEnum

# --- DANH SÁCH CẤU HÌNH MÁY (HÀNG TRĂM MẪU) ---
MODELS = [
    "samsung SM-S908E", "samsung SM-S918B", "samsung SM-S928B", "samsung SM-A546E", "samsung SM-A346E",
    "samsung SM-M346B", "samsung SM-G998B", "samsung SM-G991B", "samsung SM-N986B", "samsung SM-A145F",
    "Xiaomi 2201122G", "Xiaomi 2210132G", "Xiaomi 23049PCD8G", "Xiaomi 23122PCD1G", "Xiaomi M2101K6G",
    "Xiaomi M2103K19G", "Xiaomi 2107113SG", "Xiaomi 2201117TG", "Xiaomi 23021RAAEG", "Xiaomi 23106RN0DA",
    "vivo V2352A", "vivo V2311", "vivo V2227A", "vivo V2230", "vivo V2109", "vivo V2040", "vivo V2027",
    "vivo V1932", "vivo V2130", "vivo V2148", "OPPO CPH2451", "OPPO CPH2487", "OPPO CPH2525", "OPPO CPH2551",
    "OPPO PFFM10", "OPPO PEQM00", "OPPO PDSM00", "OPPO CPH2211", "OPPO CPH2207", "Realme RMX3700",
    "Realme RMX3630", "Realme RMX3560", "Realme RMX3471", "Realme RMX3392", "Realme RMX3350",
    "Realme RMX3241", "Realme RMX3085", "Realme RMX3063", "OnePlus LE2101", "OnePlus CPH2449",
    "OnePlus IN2011", "OnePlus LE2121", "OnePlus KB2001", "OnePlus HD1910", "OnePlus GM1910",
    "Huawei ELS-NX9", "Huawei NOH-NX9", "Huawei LIO-L29", "Huawei VOG-L29", "Huawei MAR-LX1A",
    "Huawei JNY-LX1", "Huawei STK-LX1", "Nokia TA-1053", "Nokia TA-1083", "Nokia TA-1136",
    "Motorola moto g84 5G", "Motorola moto g73 5G", "Motorola edge 40", "Motorola moto g62 5G",
    "Motorola XT2241-1", "Motorola XT2201-1", "Motorola XT2175-2", "Asus ASUS_I005DA", "Asus ASUS_I003DD",
    "Asus ASUS_I002D", "Asus Z01RD", "Google Pixel 7 Pro", "Google Pixel 7", "Google Pixel 6a",
    "Google Pixel 6", "Google Pixel 5", "Google Pixel 4a", "iPhone14,3", "iPhone14,5", "iPhone14,2",
    "iPhone14,7", "iPhone13,2", "iPhone13,3", "iPhone12,1", "iPhone12,3", "iPhone11,2", "iPhone10,3"
]

GPUS = [
    "Adreno (TM) 735", "Adreno (TM) 730", "Adreno (TM) 725", "Adreno (TM) 660", "Adreno (TM) 650",
    "Adreno (TM) 640", "Adreno (TM) 630", "Adreno (TM) 620", "Adreno (TM) 619", "Adreno (TM) 618",
    "Adreno (TM) 610", "Adreno (TM) 540", "Adreno (TM) 530", "Adreno (TM) 512", "Adreno (TM) 509",
    "Mali-G710 MC10", "Mali-G710", "Mali-G78 MP14", "Mali-G77 MC9", "Mali-G76 MC4", "Mali-G72 MP18",
    "Mali-G68 MC4", "Mali-G57 MC5", "Mali-G52 MC2", "Mali-G51 MP4", "Mali-T880 MP12", "Mali-T860 MP4",
    "PowerVR GM9446", "PowerVR GE8320", "PowerVR Rogue GE8320", "Apple A16 GPU", "Apple A15 GPU",
    "Apple A14 GPU", "Apple A13 GPU", "Apple A12 GPU", "Apple A11 GPU", "Apple A10 GPU"
]

CPUS = [
    "ARM64 FP ASIMD AES | 6028 | 8", "ARM64 FP ASIMD AES | 3200 | 6", "ARM64 FP ASIMD AES | 2800 | 8",
    "ARM64 FP ASIMD AES | 2400 | 8", "ARM64 FP ASIMD AES | 2000 | 4", "ARMv7 VFPv3 NEON | 2000 | 4",
    "ARMv7 VFPv3 NEON | 1600 | 8", "ARMv7 VFPv3 NEON | 1400 | 4", "ARMv8-A | 1800 | 8", "ARMv8-A | 2200 | 6",
    "ARMv8.2-A | 2800 | 8", "ARMv8.2-A | 3000 | 8", "ARMv8.2-A | 3200 | 8", "Apple Firestorm | 3200 | 6",
    "Apple Icestorm | 1800 | 2", "Apple Vortex | 2500 | 6", "Apple Tempest | 1600 | 2", "Apple Lightning | 2600 | 6",
    "Apple Thunder | 1600 | 2", "Kryo 585 | 2840 | 8", "Kryo 680 | 2840 | 8", "Kryo 660 | 2400 | 8"
]

OS_VERS = [
    "Android OS 16 / API-36 (BP2A.250605.031.A3/compiler260821111235)",
    "Android OS 15 / API-35 (AP3A.240905.015/compiler240821111)",
    "Android OS 14 / API-34 (UP1A.231005.007/compiler230921)",
    "Android OS 13 / API-33 (TP1A.220624.014/compiler220624)",
    "Android OS 12 / API-31 (SP1A.210812.016/compiler210812)",
    "Android OS 11 / API-30 (RP1A.201005.001/compiler201005)",
    "Android OS 10 / API-29 (QP1A.190711.020/compiler190711)",
    "Android OS 9 / API-28 (PPR1.180610.011/compiler180610)",
    "Android OS 8.1 / API-27 (OPM1.171019.011/compiler171019)",
    "Android OS 8.0 / API-26 (OPR6.170623.013/compiler170623)",
    "Android OS 7.1 / API-25 (N6F26Q/compiler161104)",
    "iOS 17.5 / Darwin 23.5.0", "iOS 17.0 / Darwin 23.0.0", "iOS 16.6 / Darwin 22.6.0",
    "iOS 16.0 / Darwin 22.0.0", "iOS 15.7 / Darwin 21.7.0", "iOS 15.0 / Darwin 21.0.0",
    "iOS 14.8 / Darwin 20.8.0", "iOS 14.0 / Darwin 20.0.0", "iOS 13.7 / Darwin 19.7.0"
]

OPERATORS = [
    "VNPT Corp", "Viettel", "MobiFone", "VinaPhone", "Vietnamobile", "Gmobile", "Reddi", "Wintel",
    "AT&T", "Verizon", "T-Mobile", "Vodafone", "Orange", "O2", "EE", "Three", "Telstra", "Optus",
    "Singtel", "StarHub", "AIS", "DTAC", "TrueMove", "Smart", "Globe", "PLDT", "Maxis", "Celcom",
    "Digi", "Indosat", "Telkomsel", "XL Axiata", "Axis", "Smartfren", "Unifi", "Yes 4G"
]

NETWORKS = ["WIFI", "4G", "5G", "LTE", "3G", "HSPA+", "EDGE"]

IP_RANGES = [
    ("113.160", "113.161"), ("113.161", "113.162"), ("123.16", "123.17"),
    ("14.160", "14.161"), ("14.161", "14.162"), ("27.64", "27.65"),
    ("27.65", "27.66"), ("116.96", "116.97"), ("116.97", "116.98"),
    ("171.224", "171.225"), ("171.225", "171.226"), ("27.72", "27.73"),
    ("113.22", "113.23"), ("113.23", "113.24"), ("118.68", "118.69"),
    ("42.112", "42.113"), ("42.113", "42.114"), ("203.162", "203.163"),
    ("103.7", "103.8"), ("125.234", "125.235"), ("220.255", "220.256")
]

def _random_vn_ip():
    a_str, _ = random.choice(IP_RANGES)
    a1, a2 = a_str.split(".")
    return f"{a1}.{a2}.{random.randint(0, 255)}.{random.randint(1, 254)}"

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
    device_id = None


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
        payload = {
            "uid": str(uid),
            "password": str(password),
            "response_type": "token",
            "client_type": "2",
            "client_id": "100067",
            "client_secret": bytes([50,101,101,52,52,56,49,57,101,57,98,52,53,57,56,56,52,53,49,52,49,48,54,55,98,50,56,49,54,50,49,56,55,52,100,48,100,53,100,55,97,102,57,100,56,102,55,101,48,48,99,49,101,53,52,55,49,53,98,55,100,49,101,51]).decode()
        }
        try:
            data = requests.post(
                "https://auth.garena.com/oauth/guest/token/grant",
                data=payload,
                headers={
                    "Accept-Encoding": "gzip, deflate",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "Mozilla/5.0 (Android 9; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0",
                },
                timeout=15,
            ).json()
            if "access_token" not in data:
                print("[auth_guest_token] fail:", data)
                return
            self._data.access_token = data["access_token"]
            self._data.open_id = data["open_id"]
            self._data.platform = data.get("platform", 0x4)
            self._data.login_platform = data.get("login_platform", 0x4)
            self._data.main_active_platform = data.get("main_active_platform")
            self._data.create_time = data.get("create_time")
            self._data.expiry_time = data.get("expiry_time")
        except Exception as e:
            print("[auth_guest_token]", e)

    def auth_token_inspect(self, access_token):
        try:
            data = requests.get(
                "https://auth.garena.com/oauth/token/inspect",
                params={"token": access_token},
                timeout=36,
            ).json()
            if "open_id" not in data:
                raise gayerr("Invalid access token")
            self._data.access_token = access_token
            self._data.open_id = data["open_id"]
            self._data.platform = data.get("platform", 0x4)
            self._data.login_platform = data.get("login_platform", 0x4)
            self._data.main_active_platform = data.get("main_active_platform")
            self._data.create_time = data.get("create_time")
            self._data.expiry_time = data.get("expiry_time")
        except Exception as e:
            pass

    def MajorLogin(self):
        try:
            self._data.device_id = f"Google|{uuid.uuid4()}"
            
            dev_model = random.choice(MODELS)
            dev_gpu   = random.choice(GPUS)
            dev_cpu   = random.choice(CPUS)
            dev_os    = random.choice(OS_VERS)
            dev_op    = random.choice(OPERATORS)
            dev_net   = random.choice(NETWORKS)
            dev_ip    = _random_vn_ip()
            mem_ram   = random.choice([5951, 6000, 6100, 5500, 3940, 11284, 228423])
            device_id_hash = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

            fields = {}
            fields[3] = str(datetime.datetime.now())[:-7]
            fields[4] = b'free fire'
            fields[5] = 1
            fields[7] = "2.132.4"
            fields[8] = dev_os
            fields[9] = b'Handheld'
            fields[10] = dev_op
            fields[11] = dev_net
            fields[12] = 1280
            fields[13] = 720
            fields[14] = b'240'
            fields[15] = dev_cpu
            fields[16] = mem_ram
            fields[17] = dev_gpu
            fields[18] = f"{dev_gpu}|OpenGL ES 3.2"
            fields[19] = self._data.device_id
            fields[20] = dev_ip
            fields[21] = "en"
            fields[22] = str(self._data.open_id).encode()
            fields[23] = b'4'
            fields[24] = b'Handheld'
            fields[25] = dev_model
            fields[26] = "en"
            fields[29] = str(self._data.access_token).encode()
            fields[30] = 1
            fields[41] = dev_op
            fields[42] = dev_net
            fields[57] = device_id_hash.encode()
            fields[60] = 30000
            fields[61] = 30000
            fields[62] = 2519
            fields[63] = 243
            fields[64] = 32357
            fields[65] = 34308
            fields[66] = 32357
            fields[67] = 34308
            fields[73] = 1
            fields[74] = b'/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/lib/arm'
            fields[76] = 2
            fields[77] = b'428775ab8c8845bd341b5357ec61d15e|/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/base.apk'
            fields[78] = 2
            fields[79] = 1
            fields[81] = b'32'
            fields[83] = b'2019118525'
            fields[85] = 3
            fields[86] = b'OpenGLES3'
            fields[87] = 4095
            fields[88] = 4
            fields[92] = random.choice([19788, 20000, 21000])
            fields[93] = b'android_max'
            fields[94] = b'KqsHT2gyPt7vUCc9SCjv2ioi3WEZSEL86ErvXB38suVVK/Z4IVt78ESl/r2S15C1pqu/j6ZmgFL7HbwoFiiVconX08ooKiisQffvEAPCo/C+Lahr'
            fields[96] = b'{"cur_rate":null,"support_etc2":true}'
            fields[97] = 1
            fields[98] = 1
            fields[99] = b'4'
            fields[100] = b'4'
            fields[102] = b''
            fields[104] = 77149
            fields[105] = 1
            fields[106] = b'https://dl.cdn.freefiremobile.com/live/ABHotUpdates/|https://dl-core.cdn.freefiremobile.com/live/ABHotUpdates/|6b2078db9d22dd98f8e9386a39af8462'
            fields[107] = b'c8e41b7a93f02d56e1a94c7b8203f5d1'

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
            print(f"[MajorLogin] HTTP {r.status_code} | Máy: {dev_model} | OS: {dev_os[:12]} | RAM: {mem_ram}")
            if r.status_code != 200:
                print(f"[MajorLogin] ❌ {r.text[:200]}")
                return

            raw = r.content
            decrypted = None
            try:
                decrypted = unpad(AES.new(self.key, AES.MODE_CBC, self.iv).decrypt(raw), 16)
            except Exception as e:
                print(f"[MajorLogin] ⚠️ Response NOT encrypted: {e}")
                decrypted = raw

            pb = ProtoBuf(decrypted)
            key_extracted = _as_bytes(pb.EXTRACT_FIELDS([22], mode="bytes"))
            iv_extracted = _as_bytes(pb.EXTRACT_FIELDS([23], mode="bytes"))

            if (not key_extracted or not iv_extracted) and len(decrypted) > 64:
                pb2 = ProtoBuf(decrypted[64:])
                key_extracted = _as_bytes(pb2.EXTRACT_FIELDS([22], mode="bytes"))
                iv_extracted = _as_bytes(pb2.EXTRACT_FIELDS([23], mode="bytes"))

            if key_extracted and iv_extracted:
                self._data.key = key_extracted
                self._data.iv = iv_extracted
            else:
                self._data.key = self.key
                self._data.iv = self.iv

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
            fields[7] = "1.132.15"
            fields[8] = "Android OS 16 / API-36 (BP2A.250605.031.A3/compiler260821111235)"
            fields[9] = "Handheld"
            fields[10] = "VNPT Corp"
            fields[11] = "WIFI"
            fields[12] = 2800
            fields[13] = 1260
            fields[14] = "403"
            fields[15] = "ARM64 FP ASIMD AES | 6028 | 8"
            fields[16] = 11284
            fields[17] = "Adreno (TM) 735"
            fields[18] = "OpenGL ES 3.2 V@0762.41 (GIT@f6b5df5188, I29aebc4401, 1758283784) (Date:09/19/25)"
            fields[19] = self._data.device_id
            fields[20] = "123.27.167.36"
            fields[21] = "vn"
            fields[22] = str(self._data.open_id)
            fields[23] = "4"
            fields[24] = "Handheld"
            fields[25] = "vivo V2352A"
            fields[26] = "VN"
            fields[29] = str(self._data.access_token)
            fields[30] = 1
            fields[41] = "VNPT Corp"
            fields[42] = "WIFI"
            fields[57] = "7428b253defc164018c604a1ebbfebdf"
            fields[60] = 228423
            fields[61] = 145375
            fields[62] = 7639
            fields[63] = 900
            fields[64] = 145503
            fields[65] = 228423
            fields[66] = 145503
            fields[67] = 228423
            fields[70] = 2
            fields[73] = 3
            fields[74] = "/data/app/~~-y-UIr3gmLEdmMjW2LQb8Q==/com.dts.freefireth--DZnru7704bHkg4HUT_TmA==/lib/arm64"
            fields[76] = 1
            fields[77] = "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~-y-UIr3gmLEdmMjW2LQb8Q==/com.dts.freefireth--DZnru7704bHkg4HUT_TmA==/base.apk"
            fields[78] = 3
            fields[79] = 2
            fields[81] = "64"
            fields[83] = "2019121229"
            fields[85] = 3
            fields[86] = "OpenGLES2"
            fields[87] = 8191
            fields[88] = 4
            fields[90] = "Hà Nội"
            fields[91] = "01"
            fields[92] = 6390
            fields[93] = "android"
            fields[94] = "KqsHT1CLbxae244E4dTGVqfMNKgyfNgwdom5oUKUVVi5ketwd/fNOTTK7CCFbGyfUhCvdLIJVGPVNaJUo6gmLWB4RQfS+M90qolEywjfzgJysWyD"
            fields[95] = 110009
            fields[96] = '{"cur_rate":[60,90,120,144],"support_etc2":false}'
            fields[97] = 1
            fields[98] = 1
            fields[99] = "4"
            fields[100] = "4"
            fields[102] = {}
            fields[102][8] = 3771217491960797021
            fields[103] = 1
            fields[104] = 61996
            fields[105] = 1
            fields[106] = "https://dl.gmc.freefiremobile.com/live/ABHotUpdates/|https://core-gmc.freefiremobile.com/live/ABHotUpdates/|dff941d41e6e3a9e76f05ed71fdc8d87"
            fields[107] = "1.16032533697c9e9e"

            key = self.key
            iv = self.iv

            payload = AES_CBC128(pb_encode(fields), key, iv)
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
                print(f"[GetLoginData] ❌ body={r.content[:300]!r}")
                return
            raw = r.content
            try:
                dec = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(raw), 16)
                data = json.loads(protobuf_dec(dec.hex()))
            except:
                data = json.loads(protobuf_dec(raw.hex()))
            self.logindata = data
            _ts_new = _scalar(data.get("21"))
            if _ts_new:
                self._data.login_time = int(_ts_new)
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
            print(f"[GetLoginData] ✅ OK online={self._data.online_ip}:{self._data.online_port} chat={self._data.chat_ip}:{self._data.chat_port}")
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
        except Exception as e:
            print(e)

    def TAO_PACKET_LOBBY(self):
        try:
            return self._auth_packet(False)
        except Exception as e:
            print(e)

    def auth(self, access_token, is_emulator=False):
        try:
            self.is_emulator = is_emulator
            if ":" in access_token:
                uid, password = access_token.split(":")
                self.auth_guest_token(int(uid), password)
            else:
                self.auth_token_inspect(access_token)
            if not self._data.access_token:
                return "account not found"
            self.MajorLogin()
            if not self._data.login_token:
                return "account not found"
            self.GetLoginData()
            if not self.logindata:
                return "account not found"
            pkt = self.TAO_PACKET_XT()
            if not pkt:
                return "account not found"
            return self._build_api_response(pkt)
        except Exception as e:
            print("[auth]", e)

    def _build_api_response(self, authpacket):
        if not self._data.login_token or not authpacket:
            return "account not found"
        if not self._data.key or not self._data.iv:
            return "account not found"
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
        response["device_id"] = self._data.device_id
        return response


class FreeFireAPI:
    def __init__(self):
        self.client = APIClient()

    def get(self, target: str, is_emulator: bool = False):
        return self.client.auth(target, is_emulator)
