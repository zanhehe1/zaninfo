import threading, json, socket, time, random, datetime, aiohttp, asyncio, os, struct
import datetime as dt
from lib import *
from GPackGEN import *
from ReQAPI import *
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import requests
from functools import wraps
import telebot
import traceback
import subprocess
import re
import queue

# ===== VOICE IMPORTS =====
try:
    import opuslib
    OPUS_AVAILABLE = True
except ImportError:
    OPUS_AVAILABLE = False
    print("[WARN] opuslib không có — cài: pip install opuslib")

TELEGRAM_BOT_TOKEN = "8851744681:AAEEKsuRKlIa4q0qvDQ765wyYNZSA31nd5Y"
telegram_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)
TELEGRAM_ADMINS = [8722607800]

# ===== MUSIC CONFIG =====
MUSIC_CACHE_DIR = "/tmp/music_cache"
os.makedirs(MUSIC_CACHE_DIR, exist_ok=True)
music_search_cache = {}
VOICE_APP_ID = "FFD58FB4F76F648C2A5E21EBCFA3AAE81B4C9B7D97"
VOICE_UUID = "682761f7-3f39-4912-b019-ced851732362"
CURRENT_VOICE_BOT = None


# ============================================================
# VOICE CLASSES (gộp từ main.py)
# ============================================================

class VoiceDispatcherGRTC:
    def __init__(self, dispatcher_ip="148.222.82.60", dispatcher_port=6674):
        self.dispatcher_ip = dispatcher_ip
        self.dispatcher_port = dispatcher_port

    def build_protobuf(self, uid, room_id, app_id, uuid_str, auth_type):
        clean_room_id = str(room_id).replace("VN_", "")
        voice_token = f"{app_id}VN_{clean_room_id}"
        device_dict = {
            1: 17, 2: 11, 3: 1, 4: "Redmi",
            5: str(uid), 6: 562135116, 7: "arm64-v8a",
            8: "", 9: uuid_str, 10: app_id,
            11: "voiceb", 12: "24094RAD4G", 13: 2, 14: "mt6855"
        }
        return pb_encode({1: voice_token, 2: pb_encode(device_dict), 3: auth_type, 4: "vn"})

    def decode_varint(self, data, start_idx):
        result = 0; shift = 0; idx = start_idx
        while True:
            b = data[idx]
            result |= (b & 0x7F) << shift
            idx += 1
            if not (b & 0x80): break
            shift += 7
        return result, idx

    async def get_voice_server(self, uid, room_id, app_id, uuid_str):
        print(f"[VOICE-STEP2] Dispatcher {self.dispatcher_ip}:{self.dispatcher_port}")
        try:
            pb_payload = self.build_protobuf(uid, room_id, app_id, uuid_str, auth_type=2)
            reader, writer = await asyncio.open_connection(self.dispatcher_ip, self.dispatcher_port)
            writer.write(struct.pack(">I", len(pb_payload)) + pb_payload)
            await writer.drain()
            try:
                resp_len_bytes = await asyncio.wait_for(reader.readexactly(4), timeout=5.0)
            except (asyncio.TimeoutError, asyncio.IncompleteReadError):
                print("[VOICE-STEP2] ❌ Timeout/đóng")
                return None, None
            resp_len = struct.unpack(">I", resp_len_bytes)[0]
            data = await reader.readexactly(resp_len)
            writer.close()
            await writer.wait_closed()

            voice_ip, voice_tcp_port = None, None
            idx = 0
            if idx < len(data) and data[idx] == 0x0A:
                idx += 1; ip_len = data[idx]; idx += 1
                voice_ip = data[idx:idx+ip_len].decode("utf-8"); idx += ip_len
            if idx < len(data) and data[idx] == 0x10:
                idx += 1; voice_tcp_port, _ = self.decode_varint(data, idx)
            if not voice_ip:
                print("[VOICE-STEP2] ❌ Không parse IP")
                return None, None
            print(f"[VOICE-STEP2 ✅] {voice_ip}:{voice_tcp_port}")
            return voice_ip, voice_tcp_port
        except Exception as e:
            print(f"[VOICE-STEP2 ❌] {repr(e)}")
            return None, None


class VoiceTCPHandshakeGRTC:
    def __init__(self, voice_ip, voice_tcp_port):
        self.voice_ip = voice_ip
        self.voice_tcp_port = voice_tcp_port

    def build_f9_auth_packet(self, uid, room_id, app_id, uuid_str):
        clean_room_id = str(room_id).replace("VN_", "")
        voice_token = f"{app_id}VN_{clean_room_id}"
        device_dict = {
            1: 7, 2: 11, 3: 1, 4: "Redmi",
            5: str(uid), 6: 562135116, 7: "arm64-v8a",
            8: "", 9: uuid_str, 10: app_id,
            11: "voiceb", 12: "24094RAD4G", 13: 2, 14: "mt6855"
        }
        return pb_encode({
            1: pb_encode(device_dict), 2: voice_token,
            10: 1, 11: str(uid), 12: 0, 14: 0, 16: 1
        })

    def decode_varint(self, data, start_idx):
        result = 0; shift = 0; idx = start_idx
        while idx < len(data):
            b = data[idx]; result |= (b & 0x7F) << shift; idx += 1
            if not (b & 0x80): break
            shift += 7
        return result, idx

    async def execute_handshake(self, uid, room_id, app_id, uuid_str):
        print(f"[VOICE-STEP3] TCP {self.voice_ip}:{self.voice_tcp_port}")
        try:
            reader, writer = await asyncio.open_connection(self.voice_ip, self.voice_tcp_port)
            pb_payload = self.build_f9_auth_packet(uid, room_id, app_id, uuid_str)
            writer.write(struct.pack(">I", len(pb_payload)) + pb_payload)
            await writer.drain()

            resp1_len_bytes = await asyncio.wait_for(reader.readexactly(4), timeout=5.0)
            resp1_len = struct.unpack(">I", resp1_len_bytes)[0]
            resp1_payload = await reader.readexactly(resp1_len)

            fields_r1 = {}
            idx = 0
            while idx < len(resp1_payload):
                tag_type = resp1_payload[idx]; idx += 1
                field_num = tag_type >> 3
                wire_type = tag_type & 0x07
                if wire_type == 0:
                    val, idx = self.decode_varint(resp1_payload, idx)
                    fields_r1[field_num] = val
                elif wire_type == 2:
                    length, idx = self.decode_varint(resp1_payload, idx)
                    raw = resp1_payload[idx:idx+length]; idx += length
                    fields_r1[field_num] = raw
                else: break

            udp_port = fields_r1.get(2) or fields_r1.get(5)
            f13 = fields_r1.get(13, 0)
            f3 = fields_r1.get(3, 0)
            ssrc = (f13 & 0xFFFFFFFF) if f13 else ((f3 & 0xFFFFFFFF) if f3 else random.randint(0x10000000, 0x7FFFFFFF))
            f3_val = f3 & 0xFFFFFFFF

            f1_raw = fields_r1.get(1, b"")
            custom_pb = (bytes([0x0A, len(f1_raw)]) + f1_raw) if f1_raw else resp1_payload
            writer.write(struct.pack(">I", len(custom_pb)) + custom_pb)
            await writer.drain()

            try:
                resp2_len_bytes = await asyncio.wait_for(reader.readexactly(4), timeout=5.0)
                resp2_len = struct.unpack(">I", resp2_len_bytes)[0]
                await reader.readexactly(resp2_len)
            except asyncio.TimeoutError:
                print("[VOICE-STEP3 ⚠️] Timeout RESP-2")

            print(f"[VOICE-STEP3 ✅] UDP={udp_port} SSRC=0x{ssrc:08X}")
            return udp_port, ssrc, f3_val, reader, writer
        except Exception as e:
            print(f"[VOICE-STEP3 ❌] {repr(e)}")
            return None, None, None, None, None


class OpusVoiceClientGRTC:
    def __init__(self, voice_ip, voice_udp_port, ssrc, fixed_2=0x00002662):
        self.voice_ip = voice_ip
        self.voice_udp_port = voice_udp_port
        self.ssrc = ssrc
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2.0)
        self.is_running = False
        if OPUS_AVAILABLE:
            self.encoder = opuslib.Encoder(48000, 1, opuslib.APPLICATION_AUDIO)
        else:
            self.encoder = None
        self.seq_num = 1
        self.timestamp = 0
        self.fixed_2 = fixed_2

    def send_open_mic(self):
        pkt = bytearray()
        pkt.append(0x71)
        pkt += (self.seq_num & 0xFFFFFF).to_bytes(3, 'big')
        pkt += struct.pack(">I", self.timestamp & 0xFFFFFFFF)
        pkt += struct.pack(">I", self.ssrc & 0xFFFFFFFF)
        pkt += struct.pack(">I", 0x00000311)
        pkt += bytes.fromhex("0000010720210000286e4672656520466972650000000000000000000000")
        pkt += bytes.fromhex("e7877176")
        self.sock.sendto(bytes(pkt), (self.voice_ip, self.voice_udp_port))
        self.seq_num += 1
        self.timestamp += 960

    def build_opus_packet(self, opus_data):
        header = bytearray()
        header.extend(b"\x41\x6f")
        header.extend(struct.pack(">H", self.seq_num & 0xFFFF))
        header.extend(struct.pack(">I", self.timestamp & 0xFFFFFFFF))
        header.extend(struct.pack(">I", self.ssrc & 0xFFFFFFFF))
        header.extend(struct.pack(">I", self.fixed_2 & 0xFFFFFFFF))
        self.seq_num += 1
        self.timestamp += 960
        return bytes(header) + opus_data

    def udp_keepalive_loop(self):
        ka_seq = 0xF00000; ka_ts = 0x74000000
        while self.is_running:
            time.sleep(2.0)
            try:
                pkt = bytearray()
                pkt.append(0x71)
                pkt += (ka_seq & 0xFFFFFF).to_bytes(3, 'big')
                pkt += struct.pack(">I", ka_ts & 0xFFFFFFFF)
                pkt += struct.pack(">I", self.ssrc & 0xFFFFFFFF)
                pkt += struct.pack(">I", 0x00002662)
                self.sock.sendto(bytes(pkt), (self.voice_ip, self.voice_udp_port))
                ka_seq = (ka_seq + 1) & 0xFFFFFF
                ka_ts = (ka_ts + 960) & 0xFFFFFFFF
            except: pass

    def _producer_thread(self, mp3_file, q):
        cmd = ['ffmpeg', '-i', mp3_file,
               '-filter:a', 'volume=4.8,alimiter=limit=0.95',
               '-f', 's16le', '-ac', '1', '-ar', '48000',
               '-loglevel', 'quiet', 'pipe:1']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=65536)
        chunk_size = 1920
        try:
            while self.is_running:
                raw = proc.stdout.read(chunk_size)
                if len(raw) < chunk_size:
                    q.put(None, block=True, timeout=5.0)
                    break
                if not any(raw[i] | raw[i+1] for i in range(0, min(len(raw), 64), 2)):
                    continue
                opus_data = self.encoder.encode(raw, 960) if self.encoder else raw[:200]
                q.put(opus_data, block=True, timeout=5.0)
        except Exception as e:
            print(f"[VOICE-PRODUCER ❌] {e}")
            try: q.put(None, block=False)
            except: pass
        finally:
            proc.terminate(); proc.wait()

    def start_music_stream(self, mp3_file, on_finish=None):
        self.is_running = True
        for _ in range(3):
            self.send_open_mic()
            time.sleep(0.02)
        threading.Thread(target=self.audio_stream_loop, args=(mp3_file, on_finish), daemon=True).start()
        threading.Thread(target=self.udp_keepalive_loop, daemon=True).start()

    def audio_stream_loop(self, mp3_file, on_finish=None):
        q = queue.Queue(maxsize=500)
        producer = threading.Thread(target=self._producer_thread, args=(mp3_file, q), daemon=True)
        producer.start()
        while q.qsize() < 100 and self.is_running:
            time.sleep(0.05)
        print(f"[VOICE-AUDIO] Stream {mp3_file}")
        packets_sent = 0
        next_send = time.perf_counter()
        try:
            while self.is_running:
                try:
                    opus_data = q.get(timeout=0.5)
                except queue.Empty:
                    next_send = time.perf_counter()
                    continue
                if opus_data is None:
                    print(f"[VOICE-AUDIO] Hết nhạc ({packets_sent} frames)")
                    break
                packet = self.build_opus_packet(opus_data)
                try:
                    self.sock.sendto(packet, (self.voice_ip, self.voice_udp_port))
                except OSError:
                    pass
                packets_sent += 1
                next_send += 0.020
                sleep_for = next_send - time.perf_counter()
                if sleep_for > 0: time.sleep(sleep_for)
                elif sleep_for < -0.060: next_send = time.perf_counter()
        except Exception as e:
            print(f"[VOICE-AUDIO ❌] {e}")
        finally:
            self.is_running = False
            if on_finish:
                try: on_finish()
                except: pass


# ============================================================
# PIPELINE PHÁT NHẠC
# ============================================================

def trigger_music_pipeline(bot, gvoice_room_id, gvoice_squad_id, music_file):
    global CURRENT_VOICE_BOT
    CURRENT_VOICE_BOT = bot
    
    def _start_music():
        time.sleep(0.5)
        _app_id = VOICE_APP_ID
        _uuid = VOICE_UUID
        _uid = bot.botid
        
        loop = asyncio.new_event_loop()
        
        async def master_voice_pipeline():
            print(f"[VOICE-PIPELINE] Room={gvoice_room_id} Music={music_file}")
            
            async def send_tcp_cmd(writer, cmd_id):
                try:
                    clean_room_id = str(gvoice_room_id).replace("VN_", "")
                    voice_token = f"{_app_id}VN_{clean_room_id}"
                    f1_bytes = pb_encode({1: cmd_id, 2: 0, 3: 0})
                    f3_bytes = pb_encode({1: str(_uid), 2: 1})
                    payload = pb_encode({1: f1_bytes, 2: voice_token, 3: f3_bytes})
                    writer.write(struct.pack(">I", len(payload)) + payload)
                    await writer.drain()
                except Exception as e:
                    print(f"[VOICE-TX ❌] CMD={cmd_id}: {e}")
            
            async def send_agora_join(writer):
                try:
                    agora_pkt = bytes.fromhex("feffff7f")
                    writer.write(struct.pack(">I", len(agora_pkt)) + agora_pkt)
                    await writer.drain()
                except Exception:
                    pass
            
            dispatcher = VoiceDispatcherGRTC()
            voice_ip, voice_tcp_port = await dispatcher.get_voice_server(_uid, gvoice_room_id, _app_id, _uuid)
            if not voice_ip or not voice_tcp_port: return
            
            await asyncio.sleep(0.1)
            handshake = VoiceTCPHandshakeGRTC(voice_ip, voice_tcp_port)
            udp_port, ssrc, fixed_2, v_reader, v_writer = await handshake.execute_handshake(_uid, gvoice_room_id, _app_id, _uuid)
            if not udp_port or not ssrc: return
            
            print("[VOICE-PIPELINE] Sync Game...")
            await send_tcp_cmd(v_writer, 9)
            await asyncio.sleep(0.05)
            await send_agora_join(v_writer)
            
            opus_client = OpusVoiceClientGRTC(voice_ip, udp_port, ssrc, fixed_2)
            opus_client.send_open_mic()
            await asyncio.sleep(0.1)
            
            await send_tcp_cmd(v_writer, 24)
            await send_tcp_cmd(v_writer, 35)
            
            async def tcp_reader_and_keepalive():
                last_cmd9_time = time.time()
                music_started = False
                while not v_writer.is_closing():
                    if time.time() - last_cmd9_time >= 18:
                        await send_tcp_cmd(v_writer, 9)
                        last_cmd9_time = time.time()
                    phase = "header"; pay_len = 0
                    try:
                        hdr = await asyncio.wait_for(v_reader.readexactly(4), timeout=1.0)
                        pay_len = struct.unpack(">I", hdr)[0]
                        if pay_len == 0: continue
                        if pay_len > 500_000:
                            print(f"[VOICE-TCP] pay_len lạ ({pay_len}), ngắt")
                            break
                        phase = "payload"
                        payload = await asyncio.wait_for(v_reader.readexactly(pay_len), timeout=10.0)
                        phase = "done"
                        
                        if pay_len > 100 and not music_started:
                            print("[VOICE-RX] Member Info → kích nhạc")
                            await send_agora_join(v_writer)
                            await send_tcp_cmd(v_writer, 33)
                            music_started = True
                            if not getattr(opus_client, 'is_running', False):
                                def _on_finish():
                                    print("[VOICE-FINISH] Hết nhạc")
                                    opus_client.is_running = False
                                    try: v_writer.close()
                                    except: pass
                                    try:
                                        bot.is_busy = False
                                        bot.rstatus = (0, 0)
                                    except: pass
                                opus_client.start_music_stream(music_file, on_finish=_on_finish)
                        
                        cmd_id = None
                        if len(payload) >= 3 and payload[0] == 0x0a:
                            inner_len = payload[1]
                            if inner_len >= 2 and payload[2] == 0x08:
                                cmd_id = payload[3] if len(payload) > 3 else None
                        if cmd_id == 11:
                            await send_tcp_cmd(v_writer, 11)
                        elif cmd_id == 10 or b"\x08\x0a" in payload[:15]:
                            await send_tcp_cmd(v_writer, 11)
                    except asyncio.TimeoutError:
                        if phase == "payload":
                            print(f"[VOICE-TCP] Timeout payload ({pay_len})")
                            break
                    except Exception as e:
                        print(f"[VOICE-TCP ❌] {e}")
                        try:
                            for _ in range(3):
                                opus_client.send_open_mic()
                                time.sleep(0.05)
                        except: pass
                        break
            await tcp_reader_and_keepalive()
        
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(master_voice_pipeline())
        except Exception as e:
            print(f"[VOICE-LOOP ❌] {e}")
        finally:
            loop.close()
    threading.Thread(target=_start_music, daemon=True).start()


# ============================================================
# FREE FIRE TCP BOT CLASS (giữ nguyên)
# ============================================================

class FreeFireTCP:
 def __init__(self, bot_config, manager):
  self.bot_config = bot_config
  self.manager = manager
  self.running_event = threading.Event()
  self.rstatus = (0, 0)
  self.ids = []
  self.status = True
  self.started = False
  self.base_url = "https://clientbp.ppmainecoonghj.com"
  self.reconnect_lock = threading.Lock()
  self.last_spam_time = {}
  self.roomcode = self.packetAuth = self.packetAuthLobby = self.playerstatus = None
  self.AuthenCode = self.sock39699 = self.sock39801 = None
  self.ChatIP = self.OnlineIP = self.OnlinePort = self.ChatPort = None
  self.roomid = self.GuildIds = self.DesId = self.botid = None
  self.key = self.iv = self.token = b''
  self.login_session = self._data = None
  self.botid = self.nickname = self.region = None
  self._online_gen = 0
  self._chat_gen = 0
  self._online_lock = threading.Lock()
  self.stop_actions = threading.Event()
  self.stop_emote = threading.Event()
  self.emoting = False
  self.running = True
  self.target_uid = None
  self.emote_target = None
  self.is_busy = False

  self.Emotes = {
    'MP40V2': 909040010, 'MP40': 909000075, 'AK47': 909000063,
    'M1887': 909035007, 'XM8': 909000085, 'FAMAS': 909000090,
    'UMP': 909000098, 'PARAFAL': 909045001, 'M1014': 909000081,
    'M1014V2': 909039011, 'P90': 909049010, 'SCAR': 909000068,
    'M4A1': 909039011, 'THOMPSON': 909038010, 'GROZA': 909041005,
    'MP5': 909033002, 'G18': 909038012
   }

 def _IIl(self, logindata, jsdata):
   self._online_gen += 1
   self._chat_gen += 1
   self.cleanup()
   time.sleep(0.5)
   self._data = jsdata
   self._reply_lock = threading.Lock()
   self._chat_lock = threading.Lock()
   self._online_lock = threading.Lock()
   self._gen = TAO_PACKET(logindata, jsdata)
   self._bot = self.bot_session(self)
   self.running_event.set()

   threading.Thread(target=self.connect39801, daemon=True).start()
   for _ in range(20):
      if self.sock39801: break
      time.sleep(0.5)

   if not self.sock39801:
      print("[BOT] Chat chưa kết nối, vẫn tiếp tục online...")

   threading.Thread(target=self.connect39699, daemon=True).start()

 def cleanup(self):
  self.running_event.clear()
  for sock in [self.sock39699, self.sock39801]:
   try:
    if sock:
     try: sock.shutdown(socket.SHUT_RDWR)
     except: pass
     sock.close()
   except: pass
  self.sock39699 = self.sock39801 = None

 def restart_bot(self):
  self.cleanup()
  time.sleep(2)
  self.running_event.set()
  self.started = False
  self.start()

 def connect39801(self):
  gen = self._chat_gen
  with self.reconnect_lock:
   if not self.running_event.is_set() or gen != self._chat_gen: return
   client = None
   try:
    client = socket.create_connection((self.ChatIP, int(self.ChatPort)), timeout=10)
    client.settimeout(10)
    client.sendall(self.packetAuth)
    print(f"[BOT] Chat OK {self.ChatIP}:{self.ChatPort}")
    guild_active = self.bot_config.get("active-clan", True)
    if self.GuildIds and guild_active:
     client.send(self._bot.join_channel(self.GuildIds, self.AuthenCode, 1))
    client.send(self._bot.join_channel(None, None, 5))
    self.sock39801 = client
    while self.running_event.is_set() and gen == self._chat_gen:
     try:
      data = client.recv(4096)
      if len(data) == 0: break
      if data.hex()[:4] == "1200" and len(data) > 50:
       threading.Thread(target=self.C1200, args=(data, client,), daemon=True).start()
     except socket.timeout:
      continue
     except Exception as e: break
   except Exception as e: 
    print(f"Chat connection error: {e}")
   finally:
    if client:
     try: client.close()
     except Exception as e: pass
    if self.sock39801 is client:
     self.sock39801 = None
    if self.running_event.is_set() and gen == self._chat_gen:
     time.sleep(5)
     if self.running_event.is_set() and gen == self._chat_gen:
      threading.Thread(target=self.connect39801, daemon=True).start()
                                                      

 def connect39699(self):
  gen = self._online_gen
  if not self.running_event.is_set() or gen != self._online_gen: return
  if not self._online_lock.acquire(blocking=False):
     return
  client = None
  kicked = False
  try:
     pkt = self.packetAuthLobby or self.packetAuth
     if not pkt:
        print("[BOT] Online missing auth packet")
     else:
        client = socket.create_connection((self.OnlineIP, int(self.OnlinePort)), timeout=10)
        client.settimeout(10)
        client.sendall(pkt)
        self.sock39699 = client
        print(f"[BOT] Online OK uid={self.botid} nick={self.nickname} pkt={len(pkt)} {self.OnlineIP}:{self.OnlinePort}")
        while self.running_event.is_set() and gen == self._online_gen:
           try:
              data = client.recv(4096)
              if len(data) == 0:
                 print("[BOT] Online closed by server")
                 break

              hex_data = data.hex()

              # ===== Parse packet header đúng: [4-byte len LE][1-byte cmd][payload] =====
              if len(data) >= 5:
                 cmd_byte = data[4]
                 if cmd_byte in (4, 11):
                    payload_hex = data[5:].hex()
                    reason = ""
                    if "100b" in payload_hex:
                       reason = "DUPLICATE_LOGIN"
                    elif "1004" in payload_hex:
                       reason = "BANNED"
                    elif "1010" in payload_hex:
                       reason = "INVALID_SESSION"
                    print(f"[BOT] KICK cmd{cmd_byte} reason={reason} ({payload_hex})")
                    kicked = True
                    break

              if len(data) <= 20 and hex_data[:2] in ("f2", "f9", "f8", "9c", "bd", "cb", "c0", "c1", "dd"):
                 try:
                    client.sendall(data)
                 except:
                    pass
                 continue

              if hex_data[:4] == "0f00":
                 try:
                    decdata = json.loads(protobuf_dec(data.hex()[10:]))
                    self.playerstatus = decdata
                    rid = decdata.get("5", {}).get("1", {}).get("15", None)
                    if rid: self.roomid = rid
                    else: self.roomid = None
                 except:
                    pass

              if hex_data[:4] == "0600" and len(data) <= 55:
                 try:
                    res = json.loads(protobuf_dec(data.hex()[10:]))
                    uid = res.get("5", {}).get("1")
                    if uid:
                       ConfirmFriendRequest(uid, self.token, self.base_url)
                       messages = """[c][b][C678DD]HI""".format(uid)
                       self._bot.reply(uid, 2, messages)
                 except:
                    pass
              if self.status and hex_data[:4] in ("0500", "0f00", "0600"):
                 threading.Thread(target=self.gringay, args=(data,), daemon=True).start()
           except socket.timeout:
              continue
           except Exception as e: 
              if not self.running_event.is_set() or gen != self._online_gen: break
              print(f"[BOT] Online recv error: {e}")
              break

        if kicked and gen == self._online_gen:
           self.kick_count = getattr(self, 'kick_count', 0) + 1
           
           if self.kick_count >= 5:
              print(f"[BOT] Kick 5 lần liên tiếp — DỪNG 5 phút")
              time.sleep(300)
              self.kick_count = 0
           
           wait_time = min(30 * self.kick_count, 120)   # 30 → 60 → 90 → 120
           print(f"[BOT {self.bot_config.get('bot_id')}] KICK lần {self.kick_count} — chờ {wait_time}s")
           try:
              self.cleanup()
              time.sleep(wait_time)
              self.running_event.set()
              self.started = False
              self.start()
           except Exception as e:
              print(f"[BOT] Lỗi auto-restart: {e}")
        else:
           self.kick_count = 0
  except Exception as e: 
     print(f"Online connection error: {e}")
  finally:
     try:
        self._online_lock.release()
     except Exception:
        pass
     if client:
        try: client.close()
        except Exception as e: pass
     if self.sock39699 is client:
        self.sock39699 = None
     if not kicked and self.running_event.is_set() and gen == self._online_gen:
        time.sleep(3)
        if self.running_event.is_set() and gen == self._online_gen:
           threading.Thread(target=self.connect39699, daemon=True).start()

 class bot_session:
  def __init__(self, parent):
   self.par = parent
  def __getattr__(self, name):
   return getattr(self.par._gen, name)
  def reply(self, Id, Tp, Ms):
   try:
    if self.par.running_event.is_set() and self.par.sock39801:
     self.par.sock39801.sendall(self.par._gen.send_message(Ms, Tp, Id))
   except: pass

 def rstart(self):
  access_token = self.bot_config['auth_bot_login']['access_token']
  while self.running_event.is_set():
   try:
    data = FreeFireAPI().get(access_token, is_emulator=False)
    if not data or data == "account not found" or (isinstance(data, str) and "account not found" in data):
     print("[BOT] Login fail, retry...")
     time.sleep(10)
     continue
    if data.get("GuildData"):
     self.AuthenCode = data.get("GuildData").get("secret_code")
     self.GuildIds = data.get("GuildData").get("id")
    self.packetAuth = bytes(data["UserAuthPacket"])
    lobby = data.get("UserAuthPacketLobby")
    self.packetAuthLobby = bytes(lobby) if lobby else self.packetAuth
    self.botid = int(data["UserAccountUID"])
    self.nickname = data.get("logindata", {}).get("4") or "Unknown"
    self.region = str(data["LockRegion"])
    self.token = data["UserAuthToken"]
    self.ChatIP = data["GameServerAddress"]["chatip"]
    self.OnlineIP = data["GameServerAddress"]["onlineip"]
    self.OnlinePort = data["GameServerAddress"]["onlineport"]
    self.ChatPort = data["GameServerAddress"]["chatport"]
    self.key, self.iv = bytes(data["key"]), bytes(data["iv"])
    self.base_url = data["BaseUrl"]
    print(f"[BOT] Login OK uid={self.botid} online={self.OnlineIP}:{self.OnlinePort}")
    self._IIl(data["logindata"], data)
    for _ in range(14555):
     if not self.running_event.is_set(): break
     time.sleep(1)
   except Exception as e:
    traceback.print_exc()
    if self.running_event.is_set(): time.sleep(30)

 def start(self):
  if self.started: return
  self.started = True
  self.running_event.set()
  print(f"[BOT] Starting bot_id={self.bot_config.get('bot_id')}")
  threading.Thread(target=self.rstart, daemon=True).start()


class BOTMNG:
 def __init__(self):
  self.bots = {}
  self.config_lock = threading.RLock()
  self.filename = "bot.json"
  self.load_config()
  threading.Thread(target=self._auto_run_all_bots, daemon=True).start()

 def _auto_run_all_bots(self):
  time.sleep(2)
  for bot_id, bot_instance in self.bots.items():
   try:
    if not bot_instance.started: bot_instance.start()
   except: pass

 def load_config(self):
  try:
   if os.path.exists(self.filename):
    with open(self.filename, "r", encoding="utf-8") as f:
     self.config = json.load(f)
   else:
    self.config = {"bots": []}
   if "bots" not in self.config: self.config["bots"] = []
   for bot_data in self.config["bots"]:
    bot_id = bot_data["bot_id"]
    bot_instance = FreeFireTCP(bot_data, self)
    if "botid" in bot_data: bot_instance.botid = bot_data["botid"]
    if "nickname" in bot_data: bot_instance.nickname = bot_data["nickname"]
    if "access_bot" in bot_data: bot_instance.bot_config["access_bot"] = bot_data["access_bot"]
    self.bots[bot_id] = bot_instance
  except Exception as e:
   print(f"Load config error: {e}")
   self.config = {"bots": []}

 def save_config(self):
  try:
   with self.config_lock:
    for bot_id, bot_instance in self.bots.items():
     for bot_config in self.config["bots"]:
      if bot_config["bot_id"] == bot_id:
       if hasattr(bot_instance, 'botid') and bot_instance.botid:
        bot_config["botid"] = bot_instance.botid
       if hasattr(bot_instance, 'nickname') and bot_instance.nickname:
        bot_config["nickname"] = bot_instance.nickname
    with open(self.filename, 'w', encoding='utf-8') as f:
     json.dump(self.config, f, ensure_ascii=False, indent=2)
  except: pass

 def add_bot(self, access_token):
  with self.config_lock:
   bot_id = 1 if not self.config["bots"] else max(b["bot_id"] for b in self.config["bots"]) + 1
   new_bot = {
    "bot_id": bot_id,
    "auth_bot_login": {"access_token": access_token},
    "access_bot": [],
    "active-clan": True
   }
   self.config["bots"].append(new_bot)
   self.save_config()
   self.bots[bot_id] = FreeFireTCP(new_bot, self)
   return {"status": True, "bot_id": bot_id}


TCPbot = BOTMNG()
app = Flask(__name__)


# ============================================================
# HELPER: LẤY BOT RẢNH
# ============================================================

def get_available_bots(count=1):
    available = []
    for b in TCPbot.bots.values():
        if (b.running_event.is_set() and getattr(b, "sock39699", None) and not getattr(b, "is_busy", False)):
            available.append(b)
            if len(available) == count: break
    return available


# ============================================================
# CHECK USER IN GROUP
# ============================================================

CHAT_GROUP_ID_1 = "@zancommunity"
CHAT_GROUP_ID_2 = "@zanxchannel"

def is_telegram_admin(user_id):
    return user_id in TELEGRAM_ADMINS

def check_user_in_group(user_id):
    if is_telegram_admin(user_id): return True
    in_g1 = in_g2 = False
    try:
        m = telegram_bot.get_chat_member(CHAT_GROUP_ID_1, user_id)
        if m.status in ['member', 'creator', 'administrator']: in_g1 = True
    except: pass
    try:
        m = telegram_bot.get_chat_member(CHAT_GROUP_ID_2, user_id)
        if m.status in ['member', 'creator', 'administrator']: in_g2 = True
    except: pass
    return in_g1 and in_g2

def send_warn_join_group(message):
    msg = f"<blockquote><b>VUI LÒNG THAM GIA 2 NHÓM</b>\n@zancommunity\n@zanxchannel</blockquote>"
    telegram_bot.reply_to(message, msg, parse_mode="HTML")

def check_group_only(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        if is_telegram_admin(user_id): return func(message, *args, **kwargs)
        return func(message, *args, **kwargs)
    return wrapper

def async_telegram(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        threading.Thread(target=func, args=(message, *args), kwargs=kwargs, daemon=True).start()
    return wrapper


# ============================================================
# MUSIC HELPERS
# ============================================================

def _search_youtube(query, max_results=10):
    try:
        cmd = ["yt-dlp", f"ytsearch{max_results}:{query}",
               "--dump-json", "--no-playlist", "--flat-playlist",
               "--no-warnings", "--skip-download"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return []
        results = []
        for line in r.stdout.strip().split("\n"):
            if not line.strip(): continue
            try:
                j = json.loads(line)
                results.append({
                    "title": j.get("title", "Unknown"),
                    "video_id": j.get("id", ""),
                    "duration": j.get("duration", 0),
                    "uploader": j.get("uploader", ""),
                })
            except: continue
        return results
    except Exception as e:
        print(f"[MUSIC] search err: {e}")
        return []

def _download_music(video_id, title):
    try:
        safe = re.sub(r'[^\w\-]+', '_', title)[:60]
        out_file = os.path.join(MUSIC_CACHE_DIR, f"{video_id}_{safe}.mp3")
        if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
            return out_file
        cmd = ["yt-dlp", f"https://www.youtube.com/watch?v={video_id}",
               "-x", "--audio-format", "mp3", "--audio-quality", "5",
               "-o", out_file, "--no-playlist", "--no-warnings", "--force-overwrites"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.returncode != 0 or not os.path.exists(out_file):
            return None
        return out_file
    except Exception as e:
        print(f"[MUSIC] download err: {e}")
        return None


# ============================================================
# TELEGRAM COMMANDS: MUSIC
# ============================================================

@telegram_bot.message_handler(commands=['timnhac'])
@async_telegram
def telegram_timnhac(message):
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            telegram_bot.reply_to(message, "<blockquote><b>DÙNG:</b> <code>/timnhac [tên bài]</code></blockquote>", parse_mode="HTML")
            return
        query = parts[1].strip()
        msg = telegram_bot.reply_to(message, f"<blockquote><b>ĐANG TÌM</b> <code>{query}</code>...</blockquote>", parse_mode="HTML")
        
        def run():
            try:
                results = _search_youtube(query, 10)
                if not results:
                    telegram_bot.edit_message_text(f"<blockquote><b>KHÔNG TÌM THẤY</b></blockquote>",
                        chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
                    return
                music_search_cache[message.from_user.id] = {"query": query, "results": results}
                text = f"<blockquote><b>KẾT QUẢ</b>\n━━━━━━━━━━━━━━\n🔍 <code>{query}</code>\n\n"
                for i, r in enumerate(results, 1):
                    dur = r.get("duration") or 0
                    m, s = divmod(int(dur), 60) if dur else (0, 0)
                    text += f"<b>{i}.</b> {r['title'][:50]}\n   ⏱ {m}:{s:02d} | 👤 {r.get('uploader','')[:20]}\n\n"
                text += f"━━━━━━━━━━━━━━\n<code>/phatnhac [teamcode] [số]</code></blockquote>"
                telegram_bot.edit_message_text(text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
            except Exception as e:
                telegram_bot.edit_message_text(f"<blockquote><b>LỖI</b> {str(e)[:80]}</blockquote>",
                    chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
        threading.Thread(target=run, daemon=True).start()
    except Exception as e:
        telegram_bot.reply_to(message, f"LỖI: {e}")


@telegram_bot.message_handler(commands=['phatnhac'])
@async_telegram
def telegram_phatnhac(message):
    try:
        parts = message.text.split()
        if len(parts) < 3:
            telegram_bot.reply_to(message, "<blockquote><b>DÙNG:</b> <code>/phatnhac [teamcode] [số]</code></blockquote>", parse_mode="HTML")
            return
        team_code = parts[1].strip()
        if not team_code.isdigit():
            telegram_bot.reply_to(message, "Teamcode phải là số!")
            return
        choice = int(parts[2].strip())
        
        user_cache = music_search_cache.get(message.from_user.id)
        if not user_cache:
            telegram_bot.reply_to(message, "Dùng /timnhac trước!")
            return
        results = user_cache.get("results", [])
        if not (1 <= choice <= len(results)):
            telegram_bot.reply_to(message, f"Số bài phải từ 1-{len(results)}")
            return
        
        selected = results[choice - 1]
        title = selected.get("title", "Unknown")
        video_id = selected.get("video_id", "")
        
        bots = get_available_bots(1)
        if not bots:
            telegram_bot.reply_to(message, "Không có bot rảnh!")
            return
        
        bot = bots[0]
        bot.is_busy = True
        
        msg = telegram_bot.reply_to(message,
            f"<blockquote><b>CHUẨN BỊ PHÁT</b>\n🎵 {title[:55]}\n🎮 Team: {team_code}\n⏳ Đang tải nhạc...</blockquote>",
            parse_mode="HTML")
        
        def run():
            try:
                mp3 = _download_music(video_id, title)
                if not mp3:
                    bot.is_busy = False
                    telegram_bot.edit_message_text("<blockquote><b>TẢI THẤT BẠI</b></blockquote>",
                        chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
                    return
                
                # Join team
                try:
                    bot.sock39699.send(bot._bot.join_squad(int(team_code)))
                    print(f"[PHATNHAC] Join team {team_code}")
                except Exception as e:
                    bot.is_busy = False
                    telegram_bot.edit_message_text(f"<blockquote><b>JOIN FAIL</b> {str(e)[:60]}</blockquote>",
                        chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
                    return
                
                time.sleep(2.5)
                
                # Lấy room_id
                room_id = None
                if bot.playerstatus:
                    try:
                        f5 = bot.playerstatus.get("5", {}).get("1", {})
                        for rk in ["14", "17", "31", "33"]:
                            rv = f5.get(rk)
                            if rv and isinstance(rv, (int, str)):
                                rv_str = str(rv)
                                for pfx in ["VN_", "BB_", "IDC1_"]:
                                    if rv_str.startswith(pfx): rv_str = rv_str[len(pfx):]; break
                                if rv_str.isdigit():
                                    room_id = "VN_" + rv_str
                                    break
                    except: pass
                
                if not room_id:
                    bot.is_busy = False
                    telegram_bot.edit_message_text("<blockquote><b>KHÔNG LẤY ĐƯỢC ROOM ID</b></blockquote>",
                        chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
                    return
                
                # Trigger voice pipeline
                trigger_music_pipeline(bot, room_id, team_code, mp3)
                
                telegram_bot.edit_message_text(
                    f"<blockquote><b>ĐANG PHÁT NHẠC THẬT</b>\n━━━━━━━━━━━━━━\n🎵 {title[:55]}\n🎮 Team: {team_code}\n📻 Room: {room_id}\n━━━━━━━━━━━━━━\n⏹ <code>/stopnhac</code></blockquote>",
                    chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
            except Exception as e:
                bot.is_busy = False
                telegram_bot.edit_message_text(f"<blockquote><b>LỖI</b> {str(e)[:100]}</blockquote>",
                    chat_id=message.chat.id, message_id=msg.message_id, parse_mode="HTML")
        threading.Thread(target=run, daemon=True).start()
    except Exception as e:
        telegram_bot.reply_to(message, f"LỖI: {e}")


@telegram_bot.message_handler(commands=['stopnhac'])
@async_telegram
def telegram_stopnhac(message):
    global CURRENT_VOICE_BOT
    try:
        if CURRENT_VOICE_BOT:
            CURRENT_VOICE_BOT.is_busy = False
            CURRENT_VOICE_BOT.rstatus = (0, 0)
            CURRENT_VOICE_BOT = None
        for bot in TCPbot.bots.values():
            bot.is_busy = False
        telegram_bot.reply_to(message, "<blockquote><b>ĐÃ DỪNG NHẠC</b></blockquote>", parse_mode="HTML")
    except Exception as e:
        telegram_bot.reply_to(message, f"LỖI: {e}")


# ============================================================
# ADMIN COMMANDS: /addbot /delbot /checkbot
# ============================================================

@telegram_bot.message_handler(commands=['addbot'])
def telegram_add_bot(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Không có quyền!")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>SAI CÚ PHÁP</b>\n"
                "Dùng: <code>/addbot [token]</code>\n"
                "Ví dụ: <code>/addbot abc123def456...</code></blockquote>",
                parse_mode="HTML"
            )
            return

        token = parts[1].strip()

        # Kiểm tra token đã tồn tại chưa
        with TCPbot.config_lock:
            for b in TCPbot.config.get("bots", []):
                old_token = b.get("auth_bot_login", {}).get("access_token", "")
                if old_token == token:
                    telegram_bot.reply_to(
                        message,
                        f"❌ Token này đã tồn tại ở bot ID <b>{b.get('bot_id')}</b>!",
                        parse_mode="HTML"
                    )
                    return

        result = TCPbot.add_bot(token)
        if result.get("status"):
            bot_id = result["bot_id"]
            TCPbot.bots[bot_id].start()
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>✅ THÊM BOT THÀNH CÔNG</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Bot ID: <code>{bot_id}</code>\n"
                f"🔑 Token: <code>{token[:25]}...</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⏳ Bot đang khởi động...</blockquote>",
                parse_mode="HTML"
            )
        else:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ THÊM BOT THẤT BẠI</b>\n"
                f"Lý do: {result.get('message', 'unknown')}</blockquote>",
                parse_mode="HTML"
            )
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ LỖI: {str(e)[:100]}")


@telegram_bot.message_handler(commands=['delbot'])
def telegram_del_bot(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Không có quyền!")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>SAI CÚ PHÁP</b>\n"
                "Dùng: <code>/delbot [botid]</code>\n"
                "Hoặc: <code>/delbot all</code> (xóa tất cả)\n"
                "Ví dụ: <code>/delbot 1</code></blockquote>",
                parse_mode="HTML"
            )
            return

        target = parts[1].strip().lower()

        # ===== XÓA ALL =====
        if target == "all":
            count = len(TCPbot.bots)
            if count == 0:
                telegram_bot.reply_to(
                    message,
                    "<blockquote><b>⚠️ KHÔNG CÓ BOT</b>\nKhông có bot nào để xóa!</blockquote>",
                    parse_mode="HTML"
                )
                return

            for bid in list(TCPbot.bots.keys()):
                try:
                    TCPbot.bots[bid].cleanup()
                except:
                    pass
                del TCPbot.bots[bid]

            TCPbot.config["bots"] = []
            TCPbot.save_config()

            telegram_bot.reply_to(
                message,
                f"<blockquote><b>✅ ĐÃ XÓA TẤT CẢ</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🗑 Đã xóa <b>{count}</b> bot khỏi hệ thống\n"
                f"📁 Đã lưu <code>bot.json</code> rỗng</blockquote>",
                parse_mode="HTML"
            )
            return

        # ===== XÓA 1 BOT =====
        try:
            bid = int(target)
        except:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>❌ LỖI</b>\nBot ID phải là số hoặc <code>all</code>!</blockquote>",
                parse_mode="HTML"
            )
            return

        if bid not in TCPbot.bots:
            telegram_bot.reply_to(
                message,
                f"<blockquote><b>❌ KHÔNG TÌM THẤY</b>\nBot ID <code>{bid}</code> không tồn tại!</blockquote>",
                parse_mode="HTML"
            )
            return

        bot_name = getattr(TCPbot.bots[bid], 'nickname', 'Unknown')
        bot_uid = getattr(TCPbot.bots[bid], 'botid', '?')

        # Cleanup socket
        try:
            TCPbot.bots[bid].cleanup()
        except:
            pass

        # Xóa khỏi RAM
        del TCPbot.bots[bid]

        # Xóa khỏi config
        TCPbot.config["bots"] = [
            b for b in TCPbot.config.get("bots", [])
            if b.get("bot_id") != bid
        ]
        TCPbot.save_config()

        telegram_bot.reply_to(
            message,
            f"<blockquote><b>✅ XÓA BOT THÀNH CÔNG</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 Bot ID: <code>{bid}</code>\n"
            f"📛 Tên: <code>{bot_name}</code>\n"
            f"🆔 UID: <code>{bot_uid}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📁 Đã xóa khỏi <code>bot.json</code></blockquote>",
            parse_mode="HTML"
        )
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ LỖI: {str(e)[:100]}")


@telegram_bot.message_handler(commands=['checkbot'])
def telegram_checkbot(message):
    if not is_telegram_admin(message.from_user.id):
        telegram_bot.reply_to(message, "❌ Không có quyền!")
        return
    try:
        if not TCPbot.bots:
            telegram_bot.reply_to(
                message,
                "<blockquote><b>📭 KHÔNG CÓ BOT</b>\nHệ thống chưa có bot nào!</blockquote>",
                parse_mode="HTML"
            )
            return

        total = len(TCPbot.bots)
        online = sum(1 for b in TCPbot.bots.values() if b.running_event.is_set())
        offline = total - online
        busy = sum(1 for b in TCPbot.bots.values() if getattr(b, "is_busy", False))

        text = (
            f"<blockquote><b>📊 DANH SÁCH BOT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 Tổng: <b>{total}</b>\n"
            f"🟢 Online: <b>{online}</b>\n"
            f"🔴 Offline: <b>{offline}</b>\n"
            f"⚡ Busy: <b>{busy}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )

        for bid, bot in TCPbot.bots.items():
            status_icon = "🟢" if bot.running_event.is_set() else "🔴"
            status_text = "Online" if bot.running_event.is_set() else "Offline"
            busy_tag = " <b>[BUSY]</b>" if getattr(bot, "is_busy", False) else ""
            nickname = getattr(bot, 'nickname', '?') or '?'
            bot_uid = getattr(bot, 'botid', '?') or '?'
            region = getattr(bot, 'region', '?') or '?'

            text += (
                f"<b>🤖 Bot {bid}</b> {status_icon}{busy_tag}\n"
                f"├ Tên: <code>{nickname}</code>\n"
                f"├ UID: <code>{bot_uid}</code>\n"
                f"├ Region: <code>{region}</code>\n"
                f"└ Trạng thái: <b>{status_text}</b>\n\n"
            )

        text += "</blockquote>"

        # Nếu quá dài, gửi file
        if len(text) > 4000:
            import io
            plain = re.sub(r'<[^>]+>', '', text)
            f = io.BytesIO(plain.encode('utf-8'))
            f.name = "bots.txt"
            telegram_bot.send_document(
                message.chat.id, f,
                caption=f"📊 Danh sách {total} bot"
            )
        else:
            telegram_bot.reply_to(message, text, parse_mode="HTML")
    except Exception as e:
        telegram_bot.reply_to(message, f"❌ LỖI: {str(e)[:100]}")

def run_telegram():
    print("Telegram bot đang chạy...")
    telegram_bot.infinity_polling()


def ping_keep_alive():
    while True:
        try:
            requests.get("https://zangayinfo-yzah.onrender.com/", timeout=10)
        except: pass
        time.sleep(300)


@app.route("/check", methods=["GET"])
def ktr_bot():
    data = []
    for bid, bot in TCPbot.bots.items():
        data.append({
            "id": bid,
            "status": "online" if bot.running_event.is_set() else "Inactive",
            "busy": getattr(bot, "is_busy", False),
            "botid": getattr(bot, "botid", None),
            "nickname": getattr(bot, "nickname", None)
        })
    return jsonify({"data": data, "total": len(data)})


@app.route("/")
def home():
    return {"status": "online", "music": OPUS_AVAILABLE}


if __name__ == "__main__":
    threading.Thread(target=ping_keep_alive, daemon=True).start()
    threading.Thread(target=run_telegram, daemon=True).start()
    threading.Thread(target=lambda: [b.start() for b in TCPbot.bots.values()], daemon=True).start()
    app.run(host="0.0.0.0", port=2011)
