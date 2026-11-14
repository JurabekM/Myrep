"""Shell birlik testlari: tarjimalar, formatlash, sozlama, uslub fayli (oynasiz)."""

import re
from datetime import UTC, timedelta, timezone
from pathlib import Path

import pytest

from srv1_sdk.panel import LANGUAGES, PanelSpec, localize
from srv1_shell.app import THEME_FILE
from srv1_shell.config import (
    ShellConfig,
    config_path,
    default_token_file,
    load_config,
    read_token,
    save_config,
)
from srv1_shell.i18n import I18n
from srv1_shell.pages.logs_page import format_entry
from srv1_shell.pages.system_page import level_for
from srv1_shell.translations import LANGUAGE_NAMES, TEXTS

_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_SOURCE_DIR = Path(__file__).resolve().parent.parent / "shell" / "srv1_shell"


# --- tarjimalar ---------------------------------------------------------------
def test_three_languages() -> None:
    assert tuple(LANGUAGE_NAMES) == ("uz", "ru", "en") == LANGUAGES


@pytest.mark.parametrize("key", sorted(TEXTS))
def test_every_text_is_translated(key: str) -> None:
    variants = TEXTS[key]
    assert set(variants) == set(LANGUAGE_NAMES), key
    assert all(text.strip() for text in variants.values()), key
    placeholders = {lang: sorted(_PLACEHOLDER.findall(text)) for lang, text in variants.items()}
    assert placeholders["uz"] == placeholders["ru"] == placeholders["en"], key


def test_every_key_used_in_code_exists() -> None:
    """Kodda `t("...")` bilan so'ralgan har kalit tarjimalar jadvalida bo'lishi shart."""
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in _SOURCE_DIR.rglob("*.py")
        if path.name != "translations.py"
    )
    literal_keys = set(re.findall(r"""\bt\(\s*["']([a-z_.]+)["']""", source))
    assert literal_keys, "kalitlar topilmadi — regex eskirgan"
    assert literal_keys <= set(TEXTS), sorted(literal_keys - set(TEXTS))
    # f-string bilan yig'iladigan kalitlar
    dynamic = [f"nav.{k}" for k in ("system", "plugins", "logs", "memory")]
    dynamic += [f"status.{s}" for s in ("running", "stopped", "error", "crashed", "invalid")]
    dynamic += ["mode.inprocess", "mode.subprocess"]
    dynamic += [
        f"plugins.col.{c}" for c in ("name", "version", "mode", "status", "description", "action")
    ]
    dynamic += [f"memory.col.{c}" for c in ("process", "pid", "ws", "private")]
    dynamic += [
        f"server.state.{s}" for s in ("checking", "starting", "stopping", "stopped", "failed")
    ]
    # `Launcher` qaytaradigan har sabab uchun tarjima bo'lishi shart.
    launcher = (_SOURCE_DIR / "launcher.py").read_text(encoding="utf-8")
    control = (_SOURCE_DIR / "server_control.py").read_text(encoding="utf-8")
    reasons = set(re.findall(r'Outcome\(\s*"\w+",\s*"(\w+)"', launcher))
    reasons |= set(re.findall(r'reason, detail = "(\w+)"', control))
    assert len(reasons) >= 10, sorted(reasons)
    dynamic += [f"server.reason.{reason}" for reason in sorted(reasons)]
    assert set(dynamic) <= set(TEXTS)


def test_translate_and_fallbacks() -> None:
    assert I18n("ru").t("nav.system") == "Система"
    assert I18n("en").t("nav.system") == "System"
    assert I18n("uz").t("nav.system") == "Tizim"
    assert I18n("xx").language == "uz"
    assert I18n("en").t("yoq.kalit") == "yoq.kalit"
    assert I18n("en").t("memory.plugin", name="iot") == "Plugin: iot"


def test_pick_plugin_text() -> None:
    text = {"uz": "Salom", "ru": "Привет", "en": "Hello"}
    assert I18n("ru").pick(text) == "Привет"
    assert I18n("ru").pick("bir xil") == "bir xil"
    assert I18n("ru").pick({"en": "Hello"}) == "Hello"
    assert I18n("ru").pick({"uz": "Salom"}) == "Salom"
    assert localize(text, "en") == "Hello"
    assert localize({"uz": "Salom"}, "ru") == "Salom"


def test_panel_rejects_unknown_language() -> None:
    with pytest.raises(ValueError, match="til kalitlari"):
        PanelSpec.model_validate({"title": {"de": "Hallo"}, "widgets": []})
    with pytest.raises(ValueError, match="til kalitlari"):
        PanelSpec.model_validate({"title": {}, "widgets": []})


def test_number_and_size_formatting() -> None:
    megabytes = 81.3 * 1024 * 1024
    assert I18n("uz").size(megabytes) == "81,3 MB"
    assert I18n("ru").size(megabytes) == "81,3 МБ"
    assert I18n("en").size(megabytes) == "81.3 MB"
    assert I18n("en").size(4 * 1024**3) == "4.0 GB"
    assert I18n("en").size(2048) == "2 KB"
    assert I18n("en").size(1023) == "1023 B"
    assert I18n("ru").size(0) == "0 Б"
    assert I18n("uz").percent(29.04) == "29,0 %"


# --- sozlama -----------------------------------------------------------------
def test_config_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "shell.json"
    assert load_config(path) == ShellConfig()
    save_config(ShellConfig(language="ru", host="localhost", port=8799), path)
    loaded = load_config(path)
    assert (loaded.language, loaded.host, loaded.port) == ("ru", "localhost", 8799)
    assert loaded.http_url == "http://localhost:8799"
    assert loaded.ws_url == "ws://localhost:8799/ws/events"
    assert "token" not in path.read_text(encoding="utf-8").lower()


@pytest.mark.parametrize(
    "text",
    ["", "not json", "[1, 2]", '{"language": "de", "port": "x", "host": ""}', '{"port": 99999}'],
)
def test_bad_config_falls_back_to_defaults(tmp_path: Path, text: str) -> None:
    path = tmp_path / "shell.json"
    path.write_text(text, encoding="utf-8")
    assert load_config(path) == ShellConfig()


def test_paths_from_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SRV1_SHELL_CONFIG", str(tmp_path / "s.json"))
    monkeypatch.setenv("SRV1_DATA_DIR", str(tmp_path / "data"))
    assert config_path() == tmp_path / "s.json"
    assert default_token_file() == tmp_path / "data" / "auth.token"
    monkeypatch.delenv("SRV1_DATA_DIR")
    monkeypatch.setenv("PROGRAMDATA", r"C:\ProgramData")
    assert default_token_file() == Path(r"C:\ProgramData\SRV_1\auth.token")


def test_read_token(tmp_path: Path) -> None:
    token_file = tmp_path / "auth.token"
    assert read_token(token_file) is None
    token_file.write_text("\n", encoding="ascii")
    assert read_token(token_file) is None
    token_file.write_text("abc123\n", encoding="ascii")
    assert read_token(token_file) == "abc123"


# --- mayda yordamchilar --------------------------------------------------------
def test_format_log_entry() -> None:
    entry = {
        "timestamp": "2026-11-11T08:05:07.512011Z",
        "level": "warning",
        "logger": "srv1.plugins",
        "event": "plugin_crashed",
        "plugin": "iot",
    }
    assert format_entry(entry, UTC) == "08:05:07 WARNING srv1.plugins  plugin_crashed  plugin=iot"
    # yadro UTC'da yozadi, sahifa mahalliy vaqtni ko'rsatadi (bu yerda: Toshkent, UTC+5)
    tashkent = timezone(timedelta(hours=5))
    assert format_entry(entry, tashkent).startswith("13:05:07 WARNING")
    late = entry | {"timestamp": "2026-11-11T21:30:00Z"}
    assert format_entry(late, tashkent).startswith("02:30:00 ")  # kun almashadi
    assert format_entry(entry | {"timestamp": "buzuq"}, UTC).startswith("buzuq WARNING")
    assert format_entry({"event": "x"}).strip() == "x"
    # plagin maydonlari: yadro qo'shgan `p_` ko'rsatilmaydi
    stats = {
        "timestamp": "2026-11-14T15:04:10.000000Z",
        "level": "info",
        "logger": "srv1.plugin.monitor",
        "event": "netcap_stats",
        "p_packets": 110,
        "p_pps": 11.0,
        "p_tcp": 80,
    }
    assert format_entry(stats, UTC) == (
        "15:04:10 INFO    srv1.plugin.monitor  netcap_stats  packets=110 pps=11.0 tcp=80"
    )


def test_level_thresholds() -> None:
    assert [level_for(v) for v in (0, 74.9, 75, 89.9, 90, 100)] == [
        "ok",
        "ok",
        "warn",
        "warn",
        "bad",
        "bad",
    ]


def test_theme_has_no_global_widget_background() -> None:
    """`QWidget { background }` har ichki vidjetga meros bo'lib, to'q "qutilar" beradi."""
    qss = re.sub(r"/\*.*?\*/", "", THEME_FILE.read_text(encoding="utf-8"), flags=re.S)
    selectors = [block.split("{")[0] for block in qss.split("}") if "{" in block]
    bare = [s.strip() for s in selectors if re.search(r"(^|,)\s*QWidget\s*($|,)", s.strip())]
    assert bare == []
    assert "font-family" not in qss  # shrift QFont.setFamilies orqali beriladi
