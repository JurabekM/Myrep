"""Hamma modal dialoglar shu yerdan o'tadi — GUI testida almashtiriladi (T15)."""

from __future__ import annotations

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QInputDialog, QLineEdit, QMessageBox, QWidget)


def xabar(ota: QWidget | None, sarlavha: str, matn: str) -> None:
    QMessageBox.information(ota, sarlavha, matn)


def xato(ota: QWidget | None, sarlavha: str, matn: str) -> None:
    QMessageBox.warning(ota, sarlavha, matn)


def tasdiq(ota: QWidget | None, sarlavha: str, matn: str) -> bool:
    r = QMessageBox.question(ota, sarlavha, matn,
                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                             QMessageBox.StandardButton.No)
    return r == QMessageBox.StandardButton.Yes


def fayl_och(ota: QWidget | None, sarlavha: str, filtr: str) -> str:
    return QFileDialog.getOpenFileName(ota, sarlavha, "", filtr)[0]


def fayl_saqla(ota: QWidget | None, sarlavha: str, nom: str, filtr: str) -> str:
    return QFileDialog.getSaveFileName(ota, sarlavha, nom, filtr)[0]


def papka_tanla(ota: QWidget | None, sarlavha: str) -> str:
    return QFileDialog.getExistingDirectory(ota, sarlavha)


def parol(ota: QWidget | None, sarlavha: str, matn: str) -> str | None:
    s, ok = QInputDialog.getText(ota, sarlavha, matn, QLineEdit.EchoMode.Password)
    return s if ok else None


def parol_almashtirish(ota: QWidget | None) -> tuple[str, str, str] | None:
    """(eski, yangi, takror) yoki bekor qilinsa None."""
    d = QDialog(ota)
    d.setWindowTitle("Parolni o'zgartirish")
    f = QFormLayout(d)
    maydonlar = []
    for nom in ("Joriy parol", "Yangi parol", "Yangi parol (takror)"):
        e = QLineEdit()
        e.setEchoMode(QLineEdit.EchoMode.Password)
        f.addRow(nom, e)
        maydonlar.append(e)
    t = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                         | QDialogButtonBox.StandardButton.Cancel)
    t.accepted.connect(d.accept)
    t.rejected.connect(d.reject)
    f.addRow(t)
    if d.exec() != QDialog.DialogCode.Accepted:
        return None
    return tuple(e.text() for e in maydonlar)  # type: ignore[return-value]


def pico_sozlash(ota: QWidget | None, portlar: list[tuple[str, str]],
                 import_mumkin: bool) -> dict | None:
    """4.x: Pico'ni sozlash formasi. Qaytaradi: {"port", "rejim": "import"|"yangi",
    "pin", "pin2", "parol"} yoki bekor qilinsa None."""
    from PySide6.QtWidgets import QComboBox, QLabel, QRadioButton

    d = QDialog(ota)
    d.setWindowTitle("Pico imzo kalitini sozlash")
    f = QFormLayout(d)
    port = QComboBox()
    port.setEditable(True)
    port.addItem("auto")
    for p, tavsif in portlar:
        port.addItem(p, tavsif)
    f.addRow("Port", port)
    r_import = QRadioButton("Mavjud kalitni Pico'ga ko'chirish (sertifikat saqlanadi)")
    r_yangi = QRadioButton("Pico ichida YANGI kalit (bankdan yangi sertifikat kerak)")
    r_import.setEnabled(import_mumkin)
    (r_import if import_mumkin else r_yangi).setChecked(True)
    f.addRow(r_import)
    f.addRow(r_yangi)
    maydon = {}
    for kalit, nom in (("pin", "Yangi PIN"), ("pin2", "PIN (takror)"),
                       ("parol", "kalit.json paroli")):
        e = QLineEdit()
        e.setEchoMode(QLineEdit.EchoMode.Password)
        f.addRow(nom, e)
        maydon[kalit] = e
    r_yangi.toggled.connect(lambda yoq: maydon["parol"].setEnabled(not yoq))
    maydon["parol"].setEnabled(r_import.isChecked())
    f.addRow(QLabel("Bosilgandan keyin Pico tugmasini bosing (LED tez miltillaydi)."))
    t = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                         | QDialogButtonBox.StandardButton.Cancel)
    t.accepted.connect(d.accept)
    t.rejected.connect(d.reject)
    f.addRow(t)
    if d.exec() != QDialog.DialogCode.Accepted:
        return None
    return {"port": port.currentText().strip() or "auto",
            "rejim": "import" if r_import.isChecked() else "yangi",
            **{k: e.text() for k, e in maydon.items()}}
