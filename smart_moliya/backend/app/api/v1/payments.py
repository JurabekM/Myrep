import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings

from app.api.deps import (
    CurrentUser,
    get_payment_repository,
    get_transaction_repository,
    get_wallet_repository,
)
from app.repositories.payment_repository import PaymentRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.payment import PaymentCreate, PaymentRead, PaymentWebhook
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


def get_service(
    payment_repo: Annotated[PaymentRepository, Depends(get_payment_repository)],
    wallet_repo: Annotated[WalletRepository, Depends(get_wallet_repository)],
    txn_repo: Annotated[TransactionRepository, Depends(get_transaction_repository)],
) -> PaymentService:
    return PaymentService(payment_repo, wallet_repo, txn_repo)


@router.get("", response_model=list[PaymentRead])
async def list_payments(current_user: CurrentUser, service: Annotated[PaymentService, Depends(get_service)]):
    payments = await service.list_payments(current_user.id)
    return [PaymentRead.model_validate(p) for p in payments]


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreate, current_user: CurrentUser, service: Annotated[PaymentService, Depends(get_service)]
):
    payment = await service.create_payment(current_user.id, payload)
    return PaymentRead.model_validate(payment)


@router.post("/webhook", response_model=PaymentRead)
async def payment_webhook(payload: PaymentWebhook, service: Annotated[PaymentService, Depends(get_service)]):
    """To'lov provayderidan (Click/Payme/UzumBank) keladigan webhook - mock.

    Real integratsiyada bu endpoint autentifikatsiyasiz (provayder chaqiradi),
    xavfsizlik imzo tekshiruvi (`signature`) orqali ta'minlanadi.
    """
    payment = await service.confirm_payment(payload.payment_id, payload.amount, payload.signature)
    return PaymentRead.model_validate(payment)


@router.post("/{payment_id}/simulate", response_model=PaymentRead)
async def simulate_payment(
    payment_id: uuid.UUID, current_user: CurrentUser, service: Annotated[PaymentService, Depends(get_service)]
):
    """Sandbox: mock to'lovni muvaffaqiyatli yakunlaydi (production'da mavjud emas)."""
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    payment = await service.simulate_success(current_user.id, payment_id)
    return PaymentRead.model_validate(payment)
