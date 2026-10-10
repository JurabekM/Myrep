import uuid

import pytest

from omborai_desktop import auth
from omborai_desktop.offline.store import LocalStore
from omborai_desktop.sync import ops as o
from omborai_desktop.ui import login as lg


def test_password_hash_roundtrip_and_wrong_password():
    salt, digest = auth.hash_password("parol-12345")
    assert len(salt) == 32 and len(digest) == 64
    assert auth.verify_password("parol-12345", salt, digest)
    assert not auth.verify_password("parol-12346", salt, digest)


def test_same_password_gets_different_salt():
    assert auth.hash_password("parol-12345")[0] != auth.hash_password("parol-12345")[0]


def test_pairing_code_roundtrip_and_validation():
    store_id = str(uuid.uuid4())
    key = "ab" * 32
    code = auth.make_pairing_code(store_id, key)
    assert auth.parse_pairing_code(code) == (store_id, key)
    assert auth.parse_pairing_code(f"  {code.upper()}  ") == (store_id, key)
    for bad in ["", "no-colon", f"not-a-uuid:{key}", f"{store_id}:xyz", f"{store_id}:{'ab' * 31}"]:
        with pytest.raises(ValueError):
            auth.parse_pairing_code(bad)


def _user_op(store_id, device, user_id, login, password, ts, active=True):
    salt, digest = auth.hash_password(password)
    op = o.new_op(
        o.USER,
        store_id,
        {
            "id": user_id,
            "login": login,
            "name": login.title(),
            "role": "cashier",
            "salt": salt,
            "pw_hash": digest,
            "active": active,
        },
        device_id=device,
    )
    op["ts"] = ts
    return op


def test_user_lww_and_login_lookup_is_case_insensitive():
    store_id = str(uuid.uuid4())
    store = LocalStore()
    uid = str(uuid.uuid4())
    store.apply_op(_user_op(store_id, "d1", uid, "kassir", "eski-parol-1", "2026-01-01T10:00:00+00:00"))
    # Yangi parol (keyingi ts) g'olib bo'ladi; eski ts'li operatsiya uni qaytarmaydi.
    store.apply_op(_user_op(store_id, "d2", uid, "kassir", "yangi-parol-2", "2026-01-05T10:00:00+00:00"))
    store.apply_op(_user_op(store_id, "d1", uid, "kassir", "eski-parol-1", "2026-01-02T10:00:00+00:00"))

    user = store.find_user(store_id, "  KASSIR ")
    assert user is not None
    assert auth.verify_password("yangi-parol-2", user["salt"], user["pw_hash"])
    assert not auth.verify_password("eski-parol-1", user["salt"], user["pw_hash"])


def test_inactive_user_cannot_be_found():
    store_id = str(uuid.uuid4())
    store = LocalStore()
    store.apply_op(
        _user_op(
            store_id,
            "d1",
            str(uuid.uuid4()),
            "bekor",
            "parol-12345",
            "2026-01-01T10:00:00+00:00",
            active=False,
        )
    )
    assert store.find_user(store_id, "bekor") is None


def test_create_store_then_fresh_device_gets_users_by_snapshot(monkeypatch):
    saved: list[bytes] = []
    monkeypatch.setattr(lg, "save_store_key", lambda key: saved.append(key))

    owner = LocalStore()
    lg.create_store(owner, "Test do'kon", "Egasi", "Egasi", "owner-parol-1")
    store_id = owner.get_state("store_id")
    assert store_id and owner.store_name(store_id) == "Test do'kon"
    assert owner.pending_count() == 2  # do'kon + egasi hisobi navbatda
    user = owner.find_user(store_id, "egasi")
    assert user is not None and user["role"] == "owner"

    # Yangi qurilma: snapshot orqali do'kon nomi va foydalanuvchilar keladi.
    snapshot = owner.snapshot_payload(store_id)
    assert snapshot["store"]["name"] == "Test do'kon"
    assert [u["login"] for u in snapshot["users"]] == ["egasi"]

    fresh = LocalStore()
    fresh.set_state("store_id", store_id)
    op = o.new_op(o.SNAPSHOT, store_id, snapshot, device_id="d-owner")
    assert fresh.apply_op(op)
    assert fresh.store_name(store_id) == "Test do'kon"
    joined = fresh.find_user(store_id, "egasi")
    assert joined is not None
    assert auth.verify_password("owner-parol-1", joined["salt"], joined["pw_hash"])
    assert not auth.verify_password("noto'g'ri-parol", joined["salt"], joined["pw_hash"])
