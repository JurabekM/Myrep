"""`files` plagini: haqiqiy yadro, haqiqiy bola jarayon, diskdagi haqiqiy fayllar."""

import asyncio
import os
import shutil
import sqlite3
import subprocess
from collections.abc import Awaitable, Callable
from contextlib import closing
from pathlib import Path
from typing import Any

import httpx
import pytest

from conftest import serve_app
from srv1_core.paths import DataPaths
from srv1_core.plugins.registry import BUILTIN_DIR

API = "/api/v1/plugins/files/api"
WATCHED = 1  # 0 — plaginning o'z "library" papkasi


@pytest.fixture
def watched(tmp_path: Path, plugin_root: Path) -> Path:
    """`files` plaginini `watched` papkasiga ruxsat bilan o'rnatadi, namunaviy fayllar yaratadi."""
    folder = tmp_path / "watched"
    (folder / "docs" / "deep").mkdir(parents=True)
    (folder / "Hisobot_2026.pdf").write_bytes(b"x" * 1500)
    (folder / "rasm.png").write_bytes(b"x" * 10)
    (folder / "docs" / "Отчёт за ноябрь.docx").write_bytes(b"x" * 300)
    (folder / "docs" / "notes.txt").write_text("eslatma", encoding="utf-8")
    (folder / "docs" / "deep" / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("sir", encoding="utf-8")

    target = plugin_root / "files"
    shutil.copytree(BUILTIN_DIR / "files", target, ignore=shutil.ignore_patterns("__pycache__"))
    manifest = target / "plugin.toml"
    text = manifest.read_text(encoding="utf-8").replace("paths = []", f"paths = ['{folder}']")
    assert str(folder) in text
    manifest.write_text(text, encoding="utf-8")
    return folder


async def _eventually[T](
    probe: Callable[[], Awaitable[T]], accept: Callable[[T], bool], what: str, timeout_s: float = 10
) -> T:
    value = await probe()
    async with asyncio.timeout(timeout_s):
        while not accept(value):
            await asyncio.sleep(0.05)
            value = await probe()
    assert accept(value), what
    return value


async def _scanned(client: httpx.AsyncClient) -> dict[str, Any]:
    async def status() -> dict[str, Any]:
        return (await client.get(f"{API}/status")).json()

    return await _eventually(status, lambda s: s["last_scan"] is not None, "birinchi skanerlash")


async def _names(client: httpx.AsyncClient, **params: str | int) -> list[str]:
    response = await client.get(f"{API}/search", params=params)
    assert response.status_code == 200, response.text
    return [row["name"] for row in response.json()]


async def _wait_names(
    client: httpx.AsyncClient, accept: Callable[[list[str]], bool], what: str, **params: str | int
) -> list[str]:
    async def probe() -> list[str]:
        return await _names(client, **params)

    return await _eventually(probe, accept, what)


def _audit_actions(paths: DataPaths) -> list[str]:
    with closing(sqlite3.connect(paths.db_file)) as conn:
        rows = conn.execute(
            "SELECT action FROM audit_log WHERE actor = 'plugin:files' ORDER BY id"
        ).fetchall()
    return [row[0] for row in rows]


# --- skanerlash va qidiruv -----------------------------------------------------------
async def test_initial_scan_roots_and_search(paths: DataPaths, watched: Path) -> None:
    async with serve_app(paths) as served, served.client() as client:
        status = await _scanned(client)
        assert (status["files"], status["dirs"], status["roots"], status["watching"]) == (
            5,
            2,
            2,
            2,
        )
        assert status["scanning"] is False

        roots = (await client.get(f"{API}/roots")).json()
        assert [(r["root"], r["label"], r["files"], r["exists"]) for r in roots] == [
            (0, "library", 0, True),
            (1, "watched", 5, True),
        ]
        assert roots[1]["path"] == str(watched)

        # nom ichidan, katta-kichik harf farqsiz, kirill bilan ham
        assert await _names(client, q="sobot") == ["Hisobot_2026.pdf"]
        assert await _names(client, q="HISOBOT") == ["Hisobot_2026.pdf"]
        assert await _names(client, q="ноябрь") == ["Отчёт за ноябрь.docx"]
        assert await _names(client, q="pn") == ["rasm.png"]  # 2 belgi: LIKE yo'li
        assert await _names(client, q="100%") == []
        assert await _names(client, q='"; DROP TABLE files; --') == []
        # filtrlar
        assert await _names(client, ext="txt") == ["a.txt", "notes.txt"]
        assert await _names(client, ext=".TXT") == ["a.txt", "notes.txt"]
        assert await _names(client, min_size=1000) == ["Hisobot_2026.pdf"]
        assert await _names(client, max_size=5) == ["a.txt"]
        assert await _names(client, root=0) == []
        assert await _names(client, q="deep") == ["deep"]
        assert len(await _names(client, limit=3)) == 3
        assert (await client.get(f"{API}/search", params={"limit": 0})).status_code == 422

        found = (await client.get(f"{API}/search", params={"q": "notes"})).json()[0]
        assert (found["root"], found["path"], found["folder"], found["size"], found["is_dir"]) == (
            WATCHED,
            "docs/notes.txt",
            "docs",
            7,
            False,
        )

        listing = (await client.get(f"{API}/list", params={"root": WATCHED})).json()
        assert [(e["name"], e["is_dir"]) for e in listing] == [
            ("docs", True),
            ("Hisobot_2026.pdf", False),
            ("rasm.png", False),
        ]
        nested = (await client.get(f"{API}/list", params={"root": WATCHED, "path": "docs"})).json()
        assert [e["path"] for e in nested] == [
            "docs/deep",
            "docs/notes.txt",
            "docs/Отчёт за ноябрь.docx",
        ]


# --- amallar va savat ------------------------------------------------------------------
async def test_operations_and_trash(paths: DataPaths, watched: Path) -> None:
    async with serve_app(paths) as served, served.client() as client:
        await _scanned(client)

        async def post(operation: str, /, **body: object) -> httpx.Response:
            return await client.post(f"{API}{operation}", json=body)

        # papka yaratish
        assert (await post("/mkdir", root=WATCHED, path="arxiv")).status_code == 201
        assert (watched / "arxiv").is_dir()
        assert (await post("/mkdir", root=WATCHED, path="arxiv")).status_code == 409
        assert (await post("/mkdir", root=WATCHED, path="yoq/ichki")).status_code == 404
        assert await _names(client, q="arxiv") == ["arxiv"]

        # nomini o'zgartirish
        renamed = await post("/rename", root=WATCHED, path="rasm.png", new_name="surat.png")
        assert renamed.json() == {"root": WATCHED, "path": "surat.png"}
        assert (watched / "surat.png").is_file()
        assert not (watched / "rasm.png").exists()
        assert await _names(client, q="surat") == ["surat.png"]
        assert await _names(client, q="rasm") == []
        for bad in ("a/b.png", "..", "nul", "x?.png", "nuqta.", " "):
            response = await post("/rename", root=WATCHED, path="surat.png", new_name=bad)
            assert response.status_code in (400, 422), bad
        conflict = await post(
            "/rename", root=WATCHED, path="surat.png", new_name="Hisobot_2026.pdf"
        )
        assert conflict.status_code == 409
        assert (
            await post("/rename", root=WATCHED, path="yoq.txt", new_name="x.txt")
        ).status_code == 404

        # ko'chirish va nusxalash (ildizlar orasida ham)
        moved = await post(
            "/move", root=WATCHED, path="surat.png", dest_root=WATCHED, dest_path="arxiv"
        )
        assert moved.json() == {"root": WATCHED, "path": "arxiv/surat.png"}
        assert (watched / "arxiv" / "surat.png").is_file()
        copied = await post("/copy", root=WATCHED, path="docs", dest_root=0, dest_path="")
        assert copied.status_code == 201
        library = paths.plugin_data_dir("files") / "library"
        assert (library / "docs" / "deep" / "a.txt").read_text(encoding="utf-8") == "a"
        assert (watched / "docs" / "deep" / "a.txt").is_file(), "nusxalash asl nusxani saqlaydi"
        assert sorted(await _names(client, ext="txt", root=0)) == ["a.txt", "notes.txt"]
        again = await post("/copy", root=WATCHED, path="docs", dest_root=0, dest_path="")
        assert again.status_code == 409
        inside = await post(
            "/move", root=WATCHED, path="docs", dest_root=WATCHED, dest_path="docs/deep"
        )
        assert inside.status_code == 400
        assert (
            await post("/move", root=WATCHED, path="", dest_root=0, dest_path="")
        ).status_code == 400

        # savat: o'chirish -> tiklash -> yana o'chirish -> butunlay o'chirish
        deleted = await post("/delete", root=WATCHED, path="docs")
        trash_id = deleted.json()["id"]
        assert not (watched / "docs").exists()
        assert await _names(client, q="notes", root=WATCHED) == []
        trash = (await client.get(f"{API}/trash")).json()
        assert [(t["id"], t["name"], t["path"], t["is_dir"]) for t in trash] == [
            (trash_id, "docs", "docs", True)
        ]
        assert (await client.get(f"{API}/status")).json()["trash"] == 1

        restored = await post("/trash/restore", id=trash_id)
        assert restored.json() == {"root": WATCHED, "path": "docs"}
        assert (watched / "docs" / "Отчёт за ноябрь.docx").stat().st_size == 300
        assert await _names(client, q="notes", root=WATCHED) == ["notes.txt"]
        assert (await client.get(f"{API}/trash")).json() == []
        assert (await post("/trash/restore", id=trash_id)).status_code == 404

        first = (await post("/delete", root=WATCHED, path="Hisobot_2026.pdf")).json()["id"]
        (watched / "Hisobot_2026.pdf").write_bytes(b"yangi")
        blocked = await post("/trash/restore", id=first)
        assert blocked.status_code == 409, "asl joyi band bo'lsa ustidan yozilmaydi"
        assert (watched / "Hisobot_2026.pdf").read_bytes() == b"yangi"
        assert (await post("/trash/purge", id=first)).json() == {"purged": 1}
        assert (await post("/trash/purge", id=first)).status_code == 404
        await post("/delete", root=WATCHED, path="arxiv")
        await post("/delete", root=0, path="docs")
        assert (await client.delete(f"{API}/trash")).json() == {"purged": 2}
        assert list((paths.plugin_data_dir("files") / "trash").iterdir()) == []
        assert (await post("/delete", root=WATCHED, path="yoq.txt")).status_code == 404

    actions = _audit_actions(paths)
    for expected in ("file.rename", "file.move", "file.copy", "file.trash", "file.restore"):
        assert expected in actions
    assert actions.count("file.delete") == 3
    assert actions.count("file.trash") == 4


# --- ruxsatdan tashqari yo'llar ----------------------------------------------------------
async def test_paths_outside_roots_are_rejected(
    paths: DataPaths, watched: Path, tmp_path: Path
) -> None:
    secret = tmp_path / "secret.txt"
    async with serve_app(paths) as served, served.client() as client:
        await _scanned(client)
        escapes = ["../secret.txt", "docs/../../secret.txt", "..\\secret.txt", str(secret)]
        for escape in escapes:
            listed = await client.get(f"{API}/list", params={"root": WATCHED, "path": escape})
            assert listed.status_code == 403, escape
            for operation, extra in (
                ("/delete", {}),
                ("/rename", {"new_name": "x.txt"}),
                ("/move", {"dest_root": 0, "dest_path": ""}),
                ("/copy", {"dest_root": 0, "dest_path": ""}),
            ):
                body = {"root": WATCHED, "path": escape, **extra}
                response = await client.post(f"{API}{operation}", json=body)
                assert response.status_code == 403, (operation, escape)
        into = await client.post(
            f"{API}/move",
            json={"root": WATCHED, "path": "rasm.png", "dest_root": WATCHED, "dest_path": ".."},
        )
        assert into.status_code == 403
        assert (
            await client.post(f"{API}/mkdir", json={"root": WATCHED, "path": "../x"})
        ).status_code == 403
        assert (await client.get(f"{API}/list", params={"root": 9})).status_code == 404
        assert (
            await client.post(f"{API}/delete", json={"root": -1, "path": "a"})
        ).status_code == 422
        assert (
            await client.post(f"{API}/delete", json={"root": WATCHED, "path": ""})
        ).status_code == 400

    assert secret.read_text(encoding="utf-8") == "sir"
    assert not (tmp_path / "x").exists()
    assert (watched / "rasm.png").is_file()
    assert not list((paths.plugin_data_dir("files") / "library").iterdir())
    log_text = (paths.logs_dir / "srv1.log").read_text(encoding="utf-8")
    assert log_text.count("permission_denied") >= len(escapes) * 5


# --- kuzatuv -------------------------------------------------------------------------------
async def test_watcher_follows_external_changes(
    paths: DataPaths, watched: Path, tmp_path: Path
) -> None:
    async with serve_app(paths) as served, served.client() as client:
        await _scanned(client)
        events = served.core.bus.subscribe("plugin.files.changed")

        (watched / "yangi_fayl.csv").write_text("a,b\n", encoding="utf-8")
        await _wait_names(client, lambda n: n == ["yangi_fayl.csv"], "yangi fayl", q="yangi_fayl")
        event = await asyncio.wait_for(anext(events), 5)
        assert event.data["count"] >= 1
        assert f"{WATCHED}:yangi_fayl.csv" in event.data["paths"]

        (watched / "yangi_fayl.csv").write_bytes(b"x" * 4000)

        async def size() -> int:
            rows = (await client.get(f"{API}/search", params={"q": "yangi_fayl"})).json()
            return rows[0]["size"] if rows else -1

        assert await _eventually(size, lambda s: s == 4000, "hajm yangilanishi") == 4000

        (watched / "yangi_fayl.csv").rename(watched / "eski_fayl.csv")
        await _wait_names(
            client, lambda n: n == ["eski_fayl.csv"], "tashqi qayta nomlash", ext="csv"
        )

        # tashqaridan butun papka ko'chirib keltirilsa, ichidagilar ham indekslanadi
        outside = tmp_path / "import"
        (outside / "ichki").mkdir(parents=True)
        (outside / "ichki" / "chuqur_fayl.dat").write_bytes(b"12345")
        (outside / "ustki.dat").write_bytes(b"1")
        shutil.move(outside, watched / "import")
        await _wait_names(
            client,
            lambda n: sorted(n) == ["chuqur_fayl.dat", "ustki.dat"],
            "papka importi",
            ext="dat",
        )

        shutil.rmtree(watched / "import")
        await _wait_names(client, lambda n: n == [], "papka o'chirilishi", ext="dat")
        assert await _names(client, q="import") == []
        (watched / "eski_fayl.csv").unlink()
        await _wait_names(client, lambda n: n == [], "fayl o'chirilishi", ext="csv")


async def test_changes_while_stopped_are_found_by_rescan(paths: DataPaths, watched: Path) -> None:
    async with serve_app(paths) as served, served.client() as client:
        await _scanned(client)
        assert (await client.post("/api/v1/plugins/files/disable")).json()["status"] == "stopped"
        (watched / "rasm.png").unlink()
        (watched / "tunda_qoshilgan.log").write_text("x", encoding="utf-8")
        assert (await client.post("/api/v1/plugins/files/enable")).json()["status"] == "running"
        await _scanned(client)
        await _wait_names(
            client, lambda n: n == ["tunda_qoshilgan.log"], "qo'shilgan fayl", ext="log"
        )
        assert await _names(client, q="rasm") == []
        status = (await client.get(f"{API}/status")).json()
        assert (status["files"], status["dirs"]) == (5, 2)

        (watched / "qolda.tmp").write_text("x", encoding="utf-8")
        summary = (await client.post(f"{API}/rescan")).json()
        assert summary["entries"] == 8
        assert summary["seconds"] >= 0


async def test_library_root_works_without_any_permission(
    paths: DataPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """O'zgartirilmagan builtin plagin: manifestda papka yo'q, faqat o'z `library` papkasi."""
    monkeypatch.setenv("SRV1_PLUGINS__LOAD_BUILTIN", "true")
    async with serve_app(paths) as served, served.client() as client:
        info = (await client.get("/api/v1/plugins/files")).json()
        assert (info["status"], info["mode"], info["source"]) == (
            "running",
            "inprocess",
            "builtin",
        )
        assert info["permissions"]["paths"] == []
        assert info["jobs"] == ["files:rescan"]
        status = await _scanned(client)
        assert (status["roots"], status["files"]) == (1, 0)
        created = await client.post(f"{API}/mkdir", json={"root": 0, "path": "loyihalar"})
        assert created.status_code == 201
        assert (paths.plugin_data_dir("files") / "library" / "loyihalar").is_dir()
        panel = (await client.get("/api/v1/plugins/files/panel")).json()
        assert panel["title"] == {"uz": "Fayllar", "ru": "Файлы", "en": "Files"}
        search = next(w for w in panel["widgets"] if w.get("source") == "/search")
        assert [f["name"] for f in search["filters"]] == ["q", "ext"]
        assert search["row_actions"][0]["params"] == ["root", "path"]


async def test_scan_of_two_thousand_files(paths: DataPaths, watched: Path) -> None:
    for folder_index in range(20):
        folder = watched / f"katta_{folder_index:02d}"
        folder.mkdir()
        for file_index in range(100):
            (folder / f"qism_{folder_index:02d}_{file_index:03d}.bin").write_bytes(b"0")
    async with serve_app(paths) as served, served.client() as client:
        status = await _scanned(client)
        assert status["files"] == 2005
        assert status["dirs"] == 22
        assert status["last_scan_seconds"] < 20
        assert await _names(client, q="qism_07_042") == ["qism_07_042.bin"]
        assert len(await _names(client, q="qism_07", limit=1000)) == 100


async def _status(client: httpx.AsyncClient) -> dict[str, Any]:
    return (await client.get(f"{API}/status")).json()


# --- simvolik havola va junction ---------------------------------------------------------------
def _make_links(watched: Path, outside: Path) -> bool:
    """Haqiqiy havolalar; huquq yetmasa (Developer Mode o'chiq) `False`."""
    outside.mkdir()
    (outside / "sir.txt").write_text("MAXFIY", encoding="utf-8")
    (watched / "oddiy.txt").write_text("oddiy", encoding="utf-8")
    try:
        (watched / "fayl_havola.txt").symlink_to(outside / "sir.txt")
        (watched / "papka_havola").symlink_to(outside, target_is_directory=True)
    except OSError:
        return False
    shell = os.environ.get("COMSPEC", "cmd.exe")
    command = [shell, "/c", "mklink", "/J", str(watched / "junction"), str(outside)]
    made = subprocess.run(command, capture_output=True, check=False)
    return made.returncode == 0


async def test_links_are_listed_not_followed_and_can_be_removed(
    paths: DataPaths, watched: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "tashqari"
    if not _make_links(watched, outside):
        pytest.skip("simvolik havola yaratishga huquq yo'q")
    async with serve_app(paths) as served, served.client() as client:
        await _eventually(
            lambda: _status(client), lambda s: s["last_scan"] is not None, "skanerlash"
        )
        # indeksga faqat haqiqiy fayl tushadi
        found = (await client.get(f"{API}/search", params={"q": ""})).json()
        names = {row["name"] for row in found}
        assert "oddiy.txt" in names
        assert not names & {"sir.txt", "fayl_havola.txt", "papka_havola", "junction"}
        # ro'yxatda havolalar ko'rinadi, lekin belgilangan va hajmsiz
        listing = (await client.get(f"{API}/list", params={"root": WATCHED})).json()
        links = {row["name"] for row in listing if row["link"]}
        assert links == {"fayl_havola.txt", "junction", "papka_havola"}
        assert {row["name"]: row["link"] for row in listing}["oddiy.txt"] is False
        assert all(row["size"] is None for row in listing if row["link"])

        # havola orqali hech narsa qilib bo'lmaydi
        body = {"root": WATCHED, "path": "papka_havola/sir.txt"}
        assert (await client.post(f"{API}/delete", json=body)).status_code == 403
        inside = {"root": WATCHED, "path": "junction"}
        assert (await client.get(f"{API}/list", params=inside)).status_code == 403
        copy = {"root": WATCHED, "path": "fayl_havola.txt", "dest_root": 0, "dest_path": ""}
        assert (await client.post(f"{API}/copy", json=copy)).status_code == 403

        # unlink: oddiy fayl, yo'q narsa, havola ichidagi yo'l va ildiz rad etiladi
        for path, code in (
            ("oddiy.txt", 400),
            ("yoq.txt", 400),
            ("papka_havola/sir.txt", 403),
            ("", 400),
        ):
            reply = await client.post(f"{API}/unlink", json={"root": WATCHED, "path": path})
            assert reply.status_code == code, (path, reply.text)
        assert (watched / "oddiy.txt").is_file()

        # havolaning o'zi olib tashlanadi; nishon joyida qoladi
        for name in ("fayl_havola.txt", "papka_havola", "junction"):
            reply = await client.post(f"{API}/unlink", json={"root": WATCHED, "path": name})
            assert reply.json() == {"path": name, "removed": True}, reply.text
            assert not os.path.lexists(watched / name)
        assert (outside / "sir.txt").read_text(encoding="utf-8") == "MAXFIY"
        assert sorted(p.name for p in outside.iterdir()) == ["sir.txt"]
        listing = (await client.get(f"{API}/list", params={"root": WATCHED})).json()
        assert not [row["name"] for row in listing if row["link"]]
        assert "oddiy.txt" in {row["name"] for row in listing}
    with closing(sqlite3.connect(paths.db_file)) as conn:
        rows = conn.execute(
            "SELECT action, ok FROM audit_log WHERE action = 'file.unlink' ORDER BY id"
        ).fetchall()
    assert rows == [("file.unlink", 1)] * 3
