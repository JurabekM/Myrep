"""Yadro API klienti: `httpx` alohida oqimda, javob GUI oqimiga signal bilan qaytadi."""

import itertools
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, cast

import httpx
from PyQt6 import sip
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

# Plagin so'rovi yadroda 30 s gacha kutilishi mumkin.
_TIMEOUT = httpx.Timeout(35.0, connect=3.0)


@dataclass(frozen=True, slots=True)
class Reply:
    """`status == 0` — yadroga ulanib bo'lmadi."""

    status: int
    data: Any
    error: str

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def rows(self) -> list[dict[str, Any]]:
        """JSON ro'yxat javobi; boshqa narsa kelsa bo'sh ro'yxat."""
        data: Any = self.data
        return cast(list[dict[str, Any]], data) if isinstance(data, list) else []


ReplyCallback = Callable[[Reply], None]


def _to_reply(response: httpx.Response) -> Reply:
    data: Any = None
    if response.headers.get("content-type", "").startswith("application/json"):
        try:
            data = response.json()
        except ValueError:
            data = None
    else:
        data = response.text
    error = ""
    if response.status_code >= 400:
        detail = data.get("detail") if isinstance(data, dict) else None  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        error = str(detail) if detail else response.reason_phrase  # pyright: ignore[reportUnknownArgumentType]
    return Reply(response.status_code, data, error)


class _Worker(QObject):
    """Fon oqimida yashaydi; so'rovlarni ketma-ket bajaradi."""

    finished = pyqtSignal(int, object)

    def __init__(self) -> None:
        super().__init__()
        self._client: httpx.Client | None = None

    @pyqtSlot(int, str, str, object, object, object)
    def perform(
        self, request_id: int, method: str, url: str, headers: object, params: object, body: object
    ) -> None:
        if self._client is None:
            self._client = httpx.Client(timeout=_TIMEOUT)
        try:
            response = self._client.request(
                method,
                url,
                headers=headers,  # pyright: ignore[reportArgumentType]
                params=params,  # pyright: ignore[reportArgumentType]
                json=body,
            )
            reply = _to_reply(response)
        except httpx.HTTPError as exc:
            reply = Reply(0, None, str(exc) or type(exc).__name__)
        self.finished.emit(request_id, reply)

    @pyqtSlot()
    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


class Api(QObject):
    """`request()` darhol qaytadi; `callback` GUI oqimida chaqiriladi.

    `owner` o'chirilgan bo'lsa (sahifa yopilgan), javob tashlab yuboriladi.
    """

    _perform = pyqtSignal(int, str, str, object, object, object)
    _close = pyqtSignal()

    def __init__(self, base_url: str, token: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}"}
        self._ids = itertools.count(1)
        self._pending: dict[int, tuple[QObject, ReplyCallback]] = {}
        self._thread = QThread(self)
        self._worker = _Worker()
        self._worker.moveToThread(self._thread)
        self._perform.connect(self._worker.perform)
        self._close.connect(self._worker.close)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()

    def set_token(self, token: str) -> None:
        """Yadro shell ochilgandan keyin ishga tushsa, token keyinroq ma'lum bo'ladi."""
        self._headers = {"Authorization": f"Bearer {token}"}

    def request(
        self,
        method: str,
        path: str,
        callback: ReplyCallback,
        *,
        owner: QObject,
        params: Mapping[str, Any] | None = None,
        body: Any = None,  # noqa: ANN401 — ixtiyoriy JSON
    ) -> None:
        request_id = next(self._ids)
        self._pending[request_id] = (owner, callback)
        self._perform.emit(
            request_id, method, self._base_url + path, self._headers, dict(params or {}), body
        )

    def get(self, path: str, callback: ReplyCallback, *, owner: QObject) -> None:
        self.request("GET", path, callback, owner=owner)

    def post(self, path: str, callback: ReplyCallback, *, owner: QObject) -> None:
        self.request("POST", path, callback, owner=owner)

    @pyqtSlot(int, object)
    def _on_finished(self, request_id: int, reply: object) -> None:
        owner, callback = self._pending.pop(request_id, (None, None))
        if owner is None or callback is None or sip.isdeleted(owner):
            return
        if isinstance(reply, Reply):
            callback(reply)

    def shutdown(self) -> None:
        """Oyna yopilishidan oldin chaqiriladi: oqim toza to'xtaydi."""
        self._pending.clear()
        self._close.emit()
        self._thread.quit()
        self._thread.wait(5000)
