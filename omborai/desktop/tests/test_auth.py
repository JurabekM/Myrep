import uuid

import pytest
from helpers import Device, join, make_owner

from omborai_desktop import auth


def test_password_hash_roundtrip_and_wrong_password():
    salt, digest = auth.hash_password("parol-12345")
    assert len(salt) == 32 and len(digest) == 64
    assert auth.verify_password("parol-12345", salt, digest)
    assert not auth.verify_password("parol-12346", salt, digest)


def test_same_password_gets_different_salt():
    assert auth.hash_password("parol-12345")[0] != auth.hash_password("parol-12345")[0]


def test_pairing_code_v2_roundtrip_and_validation():
    store_id = str(uuid.uuid4())
    device_id = str(uuid.uuid4())
    public_key = "cd" * 32
    key = "ab" * 32
    code = auth.make_pairing_code(store_id, device_id, public_key, key)
    assert auth.parse_pairing_code(code) == (store_id, device_id, public_key, key)
    assert auth.parse_pairing_code(f"  {code.upper()}  ") == (store_id, device_id, public_key, key)
    bad_codes = [
        "",
        "no-colons",
        f"{store_id}:{device_id}:{public_key}",  # 3 maydon (eski v1 + kalit yo'q)
        f"not-a-uuid:{device_id}:{public_key}:{key}",
        f"{store_id}:{device_id}:{'xy' * 32}:{key}",  # egasi kaliti hex emas
        f"{store_id}:{device_id}:{public_key}:{'ab' * 31}",  # do'kon kaliti qisqa
    ]
    for bad in bad_codes:
        with pytest.raises(ValueError):
            auth.parse_pairing_code(bad)


def test_owner_pairing_code_only_from_owner_device(monkeypatch):
    from omborai_desktop.ui import login as lg

    monkeypatch.setenv("OMBORAI_STORE_KEY", "00" * 32)  # keyring'ga murojaat qilmasin
    owner, cashier = make_owner(1), Device(2)
    join(owner, cashier)
    code = lg.pairing_code(owner.local)
    assert code is not None
    assert auth.parse_pairing_code(code)[1] == owner.id  # kod egasi qurilmasini ko'rsatadi
    assert lg.pairing_code(cashier.local) is None  # kassir kodni ko'rmaydi
