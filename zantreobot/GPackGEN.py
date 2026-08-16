# -*- coding: utf-8 -*-
from typing import Dict, Any, Optional, List
import time, random, datetime
from ReQAPI import *
from lib import *

class TAO_PACKET:
 def __init__(self, logindata, jsdata):
  self.iv = bytes(jsdata.get("iv"))
  self.key = bytes(jsdata.get("key"))
  self.account_id = logindata.get(str(1))
  self.account_region = jsdata.get("LockRegion")
  self.account_name = jsdata.get("UserNickName")
  self.client_version = jsdata.get("ClientVersion")

  self.rc = ((lambda s: "%02X" % s[self.account_region.upper()]
   if self.account_region.upper() in s else None)
   ({s["2"].upper(): s["1"] for s in logindata["19"]}))
  self.region_code = self.rc

  self._builder = lambda fields: (
   lambda packet, length: bytes.fromhex(
     "%02x%s%s%s%s" % (fields[0][1], self.region_code,
     str(0) * (8 - len(length)) if len(length) < 8 else '', length, packet)))(
     * (lambda header: (header, hex(len(header) // 2)[2:]))
     (AES_CBC128(pb_encode(dict(fields[1:])), self.key, self.iv).hex()))

  self.digtstimes = lambda s = datetime.datetime.utcnow(): int(
   (s + datetime.timedelta(days=(7 - s.weekday())))
   .replace(hour=6, minute=0, second=0, microsecond=0)
   .timestamp())
 def accept_request_invite(self, uid, rc):
  fields = {}
  fields[0] = 5
  fields[1] = 4
  fields[2] = {}
  fields[2][1] = uid
  fields[2][3] = uid
  fields[2][8] = 1
  fields[2][9] = {}
  fields[2][9][10] = 1
  fields[2][9][2] = 277
  fields[2][9][6] = 11
  fields[2][9][8] = self.client_version,
  fields[2][9][9] = 3
  fields[2][10] = rc
  return self._builder(fields=list(fields.items()))
  
 def showskin(self, sid):
    fields = {}
    fields[0] = 5
    fields[1] = 88
    fields[2] = {}
    fields[2][1] = {}
    fields[2][1][1] = int(sid)
    fields[2][1][2] = 1
    fields[2][2] = 2
    
    # Đã thêm đủ dấu ngoặc )) ở cuối
    return self._builder(fields=list(fields.items()))
    
 def send_message(self, message, messageType, chatid):
  fields = {}
  fields[0] = 18
  fields[1] = 1
  fields[2] = {}
  fields[2][1] = self.account_id
  fields[2][2] = int(chatid)
  fields[2][4] = fstr(str(message))
  fields[2][5] = int(time.time())

  if messageType:
   fields[2][3] = int(messageType)
   fields[2][7] = 0x2

  fields[2][9] = {}
  fields[2][9][1] = self.account_name
  fields[2][9][2] = getavatar()
  fields[2][9][3] = 901027033
  fields[2][9][4] = 228
  fields[2][9][5] = 827001005
  fields[2][9][10] = 1
  fields[2][9][11] = 1
  fields[2][9][12] = 1
  fields[2][9][13] = {}
  fields[2][9][13][1] = 2
  fields[2][9][14] = {}
  fields[2][9][14][1] = self.account_id
  fields[2][9][14][2] = 8
  fields[2][9][14][3] = bytes([15,6,21,8,10,11,19,12,17,4,14,20,7,2,1,5,16,3,13,18])

  fields[2][10] = self.account_region.lower()
  fields[2][13] = {}
  fields[2][13][2] = 0x1
  fields[2][13][3] = 0x1

  fields[2][14] = {}
  fields[2][14][1] = {}
  fields[2][14][1][1] = 1
  fields[2][14][1][2] = 1
  fields[2][14][1][3] = random.randint(1, 100)
  fields[2][14][1][4] = 36
  fields[2][14][1][5] = self.digtstimes()
  fields[2][14][1][6] = self.account_region
  return self._builder(fields=list(fields.items()))
  
 def lag_dev(self):
    fields = {}
    fields[0] = 5
    fields[1] = 15
    fields[2] = {}
    fields[2][1] = 2147483647
    fields[2][2] = 1
    fields[3] = 4294967295     
    fields[4] = 2147483647  
    return self._builder(fields=list(fields.items()))
  
 def cutmmdi_zan(self, idcut):
    fields = {}
    fields[0] = 5
    fields[1] = 35
    fields[2] = {}
    fields[2][1] = int(idcut)
    return self._builder(fields=list(fields.items())) 
  
 def lag_zan(self):
           fields = {}
           fields[0] = 5
           fields[1] = 15
           fields[2] = {}
           fields[2][1] = 1124759936
           fields[2][2] = 1
           return self._builder(fields=list(fields.items()))
  
 def ghost(self, uid, hv): 
  fields = {} 
  fields[0] = 5 
  fields[1] = 61 
  fields[2] = {} 
  fields[2][1] = int(uid) 
  fields[2][2] = {} 
  fields[2][2][1] = int(uid) 
  fields[2][2][3] = "[b][%s]Telegram  [FFFFFF]:  [00FFFF]@zanbackj" % grcolor() 
  fields[2][2][6] = self.digtstimes() 
  fields[2][2][7] = 0x01 
  fields[2][2][9] = 0x01 
  fields[2][3] = str(hv) 
  return self._builder(fields=list(fields.items()))                                                                                                                                                     
 def send_object(self, payload, chatid, messageType = None):
  fields = {}
  fields[0] = 18
  fields[1] = 1
  fields[2] = {}
  fields[2][1] = self.account_id
  fields[2][2] = int(chatid)
  if messageType: fields[2][3] = int(messageType)
  fields[2][5] = int(time.time())
  fields[2][8] = str(payload)
  fields[2][9] = {}
  fields[2][9][1] = self.account_name
  fields[2][9][2] = getavatar()
  fields[2][9][3] = 901027033
  fields[2][9][4] = 228
  fields[2][9][10] = 11
  fields[2][9][11] = 101
  fields[2][9][13] = {}
  fields[2][9][13][1] = 2
  fields[2][9][14] = {}
  fields[2][9][14][1] = self.account_id
  fields[2][9][14][2] = 8
  fields[2][9][14][3] = bytes([15,6,21,8,10,11,19,12,17,4,14,20,7,2,1,5,16,3,13,18])

  fields[2][10] = self.account_region.lower()
  fields[2][13] = {}
  fields[2][13][2] = 0x01
  fields[2][13][3] = 0x01
  return self._builder(fields=list(fields.items()))

 def open_squad(self, tc):
  fields = {}
  fields[0] = 5
  fields[1] = 1
  fields[2] = {}
  fields[2][2] = bytes([11])
  fields[2][3] = 1
  fields[2][4] = int(tc - 1)
  fields[2][9] = 1
  fields[2][10] = bytes([1, 7, 9, 10, 11, 18, 25, 26, 32])
  fields[2][11] = 1
  fields[2][13] = 1
  fields[2][14] = {}
  fields[2][14][1] = ''
  fields[2][14][2] = 842
  fields[2][14][6] = 11
  fields[2][14][8] = self.client_version
  fields[2][14][9] = 6
  fields[2][14][10] = 1
  fields[2][19] = 329
  return self._builder(fields=list(fields.items()))

 def join_squad_recruit(self, uid, rc):
  fields = {}
  fields[0] = 5
  fields[1] = 4
  fields[2] = {}
  fields[2][1] = uid
  fields[2][15] = rc
  fields[2][4] = bytes([1, 7, 9, 10, 11, 18, 25, 26, 32])
  fields[2][6] = 5
  fields[2][8] = 1
  fields[2][9] = {}
  fields[2][9][10] = 1
  fields[2][9][2] = 277
  fields[2][9][6] = 11
  fields[2][9][8] = self.client_version,
  fields[2][9][9] = 3
  return self._builder(fields=list(fields.items()))
 
 def send_friend_request(self, uid):
    fields = {}
    fields[0] = 5
    fields[1] = 2
    fields[2] = {}
    fields[2][1] = int(uid)
    fields[2][2] = 0
    return self._builder(fields=list(fields.items()))
 
 def join_squad(self, tc):
  fields = {}
  fields[0] = 5
  fields[1] = 4
  fields[2] = {}
  fields[2][4] = bytes([1, 7, 9, 10, 11, 18, 25, 26, 32])
  fields[2][5] = str(tc)
  fields[2][6] = 6
  fields[2][8] = 1
  fields[2][9] = {}
  fields[2][9][1] = ''
  fields[2][9][2] = 842
  fields[2][9][6] = 11
  fields[2][9][8] = self.client_version
  fields[2][9][9] = 6
  fields[2][9][10] = 1
  return self._builder(fields=list(fields.items()))

 def invite_squad(self, user_id, invite_type):
  fields = {}
  fields[0] = 5
  fields[1] = 2
  fields[2] = {}
  fields[2][1] = int(user_id)
  fields[2][2] = self.account_region
  fields[2][4] = int(invite_type)
  return self._builder(fields=list(fields.items()))

 def request_join_squad(self, user_id):
  badge = random.choice([4096, 16384, 8192, 1048576])
  fields = {}
  fields[0] = 5
  fields[1] = 33
  fields[2] = {}
  fields[2][1] = int(user_id)
  fields[2][2] = self.account_region
  fields[2][3] = 1
  fields[2][4] = 1
  fields[2][5] = bytes([1, 7, 9, 10, 11, 18, 25, 26, 32])
  fields[2][6] = self.account_name
  fields[2][7] = 330
  fields[2][8] = 1000
  fields[2][10] = self.account_region
  fields[2][11] = bytes([49, 97, 99, 52, 98, 56, 48, 101, 99, 102, 48, 52, 55, 56,
   97, 52, 52, 50, 48, 51, 98, 102, 56, 102, 97, 99, 54, 49, 50, 48, 102, 53])
  fields[2][12] = 1
  fields[2][13] = int(user_id)
  fields[2][16] = 1
  fields[2][17] = 1
  fields[2][18] = 312
  fields[2][19] = 15
  fields[2][23] = bytes([16, 1, 24, 1])
  fields[2][24] = getavatar()
  fields[2][26] = ''
  fields[2][28] = ''
  fields[2][31] = {}
  fields[2][31][1] = 1
  fields[2][31][2] = badge
  fields[2][32] = badge
  fields[2][34] = {}
  fields[2][34][1] = self.account_id
  fields[2][34][2] = 8
  fields[2][34][3] = bytes([15,6,21,8,10,11,19,12,17,4,14,20,7,2,1,5,16,3,13,18])
  return self._builder(fields=list(fields.items()))  

 def leave_squad(self, uid: int = 0x1):
  fields = {}
  fields[0] = 5
  fields[1] = 7
  fields[2] = {}
  fields[2][1] = int(uid)
  return self._builder(fields=list(fields.items()))

 def leave_channel(self, cid, type):
  fields = {}
  fields[0] = 18
  fields[1] = 4
  fields[2] = {}
  fields[2][1] = int(cid)
  if type: fields[2][2] = int(type)
  fields[2][3] = self.account_region.lower()
  return self._builder(fields=list(fields.items()))

 def join_channel(self, cid, ccode, ctype):
  fields = {}
  fields[0] = 18
  fields[1] = 3
  fields[2] = {}
  if cid: fields[2][1] = int(cid)
  if ctype: fields[2][2] = int(ctype)
  if ccode: fields[2][4] = str(ccode)
  fields[2][3] = self.account_region.lower()
  return self._builder(fields=list(fields.items()))

 def reject_invite(self, ten, uid, sid):
  fields = {}
  fields[0] = 5
  fields[1] = 5
  fields[2] = {}
  fields[2][1] = int(uid)
  fields[2][3] = int(sid)
  fields[2][4] = str(ten if ten else self.account_name)
  return self._builder(fields=list(fields.items()))

 def ghost_custom(self, teamcode, custom_name):
    colors = ["[FF0000]", "[00FF00]", "[0000FF]", "[FFFF00]", "[FF00FF]", "[00FFFF]"]
    color = random.choice(colors)
    fields = {}
    fields[0] = 5
    fields[1] = 61
    fields[2] = {}
    fields[2][1] = int(teamcode)
    fields[2][2] = {}
    fields[2][2][1] = int(teamcode)
    fields[2][2][3] = f"[b][c]{color}{custom_name}"
    fields[2][2][6] = int(time.time())
    fields[2][2][7] = 1
    fields[2][2][9] = 1
    fields[2][3] = "1"
    return self._builder(fields=list(fields.items()))
                  
 def accept_friend(self, uid):
    fields = {}
    fields[0] = 5
    fields[1] = 2
    fields[2] = {}
    fields[2][1] = int(uid)
    fields[2][2] = 0
    return self._builder(fields=list(fields.items()))
    
 def play_animation(self, aid):
  fields = {}
  fields[0] = 5
  fields[1] = 88
  fields[2] = {}
  fields[2][1] = {}
  fields[2][1][1] = int(aid)
  return self._builder(fields=list(fields.items()))

 def show_animation_skin(self, aid):
  fields = {}
  fields[0] = 5
  fields[1] = 88
  fields[2] = {}
  fields[2][1] = {}
  fields[2][1][1] = int(aid)
  fields[2][1][2] = int(1)
  fields[2][2] = {}
  fields[2][2][1] = int(aid)
  return self._builder(fields=list(fields.items()))
    
 def play_emote(self, eid, ids=[]):
  fields = {}
  fields[0] = 5
  fields[1] = 21
  fields[2] = {}
  fields[2][1] = self.account_id
  fields[2][2] = 0x362E3D41
  fields[2][5] = list([{1: id, 3: eid} for id in ids])
  return self._builder(fields=list(fields.items()))

 def start_match(self):
  fields = {}
  fields[0] = 5
  fields[1] = 9
  fields[2] = {}
  fields[2][1] = 1
  return self._builder(fields=list(fields.items()))

 def ask_for_skin(self, uid):
  fields = {}
  fields[0] = 5
  fields[1] = 77
  fields[2] = {}
  fields[2][1] = uid
  fields[2][2] = self.account_id
  return self._builder(fields=list(fields.items()))

 def join_room(self, rid):
  fields = {}
  fields[0] = 14
  fields[1] = 3
  fields[2] = {}
  fields[2][1] = int(rid)
  fields[2][9] = bytes([1, 7, 9, 10, 11, 18, 25, 26, 32])
  fields[2][10] = 0x1
  fields[2][12] = bytes([255, 255, 255, 255, 255, 255, 255, 255, 255, 1,
    255, 255, 255, 255, 255, 255, 255, 255, 255, 1])
  fields[2][13] = 0x1
  fields[2][14] = 0x1
  fields[2][16] = self.account_region
  return self._builder(fields=list(fields.items()))

 def request_join_room(self, room_id, user_id):
  fields = {}
  fields[0] = 14
  fields[1] = 78
  fields[2] = {}
  fields[2][1] = int(room_id)
  fields[2][4] = 330
  fields[2][5] = 6000
  fields[2][6] = 228
  fields[2][10] = getavatar()
  fields[2][11] = int(user_id)
  fields[2][12] = 1
  return self._builder(fields=list(fields.items()))

 def get_history(self, uid):
  uid = Encrypt(uid).hex()
  length = len(uid)
  match length:
   case 8: cc = "080112080A04{}1005".format(uid)
   case 10: cc = "080112090A05{}1005".format(uid)
   case _: return None
  packet = AES_CBC128(bytes.fromhex(cc), self.key, self.iv).hex()
  return bytes.fromhex("0f0100000010" + packet)