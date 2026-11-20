#!/usr/bin/env python3
"""
app.py — Master runner bản #0 (chạy SONG SONG ngay, không chờ)
- Quản lý file tài khoản riêng: ac.json
- Start 1.py + gen.py CÙNG LÚC
- Gen tự tắt khi count >= HIGH, tự bật lại khi count < LOW
- 1.py auto restart khi crash
"""
import asyncio
import json
import os
import signal
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

INSTANCE_ID = 0
AC_FILENAME = "ac.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AC_FILE = os.path.join(BASE_DIR, AC_FILENAME)

# ============ CONFIG ============
LOW_WATER = 200
HIGH_WATER = 500
MAX_ACCOUNTS = 2000
CHECK_INTERVAL = 15
RESTART_DELAY = 5
STOP_TIMEOUT = 10

BOT_SCRIPT = "1.py"
GEN_SCRIPT = "gen.py"


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[38;5;46m"
    RED = "\033[38;5;196m"
    YELLOW = "\033[38;5;226m"
    CYAN = "\033[38;5;51m"
    MAGENTA = "\033[38;5;201m"


class SubProcess:
    def __init__(self, name, script):
        self.name = name
        self.script = script
        self.proc = None
        self.stream_task = None

    @property
    def running(self):
        return self.proc is not None and self.proc.returncode is None

    async def start(self):
        if self.running:
            return
        env = os.environ.copy()
        env["NO_CLEAR"] = "1"
        env["TERM"] = "dumb"
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["INSTANCE_ID"] = str(INSTANCE_ID)
        env["AC_FILE"] = AC_FILENAME

        try:
            self.proc = await asyncio.create_subprocess_exec(
                sys.executable, "-u", self.script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=BASE_DIR,
                env=env,
            )
            print(f"{C.CYAN}[APP0]{C.RESET} {self.name} started (pid={self.proc.pid}, file={AC_FILENAME})",
                  flush=True)
            self.stream_task = asyncio.create_task(self._stream())
        except Exception as e:
            print(f"{C.RED}[APP0]{C.RESET} {self.name} start fail: {e}", flush=True)
            raise

    async def _stream(self):
        prefix = f"[{self.name.upper():5}]"
        try:
            async for line in self.proc.stdout:
                text = line.decode("utf-8", errors="replace").rstrip()
                text = text.replace("\x1b[H\x1b[2J", "").replace("\x1b[2J\x1b[H", "")
                if text.strip():
                    print(f"{prefix} {text}", flush=True)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def stop(self, timeout=STOP_TIMEOUT):
        if not self.running:
            return
        print(f"{C.CYAN}[APP0]{C.RESET} {self.name} stopping...", flush=True)
        try:
            self.proc.terminate()
            try:
                await asyncio.wait_for(self.proc.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                print(f"{C.YELLOW}[APP0]{C.RESET} {self.name} kill -9", flush=True)
                self.proc.kill()
                await self.proc.wait()
        except Exception:
            pass
        if self.stream_task:
            self.stream_task.cancel()
            try: await self.stream_task
            except: pass
        print(f"{C.CYAN}[APP0]{C.RESET} {self.name} stopped", flush=True)


async def count_accounts():
    try:
        with open(AC_FILE, "r", encoding="utf-8") as f:
            return len(json.load(f))
    except Exception:
        return 0


async def bot_runner(bot, stop_evt):
    """1.py auto-restart khi crash"""
    while not stop_evt.is_set():
        try:
            await bot.start()
            await bot.proc.wait()
            code = bot.proc.returncode
            print(f"{C.RED}[APP0]{C.RESET} 1.py exited (code={code}), "
                  f"restart {RESTART_DELAY}s", flush=True)
        except Exception as e:
            print(f"{C.RED}[APP0]{C.RESET} 1.py err: {e}", flush=True)
        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=RESTART_DELAY)
            return
        except asyncio.TimeoutError:
            pass


async def gen_controller(gen, stop_evt):
    """Start gen.py NGAY (nếu chưa đủ HIGH_WATER), sau đó check count để tắt/bật"""
    init_count = await count_accounts()
    if init_count < HIGH_WATER:
        print(f"{C.GREEN}[CTRL0]{C.RESET} start gen.py ngay (song song với 1.py)",
              flush=True)
        try:
            await gen.start()
        except Exception as e:
            print(f"{C.RED}[CTRL0]{C.RESET} gen start: {e}", flush=True)
    else:
        print(f"{C.CYAN}[CTRL0]{C.RESET} {AC_FILENAME} đã có {init_count}>={HIGH_WATER} acc → tạm nghỉ gen.py",
              flush=True)

    while not stop_evt.is_set():
        count = await count_accounts()

        # Hard limit
        if count >= MAX_ACCOUNTS and gen.running:
            print(f"{C.RED}[CTRL0]{C.RESET} {count}>={MAX_ACCOUNTS} → TẮT gen (hard)",
                  flush=True)
            await gen.stop()

        # Cao → tắt
        elif count >= HIGH_WATER and gen.running:
            print(f"{C.YELLOW}[CTRL0]{C.RESET} {count}>={HIGH_WATER} → TẮT gen",
                  flush=True)
            await gen.stop()

        # Thấp → bật lại
        elif count < LOW_WATER and not gen.running:
            print(f"{C.GREEN}[CTRL0]{C.RESET} {count}<{LOW_WATER} → BẬT lại gen",
                  flush=True)
            try:
                await gen.start()
            except Exception as e:
                print(f"{C.RED}[CTRL0]{C.RESET} gen start: {e}", flush=True)

        # Crash → reset
        elif gen.proc and gen.proc.returncode is not None:
            gen.proc = None

        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=CHECK_INTERVAL)
            return
        except asyncio.TimeoutError:
            pass


async def monitor(stop_evt):
    while not stop_evt.is_set():
        count = await count_accounts()
        print(f"{C.CYAN}[MON0]{C.RESET} {count} acc trong {AC_FILENAME} "
              f"(LOW={LOW_WATER} HIGH={HIGH_WATER} MAX={MAX_ACCOUNTS})", flush=True)
        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=60)
            return
        except asyncio.TimeoutError:
            pass


async def main():
    print(f"{C.MAGENTA}{'='*58}{C.RESET}")
    print(f"  {C.BOLD}APP RUNNER #0 (app.py){C.RESET} — 1.py + gen.py ({AC_FILENAME})")
    print(f"{C.MAGENTA}{'='*58}{C.RESET}")
    print(f"  LOW={LOW_WATER}  HIGH={HIGH_WATER}  MAX={MAX_ACCOUNTS}")
    print(f"  Check={CHECK_INTERVAL}s  Restart={RESTART_DELAY}s\n")

    for f in (BOT_SCRIPT, GEN_SCRIPT):
        if not os.path.exists(os.path.join(BASE_DIR, f)):
            print(f"{C.RED}[APP0]{C.RESET} thiếu file {f}", flush=True)
            return

    stop_evt = asyncio.Event()

    def on_signal():
        print(f"\n{C.YELLOW}[APP0]{C.RESET} shutdown signal", flush=True)
        stop_evt.set()

    try:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, on_signal)
        loop.add_signal_handler(signal.SIGTERM, on_signal)
    except Exception:
        pass

    bot = SubProcess("bot", BOT_SCRIPT)
    gen = SubProcess("gen", GEN_SCRIPT)

    tasks = [
        asyncio.create_task(bot_runner(bot, stop_evt)),
        asyncio.create_task(gen_controller(gen, stop_evt)),
        asyncio.create_task(monitor(stop_evt)),
    ]

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except KeyboardInterrupt:
        pass
    finally:
        stop_evt.set()
        await bot.stop()
        await gen.stop()
        print(f"\n{C.YELLOW}[APP0]{C.RESET} done", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}[CTRL+C]{C.RESET}")
