import requests , json , binascii , time , urllib3 , base64 , datetime , re ,socket , threading , random , os , sys , psutil
from protobuf_decoder.protobuf_decoder import Parser
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad , unpad
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from random import choice

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

Key , Iv = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56]) , bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def Ua():
    versions = [
        '4.0.18P6', '4.0.19P7', '4.0.20P1', '4.1.0P3', '4.1.5P2', '4.2.1P8',
        '4.2.3P1', '5.0.1B2', '5.0.2P4', '5.1.0P1', '5.2.0B1', '5.2.5P3',
        '5.3.0B1', '5.3.2P2', '5.4.0P1', '5.4.3B2', '5.5.0P1', '5.5.2P3'
    ]
    models = [
        'SM-A125F', 'SM-A225F', 'SM-A325M', 'SM-A515F', 'SM-A725F', 'SM-M215F', 'SM-M325FV',
        'Redmi 9A', 'Redmi 9C', 'POCO M3', 'POCO M4 Pro', 'RMX2185', 'RMX3085',
        'moto g(9) play', 'CPH2239', 'V2027', 'OnePlus Nord', 'ASUS_Z01QD',
    ]
    android_versions = ['9', '10', '11', '12', '13', '14']
    languages = ['en-US', 'es-MX', 'pt-BR', 'id-ID', 'ru-RU', 'hi-IN', 'en-BD']
    countries = ['USA', 'MEX', 'BRA', 'IDN', 'RUS', 'BD', 'IND']
    version = random.choice(versions)
    model = random.choice(models)
    android = random.choice(android_versions)
    lang = random.choice(languages)
    country = random.choice(countries)
    return f"GarenaMSDK/{version}({model};Android {android};{lang};{country};)"
    
def EnC_AEs(HeX):
    cipher = AES.new(Key , AES.MODE_CBC , Iv)
    return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()

def ArA_CoLor():
    Tp = ["32CD32" , "00BFFF" , "00FA9A" , "90EE90" , "FF4500" , "FF6347" , "FF69B4" , "FF8C00" , "FF6347" , "FFD700" , "FFDAB9" , "F0F0F0" , "F0E68C" , "D3D3D3" , "A9A9A9" , "D2691E" , "CD853F" , "BC8F8F" , "6A5ACD" , "483D8B" , "4682B4", "9370DB" , "C71585" , "FF8C00" , "FFA07A"]
    return random.choice(Tp) 

def DEc_AEs(HeX):
    cipher = AES.new(Key , AES.MODE_CBC , Iv)
    return unpad(cipher.decrypt(bytes.fromhex(HeX)), AES.block_size).hex()
    
def EnC_PacKeT(HeX , K , V): 
    return AES.new(K , AES.MODE_CBC , V).encrypt(pad(bytes.fromhex(HeX) ,16)).hex()
    
def DEc_PacKeT(HeX , K , V):
    return unpad(AES.new(K , AES.MODE_CBC , V).decrypt(bytes.fromhex(HeX)) , 16).hex()  

def random_channel():
    channel = random.choice(['en','ar','fr','br'])
    return channel

def EnC_Uid(H , Tp):
    e , H = [] , int(H)
    while H:
        e.append((H & 0x7F) | (0x80 if H > 0x7F else 0)) ; H >>= 7
    return bytes(e).hex() if Tp == 'Uid' else None

def EnC_Vr(N):
    if N < 0: ''
    H = []
    while True:
        BesTo = N & 0x7F ; N >>= 7
        if N: BesTo |= 0x80
        H.append(BesTo)
        if not N: break
    return bytes(H)
    
def DEc_Uid(H):
    n = s = 0
    for b in bytes.fromhex(H):
        n |= (b & 0x7F) << s
        if not b & 0x80: break
        s += 7
    return n
    
def CrEaTe_VarianT(field_number, value):
    field_header = (field_number << 3) | 0
    return EnC_Vr(field_header) + EnC_Vr(value)

def CrEaTe_LenGTh(field_number, value):
    field_header = (field_number << 3) | 2
    encoded_value = value.encode() if isinstance(value, str) else value
    return EnC_Vr(field_header) + EnC_Vr(len(encoded_value)) + encoded_value

def CrEaTe_ProTo(fields):
    packet = bytearray()    
    for field, value in fields.items():
        if isinstance(value, dict):
            nested_packet = CrEaTe_ProTo(value)
            packet.extend(CrEaTe_LenGTh(field, nested_packet))
        elif isinstance(value, int):
            packet.extend(CrEaTe_VarianT(field, value))           
        elif isinstance(value, str) or isinstance(value, bytes):
            packet.extend(CrEaTe_LenGTh(field, value))           
    return packet    
    
def DecodE_HeX(H):
    R = hex(H) 
    F = str(R)[2:]
    if len(F) == 1: F = "0" + F ; return F
    else: return F

def Fix_PackEt(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data['wire_type'] = result.wire_type
        if result.wire_type == "varint":
            field_data['data'] = result.data
        if result.wire_type == "string":
            field_data['data'] = result.data
        if result.wire_type == "bytes":
            field_data['data'] = result.data
        elif result.wire_type == 'length_delimited':
            field_data["data"] = Fix_PackEt(result.data.results)
        result_dict[result.field] = field_data
    return result_dict

def DeCode_PackEt(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        parsed_results_objects = parsed_results
        parsed_results_dict = Fix_PackEt(parsed_results_objects)
        json_data = json.dumps(parsed_results_dict)
        return json_data
    except Exception as e:
        print(f"error {e}")
        return None

def xBunnEr():
    avatar_list = [
        '902000016', '902000031', '902000011', '902000065',
        '902000204', '902000192', '902000191', '902000179',
        '902000133', '902045001', '902038023', '902048004',
        '902039014', '902000063', '902000306', '902047009'
    ]
    return int(random.choice(avatar_list))
    
def GLobaL(T , K , V):
    fields =  {1: 3 , 2: {2: 5 , 3: f"fr"}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '1215' , K , V)

def ChaT_sQ(T , N , U , sQ , K , V):
    fields =  {1: N , 2: {1: int(U) , 3: f"{T}" , 4: str(sQ)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '1215' , K , V)

def trydecByRedZed(pack):
    try:
        r = pack['5']['data']['3']['data']['31']['data']
    except KeyError:
        r = pack['5']['data']['31']['data']
    except:
        return None
    return r

# ========== MÃ HÓA ID CHO KẾT BẠN (từ file telegram) ==========
def Encrypt_ID(x):
    dec = ['80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '8a', '8b', '8c', '8d', '8e', '8f', '90', '91', 
     '92', '93', '94', '95', '96', '97', '98', '99', '9a', '9b', '9c', '9d', '9e', '9f', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 'a8', 'a9', 'aa', 'ab', 'ac', 'ad', 'ae', 'af', 'b0', 'b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'b7', 'b8', 'b9', 'ba', 'bb', 'bc', 'bd', 'be', 'bf', 'c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'ca', 'cb', 'cc', 'cd', 'ce', 'cf', 'd0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8', 'd9', 'da', 'db', 'dc', 'dd', 'de', 'df', 'e0', 'e1', 'e2', 'e3', 'e4', 'e5', 'e6', 'e7', 'e8', 'e9', 'ea', 'eb', 'ec', 'ed', 'ee', 'ef', 'f0', 'f1', 'f2', 'f3', 'f4', 
     'f5', 'f6', 'f7', 'f8', 'f9', 'fa', 'fb', 'fc', 'fd', 'fe', 'ff']
    xxx = ['1', '01', '02', '03', '04', '05', '06', '07', '08', '09', '0a', '0b', '0c', '0d', '0e', '0f', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '1a', '1b', '1c', '1d', '1e', '1f', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '2a', '2b', '2c', '2d', '2e', '2f', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '3a', '3b', '3c', '3d', '3e', '3f', '40', '41', '42', '43', '44', '45', '46', '47', '48', '49', '4a', '4b', '4c', '4d', '4e', '4f', '50', '51', '52', 
     '53', '54', '55', '56', '57', '58', '59', '5a', '5b', '5c', '5d', '5e', '5f', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '6a', '6b', '6c', '6d', '6e', '6f', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '7a', '7b', '7c', '7d', '7e', '7f']
    try:
        x = int(x)
        x_float = float(x) / 128
        if x_float > 128:
            x_float /= 128
            if x_float > 128:
                x_float /= 128
                if x_float > 128:
                    x_float /= 128
                    strx = int(x_float)
                    y = (x_float - strx) * 128
                    z = (y - int(y)) * 128
                    n = (z - int(z)) * 128
                    m = (n - int(n)) * 128
                    return dec[int(m)] + dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
                else:
                    strx = int(x_float)
                    y = (x_float - strx) * 128
                    z = (y - int(y)) * 128
                    n = (z - int(z)) * 128
                    return dec[int(n)] + dec[int(z)] + dec[int(y)] + xxx[int(x_float)] 
        return None 
    except Exception: 
        return None

# ========== GỬI KẾT BẠN QUA HTTP (cách mới) ==========
def SendFriendRequest_HTTP(target_uid, token, bot_uid=""):
    # Thử các domain khác nhau
    domains = [
        'https://clientbp.ggpolarbear.com/RequestAddingFriend',
        'https://clientbp.ggwhitehawk.com/RequestAddingFriend',
        'https://clientbp.ggpbn.com/RequestAddingFriend',
    ]
    
    headers = {
        'X-Unity-Version': '2018.4.11f1',
        'ReleaseVersion': 'OB54',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-GA': 'v1 1',
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }
    
    encrypted_id = Encrypt_ID(target_uid)
    if not encrypted_id:
        return False, f"Lỗi mã hóa UID: {target_uid}"
    
    plain_text_payload = f'08a7c4839f1e10{encrypted_id}1801'
    data = bytes.fromhex(EnC_AEs(plain_text_payload))
    
    for url in domains:
        try:
            response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
            text = response.text
            
            if response.status_code == 200:
                return True, "Gửi kết bạn thành công!"
            elif 'BR_FRIEND_NOT_SAME_REGION' in text:
                return False, "Khác khu vực!"
            elif 'BR_FRIEND_MAX_REQUEST' in text:
                return False, "Đã đạt giới hạn yêu cầu!"
            elif 'BR_FRIEND_ALREADY_SENT_REQUEST' in text:
                return False, "Đã gửi yêu cầu trước đó!"
            else:
                # Nếu domain sai, thử domain tiếp theo
                continue
        except Exception as e:
            continue
    
    return False, "Không kết nối được đến server (thử hết các domain)"

# ========== HÀM CŨ (giữ để tương thích) ==========
def RedZed_SendInv(uid, k, v):
    fields = {
        1: 33,
        2: {
            1: uid, 
            2: "VN", 
            3: 1, 
            4: 1,
            5: "\u0001\t\n\u000b\u0012\u0019 '",
            6: "Vbage!!", 
            7: 330, 
            8: 1570, 
            9: 100, 
            10: "DZ",
            11: "7428b253defc164018c604a1ebbfebdf",
            12: 1, 
            13: uid, 
            16: 1, 
            17: {
                2: 290, 
                4: "zW\\R",
                6: 11,
                7: "\u0014eamawl\u0016\u0013",
                8: "1.123.6", 
                9: 3, 
                10: 2
            }, 
            18: 311, 
            19: 38,
            23: {
                2: 1,
                3: 1
            }, 
            24: xBunnEr(),
            31: {1: 1, 2: 32768}, 
            32: 32768, 
            34: {
                2: 3,
                3: "\u0010\u0015\b\n\u000b\u0013\f\u000f\u0011\u0004\u0007\u0002\u0003\r\u000e\u0012\u0001\u0005"
            }
        }
    }
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()) , '0515' , k, v)

def GeneRaTePk(Pk , N , K , V):
    PkEnc = EnC_PacKeT(Pk , K , V)
    _ = DecodE_HeX(int(len(PkEnc) // 2))
    if len(_) == 2: HeadEr = N + "000000"
    elif len(_) == 3: HeadEr = N + "00000"
    elif len(_) == 4: HeadEr = N + "0000"
    elif len(_) == 5: HeadEr = N + "000"
    return bytes.fromhex(HeadEr + _ + PkEnc)
        
def ResTarTinG():
    print('\n - ResTartinG BoT ... ! ')
    try:
        p = psutil.Process(os.getpid())
        for f in p.open_files():
            try: os.close(f.fd)
            except: pass
        for conn in p.net_connections(kind='inet'):
            try:
                if conn.fd != -1: os.close(conn.fd)
            except: pass
    except: pass
    time.sleep(0.5)
    python = sys.executable
    os.execl(python, python, *sys.argv)
    
def AuTo_ResTartinG():
    time.sleep(6 * 60 * 60)
    print('\n - AuTo ResTartinG The BoT ... ! ')
    try:
        p = psutil.Process(os.getpid())
        for f in p.open_files():
            try:
                os.close(f.fd)
            except Exception as e:
                print(f" - Error Close File: {e}")
        for conn in p.net_connections(kind='inet'):
            try:
                if conn.fd != -1:
                    os.close(conn.fd)
            except Exception as e:
                print(f" - Error Close Connection: {e}")
    except Exception as e:
        print(f" - Error Accessing Process Info: {e}")

    python = sys.executable
    os.execl(python, python, *sys.argv)    
    
def GeT_Time(timestamp):
    last_login = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    diff = now - last_login   
    h , rem = divmod(diff.seconds, 3600)
    m , s = divmod(rem, 60)    
    return h, m, s             

def xMsGFixinG(n):
    return '🗿'.join(str(n)[i:i + 1] for i in range(0 , len(str(n)) , 1))

def LogOuT(A):
    R = requests.Session().get(f'https://100067.connect.garena.com/oauth/logout?access_token={A}&refresh_token=')
    print(' - LoGOuT => ' , R.text)
    if R.status_code == 200 and '0' in R.text: return True
    else: return False