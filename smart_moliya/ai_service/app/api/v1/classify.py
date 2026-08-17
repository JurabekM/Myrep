from fastapi import APIRouter

from app.inference.classifier_service import get_classifier_service
from app.schemas.classify import ClassifyRequest, ClassifyResponse

router = APIRouter(prefix="/classify", tags=["classify"])


@router.post("", response_model=ClassifyResponse)
async def classify_transaction(payload: ClassifyRequest) -> ClassifyResponse:
    category, confidence = get_classifier_service().predict(payload.text)
    return ClassifyResponse(category=category, confidence=confidence)
