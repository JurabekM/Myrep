"""ESC/POS xom baytlar (termal printer). Kutubxonasiz; tarmoq printeri (9100-port) orqali yuboriladi."""

import socket

ESC = b"\x1b"
GS = b"\x1d"
INIT = ESC + b"@"
CUT = GS + b"V" + b"\x42" + b"\x00"  # qisman kesish
CODEPAGE_CP866 = ESC + b"t" + b"\x11"  # kirill/lotin uchun ko'p printerlarda mos sahifa


def build_receipt_bytes(text: str) -> bytes:
    body = text.replace("\r", "").encode("cp866", errors="replace")
    return INIT + CODEPAGE_CP866 + body + b"\n\n\n" + CUT


def send_to_network_printer(host: str, data: bytes, port: int = 9100, timeout: float = 5.0) -> None:
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(data)
