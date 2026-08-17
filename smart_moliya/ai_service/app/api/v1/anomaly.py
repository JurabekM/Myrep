from fastapi import APIRouter

from app.inference.anomaly_service import get_anomaly_service
from app.schemas.anomaly import AnomalyRequest, AnomalyResponse

router = APIRouter(prefix="/anomaly", tags=["anomaly"])


@router.post("", response_model=AnomalyResponse)
async def detect_anomaly(payload: AnomalyRequest) -> AnomalyResponse:
    result = get_anomaly_service().detect(payload.amount, payload.category_history)
    return AnomalyResponse(**result)
