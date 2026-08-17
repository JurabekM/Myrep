import uuid

from app.models.transaction import Transaction
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.sync import SyncPullResponse, SyncPushRequest, SyncPushResult


class SyncService:
    """Offline mobil klient bilan incremental sinxronizatsiya (last-write-wins)."""

    def __init__(self, transaction_repository: TransactionRepository, wallet_repository: WalletRepository):
        self.transaction_repository = transaction_repository
        self.wallet_repository = wallet_repository

    async def push(self, user_id: uuid.UUID, request: SyncPushRequest) -> list[SyncPushResult]:
        accepted: list[SyncPushResult] = []
        for item in request.transactions:
            transaction = Transaction(
                user_id=user_id,
                wallet_id=item.wallet_id,
                category_id=item.category_id,
                type=item.type,
                amount=item.amount,
                currency=item.currency,
                note=item.note,
                source=item.source,
                occurred_at=item.occurred_at,
                version=item.version,
            )
            transaction = await self.transaction_repository.add(transaction)
            accepted.append(
                SyncPushResult(client_id=item.client_id, server_id=transaction.id, version=transaction.version)
            )
        await self.transaction_repository.commit()
        return accepted

    async def pull(self, user_id: uuid.UUID, since_version: int) -> SyncPullResponse:
        wallets = await self.wallet_repository.list_by_user(user_id)
        transactions = await self.transaction_repository.list_updated_since(user_id, since_version)
        server_version = max([since_version] + [t.version for t in transactions])

        return SyncPullResponse(
            since_version=since_version,
            server_version=server_version,
            wallets=list(wallets),
            transactions=list(transactions),
        )
