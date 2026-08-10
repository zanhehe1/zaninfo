from flask import Flask, request, jsonify, send_file
import requests
import base64
import json
import time
import os
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

# ====== KEY ======
KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

# ====== DECODE JWT ======
def decode_jwt(jwt_token):
    try:
        parts = jwt_token.split('.')
        payload_part = parts[1]
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += '=' * padding
        decoded = base64.urlsafe_b64decode(payload_part)
        return json.loads(decoded)
    except:
        return None

# ====== GIẢI MÃ ACCESS TOKEN ======
def decode_access_token(access_token):
    try:
        parts = access_token.split('.')
        if len(parts) >= 2:
            payload_b64 = parts[1]
            while len(payload_b64) % 4 != 0:
                payload_b64 += '='
            decoded = json.loads(base64.urlsafe_b64decode(payload_b64))
            return decoded
    except:
        pass
    return None

# ====== LẤY NICKNAME TỪ ACCESS TOKEN ======
def get_nickname_from_token(access_token):
    try:
        decoded = decode_access_token(access_token)
        if decoded:
            nickname = decoded.get('nickname', 'Unknown')
            if nickname and nickname != 'Unknown':
                try:
                    nickname = base64.b64decode(nickname).decode('utf-8', errors='ignore')
                except:
                    pass
            return nickname, decoded.get('account_id', 'N/A')
    except:
        pass
    return 'Unknown', 'N/A'

# ====== MÃ HÓA ======
def aes_encrypt(data):
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    return cipher.encrypt(pad(data, AES.block_size))

def encode_varint(n):
    result = []
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            byte |= 0x80
        result.append(byte)
        if not n:
            break
    return bytes(result)

def build_bio_proto(bio_text):
    result = b''
    header = (2 << 3) | 0
    result += encode_varint(header)
    result += encode_varint(17)

