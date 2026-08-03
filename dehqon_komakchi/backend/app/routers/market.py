from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.logging_config import audit
from app.models import Listing, ListingReport, SellGroup, User
from app.rate_limit import limiter
from app.schemas import ListingIn, ListingOut, ListingReportIn, SellGroupIn, SellGroupOut
from app.security import get_current_user

router = APIRouter(prefix="/v1/market", tags=["market"])

AUTO_HIDE_REPORT_THRESHOLD = 3


def _listing_to_out(listing: Listing) -> ListingOut:
    return ListingOut(
        id=listing.id,
        variety=listing.variety,
        quantity_kg=listing.quantity_kg,
        price_som=listing.price_som,
        negotiable=listing.negotiable,
        region=listing.region,
        availability_date=listing.availability_date,
        photo_path=listing.photo_path,
        contact_method=listing.contact_method,
        contact_value=listing.contact_value if listing.contact_consent else None,
        contact_consent=listing.contact_consent,
        group_id=listing.group_id,
        created_at=listing.created_at,
    )


@router.get("/listings", response_model=list[ListingOut])
def list_listings(
    region: str | None = None,
    min_quantity_kg: float | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Listing).filter(Listing.is_hidden.is_(False))
    if region:
        query = query.filter(Listing.region == region)
    if min_quantity_kg is not None:
        query = query.filter(Listing.quantity_kg >= min_quantity_kg)
    listings = query.order_by(Listing.created_at.desc()).limit(200).all()
    return [_listing_to_out(item) for item in listings]


@router.post("/listings", response_model=ListingOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def create_listing(
    request: Request,
    payload: ListingIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.group_id:
        group = db.query(SellGroup).filter(SellGroup.id == payload.group_id).first()
        if group is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown group_id")

    listing = Listing(
        owner_id=user.id,
        variety=payload.variety,
        quantity_kg=payload.quantity_kg,
        price_som=None if payload.negotiable else payload.price_som,
        negotiable=payload.negotiable,
        region=payload.region,
        availability_date=payload.availability_date,
        contact_method=payload.contact_method,
        contact_value=payload.contact_value,
        contact_consent=payload.contact_consent,
        group_id=payload.group_id,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    audit("listing_created", actor=user.phone_number, detail=listing.id)
    return _listing_to_out(listing)


@router.delete("/listings/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(listing_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your listing")
    db.delete(listing)
    db.commit()
    audit("listing_deleted", actor=user.phone_number, detail=listing_id)


@router.post("/listings/{listing_id}/report", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
def report_listing(
    request: Request,
    listing_id: str,
    payload: ListingReportIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    report = ListingReport(
        listing_id=listing_id,
        reporter_user_id=user.id,
        reason=payload.reason,
        note=payload.note,
    )
    db.add(report)
    db.commit()

    report_count = db.query(func.count(ListingReport.id)).filter(ListingReport.listing_id == listing_id).scalar()
    if report_count >= AUTO_HIDE_REPORT_THRESHOLD and not listing.is_hidden:
        listing.is_hidden = True
        db.commit()
        audit("listing_auto_hidden", actor="system", detail=f"{listing_id} reports={report_count}")

    audit("listing_reported", actor=user.phone_number, detail=f"{listing_id} reason={payload.reason}")


@router.post("/groups", response_model=SellGroupOut, status_code=status.HTTP_201_CREATED)
def create_group(payload: SellGroupIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = SellGroup(name=payload.name, region=payload.region, admin_user_id=user.id)
    db.add(group)
    db.commit()
    db.refresh(group)
    audit("group_created", actor=user.phone_number, detail=group.id)
    return SellGroupOut(
        id=group.id,
        name=group.name,
        region=group.region,
        admin_user_id=group.admin_user_id,
        created_at=group.created_at,
        aggregated_quantity_kg=0.0,
    )


@router.get("/groups", response_model=list[SellGroupOut])
def list_groups(db: Session = Depends(get_db)):
    groups = db.query(SellGroup).order_by(SellGroup.created_at.desc()).all()
    out = []
    for g in groups:
        total = (
            db.query(func.coalesce(func.sum(Listing.quantity_kg), 0.0))
            .filter(Listing.group_id == g.id, Listing.is_hidden.is_(False))
            .scalar()
        )
        out.append(
            SellGroupOut(
                id=g.id,
                name=g.name,
                region=g.region,
                admin_user_id=g.admin_user_id,
                created_at=g.created_at,
                aggregated_quantity_kg=float(total or 0.0),
            ),
        )
    return out
