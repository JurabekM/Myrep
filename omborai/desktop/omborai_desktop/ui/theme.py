from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication) -> None:
    """Fusion uslubi: uchala OS'da bir xil ko'rinadi. Yorug'/tungi rejim tizim sozlamasiga ergashadi."""
    app.setStyle("Fusion")
    font = QFont(app.font())
    font.setPointSize(max(font.pointSize(), 11))
    app.setFont(font)
