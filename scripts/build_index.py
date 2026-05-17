"""
Build the ChromaDB vector index from the SHL product catalog.
Embeds name + description + keys + job_levels for semantic search.
Stores all fields as metadata for retrieval.
"""
import json
import os
import shutil
import chromadb
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
VECTORSTORE_PATH = os.path.join(os.path.dirname(__file__), "..", "vectorstore")
CATALOG_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "catalog.json")

# Key mapping for test_type codes
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


def build_index():
    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    # Clear existing vectorstore
    if os.path.exists(VECTORSTORE_PATH):
        shutil.rmtree(VECTORSTORE_PATH)
        print("Cleared existing vectorstore")

    client = chromadb.PersistentClient(path=VECTORSTORE_PATH)
    collection = client.get_or_create_collection(
        name="shl_catalog",
        metadata={"hnsw:space": "cosine"}
    )

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Indexing {len(data)} products ...")

    batch_size = 100
    for batch_start in range(0, len(data), batch_size):
        batch = data[batch_start:batch_start + batch_size]

        ids = []
        documents = []
        metadatas = []

        for idx, item in enumerate(batch):
            global_idx = batch_start + idx

            keys = item.get("keys", [])
            job_levels = item.get("job_levels", [])
            languages = item.get("languages", [])

            # Build test_type code string
            test_type_codes = []
            for k in keys:
                code = KEY_TO_CODE.get(k, "")
                if code and code not in test_type_codes:
                    test_type_codes.append(code)
            test_type = ",".join(test_type_codes) if test_type_codes else "K"

            # Build rich embedding text
            text = f"""
Name: {item.get('name', '')}
Description: {item.get('description', '')}
Keys: {', '.join(keys)}
Job Levels: {', '.join(job_levels)}
Duration: {item.get('duration', '')}
Remote: {item.get('remote', '')}
Adaptive: {item.get('adaptive', '')}
""".strip()

            # ChromaDB metadata must be str/int/float/bool
            meta = {
                "name": item.get("name", ""),
                "url": item.get("link", ""),
                "entity_id": item.get("entity_id", ""),
                "test_type": test_type,
                "keys": ", ".join(keys),
                "duration": item.get("duration", ""),
                "languages": ", ".join(languages[:5]) if languages else "",
                "languages_count": len(languages),
                "languages_full": ", ".join(languages),
                "job_levels": ", ".join(job_levels),
                "description": item.get("description", "")[:500],
                "remote": item.get("remote", ""),
                "adaptive": item.get("adaptive", ""),
            }

            ids.append(str(global_idx))
            documents.append(text)
            metadatas.append(meta)

        embeddings = model.encode(documents).tolist()

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        print(f"  Indexed batch {batch_start} - {batch_start + len(batch)}")

    print(f"\nVector database built successfully with {len(data)} items")


if __name__ == "__main__":
    build_index()