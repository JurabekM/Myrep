"""Interfeys matnlari: har kalit uchun uch til (uz, ru, en). Yangi matn — shu yerga."""

LANGUAGE_NAMES: dict[str, str] = {"uz": "Oʻzbekcha", "ru": "Русский", "en": "English"}
DEFAULT_LANGUAGE = "uz"


def _t(uz: str, ru: str, en: str) -> dict[str, str]:
    return {"uz": uz, "ru": ru, "en": en}


TEXTS: dict[str, dict[str, str]] = {
    # --- umumiy -----------------------------------------------------------
    "app.title": _t("SRV_1 boshqaruvi", "Управление SRV_1", "SRV_1 Control"),
    "common.yes": _t("Ha", "Да", "Yes"),
    "common.no": _t("Yoʻq", "Нет", "No"),
    "common.refresh": _t("Yangilash", "Обновить", "Refresh"),
    "header.language": _t("Til", "Язык", "Language"),
    "conn.connected": _t("Ulangan", "Подключено", "Connected"),
    "conn.disconnected": _t("Ulanmagan", "Нет соединения", "Disconnected"),
    "conn.core": _t("Yadro {address}", "Ядро {address}", "Core {address}"),
    "error.network": _t(
        "Yadroga ulanib boʻlmadi", "Не удалось подключиться к ядру", "Cannot reach the core"
    ),
    "error.unauthorized": _t("Token notoʻgʻri", "Неверный токен", "Invalid token"),
    "error.http": _t(
        "Xato {status}: {detail}", "Ошибка {status}: {detail}", "Error {status}: {detail}"
    ),
    "token.title": _t("Yadro tokeni", "Токен ядра", "Core token"),
    "token.prompt": _t(
        "Token fayli topilmadi:\n{path}\n\nTokenni qoʻlda kiriting:",
        "Файл токена не найден:\n{path}\n\nВведите токен вручную:",
        "Token file not found:\n{path}\n\nEnter the token manually:",
    ),
    # --- navigatsiya ------------------------------------------------------
    "nav.system": _t("Tizim", "Система", "System"),
    "nav.plugins": _t("Plaginlar", "Плагины", "Plugins"),
    "nav.logs": _t("Jurnal", "Журнал", "Log"),
    "nav.memory": _t("Xotira", "Память", "Memory"),
    # --- tizim ------------------------------------------------------------
    "system.cpu": _t("Protsessor", "Процессор", "CPU"),
    "system.memory": _t("Tezkor xotira", "Оперативная память", "Memory"),
    "system.core": _t("Yadro jarayoni", "Процесс ядра", "Core process"),
    "system.disks": _t("Disklar", "Диски", "Disks"),
    "system.chart": _t("Yuklama, %", "Нагрузка, %", "Load, %"),
    "system.series.cpu": _t("Protsessor", "Процессор", "CPU"),
    "system.series.memory": _t("Xotira", "Память", "Memory"),
    "system.cores": _t("{n} ta mantiqiy yadro", "логических ядер: {n}", "{n} logical cores"),
    "system.memory_detail": _t("{used} / {total}", "{used} / {total}", "{used} / {total}"),
    "system.core_detail": _t(
        "PID {pid}, {threads} ta oqim",
        "PID {pid}, потоков: {threads}",
        "PID {pid}, {threads} threads",
    ),
    "system.disk_free": _t(
        "{free} boʻsh / {total}", "свободно {free} / {total}", "{free} free / {total}"
    ),
    # --- plaginlar --------------------------------------------------------
    "plugins.col.name": _t("Nom", "Имя", "Name"),
    "plugins.col.version": _t("Versiya", "Версия", "Version"),
    "plugins.col.mode": _t("Rejim", "Режим", "Mode"),
    "plugins.col.status": _t("Holat", "Состояние", "Status"),
    "plugins.col.description": _t("Tavsif", "Описание", "Description"),
    "plugins.col.action": _t("Amal", "Действие", "Action"),
    "plugins.enable": _t("Yoqish", "Включить", "Enable"),
    "plugins.disable": _t("Oʻchirish", "Отключить", "Disable"),
    "plugins.empty": _t("Plaginlar topilmadi", "Плагины не найдены", "No plugins found"),
    "plugins.heavy": _t("ogʻir", "тяжёлый", "heavy"),
    "plugins.error": _t("{name}: {error}", "{name}: {error}", "{name}: {error}"),
    "status.running": _t("Ishlayapti", "Работает", "Running"),
    "status.stopped": _t("Toʻxtagan", "Остановлен", "Stopped"),
    "status.error": _t("Ishga tushmadi", "Не запустился", "Failed to start"),
    "status.crashed": _t("Yiqilgan", "Сбой", "Crashed"),
    "status.invalid": _t("Yaroqsiz", "Некорректен", "Invalid"),
    "mode.inprocess": _t("Yadro ichida", "Внутри ядра", "In core"),
    "mode.subprocess": _t("Alohida jarayon", "Отдельный процесс", "Separate process"),
    # --- jurnal -----------------------------------------------------------
    "logs.level": _t("Daraja", "Уровень", "Level"),
    "logs.all": _t("Hammasi", "Все", "All"),
    "logs.pause": _t("Toʻxtatib turish", "Пауза", "Pause"),
    "logs.clear": _t("Tozalash", "Очистить", "Clear"),
    # --- xotira -----------------------------------------------------------
    "memory.col.process": _t("Jarayon", "Процесс", "Process"),
    "memory.col.pid": _t("PID", "PID", "PID"),
    "memory.col.ws": _t("Ishchi toʻplam", "Рабочий набор", "Working set"),
    "memory.col.private": _t("Xususiy", "Частная", "Private"),
    "memory.core": _t("Yadro", "Ядро", "Core"),
    "memory.shell": _t("Shell (shu oyna)", "Shell (это окно)", "Shell (this window)"),
    "memory.plugin": _t("Plagin: {name}", "Плагин: {name}", "Plugin: {name}"),
    "memory.total": _t(
        "Jami {used} — chegara {budget}",
        "Всего {used} — лимит {budget}",
        "Total {used} — limit {budget}",
    ),
    "memory.note": _t(
        "Chegara boʻsh holat uchun: yadro + Caddy + shell.",
        "Лимит для состояния покоя: ядро + Caddy + shell.",
        "The limit applies to the idle state: core + Caddy + shell.",
    ),
    # --- plagin paneli ----------------------------------------------------
    "panel.submit": _t("Yuborish", "Отправить", "Submit"),
    "panel.search": _t("Qidirish", "Найти", "Search"),
    "panel.show": _t("Koʻrsatish", "Показать", "Show"),
    "panel.confirm.title": _t("Tasdiqlash", "Подтверждение", "Confirm"),
    "panel.confirm.text": _t(
        "«{action}» bajarilsinmi?", "Выполнить «{action}»?", "Run “{action}”?"
    ),
    "panel.required": _t(
        "«{field}» toʻldirilishi shart", "Поле «{field}» обязательно", "“{field}” is required"
    ),
    "panel.number": _t(
        "«{field}» son boʻlishi kerak",
        "Поле «{field}» должно быть числом",
        "“{field}” must be a number",
    ),
    "panel.done": _t("Bajarildi: {result}", "Выполнено: {result}", "Done: {result}"),
}
