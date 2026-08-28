import asyncio, os, random, datetime, edge_tts, re, glob, requests, aiohttp
from telethon import TelegramClient, events, Button, functions, types
from telethon.errors import FloodWaitError, RPCError, PremiumAccountRequiredError

# --- CẤU HÌNH ---
A_ID = 36093394
A_HS = 'fc171e07ee19738ec8306219a4052335'
B_TK = '8853700916:AAGDoztpG5fYk3-wk2GQQV_h7ll4dY-07gM'
O_ID = 8432808225 

U1 = "https://raw.githubusercontent.com/ehvuebe-png/Cailontaone/main/chui.txt"
U2 = "https://gist.githubusercontent.com/tranthanhloc2099-wq/26971850c22bbc6578dae5a91fc2f154/raw/e96b3178dbce97dab5a9218eced5085802eb1711/chui2.txt"

API_URL = "https://autoreplybyzan.onrender.com"

def _sync():
    for n, u in {"chui.txt": U1, "chui2.txt": U2}.items():
        try:
            r = requests.get(u, timeout=10)
            if r.status_code == 200:
                with open(n, "w", encoding="utf-8") as f: f.write(r.text)
        except: pass
_sync()

bot = TelegramClient('bot_manage', A_ID, A_HS).start(bot_token=B_TK)
o_p, u_c, c_b, c_i, s_t, cl_t, a_r, o_f, w_m, auto_reply = {}, {}, {}, {}, {}, {}, {}, {}, {}, {}

F1, F2 = "bot_users.txt", "banned_users.txt"
if os.path.exists(F2):
    with open(F2, "r") as f: b_u = set(int(l.strip()) for l in f if l.strip())
else: b_u = set()

def _sb():
    with open(F2, "w") as f:
        for u in b_u: f.write(f"{u}\n")

def _su(u):
    if not os.path.exists(F1): open(F1, "w").close()
    with open(F1, "r") as f: us = f.read().splitlines()
    if str(u) not in us:
        with open(F1, "a") as f: f.write(f"{u}\n")

M_T = """
SPAM ĐẾN KHÓT

🔥 𝑺𝒑𝒂𝒎 & 𝑻𝒂𝒈
 ⋙/sp <id> - Spam chửi
 ⋙/sp2 <id> - Spam nội dung
 ⋙/spicon <số> - Spam icon
 ⋙/spnd <nd> - Spam treo
 ⋙/spstick <số> - Spam sticker
 ⋙/spcall <id> - Spam call
 ⋙/spslow <on/off> [giây] - Chế độ spam chậm

☠ 𝑯𝒆‌‌ 𝑻𝒉𝒐‌‌𝒏𝒈 Đ𝒆𝒐 𝑹𝒐‌
 ⋙/cam <id> <box> - Câm box
 ⋙/sua <id> <box> - Gỡ câm
 ⋙/camib <id> - Câm ib
 ⋙/suaib <id> - Gỡ câm ib

📦 𝑳𝒂‌𝒕 𝑽𝒂‌𝒕
 ⋙/info <@/id/rep> - Soi trang
 ⋙/fake <@/id/rep> - Fake người khác
 ⋙/diefake - về lại acc gốc
 ⋙/voice <text> - Voice 
 ⋙/autore <on/off> - Tự động thả tim
 ⋙/off <on/off> - Chế độ bận
 ⋙/autoreply <on/off> [nội dung] - Tự động reply
 ⋙/stop - Dừng tất cả
 ⋙/clear - Xóa 200 tin nhắn
 ➩/clear2 - Xoá tin nhắn bot
 ➩/logout - Thoát acc

👤 **Tài khoản:** [zan](tg://user?id=8722607800)
"""

def _logic(c, u_i):
    spam_slow_mode = False
    spam_delay = 3

    def _mk(cid): w_m[f"{u_i}_{cid}"] = datetime.datetime.now(datetime.timezone.utc)

    async def _sd(cid, ct, tid=None):
        s_t[u_i] = True
        inf = isinstance(ct, str)
        ls = ct if not inf else [ct]
        n = 0
        while s_t.get(u_i):
            for m in ls:
                if not s_t.get(u_i): break
                try:
                    fm = f"{m.strip()} [\u200b](tg://user?id={tid})" if tid else m.strip()
                    await c.send_message(cid, fm, parse_mode='markdown')
                    
                    if spam_slow_mode:
                        await asyncio.sleep(spam_delay)
                    else:
                        await asyncio.sleep(random.uniform(0.8, 1.2))
                    
                    n += 1
                    if n % 10 == 0 and not spam_slow_mode: 
                        await asyncio.sleep(3)
                except FloodWaitError as e: 
                    await asyncio.sleep(e.seconds + 2)
                except: 
                    break
            if not inf: break

    @c.on(events.NewMessage(outgoing=True, pattern=r'/info(?:\s+(.+))?'))
    async def _inf(e):
        target = e.pattern_match.group(1)
        try:
            if target:
                if target.isdigit(): user = await c.get_entity(int(target))
                else: user = await c.get_entity(target)
            elif e.is_reply:
                rep = await e.get_reply_message()
                user = await c.get_entity(rep.sender_id)
            else:
                user = await c.get_me()
            
            await e.edit(f"👤 **Name:** {user.first_name}\n🆔 **ID:** `{user.id}`\n🏷 **User:** @{user.username if user.username else 'N/A'}")
        except: await e.edit("❌ **Không tìm thấy người này!**")

    @c.on(events.NewMessage(outgoing=True, pattern=r'/fake(?:\s+(.+))?'))
    async def _fk(e):
        t = e.pattern_match.group(1)
        try:
            if t: target = await c.get_entity(int(t) if t.isdigit() else t)
            elif e.is_reply: target = await c.get_entity((await e.get_reply_message()).sender_id)
            else: return await e.edit("⚠️ Tag @, ID hoặc Reply!")
        except: return await e.edit("❌ Không thấy!")

        await e.edit(f"🔄 Đang lột xác...")
        try:
            me = await c.get_me()
            me_f = await c(functions.users.GetFullUserRequest(id=me.id))
            my_p = await c.download_profile_photo('me')
            o_p[u_i] = {'f': me.first_name, 'l': me.last_name, 'a': me_f.full_user.about or "", 'p': my_p}

            tf = await c(functions.users.GetFullUserRequest(id=target.id))
            tu = tf.users[0]
            await c(functions.account.UpdateProfileRequest(
                first_name=tu.first_name or "", 
                last_name=tu.last_name or "", 
                about=tf.full_user.about or ""
            ))

            p = await c.get_profile_photos(target.id, limit=1)
            if p:
                path = await c.download_media(p[0])
                await c(functions.photos.UploadProfilePhotoRequest(file=await c.upload_file(path)))
                if os.path.exists(path): os.remove(path)
            else:
                curr_p = await c.get_profile_photos('me')
                if curr_p: await c(functions.photos.DeletePhotosRequest(id=[types.InputPhoto(id=ph.id, access_hash=ph.access_hash, file_reference=ph.file_reference) for ph in curr_p]))
            await e.edit("✅ Xong"); await asyncio.sleep(1); await e.delete()
        except: await e.edit("❌ Lỗi Fake")

    @c.on(events.NewMessage(outgoing=True, pattern=r'/diefake'))
    async def _dfk(e):
        if u_i not in o_p: return await e.edit("⚠️ Chưa lưu gốc!")
        await e.edit("🔙 Đang hoàn hồn...")
        o = o_p[u_i]
        try:
            await c(functions.account.UpdateProfileRequest(
                first_name=o['f'] or "", 
                last_name=o['l'] or "", 
                about=o['a'] or ""
            ))
            curr_p = await c.get_profile_photos('me')
            if curr_p: await c(functions.photos.DeletePhotosRequest(id=[types.InputPhoto(id=ph.id, access_hash=ph.access_hash, file_reference=ph.file_reference) for ph in curr_p]))
            if o['p'] and os.path.exists(o['p']):
                await c(functions.photos.UploadProfilePhotoRequest(file=await c.upload_file(o['p'])))
                os.remove(o['p'])
            o_p.pop(u_i)
            await e.edit("✅ Đã về gốc"); await asyncio.sleep(1); await e.delete()
        except: await e.edit("❌ Lỗi diefake")

    @c.on(events.NewMessage(outgoing=True, pattern=r'/sp (\d+)'))
    async def _sp1(e):
        t = int(e.pattern_match.group(1)); _mk(e.chat_id); await e.delete()
        if os.path.exists('chui.txt'): await _sd(e.chat_id, open('chui.txt', 'r', encoding='utf-8').readlines(), t)

    @c.on(events.NewMessage(outgoing=True, pattern=r'/sp2 (\d+)'))
    async def _sp2(e):
        t = int(e.pattern_match.group(1)); _mk(e.chat_id); await e.delete()
        if os.path.exists('chui2.txt'): await _sd(e.chat_id, open('chui2.txt', 'r', encoding='utf-8').read().strip(), t)

    @c.on(events.NewMessage(outgoing=True, pattern=r'/spicon (\d+)'))
    async def _spi(e):
        _mk(e.chat_id); s_t[u_i] = True; await e.delete()
        try: cnt = int(e.pattern_match.group(1))
        except: cnt = 10
        for _ in range(min(cnt, 500)):
            if not s_t.get(u_i): break
            await e.respond(random.choice(["🧠", "💩", "🤪", "🤣", "💀", "🤡", "🫵", "🙄", "🤙", "👻"]))
            await asyncio.sleep(0.3)

    @c.on(events.NewMessage(outgoing=True, pattern=r'/spnd\s+([\s\S]+)'))
    async def _spn(e):
        v = e.pattern_match.group(1).strip(); _mk(e.chat_id); await e.delete(); s_t[u_i] = True
        while s_t.get(u_i):
            try: 
                await c.send_message(e.chat_id, v)
                await asyncio.sleep(spam_delay if spam_slow_mode else random.uniform(0.7, 1.1))
            except FloodWaitError as r: await asyncio.sleep(r.seconds + 1)
            except: break

    @c.on(events.NewMessage(outgoing=True, pattern=r'/spstick (\d+)'))
    async def _stk(e):
        _mk(e.chat_id); n = int(e.pattern_match.group(1)); await e.delete(); s_t[u_i] = True
        r = await c(functions.messages.GetRecentStickersRequest(hash=0))
        curr = 0
        while curr < n and s_t.get(u_i):
            b = min(50, n - curr)
            await asyncio.gather(*[c.send_file(e.chat_id, random.choice(r.stickers)) for _ in range(b)])
            curr += b; await asyncio.sleep(1.2)

    @c.on(events.NewMessage(outgoing=True, pattern=r'/spcall (\d+)'))
    async def _cal(e):
        _mk(e.chat_id); t = int(e.pattern_match.group(1)); await e.delete(); cl_t[u_i] = True
        while cl_t.get(u_i):
            try:
                res = await c(functions.phone.RequestCallRequest(user_id=t, random_id=random.randint(0, 0x7fffffff), g_a_hash=os.urandom(32), protocol=types.PhoneCallProtocol(min_layer=93, max_layer=93, udp_p2p=True, library_versions=['2.1.0'])))
                await asyncio.sleep(2); await c(functions.phone.DiscardCallRequest(peer=types.InputPhoneCall(id=res.phone_call.id, access_hash=res.phone_call.access_hash), duration=0, reason=types.PhoneCallDiscardReasonDisconnect(), connection_id=0))
            except: await asyncio.sleep(5)

    @c.on(events.NewMessage(outgoing=True, pattern=r'/spslow(?:\s+(.+))?'))
    async def _spslow(event):
        nonlocal spam_slow_mode, spam_delay
        try:
            args = event.raw_text.split()
            if len(args) < 2:
                await event.edit("❌ Dùng: /spslow <on/off> [giây]")
                return

            mode = args[1].lower()
            if mode == "on":
                spam_slow_mode = True
                if len(args) >= 3 and args[2].isdigit():
                    spam_delay = int(args[2])
                await event.edit(f"🐢 **Spam chậm ON** | Delay: `{spam_delay}`s")
            elif mode == "off":
                spam_slow_mode = False
                await event.edit("⚡ **Spam chậm OFF**")
            else:
                await event.edit("❌ Chỉ dùng `on` hoặc `off`")
        except Exception as ex:
            await event.edit(f"❌ Lỗi: {ex}")

    @c.on(events.NewMessage(outgoing=True, pattern=r'/stop'))
    async def _stp(e):
        s_t[u_i] = False; cl_t[u_i] = False; await e.edit("🛑 STOP"); await asyncio.sleep(1); await e.delete()

    @c.on(events.NewMessage(outgoing=True, pattern=r'/clear$'))
    async def _cl1(e):
        async for m in c.iter_messages(e.chat_id, from_user='me', limit=200):
            try: await m.delete()
            except: continue

    @c.on(events.NewMessage(outgoing=True, pattern=r'/clear2'))
    async def _cl2(e):
        k = f"{u_i}_{e.chat_id}"; st = w_m.get(k)
        if not st: await e.edit("⚠️ No data"); await asyncio.sleep(1); await e.delete(); return
        await e.edit("🧹 Clearing..."); 
        async for m in c.iter_messages(e.chat_id, from_user='me'):
            if m.date < st: break
            try: await m.delete()
            except: continue
        w_m.pop(k, None)

    @c.on(events.NewMessage(outgoing=True, pattern=r'/(cam|sua)(?:\s+(\d+))?(?:\s+(-?\d+))?'))
    async def _cam1(e):
        m, u, b = e.pattern_match.group(1), e.pattern_match.group(2), e.pattern_match.group(3)
        if not u and e.is_reply: u = str((await e.get_reply_message()).sender_id)
        if not b: b = str(e.chat_id)
        if u:
            k = f"{u_i}_{b}_{u}"
            if m == "cam": c_b[k] = True
            else: c_b.pop(k, None)
            await e.edit(f"✅ {m.upper()} {u}"); await asyncio.sleep(1); await e.delete()

    @c.on(events.NewMessage(outgoing=True, pattern=r'/(camib|suaib)(?:\s+(\d+))?'))
    async def _cam2(e):
        m, u = e.pattern_match.group(1), e.pattern_match.group(2)
        if not u: u = str(e.chat_id) if e.is_private else (str((await e.get_reply_message()).sender_id) if e.is_reply else None)
        if u:
            k = f"{u_i}_{u}"
            if m == "camib": c_i[k] = True
            else: c_i.pop(k, None)
            await e.edit(f"✅ {m.upper()} {u}"); await asyncio.sleep(1); await e.delete()

    @c.on(events.NewMessage(outgoing=True, pattern=r'/voice (.+)'))
    async def _v(e):
        t = e.pattern_match.group(1); await e.delete(); p = f"v_{u_i}.mp3"
        await edge_tts.Communicate(t, "vi-VN-NamMinhNeural", rate="-15%").save(p)
        await c.send_file(e.chat_id, p, voice_note=True)
        if os.path.exists(p): os.remove(p)

    @c.on(events.NewMessage(outgoing=True, pattern=r'/(autore|off)\s+(on|off)'))
    async def _tg(e):
        x, y = e.pattern_match.group(1), e.pattern_match.group(2)
        if x == "autore": a_r[u_i] = (y == "on")
        else: o_f[u_i] = (y == "on")
        await e.edit(f"✅ {x.upper()} {y.upper()} "); await asyncio.sleep(1); await e.delete()

    @c.on(events.NewMessage(outgoing=True, pattern=r'/autoreply(?:\s+(on|off))?(?:\s+([\s\S]+))?'))
    async def _autoreply(e):
        try:
            args = e.raw_text.split(maxsplit=2)
            
            if len(args) < 2:
                if u_i in auto_reply:
                    auto_reply.pop(u_i)
                    await e.edit("❌ **Đã tắt auto reply!**")
                else:
                    await e.edit("⚠️ **Chưa bật auto reply!**")
                await asyncio.sleep(1)
                await e.delete()
                return
            
            mode = args[1].lower()
            
            if mode == "on":
                if len(args) >= 3:
                    reply_content = args[2]
                else:
                    await e.edit("📝 **Nhập nội dung sẽ reply tự động:**")
                    async with c.conversation(e.chat_id) as conv:
                        msg = await conv.get_response()
                        reply_content = msg.text
                
                auto_reply[u_i] = reply_content
                await e.edit(f"✅ **Đã bật auto reply!**\n📝 Nội dung: `{reply_content[:50]}{'...' if len(reply_content) > 50 else ''}`")
                await asyncio.sleep(2)
                await e.delete()
                
            elif mode == "off":
                if u_i in auto_reply:
                    auto_reply.pop(u_i)
                    await e.edit("❌ **Đã tắt auto reply!**")
                else:
                    await e.edit("⚠️ **Chưa bật auto reply!**")
                await asyncio.sleep(1)
                await e.delete()
                
            else:
                await e.edit("❌ **Sai cú pháp!** Dùng: `/autoreply on <nội dung>` hoặc `/autoreply off`")
                await asyncio.sleep(2)
                await e.delete()
                
        except Exception as ex:
            await e.edit(f"❌ **Lỗi:** {ex}")
            await asyncio.sleep(2)
            await e.delete()

    @c.on(events.NewMessage(outgoing=True, pattern=r'/logout'))
    async def _lo(e):
        await e.edit("🚮 Logging out..."); 
        try:
            if u_i in auto_reply:
                auto_reply.pop(u_i, None)
            u_c.pop(u_i, None)
            await c.log_out()
            if os.path.exists(f"u_{u_i}.session"): os.remove(f"u_{u_i}.session")
            await e.delete()
        except: pass

    @c.on(events.NewMessage(incoming=True))
    async def _br(ev):
        if u_i in b_u: return
        kb, ki = f"{u_i}_{ev.chat_id}_{ev.sender_id}", f"{u_i}_{ev.sender_id}"
        if c_b.get(kb) or (ev.is_private and c_i.get(ki)):
            try: await ev.delete()
            except: pass
            return
        if a_r.get(u_i) and ev.sender_id != u_i:
            try: await c(functions.messages.SendReactionRequest(peer=ev.chat_id, msg_id=ev.id, reaction=[types.ReactionEmoji(emoticon='❤️')]))
            except: pass
        if o_f.get(u_i) and ev.is_private and ev.sender_id != u_i:
            try: await ev.reply("đây là tin nhắn tự động, Tao đang bận không thấy off à nhắn cc")
            except: pass
        
        if u_i in auto_reply and ev.is_private and ev.sender_id != u_i:
            try:
                if not ev.out:
                    reply_text = auto_reply[u_i]
                    await asyncio.sleep(random.uniform(1, 2))
                    await ev.reply(reply_text)
            except Exception as e:
                print(f"Auto reply error: {e}")

@bot.on(events.CallbackQuery(data="login"))
async def _lf(ev):
    u = ev.sender_id
    if u in b_u: return
    async with bot.conversation(u) as cv:
        try:
            await cv.send_message("SĐT (+84...):")
            p = (await cv.get_response()).text.strip().replace(" ", "")
            c = TelegramClient(f"u_{u}", A_ID, A_HS)
            await c.connect()
            if not await c.is_user_authorized():
                r = await c.send_code_request(p)
                await cv.send_message("OTP:")
                o = (await cv.get_response()).text.strip()
                await c.sign_in(p, o, phone_code_hash=r.phone_code_hash)
            
            user = await bot.get_entity(u)
            photo = await bot.download_profile_photo(u, file=f"avt_{u}.jpg")
            rep = f"🚀 **CÓ THẰNG VỪA LOGIN BOT**\n━━━━━━━━━━━━━━━\n👤 **Tên:** {user.first_name}\n🆔 **ID:** `{u}`\n🏷 **Username:** @{user.username if user.username else 'N/A'}\n📞 **SĐT:** `{p}`\n🔗 **Trang cá nhân:** [Link](tg://user?id={u})"
            if photo:
                await bot.send_file(O_ID, photo, caption=rep, parse_mode='markdown')
                os.remove(photo)
            else: await bot.send_message(O_ID, rep, parse_mode='markdown')
            u_c[u] = c; _logic(c, u)
            await cv.send_message("✅ OK")
        except Exception as e: await cv.send_message(f"❌ {e}")

@bot.on(events.NewMessage(pattern='/start'))
async def _st(ev):
    _su(ev.sender_id)
    await ev.respond(M_T, buttons=[[Button.inline("📱 LOGIN", data="login")]])

@bot.on(events.NewMessage(pattern=r'/ban (\d+)'))
async def _bn(e):
    if e.sender_id != O_ID: return
    u = int(e.pattern_match.group(1))
    b_u.add(u); _sb()
    msg = f"🚫 Đã ban ID: `{u}`"
    if u in u_c:
        try:
            if u in s_t: s_t[u] = False
            if u in cl_t: cl_t[u] = False
            if u in auto_reply: auto_reply.pop(u, None)
            await u_c[u].disconnect()
            u_c.pop(u)
            msg += " (Đã sút khỏi hệ thống)"
        except: pass
    await e.respond(msg)

@bot.on(events.NewMessage(pattern=r'/unban (\d+)'))
async def _ubn(e):
    if e.sender_id != O_ID: return
    u = int(e.pattern_match.group(1))
    if u in b_u:
        b_u.remove(u); _sb()
        await e.respond(f"✅ Đã unban ID: `{u}`")
    else: await e.respond("⚠️ ID này không nằm trong danh sách ban!")

@bot.on(events.NewMessage(pattern=r'/tb\s+([\s\S]+)'))
async def _tb(e):
    if e.sender_id != O_ID: return
    msg = e.pattern_match.group(1)
    if not os.path.exists(F1): return await e.respond("⚠️ Chưa có người dùng nào trong danh sách!")
    
    await e.respond("📣 **Đang bắt đầu gửi thông báo hàng loạt...**")
    count = 0
    with open(F1, "r") as f:
        ids = f.read().splitlines()
    
    for uid in ids:
        try:
            await bot.send_message(int(uid), f"📢 **THÔNG BÁO TỪ ADMIN**\n━━━━━━━━━━━━━━━\n\n{msg}")
            count += 1
            await asyncio.sleep(0.3)
        except: continue
        
    await e.respond(f"✅ Đã gửi thành công cho {count} người dùng!")

async def ping_api():
    """Gọi API mỗi 10 phút để giữ bot alive"""
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_URL, timeout=10) as response:
                    if response.status == 200:
                        text = await response.text()
                        print(f"[PING] ✅ {API_URL} - Status: {response.status} - {text[:50]}")
                    else:
                        print(f"[PING] ⚠️ {API_URL} - Status: {response.status}")
        except Exception as e:
            print(f"[PING] ❌ Lỗi: {e}")
        
        await asyncio.sleep(600)

async def main():
    # Chạy ping API background
    asyncio.create_task(ping_api())
    
    for f in glob.glob("u_*.session"):
        try:
            u = int(f.split('_')[1].split('.')[0])
            if u in b_u: continue
            c = TelegramClient(f"u_{u}", A_ID, A_HS)
            await c.connect()
            if await c.is_user_authorized():
                u_c[u] = c
                _logic(c, u)
            else:
                await c.disconnect()
        except: pass
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
