import uuid
from decimal import Decimal

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.transaction import TransactionCreate
from app.services.exceptions import NotFoundError


class TransactionService:
    def __init__(self, transaction_repository: TransactionRepository, wallet_repository: WalletRepository):
        self.transaction_repository = transaction_repository
        self.wallet_repository = wallet_repository

    async def list_transactions(self, user_id: uuid.UUID) -> list[Transaction]:
        return await self.transaction_repository.list_by_user(user_id)

    async def create_transaction(self, user_id: uuid.UUID, data: TransactionCreate) -> Transaction:
        wallet = await self.wallet_repository.get(data.wallet_id)
        if wallet is None or wallet.user_id != user_id:
            raise NotFoundError("Hamyon topilmadi")

        transaction = Transaction(
            id=data.id or uuid.uuid4(),
            user_id=user_id,
            wallet_id=data.wallet_id,
            category_id=data.category_id,
            card_id=data.card_id,
            type=data.type,
            amount=data.amount,
            currency=data.currency,
            note=data.note,
            source=data.source,
            occurred_at=data.occurred_at,
        )
        self._apply_to_wallet_balance(wallet, data.type, data.amount)
        wallet.version += 1

        transaction = await self.transaction_repository.add(transaction)
        await self.transaction_repository.commit()
        return transaction

    async def delete_transaction(self, user_id: uuid.UUID, transaction_id: uuid.UUID) -> None:
        transaction = await self.transaction_repository.get(transaction_id)
        if transaction is None or transaction.user_id != user_id:
            raise NotFoundError("Tranzaksiya topilmadi")

        wallet = await self.wallet_repository.get(transaction.wallet_id)
        if wallet is not None:
            reverse_type = (
                TransactionType.EXPENSE if transaction.type == TransactionType.INCOME else TransactionType.INCOME
            )
            self._apply_to_wallet_balance(wallet, reverse_type, transaction.amount)
            wallet.version += 1

        await self.transaction_repository.delete(transaction)
        await self.transaction_repository.commit()

    @staticmethod
    def _apply_to_wallet_balance(wallet, transaction_type: TransactionType, amount: Decimal) -> None:
        if transaction_type == TransactionType.INCOME:
            wallet.balance = Decimal(wallet.balance) + Decimal(amount)
        elif transaction_type == TransactionType.EXPENSE:
            wallet.balance = Decimal(wallet.balance) - Decimal(amount)
