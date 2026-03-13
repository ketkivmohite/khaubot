from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from database import get_session
from models import Vendor, VendorRead, VendorStatus, DiscoverRequest, DiscoverResponse
from nlp.pipeline import process_query

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

    # Step 3: Filter vendors based on extracted intent
    results = []
    for vendor in all_vendors:

        # Filter by area if detected
        if intent.get("area"):
            if intent["area"].lower() not in vendor.area.lower():
                continue

        # Filter by category if detected
        if intent.get("category"):
            if vendor.category.value != intent["category"]:
                continue

        # Filter by price if detected
        if intent.get("max_price"):
            if vendor.price_min > intent["max_price"]:
                continue

        # Filter by cuisine/dish if detected
        if intent.get("food_item"):
            food = intent["food_item"].lower()
            searchable = f"{vendor.cuisine} {vendor.signature_dishes}".lower()
            if food not in searchable:
                continue

        results.append(vendor)

    # Step 4: Return results (semantic ranking coming in Phase 3!)
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
