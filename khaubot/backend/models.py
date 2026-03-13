from sqlmodel import SQLModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime


# ─── Enums ────────────────────────────────────────────────────────────────────

class VendorCategory(str, Enum):
    STREET_STALL  = "street_stall"   # Khau Galli stalls
    CAFE          = "cafe"           # neighbourhood cafes
    CLOUD_KITCHEN = "cloud_kitchen"  # home-based cloud kitchens


class VendorStatus(str, Enum):
    PENDING   = "pending"    # submitted, not yet reviewed
    APPROVED  = "approved"   # live on platform
    REJECTED  = "rejected"   # failed moderation


# ─── Vendor Model ─────────────────────────────────────────────────────────────

class Vendor(SQLModel, table=True):
    id:            Optional[int]  = Field(default=None, primary_key=True)
    name:          str            = Field(index=True)
    category:      VendorCategory
    area:          str            = Field(index=True)   # e.g. "Bandra West"
    address:       Optional[str]  = None
    cuisine:       str                                  # e.g. "street food, vada pav"
    signature_dishes: str                               # comma-separated
    price_min:     int                                  # min price per person (₹)
    price_max:     int                                  # max price per person (₹)
    operating_hours: str                                # e.g. "7am - 11pm"
    open_days:     str                                  # e.g. "Mon-Sat"
    contact:       Optional[str]  = None                # phone or WhatsApp link
    whatsapp_link: Optional[str]  = None                # for cloud kitchens
    photo_url:     Optional[str]  = None
    status:        VendorStatus   = VendorStatus.PENDING
    created_at:    datetime       = Field(default_factory=datetime.utcnow)
    # NOTE: embedding column comes in Phase 4 when we add pgvector + PostgreSQL


# ─── Pydantic schemas (for API request/response) ──────────────────────────────

class VendorCreate(SQLModel):
    """What the vendor fills in during registration"""
    name:             str
    category:         VendorCategory
    area:             str
    address:          Optional[str] = None
    cuisine:          str
    signature_dishes: str
    price_min:        int
    price_max:        int
    operating_hours:  str
    open_days:        str
    contact:          Optional[str] = None
    whatsapp_link:    Optional[str] = None
    photo_url:        Optional[str] = None


class VendorRead(SQLModel):
    """What gets returned to the user"""
    id:               int
    name:             str
    category:         VendorCategory
    area:             str
    cuisine:          str
    signature_dishes: str
    price_min:        int
    price_max:        int
    operating_hours:  str
    contact:          Optional[str]
    whatsapp_link:    Optional[str]
    photo_url:        Optional[str]
    status:           VendorStatus


class DiscoverRequest(SQLModel):
    """User's natural language query"""
    query: str   # e.g. "spicy street food near Bandra under ₹100"


class DiscoverResponse(SQLModel):
    """Discovery results returned to user"""
    query:            str
    detected_language: str
    extracted_intent: dict
    results:          List[VendorRead]
