"""`files` plagini paneli (uch tilda)."""

from srv1_sdk.panel import (
    ButtonWidget,
    FormField,
    FormWidget,
    PanelSpec,
    RowAction,
    TableColumn,
    TableWidget,
    ValueWidget,
)


def _t(uz: str, ru: str, en: str) -> dict[str, str]:
    return {"uz": uz, "ru": ru, "en": en}


_ROOT = FormField(name="root", label=_t("Ildiz №", "Корень №", "Root #"), kind="number")
_PATH = FormField(name="path", label=_t("Yoʻl", "Путь", "Path"))


def build_panel() -> PanelSpec:
    return PanelSpec(
        title=_t("Fayllar", "Файлы", "Files"),
        widgets=(
            ValueWidget(label=_t("Fayllar", "Файлы", "Files"), source="/status", field="files"),
            ValueWidget(label=_t("Papkalar", "Папки", "Folders"), source="/status", field="dirs"),
            ValueWidget(
                label=_t("Savatda", "В корзине", "In trash"), source="/status", field="trash"
            ),
            TableWidget(
                label=_t("Kuzatilayotgan papkalar", "Отслеживаемые папки", "Watched folders"),
                source="/roots",
                refresh_s=10,
                columns=(
                    TableColumn(key="root", title="№"),
                    TableColumn(key="label", title=_t("Nom", "Имя", "Name")),
                    TableColumn(key="path", title=_t("Yoʻl", "Путь", "Path")),
                    TableColumn(key="files", title=_t("Fayllar", "Файлы", "Files")),
                ),
            ),
            ButtonWidget(label=_t("Qayta skanerlash", "Пересканировать", "Rescan"), path="/rescan"),
            TableWidget(
                label=_t("Qidiruv", "Поиск", "Search"),
                source="/search",
                refresh_s=10,
                filters=(
                    FormField(name="q", label=_t("Nom", "Имя", "Name"), required=False),
                    FormField(
                        name="ext", label=_t("Kengaytma", "Расширение", "Extension"), required=False
                    ),
                ),
                columns=(
                    TableColumn(key="name", title=_t("Nom", "Имя", "Name")),
                    TableColumn(key="folder", title=_t("Papka", "Папка", "Folder")),
                    TableColumn(key="root", title="№"),
                    TableColumn(key="size", title=_t("Hajm", "Размер", "Size"), format="size"),
                    TableColumn(
                        key="mtime", title=_t("Oʻzgargan", "Изменён", "Modified"), format="datetime"
                    ),
                ),
                row_actions=(
                    RowAction(
                        label=_t("Savatga", "В корзину", "Move to trash"),
                        path="/delete",
                        params=("root", "path"),
                        confirm=True,
                    ),
                ),
            ),
            FormWidget(
                label=_t("Papka yaratish", "Создать папку", "Create folder"),
                path="/mkdir",
                fields=(_ROOT, _PATH),
            ),
            FormWidget(
                label=_t("Nomini oʻzgartirish", "Переименовать", "Rename"),
                path="/rename",
                fields=(
                    _ROOT,
                    _PATH,
                    FormField(name="new_name", label=_t("Yangi nom", "Новое имя", "New name")),
                ),
            ),
            FormWidget(
                label=_t("Koʻchirish", "Переместить", "Move"),
                path="/move",
                fields=(
                    _ROOT,
                    _PATH,
                    FormField(
                        name="dest_root",
                        label=_t("Manzil ildizi №", "Корень назначения №", "Destination root #"),
                        kind="number",
                    ),
                    FormField(
                        name="dest_path",
                        label=_t("Manzil papka", "Папка назначения", "Destination folder"),
                        required=False,
                    ),
                ),
            ),
            TableWidget(
                label=_t("Savat", "Корзина", "Trash"),
                source="/trash",
                refresh_s=10,
                columns=(
                    TableColumn(key="name", title=_t("Nom", "Имя", "Name")),
                    TableColumn(key="path", title=_t("Asl joyi", "Откуда", "Original path")),
                    TableColumn(key="size", title=_t("Hajm", "Размер", "Size"), format="size"),
                    TableColumn(
                        key="deleted",
                        title=_t("Oʻchirilgan", "Удалён", "Deleted"),
                        format="datetime",
                    ),
                ),
                row_actions=(
                    RowAction(
                        label=_t("Tiklash", "Восстановить", "Restore"),
                        path="/trash/restore",
                        params=("id",),
                    ),
                    RowAction(
                        label=_t("Butunlay oʻchirish", "Удалить навсегда", "Delete permanently"),
                        path="/trash/purge",
                        params=("id",),
                        confirm=True,
                    ),
                ),
            ),
            ButtonWidget(
                label=_t("Savatni boʻshatish", "Очистить корзину", "Empty trash"),
                method="DELETE",
                path="/trash",
                confirm=True,
            ),
        ),
    )
