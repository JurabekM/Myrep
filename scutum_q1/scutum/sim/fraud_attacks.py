"""T1-T6 hujum laboratoriyasi — spec `docs/SPEC-ROSTOR-1.1.md` §2, §15.

Har bir ssenariy ikki holatni HAQIQATAN ijro etadi va solishtiradi:

  UNPROTECTED — bugungi kunda O'zbekistonda haqiqatda ishlaydigan,
                ROSTOR-integratsiyasiz oddiy oqim (SMS OTP, tekshiruvsiz
                APK, imzosiz "pul olish" sahifasi va h.k.);
  PROTECTED   — ROSTOR-1 mexanizmi (haqiqiy kod, `rostor/` paketi)
                ishtirokida bir xil hujum.

`sim/attacks.py` (SCUTUM-Q1 transport hujumlari) bilan bir xil naqsh:
natija oldindan yozib qo'yilmagan, har bir chaqiriqda haqiqatan
hisoblanadi.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..crypto.primitives import (
    ed25519_generate,
    hybrid_sign,
    mldsa_generate,
    random_bytes,
)
from ..protocol.identity import DeviceKeys
from ..rostor.account import apply_recovery, create_quorum_approval, create_recovery_request
from ..rostor.apk import android_sha256, create_apk_attestation
from ..rostor.badge import Badge, derive_badge
from ..rostor.errors import AccountAuthError, PolicyViolation
from ..rostor.fraud_report import create_fraud_report, is_flagged, score_reports
from ..rostor.payment import create_payment_intent, reject_unknown_fields
from ..rostor.txn_confirm import (
    create_txn_confirm_request,
    create_txn_confirm_response,
    verify_txn_confirm_response,
)
from .rostor_world import CFG, RostorWorld
from .trace import Level, Trace


class Outcome:
    BROKEN = "BROKEN"       # hujumchi maqsadiga erishdi
    SAFE = "SAFE"           # himoya ishladi
    STRUCTURAL = "STRUCTURAL"
    INFO = "INFO"


@dataclass
class FraudAttackResult:
    key: str
    title: str
    threat: str             # "T1".."T6"
    unprotected: str
    unprotected_evidence: list[str]
    protected: str
    protected_evidence: list[str]
    elapsed_ms: float = 0.0


@dataclass
class FraudAttack:
    key: str
    title: str
    threat: str
    real_world_note: str
    run: Callable[[Trace], FraudAttackResult]


def _mk(a: "FraudAttack", u_out: str, u_ev: list[str], p_out: str, p_ev: list[str]) -> FraudAttackResult:
    return FraudAttackResult(a.key, a.title, a.threat, u_out, u_ev, p_out, p_ev)


def _hex(b: bytes, n: int = 12) -> str:
    return b[:n].hex() + ("…" if len(b) > n else "")


# ===========================================================================
# T1 — Telegram orqali tarqaladigan Android SMS-stealer/dropper
# ===========================================================================
def _atk_t1_apk_dropper(trace: Trace) -> FraudAttackResult:
    w = RostorWorld(trace)
    gov = w.institutions["mygov.uz"]

    real_apk = random_bytes(256)
    real_hash = android_sha256(real_apk)
    create_apk_attestation(
        gov.idc, package_name="uz.gov.mygov", version_code=7, channel="official",
        apk_sha256=real_hash, android_signing_cert_sha256=android_sha256(b"gov-cert"),
    )

    malicious_apk = random_bytes(256)
    malicious_hash = android_sha256(malicious_apk)
    w.add_malicious_hash(malicious_hash, note="soxta MyGov_yangilanish.apk, SMS-stealer")
    sth = w.publish_and_witness_sth()

    u_ev = [
        "Foydalanuvchi Telegram'da (o'g'irlangan sessiyadan) "
        "'MyGov_yangilanish.apk' oladi",
        "Fayl nashriyotchisi yoki xeshi HECH QANDAY joyda tekshirilmaydi",
        "Foydalanuvchi o'rnatadi -> SMS/OTP/USSD ruxsatlarini so'raydi -> "
        "OTP kodlarini ushlaydi, o'z-o'zini kontaktlarga tarqatadi",
    ]

    proof = w.log.lookup(malicious_hash)
    found_malicious = w.log_client.verify_lookup(proof, sth) and proof.value is not None
    p_ev = [
        f"'Tekshiruv' vositasi fayl xeshini hisoblaydi: {_hex(malicious_hash)}",
        f"Shaffoflik jurnalidan ISBOT bilan so'raladi (non-inclusion/inclusion proof)",
        f"Natija: {'ZARARLI DEB TOPILDI' if found_malicious else 'topilmadi'} "
        f"(isbot tekshirildi: {w.log_client.verify_lookup(proof, sth)})",
    ]
    if found_malicious:
        p_ev.append("=> O'rnatish oldidan qattiq bloklandi: "
                    "'Bu fayl ZARARLI deb tasdiqlangan. O'RNATMANG.'")
    return _mk(ATTACKS["t1_apk_dropper"], Outcome.BROKEN, u_ev,
              Outcome.SAFE if found_malicious else Outcome.BROKEN, p_ev)


# ===========================================================================
# T2 — Bank fishing + vishing (OTP aytdirish)
# ===========================================================================
def _atk_t2_vishing_otp(trace: Trace) -> FraudAttackResult:
    from ..rostor.call_context import create_call_context, is_call_legitimate

    w = RostorWorld(trace)
    bank = w.institutions["Bank X"]
    user = w.citizens["Alisa"]

    u_ev = [
        "Foydalanuvchi kichik, zararsiz operatsiya haqida SMS OTP oladi "
        "(masalan 6 xonali kod, HECH QANDAY summaga/qabul qiluvchiga bog'lanmagan)",
        "'Bank xavfsizlik xizmati' nomidan +998-90-XXX-XXXX raqamidan "
        "qo'ng'iroq keladi (jo'natuvchi ID/raqam osongina soxtalashtiriladi)",
        "\"Operatsiyani bekor qilish uchun kodni ayting\" deyiladi",
        "Foydalanuvchi kodni aytadi -> aslida bu kod HUJUMCHINING o'z "
        "so'ragan katta o'tkazmasini tasdiqlaydi (kod semantik bo'sh)",
    ]

    # --- 1) CALL_CONTEXT: qo'ng'iroq qilayotgan TOMONNI tekshirish (R2) ---
    # Bank bu qo'ng'iroq uchun HECH QANDAY CALL_CONTEXT push qilmagan edi
    # (chunki bu qo'ng'iroqni bank emas, hujumchi boshlagan). Boshqa,
    # UNCHA ALOQADOR bo'lmagan haqiqiy qo'ng'iroq konteksti mavjud bo'lsa
    # ham, raqam mos kelmagani uchun `is_call_legitimate` FAIL-CLOSED:
    real_cc = create_call_context(
        bank.idc, bank.keys.institution_id, "+998712001122", "Rejadagi xizmat xabari",
    )
    attacker_number = "+998901234567"
    idc_by_inst = {bank.keys.institution_id: bank.idc.dc()}
    call_ok = is_call_legitimate(attacker_number, [real_cc], idc_by_inst)

    # --- 2) Relay hujumi: kichik operatsiya tasdig'ini kattaga yopishtirish ---
    legit_req = create_txn_confirm_request(
        bank.idc, bank.keys.institution_id, amount_minor=5_00, currency="UZS",
        recipient_masked="****0001", purpose="Kichik xarid",
    )
    legit_resp = create_txn_confirm_response(user, legit_req, "APPROVE", account_id=b"\x01" * 16)
    fraud_req = create_txn_confirm_request(
        bank.idc, bank.keys.institution_id, amount_minor=35_000_00, currency="UZS",
        recipient_masked="****9999 (noma'lum)", purpose="Noma'lum o'tkazma",
    )
    forged_ok = verify_txn_confirm_response(legit_resp, user.dc(), fraud_req)

    p_ev = [
        f"CALL_CONTEXT: {attacker_number} raqamidan kelgan qo'ng'iroq uchun mos, "
        f"haqiqiy push topildimi: {call_ok} (fail-closed — HA bo'lmasa, qo'ng'iroq "
        "davomida hech narsa ishonchni tiklay olmaydi)",
        "ROSTOR oqimida 'aytiladigan kod' UMUMAN YO'Q — foydalanuvchi ekranda "
        f"'{fraud_req.render_for_display()['amount_minor']/100:.0f} so'm -> "
        f"{fraud_req.render_for_display()['recipient_masked']}' ko'radi",
        "Hujumchi (relay orqali) foydalanuvchining BOSHQA, kichik operatsiya "
        "uchun bergan tasdig'ini katta operatsiyaga bog'lashga urinadi",
        f"TxnConfirmResponse.request_hash to'liq so'rovni qamraydi -> "
        f"mos kelish tekshirildi: {forged_ok}",
    ]
    if not call_ok:
        p_ev.append("=> UI: '⚠️ Bu raqam CALL_CONTEXT bilan tasdiqlanmagan — "
                    "gapni davom ettirmang, o'zingiz bankka qo'ng'iroq qiling'")
    if not forged_ok:
        p_ev.append("=> Relay rad etildi: javob boshqa so'rovga tegishli edi (R7)")
    protected = Outcome.SAFE if (not call_ok and not forged_ok) else Outcome.BROKEN
    return _mk(ATTACKS["t2_vishing_otp"], Outcome.BROKEN, u_ev, protected, p_ev)


# ===========================================================================
# T3 — Davlat/sud/militsiya nomidan qo'rqitish
# ===========================================================================
def _atk_t3_gov_impersonation(trace: Trace) -> FraudAttackResult:
    w = RostorWorld(trace)
    fraudster = w.fraudster

    u_ev = [
        "Foydalanuvchi 'mygov.uz' nomidan SMS oladi: "
        "\"Sizga qarshi jinoiy ish ochilgan, darhol tasdiqlang\"",
        "SMS jo'natuvchi ID'si oson soxtalashtiriladi — haqiqiy va soxta "
        "xabar orasida HECH QANDAY farq yo'q",
        "Qo'rqib ketgan foydalanuvchi havolani bosadi / to'lov qiladi",
    ]

    msg = b"Sizga qarshi jinoiy ish ochildi. 500000 som jarima toolang."
    fake_sig = hybrid_sign(fraudster.ik_ed, fraudster.ik_mldsa, msg)
    snap = w.snapshot()
    result = derive_badge(idc_dc=fraudster.dc(), sig=fake_sig, signed_payload=msg, snapshot=snap)

    p_ev = [
        "Xuddi shu xabar ROSTOR mijozida ochiladi",
        f"derive_badge natijasi: {result.badge.value} "
        f"(Mallory hech qachon mygov.uz IC/IDC zanjiriga kira olmaydi)",
    ]
    if result.badge != Badge.VERIFIED:
        p_ev.append("=> UI: '⚠️ Tasdiqlanmagan xabar — rasmiy manba EMAS'")
    return _mk(ATTACKS["t3_gov_impersonation"], Outcome.BROKEN, u_ev,
              Outcome.SAFE if result.badge != Badge.VERIFIED else Outcome.BROKEN, p_ev)


# ===========================================================================
# T4 — SIM swap / raqam ko'chirish orqali akkount egallash
# ===========================================================================
def _atk_t4_sim_swap(trace: Trace) -> FraudAttackResult:
    w = RostorWorld(trace)
    victim_account = w.accounts["Alisa"]
    attacker_device = DeviceKeys.generate("Mallory-yangi-qurilma", CFG)

    u_ev = [
        "Hujumchi telekom xodimini ijtimoiy muhandislik/poraxo'rlik orqali "
        "Alisaning raqamini o'z SIM-kartasiga ko'chirishga majbur qiladi",
        "Bank ilovasida 'parolni unutdim' -> SMS-OTP orqali tiklash -> "
        "hujumchi endi Alisaning raqami orqali OTP oladi",
        "Akkount TO'LIQ egallanadi — DIK yoki qurilma tekshiruvi yo'q",
    ]

    req = create_recovery_request(
        attacker_device.dc(), victim_account.account_id,
        victim_account.policy_epoch, "existing_device_cosign",
    )
    # Hujumchi qo'lida FAQAT SIM (telefon raqami) bor — u ROSTOR
    # tiklash kvorumi a'zolarining maxfiy kalitlariga ega EMAS, shuning
    # uchun haqiqiy QuorumApproval imzosini yasay olmaydi. Buni faqat
    # o'zining (haqiqiy bo'lmagan) kalitlari bilan taqlid qiladi:
    fake_ed, fake_ml = ed25519_generate(), mldsa_generate()
    fake_approval = create_quorum_approval(random_bytes(16), fake_ed, fake_ml, req)

    try:
        apply_recovery(victim_account, req, [fake_approval], approver_pks={})
        recovered = True
    except AccountAuthError as exc:
        recovered = False
        reason = str(exc)

    p_ev = [
        "ROSTOR'da identitet SIM'ga emas, DIK'ga (apparat kaliti) bog'langan",
        "Hujumchi SIM'ni egallagan bo'lsa ham, tiklash kvorumi a'zolarining "
        "(mavjud ishonchli qurilmalar) maxfiy kalitlariga ega EMAS",
        f"Soxta QuorumApproval bilan tiklashga urinish: "
        f"{'MUVAFFAQIYATLI (xato!)' if recovered else 'rad etildi — ' + reason}",
    ]
    return _mk(ATTACKS["t4_sim_swap"], Outcome.BROKEN, u_ev,
              Outcome.BROKEN if recovered else Outcome.SAFE, p_ev)


# ===========================================================================
# T5 — Classiscam-uslubidagi bozor firibgarligi
# ===========================================================================
def _atk_t5_classiscam(trace: Trace) -> FraudAttackResult:
    w = RostorWorld(trace)
    fraudster = w.fraudster

    u_ev = [
        "'Xaridor' OLX'da til biriktirib, Telegram'ga o'tadi",
        "'Pulni olish uchun kartangizni tasdiqlang' havolasini yuboradi "
        "(aslida bu pul YECHISH so'rovi)",
        "Foydalanuvchi karta raqami + CVV + OTP kiritadi -> pul o'g'irlanadi",
    ]

    # Hujumchi ROSTOR PaymentIntent'ga o'xshatib, lekin karta maydonini
    # qo'shib yuborishga urinadi:
    fake_raw = {
        "v": 1, "intent_id": random_bytes(16), "issuer_id": fraudster.device_id,
        "payee_token": random_bytes(32), "amount_minor": None,
        "memo": "Pulni olish uchun kartangizni tasdiqlang",
        "expires_at": int(time.time()) + 600,
        "issuer_sig": None,
        "card_number": "8600 **** **** 1234",   # <- kredensial-shaklidagi maydon
    }
    try:
        reject_unknown_fields(fake_raw)
        rejected = False
    except PolicyViolation:
        rejected = True

    p_ev = [
        "Xuddi shu so'rov ROSTOR PaymentIntent parseriga yuboriladi",
        "Sxemada `card_number` kabi kredensial maydon UMUMAN YO'Q — bu "
        "konvensiya emas, protokol invarianti",
        f"Natija: {'rad etildi' if rejected else 'MUVAFFAQIYATLI (xato!)'}",
    ]
    if rejected:
        p_ev.append("=> UI: 'Bu so'rov pul olish uchun kerak bo'lmagan "
                    "ma'lumot so'ramoqda — ehtimol firibgarlik'")
    return _mk(ATTACKS["t5_classiscam"], Outcome.BROKEN, u_ev,
              Outcome.SAFE if rejected else Outcome.BROKEN, p_ev)


# ===========================================================================
# T6 — Soxta investitsiya/kripto/ish e'lonlari
# ===========================================================================
def _atk_t6_fake_investment(trace: Trace) -> FraudAttackResult:
    w = RostorWorld(trace)
    scheme_wallet = random_bytes(16)

    u_ev = [
        "'Kafolatlangan 40% oylik daromad' reklamasi tarqaladi",
        "Hech qanday mustaqil obro' signali yo'q — birinchi qurbonlar "
        "hech narsani tekshira olmaydi",
        "O'nlab qurbon pul yuboradi, sxema g'oyib bo'ladi",
    ]

    reports = []
    for i in range(6):
        victim = DeviceKeys.generate(f"Qurbon-{i}", CFG)
        r = create_fraud_report(
            victim, "wallet", scheme_wallet, "T6",
            interaction_ref=random_bytes(16) if i < 5 else None,
        )
        reports.append(r)
    score, distinct = score_reports(reports)
    flagged = is_flagged(reports)

    p_ev = [
        f"{len(reports)} ta MUSTAQIL qurbon (turli DIK) firibgarlik hisoboti yuboradi",
        f"score={score}, distinct_reporters={distinct} "
        f"(chegara: SCORE_THRESHOLD=15, MIN_K=5)",
        f"is_flagged() = {flagged}",
    ]
    if flagged:
        p_ev.append("=> Keyingi potensial qurbon 'Tekshiruv' orqali "
                    "'⚠️ FLAGGED — ko'p marta firibgarlik deb xabar qilingan' ko'radi")
        p_ev.append("[HALOL CHEGARA] Birinchi 5 qurbon HALI himoyalanmagan edi "
                    "— tizim faqat KEYINGI qurbonlarni ogohlantiradi")
    return _mk(ATTACKS["t6_fake_investment"], Outcome.BROKEN, u_ev,
              Outcome.SAFE if flagged else Outcome.STRUCTURAL, p_ev)


# ===========================================================================
# Ro'yxat
# ===========================================================================
ATTACKS: dict[str, FraudAttack] = {}


def _reg(key, title, threat, note, fn):
    ATTACKS[key] = FraudAttack(key, title, threat, note, fn)


_reg("t1_apk_dropper", "Telegram Android SMS-stealer/dropper", "T1",
     "Group-IB: 100 000+ qurilma zararlangan", _atk_t1_apk_dropper)
_reg("t2_vishing_otp", "Bank fishing + vishing (OTP aytdirish)", "T2",
     "Click/Payme/Uzcard-Humo taqlidi", _atk_t2_vishing_otp)
_reg("t3_gov_impersonation", "Davlat/sud nomidan qo'rqitish", "T3",
     "mygov.uz taqlidi", _atk_t3_gov_impersonation)
_reg("t4_sim_swap", "SIM swap orqali akkount egallash", "T4",
     "Telekom porting hujumi", _atk_t4_sim_swap)
_reg("t5_classiscam", "Classiscam bozor firibgarligi", "T5",
     "OLX va sh.k.", _atk_t5_classiscam)
_reg("t6_fake_investment", "Soxta investitsiya/ish e'lonlari", "T6",
     "Oldindan to'lov firibgarligi", _atk_t6_fake_investment)


def run_attack(key: str, trace: Optional[Trace] = None) -> FraudAttackResult:
    trace = trace or Trace()
    atk = ATTACKS[key]
    t0 = time.perf_counter()
    try:
        res = atk.run(trace)
    except Exception as exc:  # noqa: BLE001
        res = FraudAttackResult(atk.key, atk.title, atk.threat, Outcome.BROKEN,
                                [f"hujum bajarilmadi: {exc}"], Outcome.BROKEN,
                                [f"hujum bajarilmadi: {exc}"])
    res.elapsed_ms = (time.perf_counter() - t0) * 1000
    return res


def run_all(trace: Optional[Trace] = None) -> list[FraudAttackResult]:
    return [run_attack(k, trace) for k in ATTACKS]
