"""
KhauBot NLP Pipeline
====================
Rule-based extraction + Groq AI + optional semantic vendor ranking
"""

import os
import re
from functools import lru_cache
from langdetect import detect
from groq import Groq

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


# ───────────────── Groq Client ─────────────────

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ───────────────── Query Normalization ─────────────────

def normalize_query(query: str) -> str:

    query = query.lower()

    query = re.sub(r"[^\w\s₹]", " ", query)

    replacements = {
        "cutting chai": "chai",
        "chai tapri": "chai",
        "tapri chai": "chai",
        "vada pao": "vada pav",
        "vadapav": "vada pav",
        "maggie": "noodles",
        "maggi": "noodles",
        "cheap": "budget",
        "sasta": "budget",
    }

    for k, v in replacements.items():
        query = query.replace(k, v)

    query = re.sub(r"\s+", " ", query).strip()

    return query


# ───────────────── Keyword Maps ─────────────────

MUMBAI_AREAS = [
    "bandra","andheri","juhu","colaba","dadar","kurla",
    "borivali","malad","goregaon","powai","thane","worli",
    "lower parel","matunga","sion","chembur","mulund"
]

CUISINE_KEYWORDS = {
    "vada pav":"vada pav",
    "biryani":"biryani",
    "pav bhaji":"pav bhaji",
    "chai":"chai",
    "coffee":"coffee",
    "pizza":"pizza",
    "burger":"burger",
    "chinese":"chinese",
    "north indian":"north indian",
    "south indian":"south indian",
    "seafood":"seafood",
    "snacks":"snacks",
}

CATEGORY_KEYWORDS = {
    "street_stall":["stall","galli","street","thela","cart"],
    "cafe":["cafe","coffee shop","study","aesthetic"],
    "cloud_kitchen":["delivery","cloud kitchen","home delivery"]
}

PRICE_PATTERNS = [
    r"under\s*[₹rs\.]*\s*(\d+)",
    r"below\s*[₹rs\.]*\s*(\d+)",
]


# ───────────────── Semantic Model (optional) ─────────────────

SEMANTIC_MODEL_NAME = os.getenv(
    "SEMANTIC_MODEL_NAME",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)


@lru_cache(maxsize=1)
def get_semantic_model():

    if SentenceTransformer is None:
        return None

    try:
        return SentenceTransformer(SEMANTIC_MODEL_NAME)
    except Exception:
        return None


def semantic_similarity(query: str, text: str):

    model = get_semantic_model()

    if not model:
        return 0.0

    embeddings = model.encode(
        [query, text],
        normalize_embeddings=True
    )

    return float(embeddings[0] @ embeddings[1])


# ───────────────── Vendor Search Text ─────────────────

def build_vendor_search_text(vendor):

    category = getattr(vendor, "category", "") or ""

    parts = [
        getattr(vendor,"name",""),
        getattr(vendor,"area",""),
        getattr(vendor,"address",""),
        getattr(vendor,"cuisine",""),
        getattr(vendor,"signature_dishes",""),
        getattr(vendor,"operating_hours",""),
        str(category)
    ]

    return " | ".join(str(p) for p in parts if p)


# ───────────────── Groq Query Analysis ─────────────────

def groq_query_analysis(query: str):

    try:

        prompt=f"""
Extract structured data from this Mumbai food search query.

Return JSON with:
area
food_item
category
max_price

Query: {query}
"""

        response=groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2
        )

        return {"ai_analysis":response.choices[0].message.content}

    except Exception:
        return {}


# ───────────────── Main Query Processing ─────────────────

def process_query(query: str):

    query_lower = normalize_query(query)

    intent = {}

    # AI extraction
    intent.update(groq_query_analysis(query))

    # language detection
    try:
        intent["language"]=detect(query)
    except:
        intent["language"]="en"

    # area
    for area in MUMBAI_AREAS:
        if area in query_lower:
            intent["area"]=area
            break

    # cuisine
    for keyword,canonical in CUISINE_KEYWORDS.items():
        if keyword in query_lower:
            intent["food_item"]=canonical
            break

    # category
    for category,keywords in CATEGORY_KEYWORDS.items():
        if any(k in query_lower for k in keywords):
            intent["category"]=category
            break

    # price
    for pattern in PRICE_PATTERNS:
        match=re.search(pattern,query_lower)
        if match:
            intent["max_price"]=int(match.group(1))
            break

    intent["vibe"]=detect_vibe(query_lower)

    return intent


# ───────────────── Vendor Ranking ─────────────────

def rank_vendors(query, vendors):

    ranked=[]

    for vendor in vendors:

        score=0

        text=build_vendor_search_text(vendor)

        # semantic score
        score+=semantic_similarity(query,text)*3

        # rule boosts
        if vendor.area and vendor.area.lower() in query.lower():
            score+=2

        if vendor.cuisine and vendor.cuisine.lower() in query.lower():
            score+=2

        ranked.append((score,vendor))

    ranked.sort(reverse=True,key=lambda x:x[0])

    return [v for _,v in ranked]


# ───────────────── Vibe Detection ─────────────────

def detect_vibe(query):

    if any(w in query for w in ["study","laptop","quiet"]):
        return "study cafe"

    if any(w in query for w in ["aesthetic","instagram"]):
        return "aesthetic cafe"

    if any(w in query for w in ["late night","midnight","2am","3am"]):
        return "late night"

    if any(w in query for w in ["quick","fast","grab"]):
        return "quick snack"

    if any(w in query for w in ["delivery","home"]):
        return "home delivery"

    if any(w in query for w in ["budget","cheap","affordable"]):
        return "budget meal"

    return "general"