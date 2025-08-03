import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from collections import defaultdict
from tqdm import tqdm

# === Configuration ===
MEMORY_DIR = r"D:\.COUNCIL\Cerebro\memory"
DATA_DIR = r"D:\.COUNCIL\Cerebro\data"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
TOP_K = 5
EMBED_CACHE = os.path.join(MEMORY_DIR, "embeddings_cache.json")

# === Initialize embedding model ===
print(f"[⚙] Loading semantic model: {EMBEDDING_MODEL}")
model = SentenceTransformer(EMBEDDING_MODEL)
model.encode(["warmup"])  # Warm-up inference

# === Corpus loader ===
def load_corpus():
    corpus, metadata_list = [], []

    print(f"[📚] Loading corpus from: {DATA_DIR}")
    for file in os.listdir(DATA_DIR):
        if file.endswith(".txt"):
            txt_path = os.path.join(DATA_DIR, file)
            meta_path = txt_path.replace(".txt", ".json")

            if not os.path.exists(meta_path):
                continue

            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    text = f.read().strip()

                with open(meta_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                corpus.append(text)
                metadata_list.append(metadata)

            except Exception as e:
                print(f"[✘] Failed to load: {file} — {e}")
    
    print(f"[✔] Loaded {len(corpus)} documents.")
    return corpus, metadata_list

# === Build FAISS index from scratch ===
def build_embedding_index(texts):
    print("[⚙] Embedding texts for semantic search...")
    embeddings = model.encode(texts, convert_to_numpy=True)
    index = faiss.IndexFlatL2(EMBEDDING_DIM)
    index.add(embeddings)
    return index, embeddings

# === Save cached embeddings ===
def save_embedding_cache(embeddings, metadata_list):
    try:
        print("[💾] Caching embedding index...")
        cache = {
            "embeddings": embeddings.tolist(),
            "metadata": metadata_list
        }
        with open(EMBED_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[✘] Failed to save embedding cache: {e}")

# === Load cached embeddings if available ===
def load_embedding_cache():
    if not os.path.exists(EMBED_CACHE):
        return None, None

    try:
        with open(EMBED_CACHE, "r", encoding="utf-8") as f:
            cache = json.load(f)
        embeddings = np.array(cache["embeddings"])
        metadata = cache["metadata"]
        index = faiss.IndexFlatL2(EMBEDDING_DIM)
        index.add(embeddings)
        return index, metadata
    except Exception as e:
        print(f"[✘] Failed to load embedding cache: {e}")
        return None, None

# === Semantic Query Router ===
def route_query_semantically(query, top_k=TOP_K):
    query_embedding = model.encode([query])[0].astype("float32")

    index, metadata = load_embedding_cache()
    if index is None or metadata is None:
        print("[⏳] No cache or failed load — rebuilding index...")
        texts, metadata = load_corpus()
        index, embeddings = build_embedding_index(texts)
        save_embedding_cache(embeddings, metadata)

    # Perform semantic search
    D, I = index.search(np.array([query_embedding]), top_k)

    results = []
    for i, idx in enumerate(I[0]):
        if idx >= len(metadata):
            continue
        meta = metadata[idx]

        domain = meta.get("domain", "GENERAL")
        filename = meta.get("filename", "unknown")
        language = meta.get("language", "unknown")

        txt_file = f"{domain}__{filename}__{language}.txt"
        txt_path = os.path.join(DATA_DIR, txt_file)

        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                context = f.read().strip()

            results.append({
                "domain": domain,
                "tags": meta.get("tags", []),
                "source_file": filename,
                "path": txt_path,
                "context": context[:2000],  # truncate if needed
                "score": round(float(D[0][i]), 4)
            })

        except Exception as e:
            print(f"[✘] Failed to load context for {txt_path} — {e}")

    return results

# === Synthesized response payload ===
def synthesize_routing_result(query):
    results = route_query_semantically(query)

    domain_counter = defaultdict(int)
    tag_counter = defaultdict(int)
    sources = []
    context_chunks = []

    for res in results:
        domain_counter[res["domain"]] += 1
        for tag in res["tags"]:
            tag_counter[tag] += 1
        sources.append(res["source_file"])
        context_chunks.append(res["context"])

    return {
        "query": query,
        "domain_distribution": dict(domain_counter),
        "tags": dict(tag_counter),
        "sources": sources,
        "context": "\n\n---\n\n".join(context_chunks)
    }

# === Optional CLI Runner ===
if __name__ == "__main__":
    print("🧠 Cerebro Semantic Router (CLI Mode)")
    while True:
        q = input("Query ('exit' to quit): ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        out = synthesize_routing_result(q)
        print("\n🧠 Synthesized Context:\n")
        print(out["context"])
        print("\n--- Domains:", out["domain_distribution"])
        print("--- Tags:", out["tags"])
        print("--- Sources:", out["sources"])
