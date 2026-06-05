"""咖啡手冲看板启动脚本 — 使用方法：python 启动看板.py"""
import os
import sys
import subprocess
import threading
import webbrowser
import time

os.environ["PYTHONUTF8"] = "1"

# 强制 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")

if (
    os.path.exists(VENV_PY)
    and os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(os.path.abspath(VENV_PY))
):
    os.execv(VENV_PY, [VENV_PY, __file__, *sys.argv[1:]])


def _cleanup_old_servers():
    """Stop stale dashboard servers so the browser never keeps seeing an old app."""
    if os.name != "nt":
        return
    current_pid = os.getpid()
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return

    pids = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        local_address, state, pid_text = parts[1], parts[3].upper(), parts[-1]
        if state != "LISTENING" or local_address.rsplit(":", 1)[-1] != "5000":
            continue
        try:
            pid = int(pid_text)
        except ValueError:
            continue
        if pid != current_pid:
            pids.add(pid)

    for pid in pids:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F", "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError):
            pass


def _wait_port_released(port: int, timeout: float = 3.0) -> None:
    """Give Windows a moment to release the port after killing stale servers."""
    if os.name != "nt":
        return
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=2,
            )
        except (OSError, subprocess.SubprocessError):
            return
        still_listening = False
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].upper() == "TCP":
                if parts[3].upper() == "LISTENING" and parts[1].rsplit(":", 1)[-1] == str(port):
                    still_listening = True
                    break
        if not still_listening:
            return
        time.sleep(0.2)


print()
print("  ☕  咖啡手冲看板启动中...")
print("  → 地址：http://127.0.0.1:5000")
print("  → 按 Ctrl+C 关闭")
print()

_cleanup_old_servers()
_wait_port_released(5000)

# 等服务就绪后自动打开浏览器（最多等 15 秒）
def _open_browser():
    import urllib.request
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            urllib.request.urlopen("http://127.0.0.1:5000/", timeout=1)
            break
        except Exception:
            time.sleep(0.3)
    webbrowser.open("http://127.0.0.1:5000")

threading.Thread(target=_open_browser, daemon=True).start()

try:
    from 网页应用 import app

    # Run Flask in this process. The old wrapper spawned a child process and
    # could treat console Ctrl+C propagation as a first-start shutdown.
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
except KeyboardInterrupt:
    print("\n  已停止")
