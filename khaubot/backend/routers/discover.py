from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Vendor, VendorRead, VendorStatus, DiscoverRequest, DiscoverResponse

from nlp.pipeline import (
    process_query,
    semantic_similarity,
    build_vendor_search_text,
    get_semantic_model,
)

router = APIRouter()


@router.post("/discover", response_model=DiscoverResponse)
def discover(request: DiscoverRequest, session: Session = Depends(get_session)):
    """
    Main discovery endpoint.

    User sends a natural language query → NLP pipeline extracts intent
    → Backend matches vendors → Returns ranked results.
    """

    # Step 1: Run NLP pipeline
    intent = process_query(request.query)

    # Step 2: Fetch approved vendors
    all_vendors = session.exec(
        select(Vendor).where(Vendor.status == VendorStatus.APPROVED)
    ).all()

    scored_results = []

    for vendor in all_vendors:

        # ─── Hard Filters ─────────────────────────────

        # Area filter
        if intent.get("area"):
            if intent["area"].lower() not in (vendor.area or "").lower():
                continue

        # Price filter
        if intent.get("max_price"):
            if vendor.price_min and vendor.price_min > intent["max_price"]:
                continue

        # ─── Build searchable vendor text ─────────────

        vendor_text = build_vendor_search_text(vendor)

        # ─── Semantic similarity score ────────────────

        semantic_score = semantic_similarity(request.query, vendor_text)

        keyword_boost = 0.0

        # ─── Cuisine boost ────────────────────────────
        if intent.get("food_item"):
            food = intent["food_item"].lower()

            searchable = f"{vendor.cuisine or ''} {vendor.signature_dishes or ''}".lower()

            if food in searchable:
                keyword_boost += 0.25

        # ─── Category boost ───────────────────────────
        if intent.get("category"):
            if vendor.category and vendor.category.value == intent["category"]:
                keyword_boost += 0.15

        # ─── Token overlap boost ──────────────────────

        query_tokens = set(
            t for t in request.query.lower().split() if len(t) > 2
        )

        vendor_tokens = set(
            t for t in vendor_text.lower().split() if len(t) > 2
        )

        token_overlap = len(query_tokens.intersection(vendor_tokens))

        keyword_boost += min(token_overlap * 0.04, 0.20)

        # ─── Final score ──────────────────────────────

        final_score = semantic_score + keyword_boost

        scored_results.append((final_score, vendor))

    # ─── Sort vendors by score ───────────────────────

    scored_results.sort(key=lambda item: item[0], reverse=True)

    # If semantic model unavailable, allow lexical matches
    min_score = 0.10

    results = [vendor for score, vendor in scored_results if score >= min_score]

    if not results:
        results = [vendor for _, vendor in scored_results[:10]]

    # ─── Add debug metadata ──────────────────────────

    intent["semantic_enabled"] = bool(get_semantic_model())

    return DiscoverResponse(
        query=request.query,
        detected_language=intent.get("language", "en"),
        extracted_intent=intent,
        results=results[:10],
    )


# ─────────────────────────────────────────────────────


@router.get("/destinations", response_model=list[VendorRead])
def get_destinations(session: Session = Depends(get_session)):
    """Return all approved food vendors"""
    vendors = session.exec(
        select(Vendor).where(Vendor.status == VendorStatus.APPROVED)
    ).all()

    return vendors


# ─────────────────────────────────────────────────────


@router.get("/destinations/{vendor_id}", response_model=VendorRead)
def get_destination(vendor_id: int, session: Session = Depends(get_session)):
    """Return a single vendor"""

    vendor = session.get(Vendor, vendor_id)

    if not vendor or vendor.status != VendorStatus.APPROVED:
        raise HTTPException(status_code=404, detail="Destination not found")

    return vendor