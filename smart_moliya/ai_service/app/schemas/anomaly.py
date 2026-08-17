from pydantic import BaseModel


class AnomalyRequest(BaseModel):
    amount: float
    category_history: list[float]


class AnomalyResponse(BaseModel):
    is_anomaly: bool
    z_score: float
    reason: str
