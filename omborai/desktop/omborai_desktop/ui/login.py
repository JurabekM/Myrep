from PySide6.QtWidgets import QDialog

from ..api import ApiClient, ApiError
from .dialogs import LoginDialog


def run_login(api: ApiClient, default_email: str = "") -> bool:
    """Kirish oynasini ko'rsatadi. Muvaffaqiyatli bo'lsa True qaytaradi."""
    dialog = LoginDialog(default_email=default_email)
    while dialog.exec() == QDialog.DialogCode.Accepted:
        email, password = dialog.credentials()
        try:
            api.login(email, password)
        except ApiError as exc:
            dialog.error.setText(exc.message)
            continue
        except Exception as exc:  # noqa: BLE001 - tarmoq xatosi
            dialog.error.setText(f"Serverga ulanib bo'lmadi: {exc}")
            continue
        return True
    return False
