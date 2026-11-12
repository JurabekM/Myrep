"""`data` plagini paneli (uch tilda)."""

from srv1_sdk.panel import (
    FormField,
    FormWidget,
    LabelWidget,
    PanelSpec,
    QueryWidget,
    RowAction,
    TableColumn,
    TableWidget,
    ValueWidget,
)


def _t(uz: str, ru: str, en: str) -> dict[str, str]:
    return {"uz": uz, "ru": ru, "en": en}


_SQL = FormField(name="sql", label="SQL")
_NAME = FormField(name="name", label=_t("Nom", "Имя", "Name"))


def build_panel() -> PanelSpec:
    return PanelSpec(
        title=_t("Maʼlumotlar", "Данные", "Data"),
        widgets=(
            ValueWidget(
                label=_t("Toʻplamlar", "Наборы", "Datasets"), source="/status", field="ready"
            ),
            ValueWidget(label=_t("Qatorlar", "Строк", "Rows"), source="/status", field="rows"),
            ValueWidget(
                label=_t("Import qilinmoqda", "Импортируется", "Importing"),
                source="/status",
                field="importing",
                refresh_s=2,
            ),
            TableWidget(
                label=_t("Toʻplamlar", "Наборы данных", "Datasets"),
                source="/datasets",
                refresh_s=3,
                columns=(
                    TableColumn(key="name", title=_t("Nom", "Имя", "Name")),
                    TableColumn(key="state", title=_t("Holat", "Состояние", "State")),
                    TableColumn(key="rows", title=_t("Qatorlar", "Строк", "Rows")),
                    TableColumn(key="columns", title=_t("Ustunlar", "Столбцов", "Columns")),
                    TableColumn(key="size", title=_t("Hajm", "Размер", "Size"), format="size"),
                    TableColumn(
                        key="imported", title=_t("Import", "Импорт", "Imported"), format="datetime"
                    ),
                    TableColumn(key="error", title=_t("Xato", "Ошибка", "Error")),
                ),
                row_actions=(
                    RowAction(
                        label=_t("Oʻchirish", "Удалить", "Delete"),
                        path="/remove",
                        params=("name",),
                        confirm=True,
                    ),
                ),
            ),
            TableWidget(
                label=_t("Inbox papkasidagi fayllar", "Файлы в папке inbox", "Files in inbox"),
                source="/inbox",
                refresh_s=5,
                columns=(
                    TableColumn(key="path", title=_t("Fayl", "Файл", "File")),
                    TableColumn(key="size", title=_t("Hajm", "Размер", "Size"), format="size"),
                    TableColumn(
                        key="modified",
                        title=_t("Oʻzgargan", "Изменён", "Modified"),
                        format="datetime",
                    ),
                ),
                row_actions=(
                    RowAction(
                        label=_t("Import qilish", "Импортировать", "Import"),
                        path="/import",
                        params=("path",),
                    ),
                ),
            ),
            FormWidget(
                label=_t("Faylni import qilish", "Импорт файла", "Import a file"),
                path="/import",
                fields=(
                    FormField(name="path", label=_t("Fayl yoʻli", "Путь к файлу", "File path")),
                    FormField(
                        name="name",
                        label=_t("Toʻplam nomi", "Имя набора", "Dataset name"),
                        required=False,
                    ),
                    FormField(
                        name="encoding",
                        label=_t("Kodirovka", "Кодировка", "Encoding"),
                        kind="choice",
                        choices=("auto", "utf-8", "cp1251"),
                    ),
                    FormField(
                        name="separator",
                        label=_t("Ajratgich (CSV)", "Разделитель (CSV)", "Separator (CSV)"),
                        required=False,
                    ),
                    FormField(
                        name="sheet",
                        label=_t("Varaq (Excel)", "Лист (Excel)", "Sheet (Excel)"),
                        required=False,
                    ),
                ),
            ),
            LabelWidget(
                text=_t(
                    "Har toʻplam SQL’da oʻz nomi bilan jadval. Hisobot: SUMMARIZE nom. "
                    "Tuzilma: DESCRIBE nom. Faqat SELECT soʻrovlari bajariladi.",
                    "Каждый набор — таблица с тем же именем. Отчёт: SUMMARIZE имя. "
                    "Структура: DESCRIBE имя. Выполняются только запросы SELECT.",
                    "Each dataset is a table with the same name. Report: SUMMARIZE name. "
                    "Structure: DESCRIBE name. Only SELECT queries are executed.",
                )
            ),
            QueryWidget(
                label=_t("SQL soʻrov", "SQL-запрос", "SQL query"),
                path="/query",
                placeholder="SELECT * FROM … LIMIT 100",
            ),
            FormWidget(
                label=_t(
                    "Natijani CSV ga eksport", "Экспорт результата в CSV", "Export result to CSV"
                ),
                path="/export",
                fields=(_SQL, _NAME),
            ),
            FormWidget(
                label=_t(
                    "Natijani yangi toʻplam sifatida saqlash",
                    "Сохранить результат как новый набор",
                    "Save result as a new dataset",
                ),
                path="/save",
                fields=(_SQL, _NAME),
            ),
        ),
    )
