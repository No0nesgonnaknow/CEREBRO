import subprocess
import time
import os
import sys

# === CONFIGURATION ===
MODULES_IN_ORDER = [
    "parser.py",
    "core_memory.py",
    "meta_router.py",
    "file_watcher.py",  # optional to launch auto-watcher
    "app.py"            # Flask backend server
]

PYTHON_EXECUTABLE = sys.executable
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))  # FIXED HERE
LOG_DIR = os.path.join(os.path.dirname(BACKEND_DIR), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def run_module(module_filename, background=False):
    abs_module_path = os.path.join(BACKEND_DIR, module_filename)
    print(f"\n[🔧] Running: backend/{module_filename}")

    if not os.path.exists(abs_module_path):
        print(f"[✘] File not found: {abs_module_path}")
        sys.exit(1)

    try:
        if background:
            subprocess.Popen(
                [PYTHON_EXECUTABLE, abs_module_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"[✔] Background process started: backend/{module_filename}")
        else:
            subprocess.run(
                [PYTHON_EXECUTABLE, abs_module_path],
                check=True
            )
            print(f"[✔] Completed: backend/{module_filename}")
    except subprocess.CalledProcessError as e:
        print(f"[✘] Error in backend/{module_filename}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("\n=== 🧠 Booting CEREBRO v1 ===\n")

    for module in MODULES_IN_ORDER:
        if "file_watcher" in module or "app" in module:
            run_module(module, background=True)
            time.sleep(2)  # Allow startup buffer
        else:
            run_module(module)

    print("\n[✅] Cerebro is fully launched. Flask server is listening at http://localhost:5000")
    print("[👁️] File watcher is monitoring for changes in BOOKS/...") 
    print("[🧠] Query engine ready.\n")
 