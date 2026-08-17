import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.integrations.payments.registry import get_payment_provider
from app.models.enums import PaymentStatus, TransactionSource, TransactionType
from app.models.payment import Payment
from app.models.transaction import Transaction
from app.repositories.payment_repository import PaymentRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.payment import PaymentCreate
from app.services.exceptions import ConflictError, NotFoundError, ServiceError


class PaymentService:
    """Click/Payme/UzumBank orqali hamyonni to'ldirish (top-up)."""

    def __init__(
        self,
        payment_repository: PaymentRepository,
        wallet_repository: WalletRepository,
        transaction_repository: TransactionRepository,
    ):
        self.payment_repository = payment_repository
        self.wallet_repository = wallet_repository
        self.transaction_repository = transaction_repository

    async def create_payment(self, user_id: uuid.UUID, data: PaymentCreate) -> Payment:
        wallet = await self.wallet_repository.get(data.wallet_id)
        if wallet is None or wallet.user_id != user_id:
            raise NotFoundError("Hamyon topilmadi")

        payment = Payment(
            user_id=user_id,
            wallet_id=data.wallet_id,
            provider=data.provider,
            amount=data.amount,
            currency=wallet.currency,
            status=PaymentStatus.PENDING,
        )
        payment = await self.payment_repository.add(payment)

        provider = get_payment_provider(data.provider.value)
        session = await provider.create_checkout(str(payment.id), data.amount, data.return_url)
        payment.external_id = session.external_id
        payment.checkout_url = session.checkout_url

        await self.payment_repository.commit()
        return payment

    async def confirm_payment(self, payment_id: uuid.UUID, amount: Decimal, signature: str) -> Payment:
        payment = await self.payment_repository.get(payment_id)
        if payment is None:
            raise NotFoundError("To'lov topilmadi")
        if payment.status != PaymentStatus.PENDING:
            raise ConflictError("Bu to'lov allaqachon qayta ishlangan")

        provider = get_payment_provider(payment.provider.value)
        is_valid = provider.verify_webhook_signature(
            {"payment_id": str(payment.id), "amount": str(amount)}, signature
        )
        if not is_valid:
            raise ServiceError("Webhook imzosi yaroqsiz")
        if amount != Decimal(payment.amount):
            raise ConflictError("To'lov summasi mos kelmadi")

        wallet = await self.wallet_repository.get(payment.wallet_id)
        if wallet is None:
            raise NotFoundError("Hamyon topilmadi")

        transaction = Transaction(
            user_id=payment.user_id,
            wallet_id=payment.wallet_id,
            type=TransactionType.INCOME,
            amount=payment.amount,
            currency=payment.currency,
            note=f"{payment.provider.value.capitalize()} orqali to'ldirish",
            source=TransactionSource.BANK_SYNC,
            occurred_at=datetime.now(timezone.utc),
        )
        wallet.balance = Decimal(wallet.balance) + Decimal(payment.amount)
        wallet.version += 1

        transaction = await self.transaction_repository.add(transaction)
        payment.status = PaymentStatus.PAID
        payment.transaction_id = transaction.id

        await self.payment_repository.commit()
        return payment

    async def simulate_success(self, user_id: uuid.UUID, payment_id: uuid.UUID) -> Payment:
        """Sandbox/development uchun - haqiqiy provayder webhook'i o'rniga to'lovni
        muvaffaqiyatli yakunlaydi (imzoni server o'zi hisoblaydi). Router darajasida
        faqat non-production muhitda ochiladi."""
        payment = await self.payment_repository.get(payment_id)
        if payment is None or payment.user_id != user_id:
            raise NotFoundError("To'lov topilmadi")

        provider = get_payment_provider(payment.provider.value)
        signature = provider.sign({"payment_id": str(payment.id), "amount": str(Decimal(payment.amount))})
        return await self.confirm_payment(payment_id, Decimal(payment.amount), signature)

    async def list_payments(self, user_id: uuid.UUID) -> list[Payment]:
        return await self.payment_repository.list_by_user(user_id)
