import asyncio
import os
from pathlib import Path

import pytest

from srv1_core.auth import AuthError, TokenAuth, load_or_create_token, restrict_to_owner


def test_token_created_once(tmp_path: Path) -> None:
    token_file = tmp_path / "auth.token"
    token, created = load_or_create_token(token_file)
    again, created_again = load_or_create_token(token_file)
    assert created is True
    assert created_again is False
    assert token == again
    assert len(token) >= 43


def test_tokens_are_random(tmp_path: Path) -> None:
    first, _ = load_or_create_token(tmp_path / "a")
    second, _ = load_or_create_token(tmp_path / "b")
    assert first != second


def test_corrupt_token_file_is_an_error(tmp_path: Path) -> None:
    token_file = tmp_path / "auth.token"
    token_file.write_text("qisqa\n", encoding="ascii")
    with pytest.raises(AuthError):
        load_or_create_token(token_file)


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Bearer " + "t" * 43, True),
        ("bearer " + "t" * 43, True),
        ("Bearer  " + "t" * 43 + " ", True),
        ("Bearer " + "t" * 42, False),
        ("Bearer " + "t" * 44, False),
        ("Basic " + "t" * 43, False),
        ("t" * 43, False),
        ("Bearer ", False),
        ("Bearer tokeñ", False),
        ("", False),
        (None, False),
    ],
)
def test_verify_header(header: str | None, expected: bool) -> None:
    assert TokenAuth("t" * 43).verify_header(header) is expected


async def _icacls(path: Path) -> str:
    icacls = Path(os.environ["SystemRoot"]) / "System32" / "icacls.exe"  # noqa: SIM112
    process = await asyncio.create_subprocess_exec(
        str(icacls), str(path), stdout=asyncio.subprocess.PIPE
    )
    stdout, _ = await process.communicate()
    return stdout.decode("oem", "replace")


async def test_restrict_to_owner_removes_inherited_acl(tmp_path: Path) -> None:
    token_file = tmp_path / "auth.token"
    load_or_create_token(token_file)
    assert "(I)" in await _icacls(token_file)

    assert await restrict_to_owner(token_file) is True

    assert "(I)" not in await _icacls(token_file)
    assert load_or_create_token(token_file)[1] is False  # egasi hali ham o'qiy oladi


async def test_restrict_to_owner_reports_failure(tmp_path: Path) -> None:
    assert await restrict_to_owner(tmp_path / "yoq.token") is False
