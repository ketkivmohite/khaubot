from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import requests

from database import get_session
from models import Vendor, VendorRead, VendorStatus, DiscoverRequest, DiscoverResponse

from nlp.pipeline import (
    process_query,
    semantic_similarity,
    build_vendor_search_text,
    get_semantic_model,
)

router = APIRouter()


# ─────────────────────────────────────────────────────
# OpenStreetMap helper (free, no API key needed)
# ─────────────────────────────────────────────────────

MUMBAI_AREA_COORDS = {
    "bandra": (19.0596, 72.8295),
    "andheri": (19.1136, 72.8697),
    "juhu": (19.1075, 72.8263),
    "colaba": (18.9067, 72.8147),
    "dadar": (19.0178, 72.8478),
    "kurla": (19.0726, 72.8845),
    "borivali": (19.2307, 72.8567),
    "malad": (19.1872, 72.8484),
    "goregaon": (19.1663, 72.8526),
    "powai": (19.1197, 72.9051),
    "thane": (19.2183, 72.9781),
    "worli": (19.0176, 72.8156),
    "lower parel": (18.9945, 72.8258),
    "matunga": (19.0265, 72.8614),
    "sion": (19.0390, 72.8619),
    "chembur": (19.0622, 72.8997),
    "mulund": (19.1763, 72.9563),
}


def search_osm(area: str = "", food_type: str = "", radius: int = 2000) -> list:
    """Search real food places on OpenStreetMap. Free, no API key."""

    # Get coordinates for the area
    lat, lng = MUMBAI_AREA_COORDS.get(area.lower(), (19.0760, 72.8777))

    query = f"""
    [out:json][timeout:10];
    node
      ["amenity"~"restaurant|cafe|fast_food|food_court|bar|street_vendor"]
      ["name"]
      (around:{radius},{lat},{lng});
    out body;
    """

    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            headers={"User-Agent": "KhauBot/1.0 (khaubot-171u.vercel.app)"},
            timeout=12
        )
        resp.raise_for_status()
        elements = resp.json().get("elements", [])

        results = []
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name", "")
            if not name:
                continue

            results.append({
                "id": el.get("id"),
                "name": name,
                "area": area,
                "address": tags.get("addr:street", "Mumbai"),
                "cuisine": tags.get("cuisine", ""),
                "category": tags.get("amenity", ""),
                "operating_hours": tags.get("opening_hours", ""),
                "whatsapp": "",
                "price_min": None,
                "price_max": None,
                "signature_dishes": "",
                "source": "osm",
            })

        return results[:10]

    except Exception as e:
        print(f"OSM error: {e}")
        return []


# ─────────────────────────────────────────────────────


@router.post("/discover")
def discover(request: DiscoverRequest, session: Session = Depends(get_session)):
    """
    Main discovery endpoint.
    1. NLP extracts intent from query
    2. Search registered vendors in DB
    3. If DB has < 3 results → fallback to OpenStreetMap real data
    """

    # Step 1: Run NLP pipeline
    intent = process_query(request.query)

    # Step 2: Fetch approved vendors from DB
    all_vendors = session.exec(
        select(Vendor).where(Vendor.status == VendorStatus.APPROVED)
    ).all()

    scored_results = []

    for vendor in all_vendors:

        if intent.get("area"):
            if intent["area"].lower() not in (vendor.area or "").lower():
                continue

        if intent.get("max_price"):
            if vendor.price_min and vendor.price_min > intent["max_price"]:
                continue

        vendor_text = build_vendor_search_text(vendor)
        semantic_score = semantic_similarity(request.query, vendor_text)
        keyword_boost = 0.0

        if intent.get("food_item"):
            food = intent["food_item"].lower()
            searchable = f"{vendor.cuisine or ''} {vendor.signature_dishes or ''}".lower()
            if food in searchable:
                keyword_boost += 0.25

        if intent.get("category"):
            if vendor.category and vendor.category.value == intent["category"]:
                keyword_boost += 0.15

        query_tokens = set(t for t in request.query.lower().split() if len(t) > 2)
        vendor_tokens = set(t for t in vendor_text.lower().split() if len(t) > 2)
        token_overlap = len(query_tokens.intersection(vendor_tokens))
        keyword_boost += min(token_overlap * 0.04, 0.20)

        final_score = semantic_score + keyword_boost
        scored_results.append((final_score, vendor))

    scored_results.sort(key=lambda item: item[0], reverse=True)
    min_score = 0.10
    db_results = [v for score, v in scored_results if score >= min_score]

    if not db_results:
        db_results = [v for _, v in scored_results[:10]]

    # Step 3: OSM fallback if DB has less than 3 results
    osm_results = []
    if len(db_results) < 3:
        osm_results = search_osm(
            area=intent.get("area", ""),
            food_type=intent.get("food_item", ""),
        )

    # Step 4: Format DB results as dicts
    def vendor_to_dict(v):
        return {
            "id": v.id,
            "name": v.name,
            "area": v.area or "",
            "address": v.address or "",
            "cuisine": v.cuisine or "",
            "category": v.category.value if v.category else "",
            "signature_dishes": v.signature_dishes or "",
            "operating_hours": v.operating_hours or "",
            "whatsapp": v.whatsapp or "",
            "price_min": v.price_min,
            "price_max": v.price_max,
            "source": "khaubot",
        }

    final_results = [vendor_to_dict(v) for v in db_results] + osm_results

    intent["semantic_enabled"] = bool(get_semantic_model())

    return {
        "query": request.query,
        "detected_language": intent.get("language", "en"),
        "extracted_intent": intent,
        "results": final_results[:10],
    }


# ─────────────────────────────────────────────────────


@router.get("/destinations", response_model=list[VendorRead])
def get_destinations(session: Session = Depends(get_session)):
    vendors = session.exec(
        select(Vendor).where(Vendor.status == VendorStatus.APPROVED)
    ).all()
    return vendors


@router.get("/destinations/{vendor_id}", response_model=VendorRead)
def get_destination(vendor_id: int, session: Session = Depends(get_session)):
    vendor = session.get(Vendor, vendor_id)
    if not vendor or vendor.status != VendorStatus.APPROVED:
        raise HTTPException(status_code=404, detail="Destination not found")
    return vendor