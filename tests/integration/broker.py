"""Lokal, konteynerlashtirilgan MQTT broker — CI uchun.

Topshiriqning aniq talabi: **CI testlari `broker.hivemq.com` ga bog'liq
bo'lmasligi kerak** (ADR-0002). Shu bilan birga bu loyihaning eng katta
saboqi ham shu: soxta transport (`tests/harness.py` dagi `LoopbackBus`)
haqiqiy MQTT xulqini to'liq taqlid qilmadi va shu sabab bir nechta
jiddiy xato (o'z aks-sadosi, ikki marta obuna) uzoq vaqt ko'rinmay
qoldi — ular faqat haqiqiy `broker.hivemq.com` ustidagi qo'lda sinovda
ochildi.

Bu modul o'sha ikki talabni BIRLASHTIRADI: haqiqiy MQTT broker (asl
xulqi bilan — aks-sado, TLS, real soket), lekin **lokal va
konteynerlashtirilgan**, hech qanday tashqi tarmoqqa bog'liq emas.

Docker mavjud bo'lmasa (yoki daemon ishlamasa) shu modulni ishlatuvchi
testlar JIMGINA O'TKAZIB YUBORILADI — CI muhitida Docker odatda bor
(GitHub Actions'ning `ubuntu-latest`sida standart), lekin buni
majburiy qilish boshqa sabablarga ko'ra Docker'siz muhitlarni
bloklardi.
"""

from __future__ import annotations

import datetime as dt
import shutil
import socket
import ssl
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

_MOSQUITTO_IMAGE = "eclipse-mosquitto:2"
_CONTAINER_TLS_PORT = 8883


def docker_available() -> bool:
    """Docker CLI bor va daemon javob beryaptimi."""
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _generate_tls_materials(directory: Path) -> Path:
    """O'z-o'zini imzolagan CA + `localhost` uchun server sertifikati.

    Faqat sinov uchun — maxfiy kalit bu yerda hech qanday himoyasiz,
    har safar yangidan yaratiladi va konteyner o'chirilganda tashlanadi.
    """
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "DistribOS Test CA")])
    ca_ski = x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key())
    now = dt.datetime.now(dt.UTC)
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        # Zamonaviy OpenSSL (Python 3.13, `ssl` moduli) sertifikat
        # zanjirini qurishda AuthorityKeyIdentifier'ni talab qiladi —
        # busiz "Missing Authority Key Identifier" bilan rad etadi.
        .add_extension(ca_ski, critical=False)
        # `path_length` berilgan bo'lsa `keyCertSign` ham SHART —
        # aks holda OpenSSL "Path length given without key usage
        # keyCertSign" bilan rad etadi.
        .add_extension(
            x509.KeyUsage(
                digital_signature=False, content_commitment=False,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=True, crl_sign=True,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(ca_key, hashes.SHA256())
    )

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1")),
            ]),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(ca_ski),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )

    (directory / "ca.crt").write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    (directory / "server.crt").write_bytes(
        server_cert.public_bytes(serialization.Encoding.PEM)
    )
    (directory / "server.key").write_bytes(server_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    return directory / "ca.crt"


_MOSQUITTO_CONF = f"""\
listener {_CONTAINER_TLS_PORT} 0.0.0.0
cafile /mosquitto/certs/ca.crt
certfile /mosquitto/certs/server.crt
keyfile /mosquitto/certs/server.key
allow_anonymous true
persistence false
log_dest stdout
"""


@dataclass(frozen=True, slots=True)
class LocalBroker:
    """Ishga tushirilgan lokal broker haqida ma'lumot."""

    host: str
    port: int
    ca_cert_path: Path


class LocalMosquittoBroker:
    """TLS yoqilgan Mosquitto konteynerini boshqaradi.

    ```
    with LocalMosquittoBroker() as broker:
        settings = MqttSettings(host=broker.host, port=broker.port,
                                 ca_cert_path=broker.ca_cert_path, ...)
    ```
    """

    def __init__(self, tmp_path: Path) -> None:
        self._tmp_path = tmp_path
        self._container_name = f"distribos-test-mosquitto-{uuid.uuid4().hex[:8]}"
        self._port = _free_tcp_port()
        self._ca_cert_path: Path | None = None

    def start(self, *, timeout: float = 20.0) -> LocalBroker:
        certs_dir = self._tmp_path / "certs"
        certs_dir.mkdir(parents=True, exist_ok=True)
        self._ca_cert_path = _generate_tls_materials(certs_dir)

        conf_path = self._tmp_path / "mosquitto.conf"
        conf_path.write_text(_MOSQUITTO_CONF, encoding="utf-8")

        subprocess.run(
            [
                "docker", "run", "-d", "--rm",
                "--name", self._container_name,
                "-p", f"127.0.0.1:{self._port}:{_CONTAINER_TLS_PORT}",
                "-v", f"{certs_dir}:/mosquitto/certs:ro",
                "-v", f"{conf_path}:/mosquitto/config/mosquitto.conf:ro",
                _MOSQUITTO_IMAGE,
            ],
            check=True, capture_output=True, timeout=timeout,
        )

        self._wait_ready(timeout=timeout)
        return LocalBroker(
            host="localhost", port=self._port, ca_cert_path=self._ca_cert_path
        )

    def _wait_ready(self, *, timeout: float) -> None:
        # TCP ochilishini emas, TLS QO'L BERISHUVINI kutamiz — port ochiq
        # bo'lishi mumkin, lekin listener hali sertifikatni yuklamagan
        # bo'lishi mumkin.
        assert self._ca_cert_path is not None
        context = ssl.create_default_context(cafile=str(self._ca_cert_path))
        deadline = time.monotonic() + timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                with (
                    socket.create_connection(("localhost", self._port), timeout=1) as sock,
                    context.wrap_socket(sock, server_hostname="localhost"),
                ):
                    return
            except (OSError, ssl.SSLError) as exc:
                last_error = exc
                time.sleep(0.3)
        raise RuntimeError(
            f"Lokal Mosquitto {timeout}s ichida tayyor bo'lmadi: {last_error}"
        )

    def stop(self) -> None:
        subprocess.run(
            ["docker", "stop", self._container_name],
            capture_output=True, timeout=15, check=False,
        )

    def __enter__(self) -> LocalBroker:
        return self.start()

    def __exit__(self, *_exc_info: object) -> None:
        self.stop()
