# run_cerebro.py

import subprocess
import os
import time
import sys
import webbrowser
from datetime import datetime

# 🗂️ CONFIG
CWD = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(CWD, ".venv", "Scripts", "python.exe")  # Windows only
APP_PATH = os.path.join(CWD, "backend", "app.py")
DATA_PATH = os.path.join(CWD, "data")
MEMORY_INDEX_PATH = os.path.join(CWD, "memory", "cerebro_faiss.index")
WATCHER_PATH = os.path.join(CWD, "file_watcher.py")

# 🕰️ Timestamped logger
def log(msg, level="INFO"):
    print(f"[{datetime.now().strftime('%H:%M:%S')}][{level}] {msg}")

# ✅ Virtual environment checker
def check_venv():
    if not os.path.exists(VENV_PYTHON):
        log("Virtual environment not found. Please set it up manually in `.venv`.", "ERROR")
        return False
    return True

# 🧠 Check for memory/data and trigger bootstrap if needed
def check_and_bootstrap():
    missing_txt = True
    missing_faiss = not os.path.exists(MEMORY_INDEX_PATH)

    if os.path.exists(DATA_PATH):
        txt_files = [f for f in os.listdir(DATA_PATH) if f.endswith(".txt")]
        missing_txt = len(txt_files) == 0
    else:
        log(f"'data/' folder not found. Please create it and add your source files.", "WARN")
        return

    if missing_txt or missing_faiss:
        log("Bootstrapping parser and memory index...", "BOOT")
        subprocess.call([VENV_PYTHON, APP_PATH])
    else:
        log("Memory and data already present. Skipping bootstrap.")

# 🚀 Launch backend server
def launch_backend():
    log("Launching Cerebro backend at http://localhost:5000 ...", "LAUNCH")
    subprocess.Popen([VENV_PYTHON, APP_PATH])
    time.sleep(2)

# 👁️ Launch real-time file watcher
def launch_watcher():
    if os.path.exists(WATCHER_PATH):
        log("Activating file system monitor for real-time parsing...", "WATCH")
        subprocess.Popen([VENV_PYTHON, WATCHER_PATH])
    else:
        log("file_watcher.py not found. Skipping real-time file monitor.", "WARN")

# 🌐 Open UI in browser
def open_browser():
    try:
        log("Opening Cerebro interface in your browser...", "BROWSER")
        webbrowser.open("http://localhost:5000")
    except Exception:
        log("Could not open browser. Visit manually: http://localhost:5000", "ERROR")

# 🧭 Entry point
def main():
    print("========================================")
    print("     🧠  CEREBRO LAUNCHER v1.1          ")
    print("     A Sovereign Thought Engine         ")
    print("========================================\n")

    if not check_venv():
        log("Aborting launch due to missing virtual environment.", "FATAL")
        return

    check_and_bootstrap()
    launch_backend()
    launch_watcher()
    open_browser()

if __name__ == "__main__":
    main()
