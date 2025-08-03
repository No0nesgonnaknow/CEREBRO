# file_watcher.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import subprocess
import os
import threading
from datetime import datetime

WATCH_PATH = r"D:\BOOK\BOOKS"
DEBOUNCE_DELAY = 10  # seconds to wait before retriggering parse
LAST_TRIGGER_TIME = 0

def log(msg, level="INFO"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {"INFO": "\033[94m", "WARN": "\033[93m", "ERROR": "\033[91m", "RESET": "\033[0m"}
    print(f"{colors.get(level, '')}[{now}] [{level}] {msg}{colors['RESET']}")

class BookChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        global LAST_TRIGGER_TIME

        if event.is_directory:
            return

        current_time = time.time()
        if current_time - LAST_TRIGGER_TIME < DEBOUNCE_DELAY:
            log(f"Change detected, but within debounce window. Ignoring: {event.src_path}", "WARN")
            return

        log(f"📚 Change detected: {event.src_path}", "INFO")
        LAST_TRIGGER_TIME = current_time

        # Use a thread to run parser in background
        threading.Thread(target=self.run_parser).start()

    def run_parser(self):
        try:
            log("🔄 Running parser to update Cerebro memory...")
            result = subprocess.run(["python", "backend/parser.py"], capture_output=True, text=True)
            if result.returncode == 0:
                log("✅ Parser executed successfully.")
            else:
                log(f"❌ Parser error:\n{result.stderr}", "ERROR")
        except Exception as e:
            log(f"❗ Exception while running parser: {str(e)}", "ERROR")

if __name__ == "__main__":
    log(f"👁️ Watching for file changes in: {WATCH_PATH}", "INFO")

    if not os.path.exists(WATCH_PATH):
        log(f"Path not found: {WATCH_PATH}", "ERROR")
        exit(1)

    observer = Observer()
    event_handler = BookChangeHandler()
    observer.schedule(event_handler, WATCH_PATH, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        log("🛑 Stopping watcher due to keyboard interrupt.", "WARN")
    observer.join()
