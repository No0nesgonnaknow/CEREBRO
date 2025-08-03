from flask import Flask, request, jsonify
from gpt4all import GPT4All
from router import route_query
from parser import auto_rescan_on_start
from datetime import datetime
import subprocess
import traceback
import json
import os
import time
import re

# === CONFIGURATION ===
MODEL_PATH = r"D:\GPT4ALL\DATA\qwen2-1_5b-instruct-q4_0.gguf"
MAX_TOKENS = 4096
TEMPERATURE = 0.2
CONTEXT_LIMIT = 16000
LOG_FILE = "logs/query_log.jsonl"
DEBUG_MODE = True
RESCAN_INTERVAL_HOURS = 12  # Auto folder scan every 12 hours

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data")
MEMORY_PATH = os.path.join(os.path.dirname(__file__), "..", "memory", "cerebro_faiss.index")

# === BOOTSTRAP CHECK: Parse & Index if needed ===
def bootstrap_if_needed():
    os.makedirs(DATA_PATH, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    txt_files = [f for f in os.listdir(DATA_PATH) if f.endswith(".txt")]
    faiss_exists = os.path.exists(MEMORY_PATH)

    if not txt_files:
        print("[⏳] No .txt files found in data/. Running parser.py...")
        subprocess.run(["python", "backend/parser.py"], check=True)
    else:
        print("[✔] Found .txt files in data/. Skipping parser.")

    if not faiss_exists:
        print("[⏳] FAISS index not found. Running core_memory.py...")
        subprocess.run(["python", "backend/core_memory.py"], check=True)
    else:
        print("[✔] FAISS index found. Skipping core_memory.")

# === CALL BOOTSTRAP ===
bootstrap_if_needed()

# === Initialize Flask ===
app = Flask(__name__)

# === Load Model ===
print(f"[⚙] Loading local model: {MODEL_PATH}")
model = GPT4All(MODEL_PATH)
model.generate("Hello", max_tokens=5)  # Warm-up pass
print("[✔] Model warm-up complete.")

# === Launch background auto-folder scanner ===
auto_rescan_on_start(interval_hours=RESCAN_INTERVAL_HOURS)

# === Supported Commands ===
COMMAND_INSTRUCTIONS = {
    "analyze": "Perform a rigorous analytical breakdown. Prioritize logic, facts, and structured reasoning.",
    "summarize": "Synthesize a precise, conceptual summary faithful to the source context.",
    "philosophize": "Explore deeper meanings through epistemic, ontological, and existential analysis.",
    "compare": "Systematically compare perspectives or cases. Emphasize contrast, nuance, and implications.",
    "decolonize": "Interrogate through a decolonial lens, questioning dominant narratives and power structures.",
    "reflect": "Engage in deep, introspective, strategic synthesis of all context. Simulate sovereign reflection, integrate across domains.",
    "default": "Analyze with a sovereign, strategic mind. Prioritize coherence, logic, and evidence-based reasoning."
}

# === Utility: Logging ===
def log_interaction(data):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

# === Utility: Extract Command + Clean Query ===
def extract_command_and_query(raw):
    match = re.match(r"/(\w+)\s+(.*)", raw)
    if match:
        mode, query = match.groups()
        instruction = COMMAND_INSTRUCTIONS.get(mode.lower(), COMMAND_INSTRUCTIONS["default"])
        return mode.lower(), query, instruction
    return "default", raw, COMMAND_INSTRUCTIONS["default"]

# === Endpoint: Ask Cerebro ===
@app.route("/ask", methods=["POST"])
def ask():
    try:
        user_query = request.json.get("query", "").strip()
        if not user_query:
            return jsonify({"error": "Query cannot be empty."}), 400

        mode, clean_query, instruction = extract_command_and_query(user_query)
        print(f"[🧠] Received query in mode: {mode}")

        routed = route_query(clean_query)
        context = routed.get("context", "")[:CONTEXT_LIMIT]
        domain = routed.get("domain", "GENERAL")
        sources = routed.get("sources", [])

        # === Construct Prompt ===
        prompt = f"""
You are Cerebro — a sovereign, epistemically disciplined thinking engine rooted in the user’s unique intellectual fingerprint.
Avoid hallucination or speculation. Only use the provided context. Do not fabricate information.
Respond in a structured, coherent, and intellectually rigorous manner.

--- DOMAIN: {domain} ---
--- MODE: {mode} ---
--- SOURCES ---
{chr(10).join([f"[{i+1}] {s}" for i, s in enumerate(sources)])}

--- CONTEXT ---
{context}

--- QUERY ---
{clean_query}

--- INSTRUCTION ---
{instruction}

--- RESPONSE ---
"""

        # === Model Inference ===
        start_time = time.time()
        output = model.generate(prompt, max_tokens=MAX_TOKENS, temp=TEMPERATURE).strip()
        duration = round(time.time() - start_time, 2)

        response_payload = {
            "response": output,
            "mode": mode,
            "domain_used": domain,
            "sources_used": sources,
            "timestamp": datetime.now().isoformat(),
            "query": clean_query,
            "duration_secs": duration
        }

        log_interaction(response_payload)
        print(f"[✔] Responded in {duration}s using domain: {domain}")
        return jsonify(response_payload)

    except Exception as e:
        print("[✘] Internal error:", traceback.format_exc())
        return jsonify({
            "error": "Internal server error.",
            "details": str(e) if DEBUG_MODE else "An error occurred."
        }), 500

# === Health Check ===
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "status": "Cerebro is running",
        "model": os.path.basename(MODEL_PATH),
        "auto_rescan_interval_hours": RESCAN_INTERVAL_HOURS
    })

# === Run App ===
if __name__ == "__main__":
    app.run(port=5000, debug=DEBUG_MODE)
