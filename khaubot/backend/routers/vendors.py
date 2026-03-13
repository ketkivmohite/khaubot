from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from database import get_session
from models import Vendor, VendorCreate, VendorRead, VendorStatus

router = APIRouter()


@router.post("/register", response_model=VendorRead, status_code=201)
def register_vendor(vendor_data: VendorCreate, session: Session = Depends(get_session)):
    """
    Any informal food vendor can register here.
    No formal docs needed — just basic info about their business.
    Status starts as PENDING until moderated.
    """
    vendor = Vendor(**vendor_data.model_dump())
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return vendor


@router.get("/all", response_model=list[VendorRead])
def get_all_vendors(session: Session = Depends(get_session)):
    """Admin: see all vendors regardless of status"""
    vendors = session.exec(select(Vendor)).all()
    return vendors


@router.get("/{vendor_id}", response_model=VendorRead)
def get_vendor(vendor_id: int, session: Session = Depends(get_session)):
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.put("/{vendor_id}/update", response_model=VendorRead)
def update_vendor(vendor_id: int, updates: VendorCreate, session: Session = Depends(get_session)):
    """Vendor can update their own listing"""
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    for key, value in updates.model_dump(exclude_unset=True).items():
        setattr(vendor, key, value)
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return vendor


@router.patch("/{vendor_id}/approve", response_model=VendorRead)
def approve_vendor(vendor_id: int, session: Session = Depends(get_session)):
    """Admin: approve a pending vendor"""
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    vendor.status = VendorStatus.APPROVED
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return vendor
