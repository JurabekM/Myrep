from fastapi import APIRouter

from app.api.v1 import anomaly, chatbot, classify, forecast

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(classify.router)
api_router.include_router(forecast.router)
api_router.include_router(anomaly.router)
api_router.include_router(chatbot.router)
