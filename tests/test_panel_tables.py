"""Jadval vidjetining kengaytmalari: ustun formati, filtrlar, qator amallari."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from srv1_sdk.panel import PanelSpec, RowAction, TableColumn, TableWidget
from srv1_shell.i18n import I18n
from srv1_shell.pages.data_table import format_cell


def _table(**extra: object) -> dict[str, object]:
    return {
        "type": "table",
        "label": "Jadval",
        "source": "/rows",
        "columns": [{"key": "name", "title": "Nom"}],
        **extra,
    }


def test_table_defaults_are_backward_compatible() -> None:
    panel = PanelSpec.model_validate({"title": "T", "widgets": [_table()]})
    table = panel.widgets[0]
    assert isinstance(table, TableWidget)
    assert (table.filters, table.row_actions, table.auto_refresh) == ((), (), True)
    assert table.columns[0].format == "text"


def test_table_with_filters_and_row_actions() -> None:
    spec = _table(
        filters=[
            {"name": "q", "label": {"uz": "Nom", "ru": "Имя", "en": "Name"}, "required": False}
        ],
        row_actions=[
            {"label": "Savatga", "path": "/delete", "params": ["root", "path"], "confirm": True}
        ],
        columns=[{"key": "size", "title": "Hajm", "format": "size"}],
        auto_refresh=False,
    )
    table = PanelSpec.model_validate({"title": "T", "widgets": [spec]}).widgets[0]
    assert isinstance(table, TableWidget)
    action = table.row_actions[0]
    assert isinstance(action, RowAction)
    assert (action.method, action.params, action.confirm) == ("POST", ("root", "path"), True)
    assert table.filters[0].name == "q"


@pytest.mark.parametrize(
    "extra",
    [
        {"columns": [{"key": "a", "title": "A", "format": "html"}]},
        {"row_actions": [{"label": "X", "path": "http://evil/x", "params": ["id"]}]},
        {"row_actions": [{"label": "X", "path": "/x"}]},
        {"row_actions": [{"label": "X", "path": "/x", "params": ["id"], "method": "TRACE"}]},
        {"filters": [{"name": "q", "label": "Q", "kind": "date"}]},
    ],
)
def test_table_rejects_bad_extensions(extra: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        PanelSpec.model_validate({"title": "T", "widgets": [_table(**extra)]})


def test_format_cell() -> None:
    text = TableColumn(key="a", title="A")
    size = TableColumn(key="a", title="A", format="size")
    when = TableColumn(key="a", title="A", format="datetime")
    uz, en = I18n("uz"), I18n("en")
    assert format_cell(None, size, uz) == ""
    assert format_cell(3 * 1024 * 1024, size, uz) == "3,0 MB"
    assert format_cell(3 * 1024 * 1024, size, en) == "3.0 MB"
    assert format_cell("matn", size, uz) == "matn"
    assert format_cell(42, text, uz) == "42"
    assert format_cell(True, text, uz) == "✓"
    assert format_cell(False, text, uz) == ""
    stamp = datetime(2026, 11, 11, 14, 5).timestamp()
    assert format_cell(stamp, when, uz) == "2026-11-11 14:05"
