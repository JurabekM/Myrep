import uuid

import pytest

from omborai_desktop import auth
from omborai_desktop import users as u
from omborai_desktop.offline.store import LocalStore
from omborai_desktop.sync import ops as o


def _owner(local: LocalStore, store_id: str) -> None:
    salt, digest = auth.hash_password("egasi-parol-1")
    op = o.new_op(
        o.USER,
        store_id,
        {
            "id": str(uuid.uuid4()),
            "login": "egasi",
            "name": "Egasi",
            "role": "owner",
            "salt": salt,
            "pw_hash": digest,
            "active": True,
        },
        device_id="dev-owner",
    )
    local.apply_op(op)


def test_add_cashier_creates_working_login():
    store_id = str(uuid.uuid4())
    local = LocalStore()
    _owner(local, store_id)

    op = u.add_cashier(local, store_id, "dev-a", "  Ali ", " ALI ", "kassir-parol-1")
    assert local.apply_op(op)

    cashier = local.find_user(store_id, "ali")
    assert cashier is not None and cashier["role"] == "cashier"
    assert auth.verify_password("kassir-parol-1", cashier["salt"], cashier["pw_hash"])


def test_duplicate_login_and_short_password_are_rejected():
    store_id = str(uuid.uuid4())
    local = LocalStore()
    _owner(local, store_id)
    local.apply_op(u.add_cashier(local, store_id, "dev-a", "Ali", "ali", "kassir-parol-1"))

    with pytest.raises(u.UserError, match="band"):
        u.add_cashier(local, store_id, "dev-a", "Boshqa", "Ali", "kassir-parol-2")
    with pytest.raises(u.UserError, match="kamida"):
        u.add_cashier(local, store_id, "dev-a", "Vali", "vali", "qisqa")
    with pytest.raises(u.UserError):
        u.add_cashier(local, store_id, "dev-a", "  ", "vali", "kassir-parol-2")


def test_deactivate_and_reactivate_cashier():
    store_id = str(uuid.uuid4())
    local = LocalStore()
    _owner(local, store_id)
    add = u.add_cashier(local, store_id, "dev-a", "Ali", "ali", "kassir-parol-1")
    local.apply_op(add)
    user_id = add["payload"]["id"]

    local.apply_op(u.set_active(local, store_id, "dev-a", user_id, False))
    assert local.find_user(store_id, "ali") is None

    local.apply_op(u.set_active(local, store_id, "dev-a", user_id, True))
    assert local.find_user(store_id, "ali") is not None


def test_owner_cannot_be_deactivated_and_foreign_store_is_rejected():
    store_id = str(uuid.uuid4())
    local = LocalStore()
    _owner(local, store_id)
    owner_id = local.list_users(store_id)[0]["id"]

    with pytest.raises(u.UserError, match="egasini"):
        u.set_active(local, store_id, "dev-a", owner_id, False)
    with pytest.raises(u.UserError, match="topilmadi"):
        u.set_active(local, str(uuid.uuid4()), "dev-a", owner_id, False)
