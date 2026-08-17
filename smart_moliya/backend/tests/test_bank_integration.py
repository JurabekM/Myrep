import asyncio

import pytest

from app.integrations.banks.registry import get_bank_provider, list_supported_banks


def test_list_supported_banks_has_8_entries():
    banks = list_supported_banks()
    assert len(banks) == 8
    codes = {b["code"] for b in banks}
    assert "asaka" in codes
    assert "nbu" in codes


def test_unknown_bank_code_raises():
    with pytest.raises(ValueError):
        get_bank_provider("does-not-exist")


def test_mock_provider_is_deterministic():
    provider_a = get_bank_provider("asaka")
    provider_b = get_bank_provider("asaka")

    accounts_a = asyncio.run(provider_a.fetch_accounts("user-123"))
    accounts_b = asyncio.run(provider_b.fetch_accounts("user-123"))

    assert accounts_a == accounts_b
    assert accounts_a[0]["account_id"].startswith("asaka-")


def test_different_banks_give_different_accounts():
    asaka = get_bank_provider("asaka")
    nbu = get_bank_provider("nbu")

    asaka_account = asyncio.run(asaka.fetch_accounts("user-123"))[0]
    nbu_account = asyncio.run(nbu.fetch_accounts("user-123"))[0]

    assert asaka_account["account_id"] != nbu_account["account_id"]


def test_fetch_transactions_returns_non_empty_list():
    provider = get_bank_provider("kapitalbank")
    account = asyncio.run(provider.fetch_accounts("user-456"))[0]
    transactions = asyncio.run(provider.fetch_transactions(account["account_id"]))
    assert len(transactions) >= 3
    for txn in transactions:
        assert float(txn["amount"]) > 0
