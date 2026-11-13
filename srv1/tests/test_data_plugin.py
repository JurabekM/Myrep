"""`data` plagini: haqiqiy yadro, haqiqiy bola jarayon, haqiqiy DuckDB va polars."""

import asyncio
import sqlite3
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import psutil
import pytest

from conftest import serve_app
from data_helpers import allow_folder, install_data, write_samples
from srv1_core.paths import DataPaths

PLUGIN = "/api/v1/plugins/data"
API = f"{PLUGIN}/api"


async def _eventually[T](
    probe: Callable[[], Awaitable[T]], accept: Callable[[T], bool], what: str, timeout_s: float = 30
) -> T:
    value = await probe()
    try:
        async with asyncio.timeout(timeout_s):
            while not accept(value):
                await asyncio.sleep(0.05)
                value = await probe()
    except TimeoutError:
        pytest.fail(f"{what}: kutilgan holat yuz bermadi, oxirgi qiymat: {value!r}")
    return value


@dataclass
class Data:
    client: httpx.AsyncClient

    async def enable(self) -> dict[str, Any]:
        response = await self.client.post(f"{PLUGIN}/enable")
        info = response.json()
        assert info["status"] == "running", info
        return info

    async def post(self, operation: str, /, **body: object) -> httpx.Response:
        return await self.client.post(f"{API}{operation}", json=body)

    async def dataset(self, name: str) -> dict[str, Any]:
        rows = (await self.client.get(f"{API}/datasets")).json()
        return next(row for row in rows if row["name"] == name)

    async def load(self, path: str, **options: object) -> dict[str, Any]:
        """Importni boshlaydi va tugashini kutadi."""
        started = await self.post("/import", path=path, **options)
        assert started.status_code == 202, started.text
        name = started.json()["name"]

        async def probe() -> dict[str, Any]:
            return await self.dataset(name)

        return await _eventually(probe, lambda d: d["state"] != "importing", f"import {name}")

    async def sql(self, sql: str, **options: object) -> dict[str, Any]:
        response = await self.post("/query", sql=sql, **options)
        assert response.status_code == 200, response.text
        return response.json()

    async def rows(self, sql: str) -> list[list[Any]]:
        return (await self.sql(sql))["rows"]

    async def rejected(self, sql: str) -> tuple[int, str]:
        response = await self.post("/query", sql=sql)
        return response.status_code, response.json()["detail"]


@pytest.fixture
async def data(paths: DataPaths, plugin_root: Path) -> AsyncGenerator[Data]:
    inbox = install_data(plugin_root, paths.plugin_data_dir("data"))
    write_samples(inbox)
    async with serve_app(paths) as served, served.client() as client:
        helper = Data(client)
        await helper.enable()
        yield helper


# --- og'ir plagin: standart holatda o'chiq -------------------------------------------
async def test_heavy_plugin_is_off_until_enabled(paths: DataPaths, plugin_root: Path) -> None:
    install_data(plugin_root, paths.plugin_data_dir("data"))
    async with serve_app(paths) as served, served.client() as client:
        info = (await client.get(PLUGIN)).json()
        assert (info["status"], info["enabled"], info["heavy"], info["mode"]) == (
            "stopped",
            False,
            True,
            "subprocess",
        )
        assert info["memory_limit_mb"] == 700
        assert (await client.get(f"{API}/status")).status_code == 409
        enabled = await Data(client).enable()
        assert psutil.pid_exists(enabled["pid"])
        status = (await client.get(f"{API}/status")).json()
        assert (status["datasets"], status["engine_loaded"], status["memory_limit"]) == (
            0,
            False,
            "400MB",
        )
        pid = enabled["pid"]
    assert not psutil.pid_exists(pid)


# --- import ---------------------------------------------------------------------------
async def test_import_csv_and_query(data: Data) -> None:
    inbox = (await data.client.get(f"{API}/inbox")).json()
    assert [item["path"] for item in inbox] == [
        "jadval.tsv",
        "kirill.csv",
        "kitob.xlsx",
        "olchov.parquet",
        "Sotuvlar 2026.csv",
    ]
    sales = await data.load("Sotuvlar 2026.csv")
    assert (sales["name"], sales["state"], sales["rows"], sales["columns"]) == (
        "sotuvlar_2026",
        "ready",
        6,
        4,
    )
    assert sales["size"] > 0
    assert sales["error"] is None
    schema = (await data.client.get(f"{API}/schema", params={"name": "sotuvlar_2026"})).json()
    assert [(c["name"], c["type"]) for c in schema] == [
        ("sana", "Date"),
        ("mahsulot", "String"),
        ("soni", "Int64"),
        ("narx", "Float64"),
    ]

    total = await data.sql(
        "SELECT mahsulot, sum(soni) AS jami, round(sum(soni * narx), 2) AS tushum "
        "FROM sotuvlar_2026 GROUP BY mahsulot ORDER BY tushum DESC"
    )
    assert [c["name"] for c in total["columns"]] == ["mahsulot", "jami", "tushum"]
    assert total["rows"] == [["choy", 11, 141.0], ["non", 20, 65.0], ["qand", 15, 60.0]]
    assert total["truncated"] is False
    by_day = await data.rows(
        "SELECT sana, count(*) FROM sotuvlar_2026 WHERE sana >= DATE '2026-11-02' "
        "GROUP BY sana ORDER BY sana"
    )
    assert by_day == [["2026-11-02", 2], ["2026-11-03", 2]]

    preview = (
        await data.client.get(f"{API}/preview", params={"name": "sotuvlar_2026", "limit": 2})
    ).json()
    assert (len(preview["rows"]), preview["truncated"]) == (2, True)
    assert preview["rows"][0] == ["2026-11-01", "choy", 3, 12.5]

    # hisobot: har ustun bo'yicha statistika
    profile = (await data.client.get(f"{API}/profile", params={"name": "sotuvlar_2026"})).json()
    names = [c["name"] for c in profile["columns"]]
    report = {row[0]: dict(zip(names, row, strict=True)) for row in profile["rows"]}
    assert set(report) == {"sana", "mahsulot", "soni", "narx"}
    assert (report["soni"]["min"], report["soni"]["max"], report["soni"]["count"]) == ("1", "20", 6)
    assert report["mahsulot"]["approx_unique"] == 3
    assert report["narx"]["null_percentage"] == 0
    described = await data.rows("DESCRIBE sotuvlar_2026")
    assert [row[0] for row in described] == ["sana", "mahsulot", "soni", "narx"]


async def test_import_other_formats_and_encodings(data: Data) -> None:
    # kirillcha Windows fayli: kodirovka va ajratgich o'zi aniqlanadi
    kirill = await data.load("kirill.csv")
    assert (kirill["state"], kirill["rows"], kirill["columns"]) == ("ready", 2, 3)
    assert await data.rows("SELECT товар, цена, город FROM kirill ORDER BY цена") == [
        ["чай", 12, "Ташкент"],
        ["кофе", 30, "Самарканд"],
    ]
    explicit = await data.load("kirill.csv", name="aniq", encoding="cp1251", separator=";")
    assert (explicit["name"], explicit["rows"]) == ("aniq", 2)

    tsv = await data.load("jadval.tsv")
    assert await data.rows("SELECT a, b FROM jadval ORDER BY a") == [[1, "bir"], [2, "ikki"]]
    assert tsv["columns"] == 2

    parquet = await data.load("olchov.parquet")
    assert (parquet["rows"], parquet["columns"]) == (3, 3)
    assert await data.rows("SELECT id, qiymat, belgi FROM olchov ORDER BY id") == [
        [1, 1.5, "x"],
        [2, None, "y"],
        [3, 3.5, None],
    ]

    # Excel: standart — birinchi varaq; nom va tartib raqami bilan ham
    book = await data.load("kitob.xlsx")
    assert (book["name"], book["rows"]) == ("kitob", 2)
    assert await data.rows("SELECT ism, yosh, maosh FROM kitob ORDER BY yosh") == [
        ["Ali", 30, 4500.5],
        ["Vali", 41, 5200.0],
    ]
    by_name = await data.load("kitob.xlsx", name="bolimlar", sheet="Bo'limlar")
    assert by_name["rows"] == 3
    assert await data.rows("SELECT sum(soni) FROM bolimlar") == [[15]]
    by_index = await data.load("kitob.xlsx", name="ikkinchi", sheet="2")
    assert by_index["rows"] == 3

    # to'plamlar o'zaro birlashtiriladi
    joined = await data.rows("SELECT count(*) FROM kitob k CROSS JOIN bolimlar b")
    assert joined == [[6]]
    status = (await data.client.get(f"{API}/status")).json()
    assert (status["ready"], status["rows"], status["engine_loaded"]) == (
        7,
        2 + 2 + 2 + 3 + 2 + 3 + 3,
        True,
    )


async def test_import_failures_and_permissions(
    paths: DataPaths, plugin_root: Path, tmp_path: Path
) -> None:
    allowed = tmp_path / "ruxsat"
    allowed.mkdir()
    (allowed / "tashqi.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    secret = tmp_path / "maxfiy.csv"
    secret.write_text("parol\nsir\n", encoding="utf-8")
    inbox = install_data(plugin_root, paths.plugin_data_dir("data"))
    allow_folder(plugin_root, allowed)
    (inbox / "buzuq.xlsx").write_text("bu Excel emas", encoding="utf-8")
    (inbox / "rasm.png").write_bytes(b"\x89PNG")
    (inbox / "bosh.csv").write_text("", encoding="utf-8")
    (inbox / "yaxshi.csv").write_text("a\n1\n", encoding="utf-8")

    async with serve_app(paths) as served, served.client() as client:
        data = Data(client)
        await data.enable()
        # ruxsat etilgan tashqi papka — mutlaq yo'l bilan
        outside = await data.load(str(allowed / "tashqi.csv"))
        assert (outside["state"], outside["rows"]) == ("ready", 1)
        # ruxsatdan tashqari fayl va inbox'dan chiqish
        for path in (str(secret), "../../../../auth.token", str(paths.token_file)):
            assert (await data.post("/import", path=path)).status_code == 403, path
        assert (await data.post("/import", path="yoq.csv")).status_code == 404
        assert (await data.post("/import", path="rasm.png")).status_code == 400
        assert (await data.post("/import", path="yaxshi.csv", name="Bad Name")).status_code == 422
        assert (await data.post("/import", path="yaxshi.csv", encoding="koi8")).status_code == 422
        # inbox ro'yxatida faqat import qilsa bo'ladigan turlar
        listed = [item["path"] for item in (await client.get(f"{API}/inbox")).json()]
        assert "rasm.png" not in listed

        broken = await data.load("buzuq.xlsx")
        assert broken["state"] == "failed"
        assert broken["error"]
        empty = await data.load("bosh.csv")
        assert empty["state"] == "failed"
        # muvaffaqiyatsiz import yarim fayl qoldirmaydi va so'rovda ko'rinmaydi
        datasets_dir = paths.plugin_data_dir("data") / "datasets"
        assert sorted(p.name for p in datasets_dir.iterdir()) == ["tashqi.parquet"]
        assert (await data.rejected("SELECT * FROM buzuq"))[0] == 400
        assert (await client.get(f"{API}/preview", params={"name": "buzuq"})).status_code == 409
        assert (await client.get(f"{API}/preview", params={"name": "yoq"})).status_code == 404

        # qayta import: eski to'plam yangisi bilan almashadi
        (inbox / "yaxshi.csv").write_text("a\n1\n2\n3\n", encoding="utf-8")
        assert (await data.load("yaxshi.csv"))["rows"] == 3
        (inbox / "yaxshi.csv").write_text("a,b\n9,8\n", encoding="utf-8")
        again = await data.load("yaxshi.csv")
        assert (again["rows"], again["columns"]) == (1, 2)
        assert await data.rows("SELECT a, b FROM yaxshi") == [[9, 8]]
    assert secret.read_text(encoding="utf-8") == "parol\nsir\n"


# --- so'rov xavfsizligi --------------------------------------------------------------------
async def test_queries_cannot_touch_anything_outside_datasets(
    data: Data, paths: DataPaths, tmp_path: Path
) -> None:
    await data.load("Sotuvlar 2026.csv")
    token = paths.token_file.as_posix()
    out = (tmp_path / "chiqdi.csv").as_posix()
    forbidden = [
        "SELECT * FROM read_csv('C:/Windows/win.ini')",
        f"SELECT * FROM read_text('{token}')",
        f"SELECT * FROM '{token}'",
        "SELECT * FROM read_csv('https://example.com/a.csv')",
        f"SELECT * FROM glob('{paths.root.as_posix()}/*')",
    ]
    for sql in forbidden:
        status, detail = await data.rejected(sql)
        assert status in (400, 403), (sql, status, detail)
        assert "tgF" not in detail
    assert paths.token_file.read_text(encoding="ascii").strip() not in str(
        [await data.rejected(sql) for sql in forbidden[1:3]]
    )

    not_select = [
        f"COPY sotuvlar_2026 TO '{out}'",
        "DROP VIEW sotuvlar_2026",
        "CREATE TABLE t AS SELECT 1",
        "INSERT INTO sotuvlar_2026 VALUES (DATE '2026-01-01', 'x', 1, 1.0)",
        "DELETE FROM sotuvlar_2026",
        "SET enable_external_access = true",
        "ATTACH 'C:/Temp/x.db'",
        "INSTALL httpfs",
        "PRAGMA database_list",
        "CALL pragma_version()",
    ]
    for sql in not_select:
        status, detail = await data.rejected(sql)
        assert status == 403, (sql, status, detail)
        assert "faqat SELECT" in detail
    assert not Path(out).exists()

    assert (await data.rejected("SELECT 1; SELECT 2"))[0] == 400
    assert (await data.rejected("SELECT 1; DROP VIEW sotuvlar_2026"))[0] == 400
    assert (await data.rejected("SELEKT 1"))[0] == 400
    assert (await data.rejected("SELECT * FROM yoq_jadval"))[0] == 400
    assert (await data.post("/query", sql="")).status_code == 422
    assert (await data.post("/query", sql="SELECT 1", limit=0)).status_code == 422
    # hammasidan keyin to'plam joyida
    assert await data.rows("SELECT count(*) FROM sotuvlar_2026") == [[6]]
    assert await data.rows("EXPLAIN SELECT 1") != []


async def test_paging_types_and_cell_limits(data: Data) -> None:
    page = await data.sql("SELECT i FROM range(25) t(i) ORDER BY i", limit=10, offset=10)
    assert (page["rows"][0], page["rows"][-1], page["truncated"]) == ([10], [19], True)
    last = await data.sql("SELECT i FROM range(25) t(i) ORDER BY i", limit=10, offset=20)
    assert ([row[0] for row in last["rows"]], last["truncated"]) == ([20, 21, 22, 23, 24], False)
    beyond = await data.sql("SELECT i FROM range(25) t(i)", limit=10, offset=100)
    assert (beyond["rows"], beyond["truncated"]) == ([], False)
    capped = await data.sql("SELECT i FROM range(5000) t(i)", limit=5000)
    assert (len(capped["rows"]), capped["truncated"]) == (1000, True)

    typed = await data.sql(
        "SELECT DATE '2026-11-11' AS d, TIMESTAMP '2026-11-11 14:05:00' AS t, "
        "CAST(12.50 AS DECIMAL(10,2)) AS dec, NULL AS n, 'nan'::DOUBLE AS nan_value, "
        "'\\xAA\\xBB'::BLOB AS b, INTERVAL 90 MINUTE AS iv, [1, 2, 3] AS l, "
        "true AS flag, repeat('x', 2000) AS uzun, 9007199254740993 AS katta"
    )
    row = typed["rows"][0]
    assert row[:9] == [
        "2026-11-11",
        "2026-11-11 14:05:00",
        12.5,
        None,
        None,
        "<2 bayt>",
        5400.0,
        "[1, 2, 3]",
        True,
    ]
    assert len(row[9]) == 500
    assert row[9].endswith("…")
    assert row[10] == 9007199254740993
    assert [c["type"] for c in typed["columns"]][:3] == ["DATE", "TIMESTAMP", "DECIMAL(10,2)"]


async def test_timeout_and_memory_limit_do_not_kill_plugin(
    paths: DataPaths, plugin_root: Path
) -> None:
    install_data(
        plugin_root, paths.plugin_data_dir("data"), query_timeout_s=1.5, memory_limit="64MB"
    )
    async with serve_app(paths) as served, served.client() as client:
        data = Data(client)
        pid = (await data.enable())["pid"]

        slow = "SELECT count(*) FROM range(3000000) a, range(3000000) b WHERE a.range + b.range < 0"
        started = asyncio.get_running_loop().time()
        status, detail = await data.rejected(slow)
        elapsed = asyncio.get_running_loop().time() - started
        assert (status, "vaqt chegarasi" in detail) == (408, True)
        assert elapsed < 10, f"so'rov {elapsed:.1f} s da to'xtatildi"
        assert await data.rows("SELECT 41 + 1") == [[42]], "to'xtatilgandan keyin mexanizm ishlaydi"

        hungry = "SELECT list(i) FROM range(60000000) t(i)"
        status, detail = await data.rejected(hungry)
        assert status in (507, 408), (status, detail)
        assert await data.rows("SELECT 1") == [[1]]
        info = (await client.get(PLUGIN)).json()
        assert (info["status"], info["pid"]) == ("running", pid)


# --- eksport, saqlash, o'chirish, qayta ishga tushish ----------------------------------------
async def test_export_save_remove_and_restart(paths: DataPaths, plugin_root: Path) -> None:
    data_dir = paths.plugin_data_dir("data")
    write_samples(install_data(plugin_root, data_dir))
    top = (
        "SELECT mahsulot, sum(soni) AS jami FROM sotuvlar_2026 GROUP BY mahsulot ORDER BY jami DESC"
    )
    async with serve_app(paths) as served, served.client() as client:
        data = Data(client)
        await data.enable()
        await data.load("Sotuvlar 2026.csv")

        exported = await data.post("/export", sql=top, name="hisobot")
        assert exported.status_code == 201, exported.text
        body = exported.json()
        csv_file = data_dir / "exports" / "hisobot.csv"
        assert (body["file"], body["rows"]) == (str(csv_file), 3)
        assert csv_file.read_text(encoding="utf-8").splitlines() == [
            "mahsulot,jami",
            "non,20",
            "qand,15",
            "choy,11",
        ]
        assert (
            await data.post("/export", sql="DROP VIEW sotuvlar_2026", name="x")
        ).status_code == 403
        assert (await data.post("/export", sql=top, name="../qochoq")).status_code == 422
        assert (await data.post("/export", sql="SELECT * FROM yoq", name="y")).status_code == 400
        assert sorted(p.name for p in (data_dir / "exports").iterdir()) == ["hisobot.csv"]

        saved = await data.post("/save", sql=top, name="jami")
        assert saved.status_code == 201, saved.text
        assert (saved.json()["rows"], saved.json()["columns"], saved.json()["state"]) == (
            3,
            2,
            "ready",
        )
        assert await data.rows("SELECT mahsulot FROM jami WHERE jami > 12 ORDER BY 1") == [
            ["non"],
            ["qand"],
        ]
        assert (await data.post("/save", sql=top, name="jami")).status_code == 409

    # qayta ishga tushish: plagin yoqilgan holda qoladi, to'plamlar joyida
    async with serve_app(paths) as served, served.client() as client:
        data = Data(client)
        assert (await client.get(PLUGIN)).json()["status"] == "running"
        names = [d["name"] for d in (await client.get(f"{API}/datasets")).json()]
        assert names == ["jami", "sotuvlar_2026"]
        assert await data.rows("SELECT count(*) FROM sotuvlar_2026") == [[6]]

        removed = await data.post("/remove", name="jami")
        assert removed.json() == {"removed": "jami"}
        assert not (data_dir / "datasets" / "jami.parquet").exists()
        assert (await data.rejected("SELECT * FROM jami"))[0] == 400
        assert (await data.post("/remove", name="jami")).status_code == 404

    with closing(sqlite3.connect(paths.db_file)) as conn:
        rows = conn.execute(
            "SELECT action, ok FROM audit_log WHERE actor = 'plugin:data' ORDER BY id"
        ).fetchall()
    assert rows == [("file.delete", 1)]


async def test_two_hundred_thousand_rows_stream_through(data: Data, paths: DataPaths) -> None:
    inbox = paths.plugin_data_dir("data") / "inbox"
    with (inbox / "katta.csv").open("w", encoding="utf-8", newline="") as handle:
        handle.write("id,guruh,qiymat\n")
        for start in range(0, 200_000, 20_000):
            handle.write("".join(f"{i},g{i % 7},{i * 0.5}\n" for i in range(start, start + 20_000)))
    big = await data.load("katta.csv")
    assert (big["state"], big["rows"], big["columns"]) == ("ready", 200_000, 3)
    assert big["seconds"] < 30
    result = await data.sql(
        "SELECT guruh, count(*) AS n, max(qiymat) AS eng FROM katta GROUP BY guruh ORDER BY guruh"
    )
    assert len(result["rows"]) == 7
    assert sum(row[1] for row in result["rows"]) == 200_000
    assert max(row[2] for row in result["rows"]) == 99_999.5
    assert result["seconds"] < 5
