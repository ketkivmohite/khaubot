"""
KhauBot NLP Pipeline
====================
Phase 1: Rule-based keyword extraction (works right now, no GPU needed)
Phase 3: Multilingual sentence-transformers semantic search

This file is the brain of KhauBot.
"""

import os
import re
from functools import lru_cache
from langdetect import detect

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

# ─── Keyword maps ─────────────────────────────────────────────────────────────

MUMBAI_AREAS = [
    "bandra", "andheri", "juhu", "colaba", "dadar", "kurla",
    "borivali", "malad", "goregaon", "powai", "thane", "worli",
    "lower parel", "matunga", "sion", "chembur", "mulund"
]

CUISINE_KEYWORDS = {
    "vada pav": "vada pav", "vadapav": "vada pav", "wada pao": "vada pav",
    "biryani": "biryani", "biriyani": "biryani",
    "pav bhaji": "pav bhaji", "pavbhaji": "pav bhaji",
    "chai": "chai", "tea": "chai", "tapri": "chai", "tapree": "chai", "tapri chai": "chai",
    "chai tapri": "chai", "tea stall": "chai", "cutting chai": "chai", "adrak chai": "chai",
    "chaha": "chai", "chay": "chai",
    "coffee": "coffee",
    "pizza": "pizza",
    "burger": "burger",
    "chinese": "chinese", "hakka": "chinese",
    "north indian": "north indian", "punjabi": "north indian",
    "south indian": "south indian", "idli": "south indian", "dosa": "south indian",
    "seafood": "seafood", "fish": "seafood",
    "street food": "street food",
    "snacks": "snacks", "chaat": "chaat",
}

CATEGORY_KEYWORDS = {
    "street_stall": ["stall", "khau galli", "khaugalli", "galli", "street", "thela", "cart"],
    "cafe": ["cafe", "coffee shop", "study", "aesthetic", "cozy", "chill", "work"],
    "cloud_kitchen": ["cloud kitchen", "delivery", "home delivery", "ghar", "order online", "whatsapp"],
}

PRICE_PATTERNS = [
    r"under\s*[₹rs\.]*\s*(\d+)",
    r"below\s*[₹rs\.]*\s*(\d+)",
    r"less than\s*[₹rs\.]*\s*(\d+)",
    r"[₹rs\.]+\s*(\d+)\s*se kam",   # Hindi: ₹100 se kam
    r"(\d+)\s*rupees\s*se kam",
]

SEMANTIC_MODEL_NAME = os.getenv(
    "SEMANTIC_MODEL_NAME",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)


@lru_cache(maxsize=1)
def get_semantic_model():
    """
    Lazy-load multilingual embedding model once per process.
    Falls back gracefully if package/model cannot load.
    """
    if SentenceTransformer is None:
        return None

    try:
        return SentenceTransformer(SEMANTIC_MODEL_NAME)
    except Exception:
        return None


def semantic_similarity(query: str, candidate_text: str) -> float:
    """
    Returns cosine-like similarity in [approximately -1, 1] using normalized embeddings.
    If semantic model is unavailable, returns 0.0 so API still works.
    """
    model = get_semantic_model()
    if not model:
        return 0.0

    if not query or not candidate_text:
        return 0.0

    embeddings = model.encode(
        [query, candidate_text],
        normalize_embeddings=True,
    )
    return float(embeddings[0] @ embeddings[1])


def build_vendor_search_text(vendor) -> str:
    """
    Build rich searchable text per vendor for semantic matching.
    Works with SQLModel instances from DB.
    """
    category = getattr(vendor, "category", "") or ""
    category_value = getattr(category, "value", category)

    parts = [
        getattr(vendor, "name", "") or "",
        category_value,
        getattr(vendor, "area", "") or "",
        getattr(vendor, "address", "") or "",
        getattr(vendor, "cuisine", "") or "",
        getattr(vendor, "signature_dishes", "") or "",
        getattr(vendor, "operating_hours", "") or "",
    ]
    return " | ".join(str(p) for p in parts if p)


# ─── Main pipeline ────────────────────────────────────────────────────────────

def process_query(query: str) -> dict:
    """
    Takes a raw user query in any language and extracts structured intent.

    Returns a dict like:
    {
        "language": "hi",
        "area": "bandra",
        "food_item": "vada pav",
        "category": "street_stall",
        "max_price": 100,
        "vibe": "quick snack"
    }
    """
    query_lower = query.lower().strip()
    intent = {}

    # Step 1: Detect language
    try:
        intent["language"] = detect(query)
    except Exception:
        intent["language"] = "en"

    # Step 2: Extract area / location
    for area in MUMBAI_AREAS:
        if area in query_lower:
            intent["area"] = area
            break

    # Step 3: Extract food item / cuisine
    for keyword, canonical in CUISINE_KEYWORDS.items():
        if keyword in query_lower:
            intent["food_item"] = canonical
            break

    # Step 4: Detect vendor category
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                intent["category"] = category
                break

    # Step 5: Extract price constraint
    for pattern in PRICE_PATTERNS:
        match = re.search(pattern, query_lower)
        if match:
            intent["max_price"] = int(match.group(1))
            break

    # Step 6: Detect vibe (simple rules for now)
    intent["vibe"] = detect_vibe(query_lower)

    return intent


def detect_vibe(query: str) -> str:
    if any(w in query for w in ["study", "work", "laptop", "quiet"]):
        return "study cafe"
    if any(w in query for w in ["aesthetic", "pretty", "instagram", "vibes"]):
        return "aesthetic cafe"
    if any(w in query for w in ["late night", "raat ko", "midnight", "2am", "3am"]):
        return "late night"
    if any(w in query for w in ["quick", "jaldi", "fast", "grab"]):
        return "quick snack"
    if any(w in query for w in ["delivery", "ghar", "home"]):
        return "home delivery"
    if any(w in query for w in ["cheap", "budget", "sasta", "affordable", "kam paise"]):
        return "budget meal"
    return "general"
