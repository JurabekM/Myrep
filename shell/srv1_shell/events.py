"""Hodisalar oqimi: `QWebSocket` orqali `/ws/events`, uzilganda o'zi qayta ulanadi."""

import json
from typing import Any, cast

from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtNetwork import QAbstractSocket, QNetworkRequest
from PyQt6.QtWebSockets import QWebSocket

RECONNECT_MS = 2000


class EventStream(QObject):
    """`received(topic, data)` va `connection_changed(bool)` signallarini beradi."""

    received = pyqtSignal(str, dict)
    connection_changed = pyqtSignal(bool)

    def __init__(self, ws_url: str, token: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._url = QUrl(f"{ws_url}?topics=*")
        self._token = token.encode("ascii")
        self._running = False
        self._connected = False
        self._socket = QWebSocket(parent=self)
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.textMessageReceived.connect(self._on_message)
        self._retry = QTimer(self)
        self._retry.setSingleShot(True)
        self._retry.setInterval(RECONNECT_MS)
        self._retry.timeout.connect(self._open)

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        self._running = True
        self._open()

    def stop(self) -> None:
        self._running = False
        self._retry.stop()
        self._socket.abort()

    def _open(self) -> None:
        if not self._running:
            return
        if self._socket.state() != QAbstractSocket.SocketState.UnconnectedState:
            return
        request = QNetworkRequest(self._url)
        request.setRawHeader(b"Authorization", b"Bearer " + self._token)
        self._socket.open(request)

    def _on_connected(self) -> None:
        self._connected = True
        self.connection_changed.emit(True)

    def _on_disconnected(self) -> None:
        was_connected, self._connected = self._connected, False
        if was_connected:
            self.connection_changed.emit(False)
        if self._running:
            self._retry.start()

    def _on_message(self, text: str) -> None:
        try:
            message = json.loads(text)
        except ValueError:
            return
        if not isinstance(message, dict):
            return
        typed = cast(dict[str, Any], message)
        topic, data = typed.get("topic"), typed.get("data")
        if isinstance(topic, str) and isinstance(data, dict):
            self.received.emit(topic, data)
