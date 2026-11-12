"""SDK birlik testlari: manifest, kontekst (ruxsatlar), panel, ASGI ko'prik, tiplar."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from srv1_sdk.asgi import MAX_RESPONSE_BYTES, AsgiApp, call_asgi
from srv1_sdk.context import LogLevel, PluginContext
from srv1_sdk.manifest import ManifestError, PluginManifest, PortRange, load_manifest
from srv1_sdk.panel import PanelSpec, ValueWidget, parse_panel
from srv1_sdk.types import Job, PermissionDenied


def _manifest_dir(tmp_path: Path, text: str, name: str = "demo") -> Path:
    directory = tmp_path / name
    directory.mkdir()
    (directory / "plugin.toml").write_text(text, encoding="utf-8")
    return directory


# --- manifest ---------------------------------------------------------------
def test_minimal_manifest_defaults(tmp_path: Path) -> None:
    manifest = load_manifest(_manifest_dir(tmp_path, 'name = "demo"\nversion = "1.2.3"\n'))
    assert manifest.mode == "inprocess"
    assert manifest.heavy is False
    assert manifest.memory_limit_mb == 256
    assert manifest.permissions.paths == ()


def test_full_manifest(tmp_path: Path) -> None:
    text = """
        name = "demo"
        version = "0.1.0-beta.1"
        mode = "subprocess"
        heavy = true
        memory_limit_mb = 512
        [permissions]
        paths = ["C:/data/in"]
        ports = [9000, "9010-9019"]
        serial = ["com3"]
    """
    manifest = load_manifest(_manifest_dir(tmp_path, text))
    assert manifest.permissions.paths == (Path("C:/data/in"),)
    assert manifest.permissions.ports == (
        PortRange(start=9000, end=9000),
        PortRange(start=9010, end=9019),
    )
    assert manifest.permissions.serial == ("COM3",)
    assert 9015 in manifest.permissions.ports[1]
    assert 9020 not in manifest.permissions.ports[1]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "not toml [",
        'name = "demo"\n',
        'name = "Demo"\nversion = "1.0.0"\n',
        'name = "demo"\nversion = "1.0"\n',
        'name = "demo"\nversion = "1.0.0"\nmode = "thread"\n',
        'name = "demo"\nversion = "1.0.0"\nheavy = true\n',
        'name = "demo"\nversion = "1.0.0"\nunknown = 1\n',
        'name = "demo"\nversion = "1.0.0"\nmemory_limit_mb = 8\n',
        'name = "demo"\nversion = "1.0.0"\n[permissions]\npaths = ["relative/dir"]\n',
        'name = "demo"\nversion = "1.0.0"\n[permissions]\nports = [70000]\n',
        'name = "demo"\nversion = "1.0.0"\n[permissions]\nports = ["9010-9000"]\n',
        'name = "demo"\nversion = "1.0.0"\n[permissions]\nports = ["http"]\n',
        'name = "demo"\nversion = "1.0.0"\n[permissions]\nports = [true]\n',
        'name = "demo"\nversion = "1.0.0"\n[permissions]\nserial = ["/dev/ttyUSB0"]\n',
        'name = "demo"\nversion = "1.0.0"\n[permissions]\nnetwork = true\n',
    ],
)
def test_invalid_manifest(tmp_path: Path, text: str) -> None:
    with pytest.raises(ManifestError):
        load_manifest(_manifest_dir(tmp_path, text))


def test_manifest_missing_or_misnamed(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="topilmadi"):
        load_manifest(tmp_path)
    misnamed = _manifest_dir(tmp_path, 'name = "demo"\nversion = "1.0.0"\n', name="other")
    with pytest.raises(ManifestError, match="mos emas"):
        load_manifest(misnamed)


# --- kontekst -----------------------------------------------------------------
class _FakeBackend:
    def __init__(self) -> None:
        self.published: list[tuple[str, Mapping[str, Any]]] = []
        self.logs: list[tuple[str, str, Mapping[str, Any]]] = []
        self.audits: list[tuple[str, str, bool]] = []

    def publish(self, topic: str, data: Mapping[str, Any]) -> None:
        self.published.append((topic, data))

    async def audit(self, action: str, target: str, ok: bool, detail: Mapping[str, Any]) -> None:
        self.audits.append((action, target, ok))

    def log(self, level: LogLevel, event: str, fields: Mapping[str, Any]) -> None:
        self.logs.append((level, event, fields))


def _context(tmp_path: Path, **permissions: object) -> tuple[PluginContext, _FakeBackend]:
    manifest = PluginManifest.model_validate(
        {"name": "demo", "version": "1.0.0", "permissions": permissions}
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    backend = _FakeBackend()
    return PluginContext(manifest, data_dir, backend), backend


def test_own_data_dir_always_allowed(tmp_path: Path) -> None:
    ctx, _ = _context(tmp_path)
    assert ctx.data_path("a", "b.txt") == (tmp_path / "data" / "a" / "b.txt").resolve()
    assert ctx.resolve_path("notes.txt") == (tmp_path / "data" / "notes.txt").resolve()


def test_declared_path_allowed_others_denied(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    ctx, backend = _context(tmp_path, paths=[str(allowed)])

    assert ctx.resolve_path(allowed / "sub" / "x.csv") == (allowed / "sub" / "x.csv").resolve()
    for forbidden in (
        tmp_path / "secret.txt",
        allowed / ".." / "secret.txt",
        Path(r"C:\Windows\System32\drivers\etc\hosts"),
        "../outside.txt",
        allowed / "nul.txt",
        str(allowed / "a.txt") + ":stream",
    ):
        with pytest.raises(PermissionDenied):
            ctx.resolve_path(forbidden)
    assert [(level, event) for level, event, _ in backend.logs] == [
        ("warning", "permission_denied")
    ] * 6
    assert backend.logs[0][2]["kind"] == "path"


def test_sibling_prefix_is_not_inside(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    (tmp_path / "allowed-evil").mkdir()
    allowed.mkdir()
    ctx, _ = _context(tmp_path, paths=[str(allowed)])
    with pytest.raises(PermissionDenied):
        ctx.resolve_path(tmp_path / "allowed-evil" / "x")


def test_ports_and_serial(tmp_path: Path) -> None:
    ctx, _ = _context(tmp_path, ports=[9000, "9010-9012"], serial=["COM3"])
    assert ctx.check_port(9000) == 9000
    assert ctx.check_port(9011) == 9011
    assert ctx.check_serial("com3") == "COM3"
    for port in (8999, 9001, 9013, 80):
        with pytest.raises(PermissionDenied):
            ctx.check_port(port)
    with pytest.raises(PermissionDenied):
        ctx.check_serial("COM4")


def test_no_permissions_means_nothing_allowed(tmp_path: Path) -> None:
    ctx, _ = _context(tmp_path)
    with pytest.raises(PermissionDenied):
        ctx.check_port(9000)
    with pytest.raises(PermissionDenied):
        ctx.check_serial("COM1")


async def test_publish_is_namespaced(tmp_path: Path) -> None:
    ctx, backend = _context(tmp_path)
    ctx.publish("tick", {"n": 1})
    await ctx.audit("file.delete", "x", ok=False)
    assert backend.published == [("plugin.demo.tick", {"n": 1})]
    assert backend.audits == [("file.delete", "x", False)]
    for bad in ("", "UPPER", "a b", "x" * 65, "../audit"):
        with pytest.raises(ValueError, match="yaroqsiz mavzu"):
            ctx.publish(bad)


# --- panel va tiplar ------------------------------------------------------------
def test_panel_from_dict() -> None:
    panel = parse_panel(
        {
            "title": "Demo",
            "widgets": [
                {"type": "label", "text": "salom"},
                {"type": "value", "label": "N", "source": "/stats", "field": "n"},
            ],
        }
    )
    assert isinstance(panel, PanelSpec)
    assert isinstance(panel.widgets[1], ValueWidget)
    assert parse_panel(None) is None


@pytest.mark.parametrize(
    "widget",
    [
        {"type": "webview", "url": "http://x"},
        {"type": "value", "label": "N", "source": "http://evil/stats", "field": "n"},
        {"type": "button", "label": "B", "path": "../../system"},
        {"type": "button", "label": "B", "path": "/x", "method": "TRACE"},
        {"type": "label", "text": "x", "extra": 1},
    ],
)
def test_panel_rejects_bad_widgets(widget: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        parse_panel({"title": "Demo", "widgets": [widget]})


async def _noop() -> None:
    return None


def test_job_needs_exactly_one_trigger() -> None:
    assert Job("a", _noop, interval_s=1.0).cron is None
    assert Job("a", _noop, cron="*/5 * * * *").interval_s is None
    with pytest.raises(ValueError, match="vazifa"):
        Job("a", _noop)
    with pytest.raises(ValueError, match="vazifa"):
        Job("a", _noop, interval_s=1.0, cron="* * * * *")
    with pytest.raises(ValueError, match="vazifa"):
        Job("a", _noop, interval_s=0)


# --- ASGI ko'prik ----------------------------------------------------------------
def _demo_app() -> AsgiApp:
    app = FastAPI()

    @app.get("/echo")
    async def echo(q: str = "") -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"q": q}

    @app.post("/sum")
    async def total(numbers: list[int]) -> dict[str, int]:  # pyright: ignore[reportUnusedFunction]
        return {"sum": sum(numbers)}

    @app.get("/boom")
    async def boom() -> None:  # pyright: ignore[reportUnusedFunction]
        raise RuntimeError("ichki sir")

    @app.get("/huge")
    async def huge() -> str:  # pyright: ignore[reportUnusedFunction]
        return "x" * (MAX_RESPONSE_BYTES + 1)

    return app  # pyright: ignore[reportReturnType]


async def test_call_asgi_roundtrip() -> None:
    app = _demo_app()
    echo = await call_asgi(app, method="GET", path="/echo", query=b"q=salom")
    assert (echo.status, echo.body, echo.content_type) == (
        200,
        b'{"q":"salom"}',
        "application/json",
    )

    total = await call_asgi(
        app,
        method="POST",
        path="/sum",
        headers=[("Content-Type", "application/json")],
        body=b"[1,2,3]",
    )
    assert (total.status, total.body) == (200, b'{"sum":6}')

    assert (await call_asgi(app, method="GET", path="/yoq")).status == 404
    assert (await call_asgi(app, method="POST", path="/sum", body=b"x")).status == 422


async def test_call_asgi_hides_exception_details() -> None:
    reply = await call_asgi(_demo_app(), method="GET", path="/boom")
    assert reply.status == 500
    assert b"ichki sir" not in reply.body


async def test_call_asgi_caps_response_size() -> None:
    reply = await call_asgi(_demo_app(), method="GET", path="/huge")
    assert reply.status == 502
