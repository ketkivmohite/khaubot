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

# ── Auto geocoding — works for ANY Mumbai area ──────────────────
_geocode_cache = {}

def get_area_coords(area: str) -> tuple:
    if not area:
        return (19.0760, 72.8777)
    area_lower = area.lower().strip()
    if area_lower in _geocode_cache:
        return _geocode_cache[area_lower]
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{area}, Mumbai, India", "format": "json", "limit": 1},
            headers={"User-Agent": "KhauBot/1.0 (khaubot-171u.vercel.app)"},
            timeout=5
        )
        results = resp.json()
        if results:
            lat = float(results[0]["lat"])
            lng = float(results[0]["lon"])
            _geocode_cache[area_lower] = (lat, lng)
            return (lat, lng)
    except Exception:
        pass
    return (19.0760, 72.8777)


# ── OpenStreetMap search ────────────────────────────────────────
def search_osm(area: str = "", food_type: str = "", radius: int = 5000, lat: float = None, lng: float = None) -> list:
    if lat is None or lng is None:
        lat, lng = get_area_coords(area)
    # else: GPS coords provided directly, skip Nominatim geocoding

    # Build Overpass query — filter by cuisine tag OR place name when food_type is known
    if food_type:
        overpass_query = f"""
[out:json][timeout:10];
(
  node["amenity"~"restaurant|cafe|fast_food|food_court|bar|street_vendor"]["name"]["cuisine"~"{food_type}",i](around:{radius},{lat},{lng});
  node["amenity"~"restaurant|cafe|fast_food|food_court|bar|street_vendor"]["name"~"{food_type}",i](around:{radius},{lat},{lng});
);
out body;
"""
    else:
        overpass_query = f"""
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
            data={"data": overpass_query},
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
                "area": area or "Near You",
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

        return results[:15]
    except Exception as e:
        print(f"OSM error: {e}")
        return []


# ── Main discover endpoint ──────────────────────────────────────
router = APIRouter()

@router.post("/discover")
def discover(request: DiscoverRequest, session: Session = Depends(get_session)):
    intent = process_query(request.query)
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
    osm_results = []
    if len(db_results) < 10:
        is_near_me = "near me" in request.query.lower()
        osm_results = search_osm(
            area=intent.get("area", ""),
            food_type=intent.get("food_item", ""),
            lat=request.lat if is_near_me else None,
            lng=request.lng if is_near_me else None,
        )
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
            "whatsapp": getattr(v, "whatsapp", "") or "",
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