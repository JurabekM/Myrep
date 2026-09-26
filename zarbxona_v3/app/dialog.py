"""Hamma modal dialoglar shu yerdan o'tadi — GUI testida almashtiriladi (T15)."""

from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QMessageBox, QWidget


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
