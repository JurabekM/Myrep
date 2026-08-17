from abc import ABC, abstractmethod
from decimal import Decimal


class BankAccountInfo(dict):
    """Mock bank hisob ma'lumoti - {account_id, masked_number, balance, currency}."""


class BankTransactionInfo(dict):
    """Mock bank tranzaksiyasi - {external_id, amount, type, description, occurred_at}."""


class BankProvider(ABC):
    """Universal Bank API Layer - har bank uchun bitta interfeys (Strategy pattern).

    Hozircha barcha implementatsiyalar Mock (`MockBankProvider`) orqali ishlaydi.
    Real bank API integratsiyasi kelajakda shu interfeysni implement qiluvchi
    yangi adapter yozish orqali qo'shiladi - servis/API qatlamlari o'zgarmaydi
    (Open/Closed Principle).
    """

    bank_code: str
    bank_name: str

    @abstractmethod
    async def fetch_accounts(self, external_user_ref: str) -> list[BankAccountInfo]: ...

    @abstractmethod
    async def fetch_transactions(self, account_id: str) -> list[BankTransactionInfo]: ...

    @abstractmethod
    async def fetch_balance(self, account_id: str) -> Decimal: ...
