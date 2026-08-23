# AETHER-Q v5.1 — hujjat xaritasi (mapping table)

Texnik topshiriqda so'ralgan fayl nomlari AETHER-Q loyihasida **boshqacha
nomlanadi**. Bu jadval so'ralgan nom → haqiqiy manba mosligini qulflaydi.

Manba ildizi (upstream, bu repo tashqarisida):
`C:/Users/comp_2.1/Downloads/aether_q_v3/`

| Topshiriqdagi nom | Haqiqiy manba fayl | Holat |
|---|---|---|
| `SPEC.md` | `spec/AETHER_Q_V5.1_FULL_SPEC.md` (22 KB, 5.1.0-FINAL) | ✅ MAVJUD |
| `WIRE_FORMAT.md` | `spec/AETHER_Q_V5.1_FULL_SPEC.md` §6.1.1, §8.3 + `spec/AETHER_Q_V5.1_HANDSHAKE_DESIGN.md` | ✅ QISMAN — handshake va record wire-format bor; alohida hujjat yo'q |
| `THREAT_MODEL.md` | `audit_package/02_THREAT_MODEL.md` | ✅ MAVJUD |
| `KEY_LIFECYCLE.md` | `spec/AETHER_Q_V5.1_FULL_SPEC.md` §5 (epoch), §8.1 (key schedule), §8.4 (rekey) | ⚠ TARQOQ — yagona hujjat yo'q |
| `TEST_VECTORS.json` | `kat/aether_q_v51_kat.json` + `kat/gen_kat.py` | ⚠ QISMAN — pastga qarang |
| `ERROR_CODES.md` | `aether_q_v51/handshake.py` → `class Alert(IntEnum)` | ⚠ FAQAT KODDA — hujjat yo'q |

## Referens implementatsiya

`aether_q_v3/aether_q_v51/` — Python referens. Bizga kerakli modullar:

| Modul | Vazifa | Olinadi? |
|---|---|---|
| `kdf.py` | HKDF-SHA3-256, KMAC256, cSHAKE256, ct_eq | ✅ ha |
| `kem.py` | ML-KEM-768 (FIPS 203, OpenSSL orqali — **real**) | ✅ ha |
| `sig.py` | ML-DSA-65 (FIPS 204 — **real**) | ✅ ha |
| `hybrid.py` | X25519 + ML-KEM combiner (profil 0x01) | ✅ ha |
| `handshake.py` | negotiation, key schedule, ticket, resumption | ✅ ha |
| `transport.py` | §8 AEAD record layer (ChaCha20-Poly1305) | ✅ ha |
| `dos.py` | stateless PoW cookie | ✅ ha |
| `early.py` | 0-RTT (biz ISHLATMAYMIZ; `handshake` import qiladi) | ✅ ha, lekin o'chirilgan |
| `field.py` | GF(p) arifmetikasi (`hybrid` uchun) | ✅ ha |
| `zkp*.py`, `threshold*.py`, `dkg_pq.py`, `kkw.py`, `lsag.py`, `puf.py`, `mimc.py`, `zkboo.py` | 0x06/0x07/0x08 tadqiqot profillari | ❌ **YO'Q** |
| `net.py` | TCP framing | ❌ yo'q — bizda transport MQTT |

### Nega 0x06/0x07/0x08 olinmaydi

AETHER-Q ning 5-audit raundida ikkita KRITIK topilma bor edi (AQ-L01
soundness, AQ-L02 kvant modelida yaroqsiz yumshatuv), shu sababli bu
profillar deployable build'dan chiqarilgan. DistribOS AI ularga
**tayanmaydi** va ularni import qilmaydi — buni test qulflaydi.

Biz faqat **0x01 (X25519+ML-KEM-768 hybrid)** va **0x03 (ML-KEM-768
standalone)** profillarini ishlatamiz.

## Test vektorlari — halol baho

`kat/aether_q_v51_kat.json` (3.3 KB) quyidagilarni qamraydi:

* ✅ `hkdf_sha3_256`, `kmac256`, `cshake256` — primitiv darajasi
* ⚠ `zkp_0x06_combiner`, `threshold_0x07_combiner`, `puf_0x08_fuzzy` —
  **biz ishlatmaydigan** profillar uchun

**YETISHMAYDI:** 0x01/0x03 handshake uchun to'liq wire-level KAT, va §8
transport record layer uchun KAT.

DistribOS Mesh loyihasi bu bo'shliqni `android/shared-kat/aetherq_kat.json`
bilan to'ldirgan — Python yozuvi asosida generatsiya qilingan, Kotlin uni
baytma-bayt tekshiradi. Biz shu yondashuvni takrorlaymiz va kengaytiramiz
(`tools/gen_kat.py`), lekin buni **rasmiy AETHER-Q KAT'i deb atamaymiz** —
bu bizning cross-implementation moslik testimiz.

## Statusning halol bahosi

AETHER-Q o'z hujjatlari (`SECURITY.md`) bo'yicha:

> tadqiqot/demo — tayyor; pilot — shartli; **production — mustaqil audit shart**

DistribOS AI uni kuchli, sinovdan o'tgan qatlam sifatida ishlatadi, lekin
**sertifikatlangan deb da'vo qilmaydi**. Bu `docs/SECURITY.md` da ham
takrorlanadi va README'da da'vo sifatida ko'tarilmaydi.
