"""Konfiguratsiya — validatsiya bilan, fail-closed.

Noto'g'ri konfiguratsiya jim tuzatilmaydi: ilova ishga tushmaydi va sabab
aniq aytiladi. Ayniqsa broker profili — ADR-0002 ga qarang.
"""

from __future__ import annotations

import enum
import os
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

#: HiveMQ ning ochiq brokeri. Bu hostda `PRIVATE_PRODUCTION` TAQIQLANADI.
PUBLIC_PILOT_HOSTS: frozenset[str] = frozenset(
    {"broker.hivemq.com", "broker.mqttdashboard.com"}
)

#: Rasmiy manbadan tekshirilgan (mqtt-dashboard.com, 2026-08-23): TLS = 8883.
PUBLIC_PILOT_TLS_PORT = 8883


class MqttProfile(enum.StrEnum):
    PUBLIC_PILOT = "PUBLIC_PILOT"
    PRIVATE_PRODUCTION = "PRIVATE_PRODUCTION"


class ConfigError(RuntimeError):
    """Konfiguratsiya yaroqsiz. Ilova ishga tushmaydi."""


class MqttSettings(BaseModel):
    """MQTT transport sozlamalari.

    DIQQAT: `session_expiry_seconds` — bu bizning **so'rovimiz**. Broker
    CONNACK'da kamroq qiymat qaytarishi mumkin; haqiqiy qiymat ulanishdan
    keyin `mqtt.client` dan olinadi, bu yerdagi son taxmin sifatida
    ishlatilmaydi (ADR-0003).
    """

    profile: MqttProfile = MqttProfile.PUBLIC_PILOT
    host: str = "broker.hivemq.com"
    port: int = PUBLIC_PILOT_TLS_PORT
    tls_required: bool = True
    clean_start: bool = False
    session_expiry_seconds: int = 3600
    keepalive_seconds: int = 60
    username: str | None = None
    password: str | None = None
    client_cert_path: Path | None = None
    client_key_path: Path | None = None
    ca_cert_path: Path | None = None

    #: Public brokerga yuboriladigan xabar hajmi qat'iy cheklanadi.
    max_payload_bytes: int = 256 * 1024

    @model_validator(mode="after")
    def _enforce_public_pilot(self) -> MqttSettings:
        host = self.host.strip().lower()

        # 1. Ochiq broker HECH QACHON production deb belgilanmaydi (ADR-0002).
        if host in PUBLIC_PILOT_HOSTS and self.profile is MqttProfile.PRIVATE_PRODUCTION:
            raise ConfigError(
                f"'{self.host}' — ochiq (public) broker. Uni "
                "PRIVATE_PRODUCTION profili bilan ishlatish taqiqlanadi. "
                "HiveMQ o'z shartlarida bu brokerni Production/Dev/Staging/UAT "
                "muhitlarida ishlatishni man qiladi. Xususiy broker manzilini "
                "ko'rsating yoki profilni PUBLIC_PILOT ga o'zgartiring."
            )

        # 2. TLS — har ikkala profilda ham majburiy.
        if not self.tls_required:
            raise ConfigError(
                "MQTT_TLS_REQUIRED=false qo'llab-quvvatlanmaydi. Payload "
                "AETHER-Q bilan himoyalangan bo'lsa ham, metama'lumot "
                "(topik nomlari, xabar vaqti va hajmi) ochiq qoladi."
            )

        # 3. Public pilotda hajm chegarasi oshirilmaydi.
        if self.profile is MqttProfile.PUBLIC_PILOT and self.max_payload_bytes > 256 * 1024:
            raise ConfigError(
                "PUBLIC_PILOT profilida xabar hajmi 256 KiB dan oshmasligi kerak."
            )

        if self.max_payload_bytes < 1024:
            raise ConfigError("max_payload_bytes juda kichik (minimum 1 KiB).")

        return self

    @property
    def is_public_pilot(self) -> bool:
        return self.profile is MqttProfile.PUBLIC_PILOT

    @property
    def production_secure(self) -> bool:
        """Bu build 'production-secure' deb belgilanishi mumkinmi.

        PUBLIC_PILOT da HECH QACHON True bo'lmaydi — bu qattiq qulf,
        sozlama emas (topshiriq 2-bo'lim, 8-qoida).
        """
        return self.profile is MqttProfile.PRIVATE_PRODUCTION


class PathSettings(BaseModel):
    """Ma'lumot, log va zaxira papkalari."""

    data_dir: Path
    log_dir: Path
    backup_dir: Path

    @property
    def database_path(self) -> Path:
        return self.data_dir / "distribos.sqlite3"

    def ensure(self) -> None:
        for directory in (self.data_dir, self.log_dir, self.backup_dir):
            directory.mkdir(parents=True, exist_ok=True)


class AppSettings(BaseModel):
    """Ilovaning to'liq konfiguratsiyasi."""

    tenant_id: bytes = Field(default=b"", repr=False)
    environment: str = "pilot"
    language: str = "uz-Latn"
    mqtt: MqttSettings = Field(default_factory=MqttSettings)
    paths: PathSettings
    aether_protocol_version: str = "5.1"
    aether_profile_id: int = 0x01

    #: Foydalanuvchi ochiq broker ogohlantirishini tasdiqladimi (ADR-0002).
    public_pilot_warning_accepted: bool = False

    @model_validator(mode="after")
    def _validate(self) -> AppSettings:
        if self.aether_protocol_version != "5.1":
            raise ConfigError(
                f"Faqat AETHER-Q 5.1 qo'llab-quvvatlanadi, "
                f"berilgan: {self.aether_protocol_version}"
            )
        if self.aether_profile_id not in (0x01, 0x03):
            raise ConfigError(
                "Faqat 0x01 (hybrid) va 0x03 (minimal) profillari ishlatiladi. "
                "0x02 implementatsiya qilinmagan; 0x06/0x07/0x08 tadqiqot "
                "profillari AQ-L01/AQ-L02 topilmalari sababli taqiqlangan."
            )
        if self.environment not in ("pilot", "production", "test"):
            raise ConfigError(f"Noma'lum environment: {self.environment}")
        if self.environment == "production" and not self.mqtt.production_secure:
            raise ConfigError(
                "environment=production faqat PRIVATE_PRODUCTION broker "
                "profili bilan ishlatiladi."
            )
        return self

    @property
    def requires_public_pilot_consent(self) -> bool:
        """Ochiq broker ogohlantirishi hali tasdiqlanmaganmi."""
        return self.mqtt.is_public_pilot and not self.public_pilot_warning_accepted


PUBLIC_PILOT_WARNING = (
    "Siz ochiq MQTT brokeridan foydalanmoqdasiz. Xabar mazmuni AETHER-Q "
    "bilan himoyalanadi, biroq brokerning mavjudligi, metama'lumotlar "
    "maxfiyligi va xabarlarning doimiy saqlanishi kafolatlanmaydi.\n\n"
    "Broker egasi (HiveMQ) bu xizmatni ishlab chiqarish muhitida "
    "ishlatishni man qiladi. Haqiqiy mijoz ma'lumotlari bilan ishlash "
    "uchun xususiy broker sozlang."
)


def default_paths() -> PathSettings:
    """Windows'da `%LOCALAPPDATA%/DistribOS`, aks holda `~/.distribos`."""
    base_env = os.environ.get("DISTRIBOS_HOME")
    if base_env:
        base = Path(base_env)
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "DistribOS"
    else:
        base = Path.home() / ".distribos"
    return PathSettings(
        data_dir=base / "data",
        log_dir=base / "logs",
        backup_dir=base / "backups",
    )


def load_settings(env: dict[str, str] | None = None) -> AppSettings:
    """Muhit o'zgaruvchilaridan konfiguratsiya yuklaydi.

    Prefiks: `DISTRIBOS_`. Masalan `DISTRIBOS_MQTT_HOST`.
    """
    source = dict(os.environ if env is None else env)

    def get(key: str, default: str | None = None) -> str | None:
        return source.get(f"DISTRIBOS_{key}", default)

    profile_raw = get("MQTT_PROFILE", MqttProfile.PUBLIC_PILOT.value) or ""
    try:
        profile = MqttProfile(profile_raw.strip().upper())
    except ValueError as exc:
        raise ConfigError(
            f"Noma'lum MQTT profili: {profile_raw!r}. "
            f"Ruxsat etilgan: {[p.value for p in MqttProfile]}"
        ) from exc

    host = (get("MQTT_HOST", "broker.hivemq.com") or "").strip()
    port_raw = get("MQTT_PORT")
    port = int(port_raw) if port_raw else PUBLIC_PILOT_TLS_PORT

    def flag(key: str, default: bool) -> bool:
        raw = get(key)
        if raw is None:
            return default
        return raw.strip().lower() in ("1", "true", "yes", "ha")

    mqtt = MqttSettings(
        profile=profile,
        host=host,
        port=port,
        tls_required=flag("MQTT_TLS_REQUIRED", True),
        clean_start=flag("MQTT_CLEAN_START", False),
        session_expiry_seconds=int(get("MQTT_SESSION_EXPIRY_SECONDS", "3600") or 3600),
        username=get("MQTT_USERNAME"),
        password=get("MQTT_PASSWORD"),
    )

    tenant_hex = get("TENANT_ID", "") or ""
    return AppSettings(
        tenant_id=bytes.fromhex(tenant_hex) if tenant_hex else b"",
        environment=(get("ENVIRONMENT", "pilot") or "pilot").strip(),
        language=(get("LANGUAGE", "uz-Latn") or "uz-Latn").strip(),
        mqtt=mqtt,
        paths=default_paths(),
        aether_profile_id=int(get("AETHER_PROFILE_ID", "1") or 1),
    )
