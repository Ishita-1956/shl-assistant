"""
Fetch the SHL product catalog JSON from the provided URL and save it locally.
"""
import requests
import json
import os

CATALOG_URL = "https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "catalog.json")


def fetch_catalog():
    print(f"Fetching catalog from {CATALOG_URL} ...")
    response = requests.get(CATALOG_URL, timeout=60)
    response.raise_for_status()

    data = response.json()
    print(f"Fetched {len(data)} products")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    fetch_catalog()