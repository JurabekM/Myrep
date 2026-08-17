import uuid

from app.models.wallet import Wallet
from app.repositories.wallet_repository import WalletRepository
from app.schemas.wallet import WalletCreate, WalletUpdate
from app.services.exceptions import NotFoundError


class WalletService:
    def __init__(self, wallet_repository: WalletRepository):
        self.wallet_repository = wallet_repository

    async def list_wallets(self, user_id: uuid.UUID) -> list[Wallet]:
        return await self.wallet_repository.list_by_user(user_id)

    async def create_wallet(self, user_id: uuid.UUID, data: WalletCreate) -> Wallet:
        wallet = Wallet(
            id=data.id or uuid.uuid4(),
            user_id=user_id,
            name=data.name,
            currency=data.currency,
            is_shared=data.is_shared,
        )
        wallet = await self.wallet_repository.add(wallet)
        await self.wallet_repository.commit()
        return wallet

    async def update_wallet(self, user_id: uuid.UUID, wallet_id: uuid.UUID, data: WalletUpdate) -> Wallet:
        wallet = await self._get_owned(user_id, wallet_id)
        if data.name is not None:
            wallet.name = data.name
        if data.is_shared is not None:
            wallet.is_shared = data.is_shared
        wallet.version += 1
        await self.wallet_repository.commit()
        return wallet

    async def delete_wallet(self, user_id: uuid.UUID, wallet_id: uuid.UUID) -> None:
        wallet = await self._get_owned(user_id, wallet_id)
        await self.wallet_repository.delete(wallet)

    async def _get_owned(self, user_id: uuid.UUID, wallet_id: uuid.UUID) -> Wallet:
        wallet = await self.wallet_repository.get(wallet_id)
        if wallet is None or wallet.user_id != user_id:
            raise NotFoundError("Hamyon topilmadi")
        return wallet
