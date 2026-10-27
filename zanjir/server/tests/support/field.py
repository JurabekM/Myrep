"""Dala qurilmasi taqlidi: ilovadagi kabi qatorlar, audit hash-zanjiri va protokol imzosini yaratadi (sim formatida)."""

from __future__ import annotations

import base64
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from zanjir_server.crypto.canonical import canonical_json, canonical_json_bytes
from zanjir_server.crypto.hash_chain import GENESIS_HASH, compute_event_hash, payload_hash
from zanjir_server.crypto.hashing import sha256_hex
from zanjir_server.crypto.protocol import protocol_message, qr_token_from_signature, qr_token_message
from zanjir_server.crypto.signing import Ed25519Signer
from zanjir_server.sync.service import measurement_audit_payload, protocol_audit_payload
from zanjir_server.sync.wire import iso

NORMS = 'schema_version: 1\nversion: "0.1.1"\nreviewed_by: "{rb}"\nreviewed_at: "{ra}"\nmargin_pct: 0\nnorms: []\n'
REVIEWER = "TEST FIXTURE — haqiqiy tekshiruv emas"


def norms_yaml(reviewed: bool) -> str:
    return NORMS.format(rb=REVIEWER, ra="2026-10-01") if reviewed else NORMS.format(rb="", ra="")


def new_id() -> str:
    return str(uuid.uuid4())


def fake_pdf(payload_sha: str, body: bytes = b"") -> bytes:
    """Server PDF'ni chizmaydi — faqat hash va `/ID[<sha><sha>]` ni tekshiradi."""
    s = payload_sha.encode()
    return b"%PDF-1.7\n1 0 obj<<>>endobj\n" + body + b"\ntrailer<</ID[<" + s + b"><" + s + b">]>>\n%%EOF"


class Field:
    def __init__(self, org_id: str, user_id: str, device_id: str, seed: int = 7) -> None:
        self.org_id = org_id
        self.user_id = user_id
        self.device_id = device_id
        self.signer = Ed25519Signer(bytes([seed]) * 32)
        self.seq = 0
        self.prev = GENESIS_HASH
        self.t = datetime(2026, 10, 26, 7, 0, tzinfo=UTC)
        self.n = 0
        self.protocols = 0

    def snapshot(self) -> tuple[int, str]:
        """Zanjir holati — rad etilgan paketdan keyin qaytarish uchun (serverda hech narsa saqlanmagan)."""
        return self.seq, self.prev

    def restore(self, state: tuple[int, str]) -> None:
        self.seq, self.prev = state

    @property
    def public_key(self) -> str:
        return self.signer.public_key_hex

    def now(self) -> str:
        self.t += timedelta(seconds=1)
        return iso(self.t)

    def op(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        self.n += 1
        return {"client_op_id": f"{self.device_id[:8]}-{self.n}-{new_id()[:8]}", "table": table, "row": row}

    def base(self, **row: Any) -> dict[str, Any]:
        now = self.now()
        return {"id": new_id(), "org_id": self.org_id, "created_at": now, "updated_at": now, "rev": 1, **row}

    def event(self, event_type: str, entity_id: str | None, payload: object) -> dict[str, Any]:
        self.seq += 1
        at = self.now()
        ph = payload_hash(payload)
        h = compute_event_hash(
            seq=self.seq,
            prev_hash=self.prev,
            actor_id=self.user_id,
            event_type=event_type,
            entity_id=entity_id,
            payload_hash=ph,
            created_at=at,
        )
        row = self.base(
            device_id=self.device_id,
            seq=self.seq,
            prev_hash=self.prev,
            event_hash=h,
            actor_id=self.user_id,
            event_type=event_type,
            entity_id=entity_id,
            payload_hash=ph,
            device_sig=self.signer.sign(bytes.fromhex(h)).hex(),
            sig_alg="Ed25519",
            event_at=at,
        )
        self.prev = h
        return self.op("audit_event", row)

    # --- metadata ---

    def site(self) -> dict[str, Any]:
        return self.op(
            "site",
            self.base(
                name="Obyekt",
                address="Manzil 1",
                customer="Buyurtmachi",
                earthing_system="TN-C-S",
                u0_volts=220.0,
                deleted=False,
            ),
        )

    def node(self, site_id: str, label: str = "XS1", kind: str = "SOCKET_GROUP") -> dict[str, Any]:
        return self.op(
            "node",
            self.base(
                site_id=site_id,
                kind=kind,
                label=label,
                panel_id=None,
                state=None,
                attrs={"circuit_role": "final"},
                verified=True,
                x=None,
                y=None,
                deleted=False,
            ),
        )

    def instrument(self, verified_until: str = "2027-03-01T00:00:00.000Z") -> dict[str, Any]:
        return self.op(
            "instrument",
            self.base(
                kind="MULTIFUNCTION",
                model="MI 3152",
                serial_no="SN-1",
                verification_cert_no="QV-1",
                verified_until=verified_until,
                deleted=False,
            ),
        )

    def session(self, site_id: str, closed: bool = True) -> dict[str, Any]:
        return self.op(
            "measurement_session",
            self.base(
                site_id=site_id,
                kind="DAVRIY",
                engineer_id=self.user_id,
                ambient_temp_c=20.0,
                humidity_pct=None,
                started_at=self.now(),
                closed_at=self.now() if closed else None,
                deleted=False,
            ),
        )

    def measurement(
        self,
        session_id: str,
        node_id: str,
        instrument_id: str,
        verdict: str = "PASS",
        zs: float = 0.84,
        supersedes_id: str | None = None,
    ) -> list[dict[str, Any]]:
        row = self.base(
            session_id=session_id,
            node_id=node_id,
            type="LOOP_IMPEDANCE",
            instrument_id=instrument_id,
            values={"pair": "L1-PE", "zs_ohm": zs},
            entered_via="MANUAL",
            verdict=verdict,
            norm_id="LOOP-TN-FINAL" if verdict != "NEEDS_REVIEW" else None,
            norm_set_version="0.1.1",
            eval_detail={"reason": None},
            supersedes_id=supersedes_id,
        )
        return [self.event("MEASUREMENT_ADDED", row["id"], measurement_audit_payload(row)), self.op("measurement", row)]

    def norm_set(self, reviewed: bool = True) -> dict[str, Any]:
        yaml = norms_yaml(reviewed)
        return self.op(
            "norm_set",
            self.base(
                version="0.1.1",
                sha256=sha256_hex(yaml.encode()),
                yaml=yaml,
                reviewed_by=REVIEWER if reviewed else None,
                reviewed_at="2026-10-01" if reviewed else None,
                deleted=False,
            ),
        )

    # --- protokol ---

    @property
    def device_tag(self) -> str:
        return self.device_id.replace("-", "")[-6:].upper()

    def protocol_payload(
        self,
        session: dict[str, Any],
        measurements: list[dict[str, Any]],
        instruments: list[dict[str, Any]],
        *,
        signer_role: str = "LEAD",
        lead_comment: str | None = None,
        reviewed: bool = True,
        qr_token: str | None = None,
        number: str | None = None,
    ) -> dict[str, Any]:
        if number is None:
            self.protocols += 1
            number = f"2026-{self.device_tag}-{self.protocols:03d}"
        qr_sig = self.signer.sign(qr_token_message(self.org_id, number)).hex()
        norms = norms_yaml(reviewed)
        return {
            "schema": "zanjir.protocol/1",
            "protocol": {
                "number": number,
                "qr_token": qr_token or qr_token_from_signature(qr_sig),
                "qr_sig": qr_sig,
                "verify_url": "zanjir://app/v/x",
                "language": "uz",
            },
            "lab": {
                "org_id": self.org_id,
                "name": "Elektrolab",
                "license_no": "EL-1",
                "license_valid_until": "2027-12-31T00:00:00.000Z",
            },
            "session": {"id": session["id"]},
            "signer": {"id": self.user_id, "role": signer_role},
            "signed_at": self.now(),
            "lead_comment": lead_comment,
            "norm_set": {
                "version": "0.1.1",
                "sha256": sha256_hex(norms.encode()),
                "reviewed_by": REVIEWER if reviewed else None,
                "reviewed_at": "2026-10-01" if reviewed else None,
            },
            "instruments": [{"id": i["id"], "verified_until": i["verified_until"]} for i in instruments],
            "measurements": [
                {
                    "id": m["id"],
                    "instrument_id": m["instrument_id"],
                    "created_at": m["created_at"],
                    "verdict": m["verdict"],
                    "values": m["values"],
                }
                for m in measurements
            ],
        }

    def protocol(self, session_id: str, payload: dict[str, Any], pdf: bytes | None = None) -> list[dict[str, Any]]:
        payload_sha = sha256_hex(canonical_json_bytes(payload))
        pdf = pdf if pdf is not None else fake_pdf(payload_sha)
        pdf_sha = sha256_hex(pdf)
        row = self.base(
            session_id=session_id,
            number=payload["protocol"]["number"],
            payload_sha256=payload_sha,
            pdf_sha256=pdf_sha,
            signed_by=self.user_id,
            device_id=self.device_id,
            signature=self.signer.sign(protocol_message(payload_sha, pdf_sha)).hex(),
            sig_alg="Ed25519",
            qr_token=payload["protocol"]["qr_token"],
        )
        doc = self.base(protocol_id=row["id"], payload_json=canonical_json(payload), pdf=base64.b64encode(pdf).decode())
        return [
            self.event("PROTOCOL_SIGNED", row["id"], protocol_audit_payload(row)),
            self.op("protocol", row),
            self.op("protocol_document", doc),
        ]


def rows(ops: list[dict[str, Any]], table: str) -> list[dict[str, Any]]:
    return [o["row"] for o in ops if o["table"] == table]
