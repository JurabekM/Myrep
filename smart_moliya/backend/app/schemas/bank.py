from pydantic import BaseModel


class BankInfo(BaseModel):
    code: str
    name: str


class BankAccount(BaseModel):
    account_id: str
    masked_number: str
    balance: str
    currency: str


class BankSyncResult(BaseModel):
    bank_code: str
    account_id: str
    imported_transactions: int
