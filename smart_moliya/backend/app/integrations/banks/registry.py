from app.integrations.banks.base import BankProvider
from app.integrations.banks.mock_provider import MockBankProvider

SUPPORTED_BANKS: dict[str, str] = {
    "asaka": "Asaka Bank",
    "nbu": "Milliy Bank (NBU)",
    "ipoteka": "Ipoteka Bank",
    "kapitalbank": "Kapitalbank",
    "hamkorbank": "Hamkorbank",
    "sqb": "SQB (Sanoat-Qurilish Bank)",
    "agrobank": "Agrobank",
    "aloqabank": "Aloqabank",
}


def get_bank_provider(bank_code: str) -> BankProvider:
    """Registry - bank_code bo'yicha adapterni qaytaradi (Strategy pattern).

    Real bank API tayyor bo'lganda shu yerda `MockBankProvider(...)` o'rniga
    haqiqiy adapter (masalan `AsakaBankProvider`) ulanadi - qolgan kod o'zgarmaydi.
    """
    if bank_code not in SUPPORTED_BANKS:
        raise ValueError(f"Noma'lum bank kodi: {bank_code}")
    return MockBankProvider(bank_code=bank_code, bank_name=SUPPORTED_BANKS[bank_code])


def list_supported_banks() -> list[dict[str, str]]:
    return [{"code": code, "name": name} for code, name in SUPPORTED_BANKS.items()]
