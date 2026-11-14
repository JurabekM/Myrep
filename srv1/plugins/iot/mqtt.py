"""MQTT: Mosquitto'ni boshqarish va `paho-mqtt` klienti (o'z oqimida, `loop_start()`)."""

import asyncio
import base64
import hashlib
import os
import secrets
from collections.abc import Callable
from pathlib import Path
from typing import Any

import paho.mqtt.client as paho
from paho.mqtt.enums import CallbackAPIVersion

from srv1_sdk.context import PluginContext
from srv1_sdk.process import ManagedProcess

from .models import MqttConfig

ENV_MOSQUITTO_EXE = "SRV1_MOSQUITTO_EXE"
BROKER_MEMORY_LIMIT_MB = 128
BROKER_READY_TIMEOUT_S = 10.0
_PBKDF2_ITERATIONS = 101

MessageSink = Callable[[str, bytes], None]


def find_mosquitto() -> Path:
    """`SRV1_MOSQUITTO_EXE`, `tools/mosquitto/mosquitto.exe` yoki standart o'rnatish joyi."""
    override = os.environ.get(ENV_MOSQUITTO_EXE, "").strip()
    if override:
        return Path(override)
    bundled = Path(__file__).resolve().parents[2] / "tools" / "mosquitto" / "mosquitto.exe"
    if bundled.is_file():
        return bundled
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")  # noqa: SIM112
    return Path(program_files) / "mosquitto" / "mosquitto.exe"


def password_line(username: str, password: str) -> str:
    """Mosquitto `password_file` satri: `user:$7$<iter>$<tuz>$<xesh>` (PBKDF2-SHA512).

    Mosquitto 2.1.2 bilan sinalgan (`tests/test_iot_mosquitto.py`). Format mos kelmasa
    broker hech kimni kiritmaydi (ochiq qolmaydi).
    """
    salt = secrets.token_bytes(12)
    digest = hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS, 64)
    encoded_salt = base64.b64encode(salt).decode("ascii")
    encoded_hash = base64.b64encode(digest).decode("ascii")
    return f"{username}:$7${_PBKDF2_ITERATIONS}${encoded_salt}${encoded_hash}"


def broker_config(cfg: MqttConfig, password_file: Path) -> str:
    lines = [
        "# SRV_1 iot plagini yozgan; qo'lda o'zgartirmang.",
        f"listener {cfg.port} {cfg.listen_host}",
        "persistence false",
        "log_dest stdout",
        "log_type error",
        "log_type warning",
        "log_type notice",
    ]
    if cfg.username:
        lines += ["allow_anonymous false", f"password_file {password_file.as_posix()}"]
    else:
        lines.append("allow_anonymous true")
    return "\n".join(lines) + "\n"


class Broker:
    def __init__(self, ctx: PluginContext, cfg: MqttConfig) -> None:
        self._ctx = ctx
        self._cfg = cfg
        self._process: ManagedProcess | None = None
        self.exe = find_mosquitto()
        self.recent: list[str] = []

    @property
    def available(self) -> bool:
        return self.exe.is_file()

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.running

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process is not None and self.running else None

    async def start(self) -> None:
        await self.stop()  # qayta ishga tushirishda o'lgan jarayonning job'i va o'quvchisi yopiladi
        self._ctx.check_port(self._cfg.port)
        config_file = self._ctx.data_path("mosquitto.conf")
        password_file = self._ctx.data_path("mosquitto.passwd")
        await asyncio.to_thread(self._write_files, config_file, password_file)
        env = {k: v for k, v in os.environ.items() if not k.startswith("SRV1_")}
        self._process = await self._ctx.spawn(
            [str(self.exe), "-c", str(config_file)],
            cwd=self._ctx.data_dir,
            env=env,
            memory_limit_mb=BROKER_MEMORY_LIMIT_MB,
            on_line=self._on_line,
        )
        await self._wait_listening()

    def _write_files(self, config_file: Path, password_file: Path) -> None:
        if self._cfg.username:
            line = password_line(self._cfg.username, self._cfg.password)
            password_file.write_text(line + "\n", encoding="utf-8")
        config_file.write_text(broker_config(self._cfg, password_file), encoding="utf-8")

    def _on_line(self, line: str) -> None:
        self.recent = [*self.recent[-19:], line[:300]]

    async def _wait_listening(self) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + BROKER_READY_TIMEOUT_S
        while loop.time() < deadline and self.running:
            try:
                _reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self._cfg.host, self._cfg.port), 0.5
                )
            except (OSError, TimeoutError):
                await asyncio.sleep(0.1)
                continue
            writer.close()
            return
        tail = " | ".join(self.recent[-3:])
        await self.stop()
        raise RuntimeError(f"Mosquitto ishga tushmadi: {tail or 'port ochilmadi'}")

    async def stop(self) -> None:
        process, self._process = self._process, None
        if process is not None:
            await process.stop()


class MqttClient:
    """`paho` o'z oqimida ishlaydi; xabarlar `on_message` ga event loop oqimida yetkaziladi."""

    def __init__(
        self, cfg: MqttConfig, on_message: MessageSink, on_state: Callable[[], None]
    ) -> None:
        self._cfg = cfg
        self._on_message = on_message
        self._on_state = on_state
        self._loop = asyncio.get_running_loop()
        self.connected = False
        self.last_error: str | None = None
        self.subscriptions: list[str] = list(dict.fromkeys(cfg.subscriptions))
        self._client = paho.Client(
            CallbackAPIVersion.VERSION2, client_id=f"srv1-iot-{secrets.token_hex(4)}"
        )
        if cfg.username:
            self._client.username_pw_set(cfg.username, cfg.password)
        self._client.reconnect_delay_set(min_delay=1, max_delay=10)
        self._client.on_connect = self._handle_connect
        self._client.on_disconnect = self._handle_disconnect
        self._client.on_message = self._handle_message

    # --- paho oqimidagi qayta chaqiruvlar ---------------------------------
    def _to_loop(self, callback: Callable[..., None], *args: Any) -> None:  # noqa: ANN401
        if not self._loop.is_closed():
            self._loop.call_soon_threadsafe(callback, *args)

    def _handle_connect(
        self,
        client: paho.Client,
        _userdata: object,
        _flags: object,
        reason: object,
        _props: object,
    ) -> None:
        failed = bool(getattr(reason, "is_failure", False))
        if not failed:
            for topic in self.subscriptions:
                client.subscribe(topic)
        self._to_loop(self._set_state, not failed, str(reason) if failed else None)

    def _handle_disconnect(
        self,
        _client: paho.Client,
        _userdata: object,
        _flags: object,
        reason: object,
        _props: object,
    ) -> None:
        self._to_loop(self._set_state, False, str(reason))

    def _handle_message(
        self, _client: paho.Client, _userdata: object, message: paho.MQTTMessage
    ) -> None:
        self._to_loop(self._on_message, message.topic, bytes(message.payload))

    def _set_state(self, connected: bool, error: str | None) -> None:
        self.connected, self.last_error = connected, error
        self._on_state()

    # --- event loop tomoni ------------------------------------------------
    def start(self) -> None:
        self._client.connect_async(self._cfg.host, self._cfg.port, keepalive=30)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.disconnect()
        self._client.loop_stop()
        self.connected = False

    def publish(self, topic: str, payload: bytes, *, qos: int = 0, retain: bool = False) -> bool:
        """Navbatga qo'yadi; ulanmagan bo'lsa `False`."""
        if not self.connected:
            return False
        info = self._client.publish(topic, payload, qos=qos, retain=retain)
        return info.rc == paho.MQTT_ERR_SUCCESS

    def subscribe(self, topic: str) -> None:
        if topic not in self.subscriptions:
            self.subscriptions.append(topic)
        if self.connected:
            self._client.subscribe(topic)

    def unsubscribe(self, topic: str) -> bool:
        if topic not in self.subscriptions:
            return False
        self.subscriptions.remove(topic)
        if self.connected:
            self._client.unsubscribe(topic)
        return True
