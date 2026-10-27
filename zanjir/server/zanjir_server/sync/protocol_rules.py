"""Imzolangan protokolni serverda qayta tekshirish (CLAUDE.md 6-qoida — ikkinchi himoya qatlami, ADR-0010/0011).

Payload (`zanjir.protocol/1`) dan: normalar muhandis tekshirgan, asbob guvohnomasi o'lchov kuni amal qilgan (hozirgi
muddat va o'lchov paytida yozib qo'yilgan `instrument_verified_until` — ikkalasi ham), NEEDS_REVIEW — faqat LEAD izoh
bilan, litsenziya raqami bor va imzolash kuni amal qilgan.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any


def _day(iso: object) -> date | None:
    if not isinstance(iso, str):
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(UTC).date()
    except ValueError:
        return None


def protocol_payload_violation(payload: dict[str, Any], signer_role: str) -> str | None:
    """Birinchi buzilgan qoida kodi yoki None."""
    if payload.get("schema") != "zanjir.protocol/1":
        return "unknown_schema"
    norm_set = payload.get("norm_set")
    reviewed = norm_set.get("reviewed_by") if isinstance(norm_set, dict) else None
    if not isinstance(reviewed, str) or not reviewed.strip():
        return "norms_not_reviewed"
    measurements = payload.get("measurements")
    instruments = payload.get("instruments")
    if not isinstance(measurements, list) or not measurements or not isinstance(instruments, list):
        return "no_measurements"
    valid_until = {i.get("id"): _day(i.get("verified_until")) for i in instruments if isinstance(i, dict)}
    needs_review = False
    for m in measurements:
        if not isinstance(m, dict):
            return "invalid_payload"
        until = valid_until.get(m.get("instrument_id"))
        taken = _day(m.get("created_at"))
        if until is None or taken is None or taken > until:
            return "instrument_expired"
        if "instrument_verified_until" in m:  # o'lchov paytidagi muddat (keyingi qayta qiyoslash uni tozalamaydi)
            at_record = _day(m["instrument_verified_until"])
            if at_record is None or taken > at_record:
                return "instrument_expired"
        needs_review |= m.get("verdict") == "NEEDS_REVIEW"
    if needs_review:
        if signer_role != "LEAD":
            return "needs_review_requires_lead"
        comment = payload.get("lead_comment")
        if not isinstance(comment, str) or not comment.strip():
            return "lead_comment_required"
    lab = payload.get("lab")
    license_no = lab.get("license_no") if isinstance(lab, dict) else None
    if not isinstance(license_no, str) or not license_no.strip():
        return "license_invalid"
    license_until = _day(lab.get("license_valid_until")) if isinstance(lab, dict) else None
    signed = _day(payload.get("signed_at"))
    if license_until is None or signed is None or signed > license_until:
        return "license_invalid"
    return None
