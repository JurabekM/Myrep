# -*- coding: utf-8 -*-
"""
Qt moslik qatlami (compat shim).

PyQt6 birinchi tanlov; bo'lmasa PySide6. Ikkalasi ham topilmasa aniq
xato beriladi. Qolgan GUI kodi faqat shu moduldan import qiladi —
dvigatel almashtirilsa boshqa fayllar o'zgармaydi.
"""
from __future__ import annotations

QT_BINDING = ""

try:  # 1-tanlov: PyQt6
    from PyQt6 import QtCore, QtGui, QtWidgets  # noqa: F401
    from PyQt6.QtCore import Qt, QSize, QTimer, QUrl, pyqtSignal as Signal
    QT_BINDING = "PyQt6"

    try:
        from PyQt6.QtCharts import (  # noqa: F401
            QChart, QChartView, QBarSeries, QBarSet, QLineSeries,
            QValueAxis, QBarCategoryAxis, QPieSeries,
        )
        HAS_CHARTS = True
    except ImportError:
        HAS_CHARTS = False

    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
        from PyQt6.QtWebEngineCore import (  # noqa: F401
            QWebEngineProfile, QWebEngineSettings,
        )
        from PyQt6.QtNetwork import QNetworkCookie  # noqa: F401
        HAS_WEBENGINE = True
    except ImportError:
        HAS_WEBENGINE = False

except ImportError:
    try:  # 2-tanlov: PySide6
        from PySide6 import QtCore, QtGui, QtWidgets  # noqa: F401
        from PySide6.QtCore import Qt, QSize, QTimer, QUrl, Signal  # noqa: F401
        QT_BINDING = "PySide6"

        try:
            from PySide6.QtCharts import (  # noqa: F401
                QChart, QChartView, QBarSeries, QBarSet, QLineSeries,
                QValueAxis, QBarCategoryAxis, QPieSeries,
            )
            HAS_CHARTS = True
        except ImportError:
            HAS_CHARTS = False

        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
            from PySide6.QtWebEngineCore import (  # noqa: F401
                QWebEngineProfile, QWebEngineSettings,
            )
            from PySide6.QtNetwork import QNetworkCookie  # noqa: F401
            HAS_WEBENGINE = True
        except ImportError:
            HAS_WEBENGINE = False

    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Desktop GUI uchun PyQt6 yoki PySide6 kerak. "
            "O'rnatish: pip install PyQt6 PyQt6-Charts PyQt6-WebEngine"
        ) from exc


def is_available() -> bool:
    """GUI dvigateli mavjudligini bildiradi."""
    return bool(QT_BINDING)
