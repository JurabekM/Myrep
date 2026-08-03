from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import DiagnosisLog
from app.providers.diagnosis import get_diagnosis_provider
from app.rate_limit import limiter
from app.schemas import DiagnosisRatingIn, DiagnosisResultOut
from app.security import get_optional_user

router = APIRouter(prefix="/v1/diagnosis", tags=["diagnosis"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("", response_model=DiagnosisResultOut)
@limiter.limit("20/minute")
async def diagnose(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_optional_user),
):
    settings = get_settings()

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, or WEBP images are accepted",
        )

    image_bytes = await file.read()
    max_bytes = settings.max_upload_image_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds {settings.max_upload_image_mb}MB limit",
        )
    if len(image_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    provider = get_diagnosis_provider()
    quality_issue = provider.check_photo_quality(image_bytes)
    if quality_issue:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"reason": quality_issue, "message": "Photo quality too low, please retake"},
        )

    result = provider.diagnose(image_bytes)

    log = DiagnosisLog(
        user_id=user.id if user else None,
        category=result.category.value,
        confidence=result.confidence,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return DiagnosisResultOut(
        diagnosis_log_id=log.id,
        category=result.category.value,
        confidence=result.confidence,
        cause=result.cause,
        safe_steps=result.safe_steps,
        watch_for=result.watch_for,
        consult_advice=result.consult_advice,
    )


@router.post("/rate", status_code=status.HTTP_204_NO_CONTENT)
def rate_diagnosis(payload: DiagnosisRatingIn, db: Session = Depends(get_db)):
    log = db.query(DiagnosisLog).filter(DiagnosisLog.id == payload.diagnosis_log_id).first()
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown diagnosis_log_id")
    log.useful_rating = 1 if payload.useful else 0
    db.commit()
