# -*- coding: utf-8 -*-
"""Minimal MQTT 3.1.1 klienti — to'liq asyncio, bloklamaydi.

Nima uchun umqtt.simple emas? Chunki u bloklovchi socket ishlatadi va
web-server bilan bir vaqtda ishlaganda butun event loop'ni qotirib qo'yadi.

Qo'llab-quvvatlaydi: CONNECT (LWT bilan), PUBLISH QoS0/QoS1, SUBSCRIBE,
PINGREQ/PINGRESP keepalive, avtomatik qayta ulanish.
"""

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

import time
import logger


class MQTTError(Exception):
    pass


def _enc_len(n):
    """MQTT o'zgaruvchan uzunlik (varint) kodlash."""
    out = bytearray()
    while True:
        b = n % 128
        n //= 128
        if n:
            b |= 0x80
        out.append(b)
        if not n:
            return out


def _enc_str(s):
    if isinstance(s, str):
        s = s.encode()
    return len(s).to_bytes(2, "big") + s


class MQTTClient:
    def __init__(self, client_id, host, port=1883, user=None, password=None,
                 keepalive=60, ssl=False, will=None):
        self.client_id = client_id
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.keepalive = keepalive
        self.ssl = ssl
        self.will = will          # (topic, payload, retain, qos)

        self._r = None
        self._w = None
        self._lock = asyncio.Lock()
        self._pid = 0
        self._pending = {}        # pid -> asyncio.Event (QoS1 PUBACK kutish)
        self._reader_task = None
        self._last_tx = 0
        self._pingresp = True
        self.connected = False
        self.callback = None      # cb(topic: bytes, payload: bytes)
        self.on_connect = None    # async cb()

    # -- past darajali I/O ----------------------------------------------------
    async def _read_n(self, n):
        buf = bytearray()
        while len(buf) < n:
            chunk = await self._r.read(n - len(buf))
            if not chunk:
                raise MQTTError("aloqa uzildi")
            buf += chunk
        return bytes(buf)

    async def _read_len(self):
        n = 0
        shift = 0
        while True:
            b = (await self._read_n(1))[0]
            n |= (b & 0x7F) << shift
            if not b & 0x80:
                return n
            shift += 7
            if shift > 21:
                raise MQTTError("varint juda uzun")

    async def _send(self, data):
        self._w.write(data)
        await self._w.drain()
        self._last_tx = time.ticks_ms()

    def _next_pid(self):
        self._pid = (self._pid % 65535) + 1
        return self._pid

    # -- ulanish --------------------------------------------------------------
    async def connect(self, clean_session=True):
        logger.info("MQTT: %s:%d ga ulanmoqda" % (self.host, self.port))
        kwargs = {}
        if self.ssl:
            kwargs["ssl"] = True
        self._r, self._w = await asyncio.open_connection(self.host, self.port, **kwargs)

        flags = 0
        if clean_session:
            flags |= 0x02
        payload = _enc_str(self.client_id)

        if self.will:
            topic, msg, retain, qos = self.will
            flags |= 0x04 | (qos << 3)
            if retain:
                flags |= 0x20
            payload += _enc_str(topic) + _enc_str(msg)
        if self.user:
            flags |= 0x80
            payload += _enc_str(self.user)
            if self.password:
                flags |= 0x40
                payload += _enc_str(self.password)

        var = (_enc_str("MQTT") + b"\x04" + bytes([flags])
               + self.keepalive.to_bytes(2, "big"))
        pkt = b"\x10" + _enc_len(len(var) + len(payload)) + var + payload
        await self._send(pkt)

        # CONNACK kutamiz
        hdr = await self._read_n(1)
        if hdr[0] != 0x20:
            raise MQTTError("CONNACK kutilgan edi, keldi: 0x%02x" % hdr[0])
        await self._read_len()
        resp = await self._read_n(2)
        rc = resp[1]
        if rc != 0:
            reasons = {1: "protokol versiyasi rad etildi", 2: "client_id rad etildi",
                       3: "server mavjud emas", 4: "login/parol xato",
                       5: "avtorizatsiya rad etildi"}
            raise MQTTError("CONNACK rc=%d: %s" % (rc, reasons.get(rc, "noma'lum")))

        self.connected = True
        self._pingresp = True
        self._reader_task = asyncio.create_task(self._reader())
        logger.info("MQTT ulandi")
        if self.on_connect:
            await self.on_connect()
        return True

    async def disconnect(self):
        try:
            if self._w:
                await self._send(b"\xe0\x00")
        except Exception:
            pass
        await self._close()

    async def _close(self):
        self.connected = False
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        for ev in self._pending.values():
            ev.set()
        self._pending.clear()
        if self._w:
            try:
                self._w.close()
                await self._w.wait_closed()
            except Exception:
                pass
        self._r = self._w = None

    # -- fon oqimi ------------------------------------------------------------
    async def _reader(self):
        try:
            while True:
                hdr = await self._read_n(1)
                op = hdr[0]
                rem = await self._read_len()
                body = await self._read_n(rem) if rem else b""

                if op & 0xF0 == 0x30:            # PUBLISH
                    qos = (op >> 1) & 0x03
                    tlen = int.from_bytes(body[0:2], "big")
                    topic = body[2:2 + tlen]
                    idx = 2 + tlen
                    pid = None
                    if qos > 0:
                        pid = int.from_bytes(body[idx:idx + 2], "big")
                        idx += 2
                    payload = body[idx:]
                    if qos == 1 and pid is not None:
                        await self._send(b"\x40\x02" + pid.to_bytes(2, "big"))
                    if self.callback:
                        try:
                            self.callback(topic, payload)
                        except Exception as e:
                            logger.error("MQTT callback xatosi: %r" % e)

                elif op == 0x40:                 # PUBACK
                    pid = int.from_bytes(body[0:2], "big")
                    ev = self._pending.pop(pid, None)
                    if ev:
                        ev.set()

                elif op == 0x90:                 # SUBACK
                    pass
                elif op == 0xD0:                 # PINGRESP
                    self._pingresp = True
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warn("MQTT reader to'xtadi: %r" % e)
            self.connected = False

    # -- publish / subscribe --------------------------------------------------
    async def publish(self, topic, msg, retain=False, qos=0, timeout=5):
        if not self.connected:
            raise MQTTError("ulanmagan")
        if isinstance(msg, str):
            msg = msg.encode()

        op = 0x30 | (qos << 1) | (1 if retain else 0)
        var = _enc_str(topic)
        pid = None
        if qos > 0:
            pid = self._next_pid()
            var += pid.to_bytes(2, "big")
        pkt = bytes([op]) + _enc_len(len(var) + len(msg)) + var + msg

        async with self._lock:
            await self._send(pkt)

        if qos > 0:
            ev = asyncio.Event()
            self._pending[pid] = ev
            try:
                await asyncio.wait_for(ev.wait(), timeout)
            except asyncio.TimeoutError:
                self._pending.pop(pid, None)
                raise MQTTError("PUBACK kelmadi (pid=%d)" % pid)
        return True

    async def subscribe(self, topic, qos=0):
        if not self.connected:
            raise MQTTError("ulanmagan")
        pid = self._next_pid()
        body = pid.to_bytes(2, "big") + _enc_str(topic) + bytes([qos])
        async with self._lock:
            await self._send(b"\x82" + _enc_len(len(body)) + body)
        logger.debug("MQTT subscribe: %s" % topic)

    async def ping(self):
        async with self._lock:
            self._pingresp = False
            await self._send(b"\xc0\x00")

    async def keepalive_task(self):
        """Keepalive'ning yarmida PINGREQ yuboradi; javob kelmasa ulanishni uzadi."""
        interval = max(self.keepalive // 2, 5)
        while True:
            await asyncio.sleep(interval)
            if not self.connected:
                continue
            idle = time.ticks_diff(time.ticks_ms(), self._last_tx) / 1000
            if idle < interval:
                continue
            try:
                await self.ping()
                await asyncio.sleep(5)
                if not self._pingresp:
                    logger.warn("MQTT: PINGRESP kelmadi — uzamiz")
                    await self._close()
            except Exception as e:
                logger.warn("MQTT keepalive xatosi: %r" % e)
                await self._close()
