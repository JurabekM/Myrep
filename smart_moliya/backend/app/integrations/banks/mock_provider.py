import hashlib
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.integrations.banks.base import BankAccountInfo, BankProvider, BankTransactionInfo

_MOCK_MERCHANTS = [
    "Korzinka", "Makro", "Yandex Taxi", "Beeline", "Uzum Market",
    "Coffee Bar", "Chorsu Bozor", "Havas", "Sella", "Oqtepa AZS",
]


class MockBankProvider(BankProvider):
    """Har bir haqiqiy bank uchun asos - deterministik pseudo-random ma'lumot qaytaradi
    (bank_code + external_user_ref bo'yicha urug'lanadi), shuning uchun bir xil
    so'rov doim bir xil natija beradi (real API xatti-harakatini simulyatsiya qilish uchun qulay).
    """

    def __init__(self, bank_code: str, bank_name: str):
        self.bank_code = bank_code
        self.bank_name = bank_name

    def _rng(self, seed_ref: str) -> random.Random:
        seed = int(hashlib.sha256(f"{self.bank_code}:{seed_ref}".encode()).hexdigest(), 16)
        return random.Random(seed)

    async def fetch_accounts(self, external_user_ref: str) -> list[BankAccountInfo]:
        rng = self._rng(external_user_ref)
        last4 = f"{rng.randint(0, 9999):04d}"
        return [
            BankAccountInfo(
                account_id=f"{self.bank_code}-{last4}",
                masked_number=f"8600 **** **** {last4}",
                balance=str(Decimal(rng.randint(50_000, 5_000_000))),
                currency="UZS",
            )
        ]

    async def fetch_transactions(self, account_id: str) -> list[BankTransactionInfo]:
        rng = self._rng(account_id)
        now = datetime.now(timezone.utc)
        transactions = []
        for i in range(rng.randint(3, 8)):
            amount = Decimal(rng.randint(15_000, 400_000))
            transactions.append(
                BankTransactionInfo(
                    external_id=f"{account_id}-txn-{i}",
                    amount=str(amount),
                    type="expense",
                    description=rng.choice(_MOCK_MERCHANTS),
                    occurred_at=(now - timedelta(days=i)).isoformat(),
                )
            )
        return transactions

    async def fetch_balance(self, account_id: str) -> Decimal:
        rng = self._rng(account_id)
        return Decimal(rng.randint(50_000, 5_000_000))
