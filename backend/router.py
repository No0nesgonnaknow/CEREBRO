import os
import faiss
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict

# === CONFIGURATION ===
MEMORY_DIR = r"D:\.COUNCIL\Cerebro\memory"
INDEX_PATH = os.path.join(MEMORY_DIR, "cerebro.faiss")
METADATA_PATH = os.path.join(MEMORY_DIR, "cerebro_metadata.json")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# === LOAD COMPONENTS ===
print("[⚙] Loading semantic model and FAISS index...")
try:
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    model.encode(["warmup"])  # Warm-up to avoid cold-start lag
except Exception as e:
    raise RuntimeError(f"[✘] Failed to load embedding model: {e}")

if not os.path.exists(INDEX_PATH):
    raise FileNotFoundError(f"[✘] FAISS index file not found at: {INDEX_PATH}")

if not os.path.exists(METADATA_PATH):
    raise FileNotFoundError(f"[✘] Metadata file not found at: {METADATA_PATH}")

index = faiss.read_index(INDEX_PATH)

with open(METADATA_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

# === QUERY ROUTING ===
def route_query(query: str, top_k: int = 5) -> Dict:
    query_vec = model.encode([query])
    query_vec = np.array(query_vec).astype("float32")

    distances, indices = index.search(query_vec, top_k)
    indices = indices[0]
    distances = distances[0]

    context_chunks = []
    source_files = []
    domain_scores = {}

    for i, idx in enumerate(indices):
        if idx >= len(metadata):
            continue
        meta = metadata[idx]
        domain = meta["domain"]
        file = meta["filename"]
        chunk_text = meta["text"]

        context_chunks.append(chunk_text.strip())
        source_files.append(f"{file} [{domain}]")
        domain_scores[domain] = domain_scores.get(domain, 0) + 1

    combined_context = "\n\n---\n\n".join(context_chunks)
    sorted_domain_scores = dict(sorted(domain_scores.items(), key=lambda x: -x[1]))
    top_domain = next(iter(sorted_domain_scores), "GENERAL")

    return {
        "context": combined_context.strip(),
        "domain": top_domain,
        "sources": source_files,
        "score": sorted_domain_scores.get(top_domain, 0),
        "all_scores": sorted_domain_scores
    }
