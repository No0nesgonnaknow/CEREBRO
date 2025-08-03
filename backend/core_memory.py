import os
import json
import faiss
import pickle
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# === CONFIGURATION ===
DATA_DIR = r"D:\.COUNCIL\Cerebro\data"
MEMORY_DIR = r"D:\.COUNCIL\Cerebro\memory"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# === INITIALIZE DIRECTORIES ===
os.makedirs(MEMORY_DIR, exist_ok=True)

# === LOAD EMBEDDING MODEL ===
print(f"[⚙] Loading embedding model: {EMBEDDING_MODEL_NAME}")
embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

# Warm-up call (optional but recommended for speed)
embedder.encode(["Warm up complete."])

faiss_index = faiss.IndexFlatL2(EMBEDDING_DIM)
memory_entries = []

# === TEXT CHUNKING FUNCTION ===
def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    for i in range(0, len(words), size - overlap):
        chunk = ' '.join(words[i:i + size])
        if len(chunk.split()) >= 50:  # Filter out tiny segments
            chunks.append(chunk)
    return chunks

# === LOAD METADATA FILE (.json) ===
def load_metadata(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[✘] Failed to load metadata: {json_path} — {e}")
        return {}

# === MAIN INDEXING LOOP ===
txt_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith(".txt")])
print(f"[🧠] Indexing {len(txt_files)} text files from: {DATA_DIR}")

for txt_file in tqdm(txt_files):
    base_name = os.path.splitext(txt_file)[0]
    txt_path = os.path.join(DATA_DIR, txt_file)
    json_path = os.path.join(DATA_DIR, f"{base_name}.json")

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        
        if not raw_text.strip():
            print(f"[!] Skipped empty file: {txt_file}")
            continue

        chunks = chunk_text(raw_text)
        if not chunks:
            print(f"[!] Skipped (no valid chunks): {txt_file}")
            continue

        embeddings = embedder.encode(chunks)

        for i, emb in enumerate(embeddings):
            memory_entries.append({
                "chunk_id": f"{base_name}_chunk{i}",
                "text": chunks[i],
                "filename": base_name,
                "domain": base_name.split("__")[0] if "__" in base_name else "GENERAL",
                "metadata": load_metadata(json_path)
            })

        faiss_index.add(embeddings)

    except Exception as e:
        print(f"[✘] Failed to index: {txt_file} — {e}")

# === SAVE INDEX & MEMORY FILES ===
print(f"[💾] Saving FAISS index and memory files to: {MEMORY_DIR}")

# Save FAISS Index
faiss.write_index(faiss_index, os.path.join(MEMORY_DIR, "cerebro_faiss.index"))

# Save JSONL
jsonl_path = os.path.join(MEMORY_DIR, "cerebro_memory.jsonl")
with open(jsonl_path, "w", encoding="utf-8") as f:
    for entry in memory_entries:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# Save Pickle
with open(os.path.join(MEMORY_DIR, "cerebro_memory.pkl"), "wb") as f:
    pickle.dump(memory_entries, f)

# Save Router-Compatible Metadata JSON
metadata_for_router = []
for entry in memory_entries:
    metadata_for_router.append({
        "domain": entry["domain"],
        "filename": entry["filename"],
        "text": entry["text"]
    })

with open(os.path.join(MEMORY_DIR, "cerebro_metadata.json"), "w", encoding="utf-8") as f:
    json.dump(metadata_for_router, f, indent=2, ensure_ascii=False)

print(f"[✔] Indexed {len(memory_entries)} chunks from {len(txt_files)} files.")
