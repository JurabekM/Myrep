import uuid
from datetime import datetime
from decimal import Decimal

from app.integrations.banks.registry import get_bank_provider, list_supported_banks
from app.models.enums import TransactionSource, TransactionType
from app.models.transaction import Transaction
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.wallet_repository import WalletRepository
from app.schemas.bank import BankAccount, BankInfo, BankSyncResult
from app.services.exceptions import NotFoundError


class BankService:
    """Universal Bank API Layer ustidagi biznes logika - hozircha Mock providerlar bilan."""

    def __init__(self, wallet_repository: WalletRepository, transaction_repository: TransactionRepository):
        self.wallet_repository = wallet_repository
        self.transaction_repository = transaction_repository

    def list_banks(self) -> list[BankInfo]:
        return [BankInfo(**bank) for bank in list_supported_banks()]

    async def link_account(self, bank_code: str, user_id: uuid.UUID) -> BankAccount:
        provider = get_bank_provider(bank_code)
        accounts = await provider.fetch_accounts(str(user_id))
        return BankAccount(**accounts[0])

    async def sync_transactions(self, bank_code: str, user_id: uuid.UUID, wallet_id: uuid.UUID) -> BankSyncResult:
        wallet = await self.wallet_repository.get(wallet_id)
        if wallet is None or wallet.user_id != user_id:
            raise NotFoundError("Hamyon topilmadi")

        provider = get_bank_provider(bank_code)
        accounts = await provider.fetch_accounts(str(user_id))
        account_id = accounts[0]["account_id"]
        bank_transactions = await provider.fetch_transactions(account_id)

        imported = 0
        for bank_txn in bank_transactions:
            amount = Decimal(bank_txn["amount"])
            transaction = Transaction(
                user_id=user_id,
                wallet_id=wallet_id,
                type=TransactionType.EXPENSE,
                amount=amount,
                currency=wallet.currency,
                note=bank_txn["description"],
                source=TransactionSource.BANK_SYNC,
                occurred_at=datetime.fromisoformat(bank_txn["occurred_at"]),
            )
            wallet.balance = Decimal(wallet.balance) - amount
            await self.transaction_repository.add(transaction)
            imported += 1

        wallet.version += 1
        await self.wallet_repository.commit()
        return BankSyncResult(bank_code=bank_code, account_id=account_id, imported_transactions=imported)
