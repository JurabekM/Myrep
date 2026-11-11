from pathlib import Path

import pytest
from pydantic import ValidationError

from srv1_core.settings import Settings, ensure_config_file, is_loopback, load_settings


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_when_file_missing(tmp_path: Path) -> None:
    cfg = load_settings(tmp_path / "config.toml")
    assert (cfg.server.host, cfg.server.port) == ("127.0.0.1", 8710)
    assert cfg.logging.level == "INFO"


def test_default_config_file_equals_defaults(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    assert ensure_config_file(config) is True
    assert ensure_config_file(config) is False
    assert load_settings(config).model_dump() == Settings().model_dump()


def test_toml_overrides_defaults(tmp_path: Path) -> None:
    config = _write(tmp_path / "config.toml", '[server]\nport = 8799\n[logging]\nlevel = "DEBUG"\n')
    cfg = load_settings(config)
    assert cfg.server.port == 8799
    assert cfg.logging.level == "DEBUG"


def test_env_overrides_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = _write(tmp_path / "config.toml", "[server]\nport = 8799\n")
    monkeypatch.setenv("SRV1_SERVER__PORT", "8801")
    monkeypatch.setenv("SRV1_DATA_DIR", str(tmp_path))
    assert load_settings(config).server.port == 8801


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.5", "example.com", "::"])  # noqa: S104
def test_non_loopback_rejected_by_default(tmp_path: Path, host: str) -> None:
    config = _write(tmp_path / "config.toml", f'[server]\nhost = "{host}"\n')
    with pytest.raises(ValidationError, match="loopback emas"):
        load_settings(config)


def test_non_loopback_needs_explicit_flag(tmp_path: Path) -> None:
    config = _write(
        tmp_path / "config.toml", '[server]\nhost = "192.168.1.5"\nallow_non_loopback = true\n'
    )
    assert load_settings(config).server.host == "192.168.1.5"


def test_unknown_key_rejected(tmp_path: Path) -> None:
    config = _write(tmp_path / "config.toml", "[server]\nprot = 1\n")
    with pytest.raises(ValidationError):
        load_settings(config)


@pytest.mark.parametrize("port", [0, 70000])
def test_port_range(tmp_path: Path, port: int) -> None:
    config = _write(tmp_path / "config.toml", f"[server]\nport = {port}\n")
    with pytest.raises(ValidationError):
        load_settings(config)


def test_is_loopback() -> None:
    assert is_loopback("127.0.0.1")
    assert is_loopback("::1")
    assert is_loopback("localhost")
    assert not is_loopback("10.0.0.1")
