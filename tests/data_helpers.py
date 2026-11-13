"""`data` plagini testlari uchun: plaginni o'rnatish va namunaviy fayllar (CSV, Parquet, Excel)."""

import json
import shutil
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import polars as pl

from srv1_core.plugins.registry import BUILTIN_DIR

SALES_CSV = """sana,mahsulot,soni,narx
2026-11-01,choy,3,12.5
2026-11-01,qand,10,4.0
2026-11-02,choy,1,12.5
2026-11-02,non,20,3.25
2026-11-03,qand,5,4.0
2026-11-03,choy,7,13.0
"""
CYRILLIC_CSV = "товар;цена;город\nчай;12;Ташкент\nкофе;30;Самарканд\n"


def install_data(plugin_root: Path, plugin_data_dir: Path, **config: object) -> Path:
    """Plaginni `plugin_root` ga nusxalaydi, sozlamasini yozadi va `inbox` papkasini qaytaradi."""
    target = plugin_root / "data"
    shutil.copytree(BUILTIN_DIR / "data", target, ignore=shutil.ignore_patterns("__pycache__"))
    inbox = plugin_data_dir / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    if config:
        (plugin_data_dir / "data.json").write_text(json.dumps({"config": config}), encoding="utf-8")
    return inbox


def allow_folder(plugin_root: Path, folder: Path) -> None:
    """Manifestga import papkasini qo'shadi."""
    manifest = plugin_root / "data" / "plugin.toml"
    text = manifest.read_text(encoding="utf-8")
    assert "paths = []" in text
    manifest.write_text(text.replace("paths = []", f"paths = ['{folder}']"), encoding="utf-8")


def write_samples(inbox: Path) -> None:
    (inbox / "Sotuvlar 2026.csv").write_text(SALES_CSV, encoding="utf-8", newline="")
    (inbox / "kirill.csv").write_bytes(CYRILLIC_CSV.encode("cp1251"))
    (inbox / "jadval.tsv").write_text("a\tb\n1\tbir\n2\tikki\n", encoding="utf-8", newline="")
    frame = pl.DataFrame({"id": [1, 2, 3], "qiymat": [1.5, None, 3.5], "belgi": ["x", "y", None]})
    frame.write_parquet(inbox / "olchov.parquet")
    make_xlsx(
        inbox / "kitob.xlsx",
        {
            "Xodimlar": [["ism", "yosh", "maosh"], ["Ali", 30, 4500.5], ["Vali", 41, 5200]],
            "Bo'limlar": [["bolim", "soni"], ["IT", 4], ["Savdo", 9], ["Ombor", 2]],
        },
    )


def _cell(reference: str, value: object) -> str:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return f'<c r="{reference}"><v>{value}</v></c>'
    return f'<c r="{reference}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def _sheet_xml(rows: list[list[object]]) -> str:
    body = "".join(
        f'<row r="{row_index}">'
        + "".join(
            _cell(f"{chr(65 + column)}{row_index}", value) for column, value in enumerate(row)
        )
        + "</row>"
        for row_index, row in enumerate(rows, start=1)
    )
    namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    sheet = f'<worksheet xmlns="{namespace}"><sheetData>{body}</sheetData></worksheet>'
    return '<?xml version="1.0"?>' + sheet


def make_xlsx(path: Path, sheets: dict[str, list[list[object]]]) -> None:
    """Eng sodda `.xlsx` fayl (Excel yozuvchi kutubxonasiz): har varaq — qatorlar ro'yxati."""
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    office = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    package = "http://schemas.openxmlformats.org/package/2006/relationships"
    content = "http://schemas.openxmlformats.org/package/2006/content-types"
    sheet_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
    rels_type = "application/vnd.openxmlformats-package.relationships+xml"
    book_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="{sheet_type}"/>'
        for i in range(1, len(sheets) + 1)
    )
    sheet_tags = "".join(
        f'<sheet name="{escape(name, {chr(34): "&quot;"})}" sheetId="{i}" r:id="rId{i}"/>'
        for i, name in enumerate(sheets, start=1)
    )
    relations = "".join(
        f'<Relationship Id="rId{i}" Type="{office}/worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(sheets) + 1)
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            f'<?xml version="1.0"?><Types xmlns="{content}">'
            f'<Default Extension="rels" ContentType="{rels_type}"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f'<Override PartName="/xl/workbook.xml" ContentType="{book_type}"/>{overrides}</Types>',
        )
        archive.writestr(
            "_rels/.rels",
            f'<?xml version="1.0"?><Relationships xmlns="{package}">'
            f'<Relationship Id="rId1" Type="{office}/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>",
        )
        archive.writestr(
            "xl/workbook.xml",
            f'<?xml version="1.0"?><workbook xmlns="{main}" xmlns:r="{office}">'
            f"<sheets>{sheet_tags}</sheets></workbook>",
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            f'<?xml version="1.0"?><Relationships xmlns="{package}">{relations}</Relationships>',
        )
        for index, rows in enumerate(sheets.values(), start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(rows))
