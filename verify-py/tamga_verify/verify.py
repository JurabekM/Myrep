"""Jurnal, checkpoint va kalit tekshiruvi — spec §2, §3, §7, §8.

Birinchi xatoda to'xtaydi va `(kod, indeks, izoh)` qaytaradi. Kodlar spec §8 bilan bir xil.
"""

import base64
import hashlib
import json
import re
from dataclasses import dataclass, field

from . import FORMAT_VERSION, ed25519, merkle, mldsa65
from .jcs import NotCanonical, canonical, without

GENESIS = "sha256:" + "0" * 64
MAX_LINE = 1 << 20
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
_LOG_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
KNOWN_EVENTS = {"session.start", "session.end", "prompt", "tool.pre", "tool.post", "decision.human", "os.observed", "key.rotate", "control"}
CKPT_DOMAIN = b"TAMGA-CHECKPOINT-v1\x00"
KEY_DOMAIN = b"TAMGA-KEY-v1\x00"
ML_DSA_CONTEXT = b"tamga-checkpoint"
ROTATE_DOMAIN = b"TAMGA-ROTATE-v1\x00"
ROTATE_CONTEXT = b"tamga-rotate"
ROTATE_REASONS = ("scheduled", "compromise", "restore")


class VerifyError(Exception):
    def __init__(self, code: str, index: int, detail: str):
        super().__init__(f"{code} at index {index}: {detail}")
        self.code, self.index, self.detail = code, index, detail


@dataclass
class Report:
    log: str | None = None
    hashes: list[bytes] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checkpoints: list[dict] = field(default_factory=list)
    rotations: list[dict] = field(default_factory=list)
    keys: list[str] = field(default_factory=list)
    key_warnings: list[str] = field(default_factory=list)


def b64url(s: str) -> bytes | None:
    try:
        raw = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    except (ValueError, TypeError):
        return None
    return raw if base64.urlsafe_b64encode(raw).decode().rstrip("=") == s else None


def _valid_ts(ts: str) -> bool:
    if not isinstance(ts, str) or not _TS.match(ts):
        return False
    y, mo, d, h, mi, s = int(ts[0:4]), int(ts[5:7]), int(ts[8:10]), int(ts[11:13]), int(ts[14:16]), int(ts[17:19])
    if not 1 <= mo <= 12:
        return False
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]
    return 1 <= d <= days and h < 24 and mi < 60 and s < 60


def _lines(text: str):
    """Spec §2.2: har qator `\\n` bilan tugashi shart. (matn, tugaganmi)"""
    rest = text
    while rest:
        i = rest.find("\n")
        if i < 0:
            yield rest, False
            return
        yield rest[:i], True
        rest = rest[i + 1 :]


def _parse_canonical(line: str, ended: bool, index: int, code_parse: str, code_canon: str) -> dict:
    if not ended:
        raise VerifyError(code_parse, index, "qator \\n bilan tugamagan")
    if len(line.encode("utf-8")) > MAX_LINE:
        raise VerifyError(code_parse, index, "qator 1 MiB dan uzun")
    try:
        obj = json.loads(line)
    except ValueError as e:
        raise VerifyError(code_parse, index, f"JSON emas: {e}") from None
    if not isinstance(obj, dict):
        raise VerifyError(code_parse, index, "obyekt emas")
    try:
        canon = canonical(obj)
    except NotCanonical as e:
        raise VerifyError(code_canon, index, str(e)) from None
    if canon != line:
        raise VerifyError(code_canon, index, "qator kanonik shaklda emas")
    return obj


def record_hash(obj: dict) -> bytes:
    return hashlib.sha256(b"\x00" + canonical(without(obj, "hash")).encode("utf-8")).digest()


def _digest(s) -> bytes | None:
    return bytes.fromhex(s[7:]) if isinstance(s, str) and _DIGEST.match(s) else None


def _check_fields(o: dict) -> str | None:
    s = lambda k: o.get(k) if isinstance(o.get(k), str) else None  # noqa: E731
    if not s("log") or not _LOG_ID.match(o["log"]):
        return "`log` noto'g'ri"
    if not isinstance(o.get("seq"), int) or isinstance(o.get("seq"), bool) or o["seq"] < 0:
        return "`seq` manfiy bo'lmagan butun son emas"
    if not _valid_ts(o.get("ts")):
        return "`ts` noto'g'ri"
    if not s("session"):
        return "`session` yo'q"
    if not s("event"):
        return "`event` yo'q"
    if _digest(o.get("prev")) is None or _digest(o.get("hash")) is None:
        return "`prev`/`hash` digest emas"
    d = o.get("decision")
    if d is not None:
        if not isinstance(d, dict) or d.get("verdict") not in ("allow", "deny", "ask") or d.get("by") not in ("policy", "human", "default"):
            return "`decision` noto'g'ri"
    t = o.get("tool")
    if t is not None:
        if not isinstance(t, dict) or not isinstance(t.get("name"), str):
            return "`tool.name` yo'q"
        if "input" in t and not _payload_ok(t["input"]):
            return "`tool.input` payload-ref emas"
    if "result" in o and not _payload_ok(o["result"]):
        return "`result` payload-ref emas"
    if "ref" in o and (not isinstance(o["ref"], int) or isinstance(o["ref"], bool) or o["ref"] < 0):
        return "`ref` noto'g'ri"
    if "ext" in o and not isinstance(o["ext"], dict):
        return "`ext` obyekt emas"
    return None


def _payload_ok(p) -> bool:
    # M-1: Python'da isinstance(True, int) == True; Rust bilan mos bo'lishi uchun bool'ni rad etamiz.
    size = p.get("size") if isinstance(p, dict) else None
    return isinstance(p, dict) and _digest(p.get("digest")) is not None and isinstance(size, int) and not isinstance(size, bool) and size >= 0


def verify_log(text: str) -> Report:
    rep = Report()
    last_ts = None
    for index, (line, ended) in enumerate(_lines(text)):
        o = _parse_canonical(line, ended, index, "E_PARSE", "E_NONCANONICAL")
        if o.get("tamga") != FORMAT_VERSION:
            raise VerifyError("E_VERSION", index, "`tamga` \"0.1\" emas")
        bad = _check_fields(o)
        if bad:
            raise VerifyError("E_FIELD", index, bad)
        if rep.log is None:
            rep.log = o["log"]
        elif o["log"] != rep.log:
            raise VerifyError("E_LOG", index, f"log `{o['log']}` kutilgan `{rep.log}`")
        if o["seq"] != index:
            raise VerifyError("E_SEQ", index, f"seq {o['seq']} kutilgan {index}")
        h = record_hash(o)
        if h != _digest(o["hash"]):
            raise VerifyError("E_HASH", index, "yozuv o'zgartirilgan")
        expected_prev = rep.hashes[-1] if rep.hashes else bytes(32)
        if _digest(o["prev"]) != expected_prev:
            raise VerifyError("E_PREV", index, "zanjir uzilgan")
        if o["event"] == "key.rotate":
            try:
                rep.rotations.append(_parse_rotation(o, index))
            except ValueError as e:
                raise VerifyError("E_KEY_ROTATE", index, str(e)) from None
        if o["event"] not in KNOWN_EVENTS:
            rep.warnings.append(f"#{index}: noma'lum hodisa `{o['event']}`")
        if last_ts is not None and o["ts"] < last_ts:
            rep.warnings.append(f"#{index}: vaqt orqaga ketgan")
        last_ts = o["ts"]
        rep.hashes.append(h)
    return rep


class PublicKey:
    def __init__(self, ed: bytes, ml: bytes, key_id: str):
        self.ed, self.ml, self.key_id = ed, ml, key_id

    @staticmethod
    def compute_id(ed: bytes, ml: bytes) -> str:
        return "k:" + hashlib.sha256(KEY_DOMAIN + ed + ml).hexdigest()[:32]

    @classmethod
    def from_json(cls, v: dict) -> "PublicKey":
        if v.get("tamga") != FORMAT_VERSION or v.get("type") != "public-key":
            raise ValueError("ochiq kalit fayli: tamga/type noto'g'ri")
        ed, ml = b64url(v.get("ed25519", "")), b64url(v.get("ml-dsa-65", ""))
        if ed is None or ml is None or len(ed) != 32 or len(ml) != mldsa65.PK_LEN:
            raise ValueError("ochiq kalit fayli: kalit uzunligi noto'g'ri")
        # M-1: Ed25519 kaliti egri chiziqda ekanini darhol tekshiramiz (Rust from_bytes bilan bir xil).
        if ed25519._decompress(ed) is None:
            raise ValueError("ochiq kalit fayli: ed25519 kaliti egri chiziqda emas")
        if cls.compute_id(ed, ml) != v.get("key"):
            raise ValueError("ochiq kalit fayli: `key` identifikatori mos emas")
        return cls(ed, ml, v["key"])

    def verify(self, message: bytes, sig_ed: bytes, sig_ml: bytes, ctx: bytes = ML_DSA_CONTEXT) -> bool:
        # Gibrid AND: ikkalasi ham shart.
        return ed25519.verify(self.ed, message, sig_ed) and mldsa65.verify(self.ml, message, sig_ml, ctx)


def _parse_rotation(o: dict, seq: int) -> dict:
    """Spec §7.5: `key.rotate` yozuvining o'z-o'zidan tekshiriladigan qismi (shakl, `to`, isbot)."""
    m = o.get("key_rotation")
    if not isinstance(m, dict):
        raise ValueError("`key_rotation` obyekti yo'q")
    frm, to, reason = m.get("from"), m.get("to"), m.get("reason")
    if not all(isinstance(x, str) for x in (frm, to, reason)):
        raise ValueError("`key_rotation` maydonlari satr emas")
    if reason not in ROTATE_REASONS:
        raise ValueError(f"noma'lum sabab `{reason}`")
    ed, ml = b64url(m.get("ed25519") or ""), b64url(m.get("ml-dsa-65") or "")
    if ed is None or ml is None or len(ed) != 32 or len(ml) != mldsa65.PK_LEN:
        raise ValueError("yangi kalit uzunligi noto'g'ri")
    if PublicKey.compute_id(ed, ml) != to:
        raise ValueError("`to` yangi ochiq kalitlarga mos emas")
    if frm == to:
        raise ValueError("kalit o'ziga almashtirilgan")
    proof = m.get("proof")
    if not isinstance(proof, dict):
        raise ValueError("`proof` obyekt emas")
    p_ed, p_ml = b64url(proof.get("ed25519") or ""), b64url(proof.get("ml-dsa-65") or "")
    msg = ROTATE_DOMAIN + canonical({"from": frm, "log": o["log"], "seq": seq, "to": to}).encode("utf-8")
    pk = PublicKey(ed, ml, to)
    if p_ed is None or p_ml is None or not pk.verify(msg, p_ed, p_ml, ROTATE_CONTEXT):
        raise ValueError("egalik isboti (yangi kalit imzosi) tasdiqlanmadi")
    return {"seq": seq, "from": frm, "to": pk, "reason": reason}


def verify_all(log_text: str, checkpoint_text: str, pk: PublicKey) -> Report:
    """`pk` — langar (operator bergan birinchi) kalit; almashtirishlar jurnalning o'zidan (spec §7.5)."""
    rep = verify_log(log_text)
    active, applied = pk, 0
    rep.keys.append(pk.key_id)
    for index, (line, ended) in enumerate(_lines(checkpoint_text)):
        try:
            c = _parse_canonical(line, ended, index, "E_CKPT_FORMAT", "E_CKPT_FORMAT")
        except VerifyError as e:
            raise VerifyError("E_CKPT_FORMAT", index, e.detail) from None
        fmt = lambda d: VerifyError("E_CKPT_FORMAT", index, d)  # noqa: E731
        if c.get("tamga") != FORMAT_VERSION or c.get("type") != "checkpoint":
            raise fmt("tamga/type noto'g'ri")
        size = c.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size < 1:
            raise fmt("`size` musbat butun son emas")
        root, last = _digest(c.get("root")), _digest(c.get("last"))
        if root is None or last is None:
            raise fmt("`root`/`last` digest emas")
        if not isinstance(c.get("log"), str) or not _LOG_ID.match(c["log"]) or not _valid_ts(c.get("ts")):
            raise fmt("`log`/`ts` noto'g'ri")
        if c.get("key") != active.key_id:
            raise fmt("`key` berilgan ochiq kalitga mos emas")
        sig = c.get("sig")
        if not isinstance(sig, dict):
            raise fmt("`sig` obyekt emas")
        # M-1: `sig` maydonlari bo'lmasa yoki satr bo'lmasa E_CKPT_FORMAT (Rust bilan bir xil),
        # E_CKPT_SIG emas — imzo umuman berilmagan.
        if not isinstance(sig.get("ed25519"), str) or not isinstance(sig.get("ml-dsa-65"), str):
            raise fmt("`sig.ed25519`/`sig.ml-dsa-65` satr emas")
        sig_ed, sig_ml = b64url(sig["ed25519"]), b64url(sig["ml-dsa-65"])
        if sig_ed is None or sig_ml is None:
            raise fmt("imzo base64url emas")
        message = CKPT_DOMAIN + canonical(without(c, "sig")).encode("utf-8")
        if not active.verify(message, sig_ed, sig_ml):
            raise VerifyError("E_CKPT_SIG", index, "imzo tasdiqlanmadi")
        if rep.log is not None and c["log"] != rep.log:
            raise fmt("checkpoint boshqa jurnalga tegishli")
        if size > len(rep.hashes):
            raise VerifyError("E_CKPT_SIZE", index, f"checkpoint {size} yozuvni qamraydi, jurnalda {len(rep.hashes)} ta")
        covered = rep.hashes[:size]
        if merkle.root(covered) != root or covered[-1] != last:
            raise VerifyError("E_CKPT_ROOT", index, f"dastlabki {size} yozuv checkpoint'dan keyin qayta yozilgan")
        while applied < len(rep.rotations) and rep.rotations[applied]["seq"] < size:
            r = rep.rotations[applied]
            if r["from"] != active.key_id:
                raise VerifyError("E_KEY_ROTATE", r["seq"], f"almashtirish `{r['from']}` dan, lekin faol kalit `{active.key_id}`")
            if r["reason"] == "compromise":
                rep.key_warnings.append(f"#{r['seq']}: kalit {r['from']} buzilgan deb e'lon qilingan")
            active = r["to"]
            rep.keys.append(active.key_id)
            applied += 1
        rep.checkpoints.append({"size": size, "ts": c["ts"]})
    for r in rep.rotations[applied:]:
        rep.key_warnings.append(f"#{r['seq']}: {r['to'].key_id} ga almashtirish hali tasdiqlanmagan")
    return rep


PAYLOAD_DOMAIN = b"TAMGA-PAYLOAD-v1\x00"


def payload_opens(reference: dict, salt: bytes, data: bytes) -> bool:
    """Spec §5: dalil to'plamidagi payload jurnaldagi tuzlangan majburiyatga mosmi."""
    d = _digest(reference.get("digest"))
    return d is not None and reference.get("size") == len(data) and hashlib.sha256(PAYLOAD_DOMAIN + salt + data).digest() == d
