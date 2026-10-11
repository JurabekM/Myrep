"""Foydalanuvchilar boshqaruvi (users.py): kassir qo'shish, faollashtirish, egani himoya qilish."""

import pytest
from helpers import STORE_ID, make_owner

from omborai_desktop import users as u
from omborai_desktop.offline.store import APPLIED
from omborai_desktop.sync import ops as o


def test_add_cashier_creates_signed_user_op_and_is_applied():
    owner = make_owner()
    op = u.add_cashier(owner.local, "  Ali  ", "  ALI  ", "parol-12345")
    assert op["type"] == o.USER and op["payload"]["role"] == o.ROLE_CASHIER
    assert op["payload"]["login"] == "ali"  # normallashtirilgan
    assert owner.local.apply_op(op) == APPLIED
    assert owner.local.find_user(STORE_ID, "ali")["name"] == "Ali"


def test_add_cashier_validates_input_and_duplicate_login():
    owner = make_owner()
    with pytest.raises(u.UserError):
        u.add_cashier(owner.local, " ", "x", "parol-12345")
    with pytest.raises(u.UserError):
        u.add_cashier(owner.local, "Ali", "ali", "qisqa")
    owner.local.apply_op(u.add_cashier(owner.local, "Ali", "ali", "parol-12345"))
    with pytest.raises(u.UserError):
        u.add_cashier(owner.local, "Boshqa", "ALI", "parol-12345")


def test_deactivate_and_reactivate_cashier():
    owner = make_owner()
    owner.local.apply_op(u.add_cashier(owner.local, "Ali", "ali", "parol-12345"))
    user = owner.local.find_user(STORE_ID, "ali")
    off = u.set_active(owner.local, user["id"], False)
    assert owner.local.apply_op(off) == APPLIED
    assert owner.local.find_user(STORE_ID, "ali") is None
    on = u.set_active(owner.local, user["id"], True)
    owner.local.apply_op(on)
    assert owner.local.find_user(STORE_ID, "ali") is not None


def test_owner_account_cannot_be_deactivated():
    owner = make_owner()
    own = owner.local.find_user(STORE_ID, "nobody") or None
    assert own is None
    with pytest.raises(u.UserError):
        u.set_active(owner.local, "missing-id", False)
    # Egasi hisobini yaratib, uni o'chirishga urinish
    from helpers import add_user_op

    owner.local.apply_op(add_user_op(owner))
    owner_row = owner.local.find_user(STORE_ID, "egasi")
    with pytest.raises(u.UserError):
        u.set_active(owner.local, owner_row["id"], False)
