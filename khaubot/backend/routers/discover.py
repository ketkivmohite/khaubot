from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session
from models import Vendor, VendorRead, VendorStatus, DiscoverRequest, DiscoverResponse
from nlp.pipeline import process_query, semantic_similarity, build_vendor_search_text, get_semantic_model

router = APIRouter()


@router.post("/discover", response_model=DiscoverResponse)
def discover(request: DiscoverRequest, session: Session = Depends(get_session)):
    """
    Main discovery endpoint.
    User sends a natural language query → NLP pipeline extracts intent
    → Backend matches vendors → Returns ranked results.

    Example queries:
    - "spicy street food near Bandra under ₹100"
    - "mujhe vada pav chahiye Bandra station ke paas"
    - "aesthetic cafe for studying in Bandra"
    - "cloud kitchen delivering biryani in Bandra West"
    """

    # Step 1: Run NLP pipeline on user query
    intent = process_query(request.query)

    # Step 2: Fetch all approved vendors
    all_vendors = session.exec(
        select(Vendor).where(Vendor.status == VendorStatus.APPROVED)
    ).all()

    # Step 3: Hybrid retrieval
    # - Hard filters: area + max_price
    # - Soft ranking: semantic similarity + keyword/category boosts
    scored_results = []
    for vendor in all_vendors:

        # Filter by area if detected
        if intent.get("area"):
            if intent["area"].lower() not in vendor.area.lower():
                continue

        # Filter by price if detected
        if intent.get("max_price"):
            if vendor.price_min > intent["max_price"]:
                continue

        vendor_text = build_vendor_search_text(vendor)
        semantic_score = semantic_similarity(request.query, vendor_text)
        keyword_boost = 0.0

        # Soft boost by extracted food item
        if intent.get("food_item"):
            food = intent["food_item"].lower()
            searchable = f"{vendor.cuisine} {vendor.signature_dishes}".lower()
            if food in searchable:
                keyword_boost += 0.22

        # Soft boost by extracted category
        if intent.get("category") and vendor.category.value == intent["category"]:
            keyword_boost += 0.12

        # Extra boost for very clear lexical overlap terms
        query_tokens = set(t for t in request.query.lower().split() if len(t) > 2)
        vendor_tokens = set(t for t in vendor_text.lower().split() if len(t) > 2)
        token_overlap = len(query_tokens.intersection(vendor_tokens))
        keyword_boost += min(token_overlap * 0.04, 0.20)

        final_score = semantic_score + keyword_boost
        scored_results.append((final_score, vendor))

    # Step 4: Rank by best score and keep only useful matches
    scored_results.sort(key=lambda item: item[0], reverse=True)

    # If semantic model is unavailable, scores can be low; allow top lexical matches.
    min_score = 0.10
    results = [vendor for score, vendor in scored_results if score >= min_score]

    if not results:
        results = [vendor for _, vendor in scored_results[:10]]

    # Step 5: Return ranked results
    intent["semantic_enabled"] = bool(get_semantic_model())
    return DiscoverResponse(
        query=request.query,
        detected_language=intent.get("language", "en"),
        extracted_intent=intent,
        results=results[:10]  # top 10
    )


@router.get("/destinations", response_model=list[VendorRead])
def get_destinations(session: Session = Depends(get_session)):
    """Returns all approved food businesses"""
    vendors = session.exec(
        select(Vendor).where(Vendor.status == VendorStatus.APPROVED)
    ).all()
    return vendors


@router.get("/destinations/{vendor_id}", response_model=VendorRead)
def get_destination(vendor_id: int, session: Session = Depends(get_session)):
    """Returns details of one food business"""
    from fastapi import HTTPException
    vendor = session.get(Vendor, vendor_id)
    if not vendor or vendor.status != VendorStatus.APPROVED:
        raise HTTPException(status_code=404, detail="Destination not found")
    return vendor
