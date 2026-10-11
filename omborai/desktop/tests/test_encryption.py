import uuid

import pytest
import sqlcipher3

from omborai_desktop.offline.store import LocalStore
from omborai_desktop.security import get_or_create_db_key
from omborai_desktop.sync import ops as o
from omborai_desktop.sync.identity import DeviceIdentity

KEY = "ab" * 32
WRONG = "cd" * 32
SECRET_NAME = "Maxfiy-tovar-7731"
STORE = str(uuid.uuid4())


def _seed(path: str) -> None:
    """Imzolangan egasi operatsiyasi bilan to'ldiriladi (protokol v2: imzosiz operatsiya rad etiladi)."""
    store = LocalStore(path, key=KEY, identity=DeviceIdentity(bytes(range(1, 33))))
    store.init_owner(STORE, "egasi")
    store.apply_op(
        store.new_op(
            o.PRODUCT, {"id": str(uuid.uuid4()), "name": SECRET_NAME, "unit": "dona", "sale_price": 1000}
        )
    )
    store.close()


def test_file_on_disk_has_no_plaintext(tmp_path):
    path = str(tmp_path / "local.db")
    _seed(path)
    raw = open(path, "rb").read()
    assert SECRET_NAME.encode() not in raw
    assert not raw.startswith(b"SQLite format 3\x00")


def test_correct_key_reads_data(tmp_path):
    path = str(tmp_path / "local.db")
    _seed(path)
    reopened = LocalStore(path, key=KEY)
    assert [p["name"] for p in reopened.search_products("maxfiy", STORE)] == [SECRET_NAME]
    reopened.close()


def test_wrong_key_is_rejected(tmp_path):
    path = str(tmp_path / "local.db")
    _seed(path)
    with pytest.raises(sqlcipher3.DatabaseError):
        LocalStore(path, key=WRONG)


def test_key_must_be_hex_64(tmp_path):
    with pytest.raises(ValueError):
        LocalStore(str(tmp_path / "x.db"), key="x'); DROP TABLE products; --")


def test_plain_mode_still_available_for_tests():
    store = LocalStore()
    assert store.pending_count() == 0
    store.close()


def test_key_generated_once_and_reused(monkeypatch):
    store: dict[tuple[str, str], str] = {}
    import omborai_desktop.security as sec

    monkeypatch.setattr(sec.keyring, "get_password", lambda s, a: store.get((s, a)))
    monkeypatch.setattr(sec.keyring, "set_password", lambda s, a, v: store.__setitem__((s, a), v))
    first = get_or_create_db_key()
    assert len(first) == 64
    assert get_or_create_db_key() == first
