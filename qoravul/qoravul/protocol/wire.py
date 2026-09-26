"""QVL/1 wire format.

Stream framing : ``u32 BE length || frame``
Frame          : ``ver(1)=1 || type(1) || body``
TLV-lite body  : sequence of ``u16 BE len || bytes`` fields.
"""
from __future__ import annotations

import asyncio
import struct
from enum import IntEnum

VERSION = 1
MAX_FRAME = 64 * 1024


class ProtocolError(Exception):
    """Any malformed, unauthenticated or policy-violating input."""


class FrameType(IntEnum):
    HELLO = 1
    ACCEPT = 2
    DATA = 3
    ALERT = 4
    REJECT = 5
    CLOSE = 6


class Suite(IntEnum):
    CLASSIC = 1  # X25519 only
    PQ_ONLY = 2  # ML-KEM-768 only
    HYBRID = 3  # X25519 + ML-KEM-768

    @property
    def uses_x25519(self) -> bool:
        return self in (Suite.CLASSIC, Suite.HYBRID)

    @property
    def uses_kem(self) -> bool:
        return self in (Suite.PQ_ONLY, Suite.HYBRID)


def pack_fields(fields: list[bytes]) -> bytes:
    out = bytearray()
    for f in fields:
        if len(f) > 0xFFFF:
            raise ProtocolError("field too long")
        out += struct.pack(">H", len(f)) + f
    return bytes(out)


def unpack_fields(body: bytes, expected: int | None = None) -> list[bytes]:
    fields, i = [], 0
    while i < len(body):
        if i + 2 > len(body):
            raise ProtocolError("truncated field header")
        (n,) = struct.unpack_from(">H", body, i)
        i += 2
        if i + n > len(body):
            raise ProtocolError("truncated field")
        fields.append(bytes(body[i : i + n]))
        i += n
    if expected is not None and len(fields) != expected:
        raise ProtocolError(f"expected {expected} fields, got {len(fields)}")
    return fields


def make_frame(ftype: FrameType, body: bytes) -> bytes:
    frame = bytes([VERSION, int(ftype)]) + body
    if len(frame) > MAX_FRAME:
        raise ProtocolError("frame too large")
    return frame


def parse_frame(frame: bytes) -> tuple[FrameType, bytes]:
    if len(frame) < 2:
        raise ProtocolError("short frame")
    if len(frame) > MAX_FRAME:
        raise ProtocolError("frame too large")
    if frame[0] != VERSION:
        raise ProtocolError("bad version")
    try:
        ftype = FrameType(frame[1])
    except ValueError as e:
        raise ProtocolError("unknown frame type") from e
    return ftype, frame[2:]


def encode_stream(frame: bytes) -> bytes:
    """Prefix a frame with its u32 BE length for a byte stream."""
    if len(frame) > MAX_FRAME:
        raise ProtocolError("frame too large")
    return struct.pack(">I", len(frame)) + frame


def reject_frame(reason: str) -> bytes:
    return make_frame(FrameType.REJECT, pack_fields([reason.encode()]))


async def read_frame(reader: asyncio.StreamReader) -> bytes:
    hdr = await reader.readexactly(4)
    (n,) = struct.unpack(">I", hdr)
    if n > MAX_FRAME or n < 2:
        raise ProtocolError("bad frame length")
    return await reader.readexactly(n)


async def write_frame(writer: asyncio.StreamWriter, frame: bytes) -> None:
    writer.write(encode_stream(frame))
    await writer.drain()
