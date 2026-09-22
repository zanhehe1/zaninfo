import requests, json, base64, time, struct, datetime, re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from protobuf_decoder.protobuf_decoder import Parser
from typing import Dict, Any, Optional, Tuple, Union, TypedDict, List
from dataclasses import dataclass
from enum import IntEnum
import hashlib

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
 chat_ip = chat_port = online_ip = online_port  = ""
 create_time = None
 expiry_time = None
 guild_id = None
 guild_code = None
 login_token  = None
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
 I=requests.get(f"https://play.google.com/store/apps/%s"%package)
 I=re.search(r'\[\[\["(\d+\.\d+\.\d+)"\]\]', I.text)
 if I:return I.group(1)
 return None

def bdversion(ver: str = None):
    try:
        if not ver:
            try:
                from google_play_scraper import app as play_store_app
                result = play_store_app('com.dts.freefireth', lang="fr", country='fr')
                ver = result['version']
            except Exception:
                ver = "1.132.5"
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
            "remote_version": "1.132.5"
        }
# Details: https://api.freefireservice.dnc.su/ff.status
# Telegram: @gringo_modz

class APIClient:
 def __init__(self):
  self._data = account_data()
  self.logindata = {}
  detail_vers = bdversion()
  self.is_emulator = False
  self.language = "vn"
  self.base_url = detail_vers["server_url"]
  self.client_version = detail_vers.get("remote_version") or "1.132.5"
  self.release_version = detail_vers.get("latest_release_version") or "OB55"
  self.key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
  self.iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
  from urllib.parse import urlparse
  host_name = "loginbp.ppmainecoonghj.com"
  self.session = requests.Session()
  self.session.headers.update({
  "User-Agent": "UnityPlayer/2022.3.47f1(UnityWebRequest/1.0,libcurl/8.5.0- DEV)",  "X-GA": "v1 1", "X-GA-SV": str(int(time.time())), "Content-Type": "application/x-www-form-urlencoded",
  "Accept-Encoding": "deflate, gzip", "Accept": "*/*","X-Unity-Version": "2022.3.47f1",
  "Host": host_name, "ReleaseVersion": self.release_version
  })

 def auth_guest_token(self, uid, password):
  payload = {
   "uid": str(uid), "password": str(password),
   "response_type": "token", "client_type": "2", "client_id": "100067", 
   "client_secret": bytes([50, 101, 101, 52, 52, 56, 49, 57, 101, 57, 98, 52, 53, 57, 56, 56, 52, 53, 49, 52, 49, 48, 54, 55, 98, 50, 56, 49, 54, 50, 49, 56, 55, 52, 100, 48, 100, 53, 100, 55, 97, 102, 57, 100, 56, 102, 55, 101, 48, 48, 99, 49, 101, 53, 52, 55, 49,53, 98, 55, 100, 49, 101, 51]).decode()
   }
  try:
   data = requests.post(
    "https://auth.garena.com/oauth/guest/token/grant",
    data=payload,
    headers={
     "Accept-Encoding": "gzip", "Accept-Encoding": "gzip, deflate",
     "Content-Type": "application/x-www-form-urlencoded",
     "User-Agent": "Mozilla/5.0 (Android 9; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0",
     }
    ).json()
   if "access_token" not in data: return "account not found"
   self._data.access_token = data["access_token"]
   self._data.open_id = data["open_id"]
   self._data.platform = data.get("platform", 0x4)
   self._data.login_platform = data.get("login_platform", 0x4)
   self._data.main_active_platform = data.get("main_active_platform")
   self._data.create_time = data.get("create_time")
   self._data.expiry_time = data.get("expiry_time")
  except Exception as e: print(e)

 def auth_token_inspect(self, access_token):
  try:
   data = requests.get(
    "https://auth.garena.com/oauth/token/inspect",
    params={"token": access_token}
    ).json()
   if "open_id" not in data: raise gayerr("Invalid access token")
   self._data.access_token = access_token
   self._data.open_id = data["open_id"]
   self._data.platform = data.get("platform", 0x4)
   self._data.login_platform = data.get("login_platform", 0x4)
   self._data.main_active_platform = data.get("main_active_platform")
   self._data.create_time = data.get("create_time")
   self._data.expiry_time = data.get("expiry_time")
  except Exception as e: pass

 def MajorLogin(self):
  try:
   fields = {}
   fields[3] = time.strftime("%Y-%m-%d %H:%M:%S")
   fields[4] = "free fire"
   fields[5] = 4
   fields[7] = self.client_version
   fields[8] = "Android OS 14 / API-34"
   fields[9] = "Handheld"
   fields[10] = "Viettel"
   fields[11] = "5G"
   fields[12] = 1440
   fields[13] = 3120
   fields[15] = "ARM64 FP ASIMD AES | 3200 | 12"
   fields[16] = 8192
   fields[17] = "Adreno (TM) 740"
   fields[18] = "OpenGL ES 3.2"
   fields[19] = "Google|a1b2c3d4-e5f6-7890-abcd-ef1234567890"
   fields[20] = "192.168.1.100"
   fields[21] = self.language
   fields[22] = str(self._data.open_id)
   fields[23] = int(self._data.login_platform)
   fields[24] = "Handheld"
   fields[25] = "Xiaomi 14 Pro"
   fields[29] = str(self._data.access_token)
   fields[30] = 1
   fields[41] = "O2"
   fields[42] = "5G"
   fields[57] = bytes([49, 97, 99, 52, 98, 56, 48, 101, 99, 102, 48, 52, 55, 56, 97, 52, 52, 50, 48, 51, 98, 102, 56, 102, 97, 99, 54, 49, 50, 48, 102, 53])
   fields[60] = 32969
   fields[61] = 29901
   fields[62] = 2479
   fields[63] = 900
   fields[64] = 31298
   fields[65] = 32969
   fields[66] = 31298
   fields[67] = 32969
   fields[70] = 4
   fields[73] = 3
   fields[76] = 1
   fields[78] = 6
   fields[79] = 1
   fields[85] = 3
   fields[88] = 4
   fields[93] = "3rd_party" if self.is_emulator else "android"
   fields[94] = "KqsHT0qaTCGUXRYnJ0Rqk4rOvTBtqRFCqrxSLo/afYBAXyCA5v4zw5F/rWCSaZuZONmV1TMDDY0q0rZ4Kys1ITUFfGM=" if self.is_emulator else "KqsHT1r9GNgPJ0nDb82dJ+mJ4wwzqfR9fk7HviQ+4tx58ObceZuLaFrmk9qaVIP+qB3CV0DG40yTeS+2h1GA1rqKtMVPLfDUz7rIThfm4ZKedCh3"
   fields[95] = 111111
   fields[97] = 1
   fields[98] = 1
   fields[99] = str(self._data.main_active_platform)
   fields[100] = str(self._data.platform)
   fields[102] = bytes([71, 87, 76, 65, 86, 89, 9, 4, 78, 1, 12, 19, 15, 4, 64, 94, 65, 57, 89, 83, 15, 80, 91, 61, 15, 81, 91, 110, 82, 9, 60, 10, 84, 50])
   login_url = self.base_url if str(self.base_url).endswith("/") else str(self.base_url) + "/"
   response = self.session.post(
    "%sMajorLogin" % login_url,
    data = AES_CBC128(
     pb_encode(fields),
     self.key, self.iv
    )
   )
   if getattr(response, "status_code", 0) != 200:
    return
   raw = response.content or b""
   pb = ProtoBuf(raw)
   res = pb.protobuf()
   if len(raw) > 64:
    pb2 = ProtoBuf(raw[64:])
    res2 = pb2.protobuf()
    if res2.get("8") or res2.get("1"):
     pb, res = pb2, res2
   tok = _scalar(res.get("8"))
   if isinstance(tok, bytes):
    tok = tok.decode("utf-8", "replace")
   if not (isinstance(tok, str) and tok.count(".") == 2):
    err = None
    for blob in (res, ProtoBuf(raw[64:]).protobuf() if len(raw) > 64 else {}):
     v = blob.get("4") or blob.get("13")
     if isinstance(v, dict) and v.get("4"):
      err = v.get("4"); break
     if isinstance(v, (list, tuple)):
      for i in v:
       if isinstance(i, str) and i and i != "None":
        err = i; break
       if isinstance(i, dict) and i.get("4"):
        err = i.get("4"); break
     if isinstance(v, str) and v not in ("", "None"):
      err = v
     if err: break
    if err:
     print("[MajorLogin] rejected:", err)
    return
   self._data.account_id = _scalar(res.get("1"))
   self._data.server = _scalar(res.get("3"))
   self._data.login_token = tok
   bu = _scalar(res.get("10"))
   if isinstance(bu, bytes):
    bu = bu.decode("utf-8", "replace")
   self._data.base_url = bu
   self._data.login_time = _scalar(res.get("21"))
   self._data.key = _as_bytes(pb.EXTRACT_FIELDS([22], mode="bytes"))
   self._data.iv = _as_bytes(pb.EXTRACT_FIELDS([23], mode="bytes"))
  except Exception as e: print("[MajorLogin]", e)

 def GetLoginData(self):
  try:
   tokendec = gringay.tokendecode(self._data.login_token)
   fields = {}
   fields[3]  = time.strftime("%Y-%m-%d %H:%M:%S")
   fields[7]  = self.client_version
   fields[23] = int(tokendec.get("external_type", 8))
   fields[29] = str(tokendec.get("external_id", ""))
   fields[4]  = "free fire"
   fields[5] = 4
   fields[8]  = "Android OS 14 / API-34"
   fields[9]  = "Handheld"
   fields[10] = "Viettel"
   fields[11] = "5G"
   fields[12] = 1440
   fields[13] = 3120
   fields[15] = "ARM64 FP ASIMD AES | 3200 | 12"
   fields[17] = "Adreno (TM) 740"
   fields[18] = "OpenGL ES 3.2"
   fields[19] = "Google|a1b2c3d4-e5f6-7890-abcd-ef1234567890"
   fields[20] = "192.168.1.100"
   fields[21] = self.language
   fields[22] = "40254b1770e14131d3879ea51acb93ad"
   fields[24] = "Handheld"
   fields[25] = "Xiaomi 14 Pro"
   fields[41] = "Viettel"
   fields[42] = "5G"
   fields[57] = str(tokendec.get("signature_md5", ""))
   fields[60] = 32969
   fields[61] = 29665
   fields[62] = 2479
   fields[63] = 900
   fields[64] = 31063
   fields[65] = 32969
   fields[66] = 31063
   fields[67] = 32969
   fields[70] = 4
   fields[73] = 3
   fields[76] = 1
   fields[78] = 6
   fields[79] = 1
   fields[85] = 3
   fields[88] = 4
   fields[92] = 11111
   fields[95] = 11111
   fields[97] = 1
   fields[98] = 1
   base = str(self._data.base_url or "")
   url = base.rstrip("/") + "/GetLoginData"
   host_header = base.replace("https://", "").replace("http://", "").rstrip("/")
   response = self.session.post(
    url,
    headers = {
     "Authorization": "Bearer %s" % self._data.login_token,
     "Host": host_header
     }, data = AES_CBC128(
     pb_encode(fields),
     self.key, self.iv
    )
   )
   data = json.loads(protobuf_dec(response.content.hex()))
   self.logindata = data
   self._data.guild_id = data.get("20")
   self._data.guild_code = data.get("55")
   sv, chat = _scalar(data.get("14")), _scalar(data.get("32"))
   sv, chat = str(sv or ""), str(chat or "")
   if len(chat) > 6: self._data.chat_port, self._data.chat_ip = chat[-5:], chat[:-6]
   if len(sv) > 6: self._data.online_port, self._data.online_ip = sv[-5:], sv[:-6]
  except Exception as e: pass

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

 def auth(self, access_token, is_emulator = False):
  try:
   self.is_emulator = is_emulator
   if ":" in access_token:
    uid, password = access_token.split(":")
    self.auth_guest_token(int(uid), password)
   else: self.auth_token_inspect(access_token)
   self.MajorLogin()
   self.GetLoginData()
   if not self.logindata:
    return "account not found"
   pkt = self.TAO_PACKET_XT()
   if not pkt: return "account not found"
   return self._build_api_response(pkt)
  except Exception as e: pass
 
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
  else: guild = False

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
  response["UserNickName"] = data.get("nickname")
  response["UserAccountUID"] = data.get("account_id")
  response["LockRegion"] = data.get("lock_region")
  response["ClientVersion"] = data.get("client_version")
  response["IsEmulator"] = data.get("is_emulator")
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