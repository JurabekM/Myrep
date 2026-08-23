"""DES-1 envelope xavfsizlik testlari (specs/distribos-event-seal/DES-1.md).

Bu yerda «bajarilmadi = toza» EMAS: har bir hujum ANIQ bajariladi va rad
etilgani tasdiqlanadi.
"""

from __future__ import annotations

import pytest

from distribos.aether_q import des1
from distribos.aether_q.vendor import sig

TENANT = b"tenant-demo-0001"
OTHER_TENANT = b"tenant-other-002"
ROOT = bytes(range(32))
EPOCH, KEY_ID, PROFILE = 7, 3, 0x01


@pytest.fixture(scope="module")
def keys() -> des1.EpochKeys:
    return des1.derive_epoch_keys(ROOT, TENANT, EPOCH, KEY_ID, PROFILE)


@pytest.fixture(scope="module")
def identity() -> tuple[bytes, object]:
    return sig.MLDSA65.keygen()


def _header(keys: des1.EpochKeys, sequence: int = 42) -> des1.Des1Header:
    return des1.Des1Header(
        version=des1.DES1_VERSION,
        profile_id=PROFILE,
        content_type=1,
        epoch=EPOCH,
        key_id=KEY_ID,
        tenant_tag=keys.tenant_tag,
        sender_device_id=b"\x11" * 16,
        sequence=sequence,
        rand=b"\xaa" * 6,
    )


@pytest.fixture(scope="module")
def sealed(keys, identity) -> bytes:
    _, secret_key = identity
    return des1.seal(b'{"event":"ORDER_CREATED"}', _header(keys), keys, secret_key)


# --- to'g'ri yo'l ---------------------------------------------------------


def test_roundtrip_recovers_plaintext(sealed, keys, identity) -> None:
    public_key, _ = identity
    header, packed, ciphertext, signature = des1.split(sealed)
    assert des1.verify_signature(packed, ciphertext, signature, public_key)
    assert des1.tenant_tag_matches(header, keys)
    assert des1.open_aead(header, ciphertext, keys) == b'{"event":"ORDER_CREATED"}'


def test_header_survives_pack_unpack(keys) -> None:
    header = _header(keys)
    assert des1.Des1Header.unpack(header.pack()) == header


# --- hujumlar -------------------------------------------------------------


def test_tampered_ciphertext_fails_aead(sealed, keys) -> None:
    broken = bytearray(sealed)
    broken[des1.HEADER_SIZE + 2] ^= 0x01
    header, _, ciphertext, _ = des1.split(bytes(broken))
    with pytest.raises(des1.Des1FormatError):
        des1.open_aead(header, ciphertext, keys)


def test_tampered_ciphertext_fails_signature(sealed, identity) -> None:
    public_key, _ = identity
    broken = bytearray(sealed)
    broken[des1.HEADER_SIZE + 2] ^= 0x01
    _, packed, ciphertext, signature = des1.split(bytes(broken))
    assert not des1.verify_signature(packed, ciphertext, signature, public_key)


def test_tampered_header_fails_signature(sealed, identity) -> None:
    """Header AAD va imzo ostida — o'zgarsa ikkalasi ham buziladi."""
    public_key, _ = identity
    broken = bytearray(sealed)
    broken[3] ^= 0x01  # content_type
    _, packed, ciphertext, signature = des1.split(bytes(broken))
    assert not des1.verify_signature(packed, ciphertext, signature, public_key)


def test_foreign_sender_signature_rejected(sealed) -> None:
    """Boshqa qurilma kaliti bilan tekshirilsa — rad."""
    foreign_public, _ = sig.MLDSA65.keygen()
    _, packed, ciphertext, signature = des1.split(sealed)
    assert not des1.verify_signature(packed, ciphertext, signature, foreign_public)


def test_foreign_tenant_tag_rejected(sealed) -> None:
    other = des1.derive_epoch_keys(ROOT, OTHER_TENANT, EPOCH, KEY_ID, PROFILE)
    header, _, _, _ = des1.split(sealed)
    assert not des1.tenant_tag_matches(header, other)


def test_profile_downgrade_changes_keys() -> None:
    """AETHER-Q N1/S5: profile_id KDF'ga bind — 0x01 dan 0x03 ga downgrade buziladi."""
    hybrid = des1.derive_epoch_keys(ROOT, TENANT, EPOCH, KEY_ID, 0x01)
    minimal = des1.derive_epoch_keys(ROOT, TENANT, EPOCH, KEY_ID, 0x03)
    assert hybrid.aead_key != minimal.aead_key
    assert hybrid.aead_iv != minimal.aead_iv
    assert hybrid.tenant_tag != minimal.tenant_tag


def test_epoch_and_key_id_change_keys() -> None:
    base = des1.derive_epoch_keys(ROOT, TENANT, EPOCH, KEY_ID, PROFILE)
    next_epoch = des1.derive_epoch_keys(ROOT, TENANT, EPOCH + 1, KEY_ID, PROFILE)
    next_key = des1.derive_epoch_keys(ROOT, TENANT, EPOCH, KEY_ID + 1, PROFILE)
    assert base.aead_key != next_epoch.aead_key
    assert base.aead_key != next_key.aead_key


def test_wrong_epoch_key_cannot_open(sealed, keys) -> None:
    stale = des1.derive_epoch_keys(ROOT, TENANT, EPOCH + 1, KEY_ID, PROFILE)
    header, _, ciphertext, _ = des1.split(sealed)
    with pytest.raises(des1.Des1FormatError):
        des1.open_aead(header, ciphertext, stale)


def test_truncated_envelope_rejected(sealed) -> None:
    with pytest.raises(des1.Des1FormatError):
        des1.split(sealed[: des1.MIN_ENVELOPE_SIZE - 1])


def test_empty_input_rejected() -> None:
    with pytest.raises(des1.Des1FormatError):
        des1.split(b"")


# --- maxfiy material sizib chiqmasin --------------------------------------


def test_epoch_keys_repr_hides_secrets(keys) -> None:
    text = repr(keys)
    assert "<secrets hidden>" in text
    assert keys.aead_key.hex() not in text
    assert keys.aead_iv.hex() not in text


def test_sequence_bounds_enforced(keys) -> None:
    with pytest.raises(des1.Des1FormatError):
        _header(keys, sequence=1 << 96).pack()
