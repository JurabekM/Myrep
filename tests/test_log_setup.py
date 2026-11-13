import json
import logging
from pathlib import Path

from srv1_core.log_setup import configure_logging, get_logger, shutdown_logging
from srv1_core.settings import LoggingSettings


def _lines(log_file: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]


def test_json_lines_with_uzbek_text(tmp_path: Path) -> None:
    log_file = configure_logging(tmp_path, LoggingSettings())
    get_logger("srv1.test").info("yadro_ishga_tushdi", izoh="oʻzbekcha matn", port=8710)
    logging.getLogger("uvicorn.error").warning("stdlib xabari")
    shutdown_logging()

    first, second = _lines(log_file)
    assert first["event"] == "yadro_ishga_tushdi"
    assert first["izoh"] == "oʻzbekcha matn"
    assert first["level"] == "info"
    assert first["logger"] == "srv1.test"
    assert str(first["timestamp"]).endswith("Z")
    assert second["event"] == "stdlib xabari"
    assert second["level"] == "warning"


def test_level_filter(tmp_path: Path) -> None:
    log_file = configure_logging(tmp_path, LoggingSettings(level="WARNING"))
    log = get_logger("srv1.test")
    log.info("ko'rinmaydi")
    log.error("ko'rinadi")
    shutdown_logging()
    assert [line["event"] for line in _lines(log_file)] == ["ko'rinadi"]


def test_reconfigure_releases_file(tmp_path: Path) -> None:
    first = configure_logging(tmp_path / "a", LoggingSettings()) if _mk(tmp_path / "a") else None
    configure_logging(_mk(tmp_path / "b"), LoggingSettings())
    assert first is not None
    first.unlink()  # Windows'da ochiq fayl o'chmaydi — handler yopilganini isbotlaydi


def _mk(path: Path) -> Path:
    path.mkdir()
    return path
