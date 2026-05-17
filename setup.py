"""
One-step setup: fetches catalog JSON, builds ChromaDB index, verifies everything.
Run: python setup.py
"""
import json
import os
import sys
import shutil
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

CATALOG_URL = "https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json"
CATALOG_PATH = os.path.join(SCRIPT_DIR, "app", "catalog.json")
VECTORSTORE_PATH = os.path.join(SCRIPT_DIR, "vectorstore")

KEY_TO_CODE = {
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Ability & Aptitude": "A",
    "Biodata & Situational Judgment": "B",
    "Simulations": "S",
    "Competencies": "C",
    "Development & 360": "D",
    "Assessment Exercises": "E",
}


def step1_fetch_catalog():
    print(f"\n[1/3] Fetching catalog from {CATALOG_URL} ...")

    req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw_bytes = resp.read()

    raw_text = raw_bytes.decode("utf-8-sig").strip()

    # Use strict=False to allow control characters inside JSON strings
    data = json.loads(raw_text, strict=False)

    print(f"      Fetched {len(data)} products")

    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"      Saved to {CATALOG_PATH}")
    return data


def step2_build_index(data):
    from sentence_transformers import SentenceTransformer
    import chromadb

    print(f"\n[2/3] Building vector index ...")

    if os.path.exists(VECTORSTORE_PATH):
        shutil.rmtree(VECTORSTORE_PATH)

    model = SentenceTransformer("all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=VECTORSTORE_PATH)
    collection = client.get_or_create_collection(
        name="shl_catalog",
        metadata={"hnsw:space": "cosine"}
    )

    batch_size = 50
    total = len(data)

    for batch_start in range(0, total, batch_size):
        batch = data[batch_start:batch_start + batch_size]
        ids, documents, metadatas = [], [], []

        for idx, item in enumerate(batch):
            global_idx = batch_start + idx
            keys = item.get("keys", [])
            job_levels = item.get("job_levels", [])
            languages = item.get("languages", [])

            test_type_codes = []
            for k in keys:
                code = KEY_TO_CODE.get(k, "")
                if code and code not in test_type_codes:
                    test_type_codes.append(code)
            test_type = ",".join(test_type_codes) if test_type_codes else "K"

            text = f"Name: {item.get('name', '')}\nDescription: {item.get('description', '')}\nKeys: {', '.join(keys)}\nJob Levels: {', '.join(job_levels)}\nDuration: {item.get('duration', '')}"

            meta = {
                "name": item.get("name", ""),
                "url": item.get("link", ""),
                "entity_id": str(item.get("entity_id", "")),
                "test_type": test_type,
                "keys": ", ".join(keys),
                "duration": item.get("duration", "") or "",
                "languages": ", ".join(languages[:5]) if languages else "",
                "languages_count": len(languages),
                "languages_full": ", ".join(languages),
                "job_levels": ", ".join(job_levels),
                "description": (item.get("description", "") or "")[:500],
                "remote": item.get("remote", "") or "",
                "adaptive": item.get("adaptive", "") or "",
            }

            ids.append(str(global_idx))
            documents.append(text)
            metadatas.append(meta)

        embeddings = model.encode(documents).tolist()
        collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        print(f"      Indexed {batch_start + len(batch)}/{total}")

    print(f"      Vector database ready ({total} items)")


def step3_verify():
    print(f"\n[3/3] Verifying ...")
    import chromadb
    client = chromadb.PersistentClient(path=VECTORSTORE_PATH)
    collection = client.get_collection("shl_catalog")
    count = collection.count()
    print(f"      ChromaDB collection 'shl_catalog' has {count} items")
    assert count > 0, "Vector store is empty!"
    print(f"      All good!")


if __name__ == "__main__":
    print("=" * 50)
    print("SHL Assessment Assistant - Setup")
    print("=" * 50)

    data = step1_fetch_catalog()
    step2_build_index(data)
    step3_verify()

    print(f"\n{'=' * 50}")
    print("Setup complete! Start the server with:")
    print("  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print("=" * 50)
