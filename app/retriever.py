"""
Vector-based retrieval from ChromaDB for SHL product catalog.
Falls back to keyword search on catalog.json if vectorstore is unavailable.
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
VECTORSTORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vectorstore")
CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "catalog.json")

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

# Lazy-loaded globals
_model = None
_collection = None
_vectorstore_available = None


def _init():
    global _model, _collection, _vectorstore_available
    if _vectorstore_available is not None:
        return  # Already initialized

    try:
        from sentence_transformers import SentenceTransformer
        import chromadb

        _model = SentenceTransformer(MODEL_NAME)
        client = chromadb.PersistentClient(path=VECTORSTORE_PATH)
        _collection = client.get_collection("shl_catalog")
        count = _collection.count()
        if count == 0:
            raise ValueError("Collection is empty")
        _vectorstore_available = True
        logger.info(f"ChromaDB vectorstore loaded with {count} items")
    except Exception as e:
        logger.warning(f"ChromaDB unavailable ({e}), falling back to keyword search")
        _vectorstore_available = False


def _format_languages(languages_full: str) -> str:
    """Format languages for display."""
    if not languages_full:
        return ""
    languages_list = [l.strip() for l in languages_full.split(",") if l.strip()]
    count = len(languages_list)
    if count > 4:
        return ", ".join(languages_list[:4]) + f" _(+{count - 4} more)_"
    return ", ".join(languages_list) if languages_list else ""


def _keyword_search(query: str, top_k: int = 15) -> list:
    """Fallback keyword search on catalog.json."""
    if not os.path.exists(CATALOG_PATH):
        logger.error(f"catalog.json not found at {CATALOG_PATH}")
        return []

    # Check if file is empty
    if os.path.getsize(CATALOG_PATH) < 10:
        logger.error(f"catalog.json is empty. Run 'python setup.py' first.")
        return []

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    query_lower = query.lower()
    query_words = set(query_lower.split())

    scored = []
    for item in data:
        name = (item.get("name", "") or "").lower()
        desc = (item.get("description", "") or "").lower()
        keys_str = " ".join(item.get("keys", [])).lower()
        job_levels_str = " ".join(item.get("job_levels", [])).lower()
        combined = f"{name} {desc} {keys_str} {job_levels_str}"

        score = 0
        for word in query_words:
            if len(word) < 3:
                continue
            if word in name:
                score += 3
            if word in desc:
                score += 1
            if word in keys_str:
                score += 2
            if word in job_levels_str:
                score += 1

        if score > 0:
            keys = item.get("keys", [])
            languages = item.get("languages", [])
            test_type_codes = []
            for k in keys:
                code = KEY_TO_CODE.get(k, "")
                if code and code not in test_type_codes:
                    test_type_codes.append(code)

            scored.append((score, {
                "name": item.get("name", ""),
                "url": item.get("link", ""),
                "test_type": ",".join(test_type_codes) if test_type_codes else "K",
                "keys": ", ".join(keys),
                "duration": item.get("duration", "") or "",
                "languages": _format_languages(", ".join(languages)),
                "languages_full": ", ".join(languages),
                "job_levels": ", ".join(item.get("job_levels", [])),
                "description": (item.get("description", "") or "")[:500],
                "remote": item.get("remote", "") or "",
                "adaptive": item.get("adaptive", "") or "",
                "entity_id": str(item.get("entity_id", "")),
            }))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]


def search_assessments(query: str, top_k: int = 15) -> list:
    """
    Search for assessments matching the query.
    Uses ChromaDB vector search if available, falls back to keyword search.
    """
    _init()

    if _vectorstore_available and _collection is not None and _model is not None:
        try:
            embedding = _model.encode(query).tolist()
            results = _collection.query(
                query_embeddings=[embedding],
                n_results=top_k
            )

            recommendations = []
            metadatas = results.get("metadatas", [[]])[0]

            for item in metadatas:
                rec = {
                    "name": item.get("name", ""),
                    "url": item.get("url", ""),
                    "test_type": item.get("test_type", "K"),
                    "keys": item.get("keys", ""),
                    "duration": item.get("duration", "") or "",
                    "languages": _format_languages(item.get("languages_full", "")),
                    "languages_full": item.get("languages_full", ""),
                    "job_levels": item.get("job_levels", ""),
                    "description": item.get("description", ""),
                    "remote": item.get("remote", ""),
                    "adaptive": item.get("adaptive", ""),
                    "entity_id": item.get("entity_id", ""),
                }
                recommendations.append(rec)

            return recommendations
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}, falling back to keyword search")

    # Fallback
    return _keyword_search(query, top_k)