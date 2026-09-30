# AETHER-Q Zarbxona v3 — to'liq texnik spetsifikatsiya

Versiya: 1.0 · Sana: 2026-09-26 · Til: o'zbek (kod identifikatorlari ham o'zbekcha bo'lishi mumkin)

Bu hujjat **o'zi yetarli** qilib yozilgan. Uni o'qiyotgan dasturchi (yoki AI coder)
AETHER-Q loyihasining kodini ko'rmaydi: bank serveri, Rust ma'lumotnomasi va
`aetherq_core` kutubxonasi unga berilmaydi. Shuning uchun har bir bayt formati shu
yerda to'liq ta'riflangan va hujjat bilan birga **namunaviy vektorlar (KAT)** beriladi.

## Hujjat to'plami

| Fayl | Nima |
|---|---|
| `SPEC.md` | shu hujjat |
| `kat/zarbxona_kat_v1.json` | namunaviy vektorlar. Barcha baytlar hex. Rust ma'lumotnomasi bilan tasdiqlangan |
| `tools/kat_tekshir.py` | KAT'ni **faqat standart kutubxonalar** bilan qayta hisoblaydigan mustaqil tekshiruvchi. SPEC to'g'riligining isboti, ishlaydigan namuna kod |
| `tools/kat_yarat.py` | KAT qanday yaratilgani (faqat ma'lumot uchun: u AETHER-Q muhitini talab qiladi) |

**Birinchi qadam:** `pip install pycryptodome "cryptography>=47"` va
`python tools/kat_tekshir.py kat/zarbxona_kat_v1.json`. Natija `HAMMASI MOS` bo'lishi kerak.
Keyin v3 ning yadrosini yozing va xuddi shu KAT'dan o'tkazing.

### MUST / SHOULD

- **MUST** — bajarilmasa, bank partiyani rad etadi yoki xavfsizlik buziladi.
- **SHOULD** — sifat talabi; sababsiz chetlanmang.

---

## 1. Kontekst

### 1.1 AETHER-Q tizimi

AETHER-Q — post-kvant kriptografiyaga asoslangan shaxsiy bank tizimi. Unda
**CBDC** (raqamli pul) kupyuralar ko'rinishida muomalaga chiqariladi. Tizim to'rt
dasturdan iborat: Bank, Zarbxona, Desktop klient, Mobil klient.

**Delegatsiya modeli (asosiy g'oya):**

```
  BANK                                     ZARBXONA (shu loyiha)
  ─────                                    ──────────────────────
  ML-DSA-65 kaliti (bank)                  ML-DSA-65 kaliti (zarbxona)
  ledger, zaxira qulflari                  o'z jurnali, partiya fayllari
     │
     │ 1. sertifikat (.aqcert): «shu kalitga, shuncha limit, shu muddatgacha»
     └────────────────────────────────────────►
                                           2. kupyuralarni zarb qiladi (partiya)
                                           3. Merkle ildizini o'z kaliti bilan imzolaydi
     ◄────────────────────────────────────────┘
     4. partiya: fayl (.aqbatch) yoki onlayn (MQTT + AETHER-Q sessiyasi)
  5. bank hammasini QAYTA tekshiradi va qabul qiladi yoki rad etadi
```

- Zarbxona bank kalitini **hech qachon** olmaydi va bank bazasiga yozmaydi.
- Bank zarbxonaga ishonmaydi: hamma narsani qaytadan hisoblaydi (§11).
- Pul faqat **zaxira qulfi** (bank bergan `reserve_lock` identifikatori) bilan
  chiqariladi: qoplamasiz emissiya yo'q.
- Zarb qilingan pul avval xazina hisobiga (`AQ-TREASURY`) tushadi.

### 1.2 Oldingi versiyalar

| Versiya | Nima | Muammo |
|---|---|---|
| v1 (`mint_gui` + Rust `mint_core`) | asl zarbxona | faqat bank tekshirardi, jarayon ko'rinmasdi |
| v2 (Python, mustaqil) | bir xil spec'ning ikkinchi implementatsiyasi; o'z tekshiruvchisi, jurnal↔fayl nazorati, onlayn topshirish, konveyer sur'ati | uzilgan zarb yo'qoladi, 1 300 qatorli bitta oyna fayli, topshirish qo'lda |

v2 ning bayt-ma-bayt mosligi Rust ma'lumotnomasi bilan isbotlangan, haqiqiy bank
uning partiyalarini qabul qilgan. Shu hujjatdagi KAT v2 dan olingan va Rust bilan
qayta tasdiqlangan.

### 1.3 v3 maqsadi

Pul **sekin, kompyuter resursini kam sarflab, jonli kuzatuv ostida** zarb qilinsin.
Bu v3 ning asosiy xususiyati. Operator konveyerni ko'radi, sur'atni boshqaradi,
to'xtatadi va davom ettiradi. Shu bilan birga v3:

1. katta buyurtmani kichik partiyalarga bo'ladi va uzilishdan keyin **davom etadi** (§15);
2. sur'atni birinchi darajali xususiyat qiladi (§14);
3. tayyor partiyani avtomatik topshiradi (ixtiyoriy, §15.6);
4. kodni kichik, sinaladigan modullarga ajratadi (§17).

---

## 2. Kriptografik ibtidolar

**MUST:** kriptografik algoritmlarni o'zingiz yozmang, faqat quyidagi
kutubxonalarni ishlating. Istisno — AQ-KMAC256 (§2.2). U kutubxona
ibtidolari (`hashlib.shake_256`) ustiga yig'iladi.

| Ibtido | Kutubxona | Eslatma |
|---|---|---|
| SHA3-256 | `hashlib.sha3_256` | |
| SHAKE256 | `hashlib.shake_256` | AQ-KMAC256 uchun |
| AQ-KMAC256 | o'zingiz, §2.2 bo'yicha | ⚠ standart KMAC EMAS |
| HKDF-Expand (SHA3-256) | `hmac` + `hashlib.sha3_256` | RFC 5869 |
| ChaCha20-Poly1305 | `cryptography...aead.ChaCha20Poly1305` | IETF, kalit 32 B, nonce 12 B, teg 16 B |
| ML-DSA-65 | `cryptography...asymmetric.mldsa` (≥ 47) | FIPS 204 |
| scrypt | `hashlib.scrypt` | kalit ombori |
| tasodif | `secrets.token_bytes` / `os.urandom` | |

`pycryptodome` faqat tekshiruvchida kerak (standart KMAC farq qilishini isbotlash uchun).
v3 ga u **kerak emas**.

### 2.1 SHA3-256

`sha3(b) = hashlib.sha3_256(b).digest()` — 32 bayt.

### 2.2 AQ-KMAC256 — ⚠ ENG KATTA TUZOQ

AETHER-Q ning KMAC256'i NIST SP 800-185 dagi KMAC256 tuzilmasini takrorlaydi,
**lekin** ichidagi cSHAKE256 o'rniga oddiy SHAKE256 ishlatadi: padding bayti
`0x1F`, standartdagidek `0x04` emas. Bu protokol mualliflari **ataylab**
qilgan chetlanish. Domen ajratish prefiks orqali saqlanadi, lekin natija standart
KMAC bilan mos kelmaydi.

**Oqibat:** `Crypto.Hash.KMAC256` (pycryptodome), OpenSSL KMAC va boshqa
standart implementatsiyalar **BOSHQA** natija beradi. Ular bilan yozilgan
zarbxonaning har bir kupyura identifikatori noto'g'ri bo'ladi.

```python
import hashlib

RATE = 136  # SHAKE256 rate

def _left_encode(x: int) -> bytes:
    s = x.to_bytes(max(1, (x.bit_length() + 7) // 8), "big")
    return bytes([len(s)]) + s

def _right_encode(x: int) -> bytes:
    s = x.to_bytes(max(1, (x.bit_length() + 7) // 8), "big")
    return s + bytes([len(s)])

def _encode_string(s: bytes) -> bytes:
    return _left_encode(len(s) * 8) + s

def _bytepad(x: bytes, w: int = RATE) -> bytes:
    z = _left_encode(w) + x
    return z + bytes((-len(z)) % w)

def aq_cshake256(x: bytes, n: int, name: bytes, custom: bytes) -> bytes:
    if not name and not custom:
        return hashlib.shake_256(x).digest(n)
    prefiks = _bytepad(_encode_string(name) + _encode_string(custom))
    return hashlib.shake_256(prefiks + x).digest(n)        # 0x1F — ataylab

def kmac256(key: bytes, data: bytes, custom: bytes, n: int = 32) -> bytes:
    x = _bytepad(_encode_string(key)) + data + _right_encode(n * 8)
    return aq_cshake256(x, n, b"KMAC", custom)
```

Parametrlar tartibi: `kmac256(kalit, ma'lumot, domen_yorlig'i, uzunlik)`.
Shu hujjatda `custom` har doim domen yorlig'i (§3). **MUST:** KAT
`primitivlar.kmac256` dan o'tsin. Test standart KMAC'ning **farq qilishini**
ham qulflasin: kimdir keyinchalik «tuzatib» qo'ymasin.

### 2.3 HKDF-Expand (SHA3-256)

RFC 5869 Expand, xesh — SHA3-256 (HashLen = 32). Extract ishlatilmaydi.

```python
import hmac
def hkdf_expand(prk: bytes, info: bytes, n: int) -> bytes:
    assert n <= 255 * 32
    out, t, c = b"", b"", 1
    while len(out) < n:
        t = hmac.new(prk, t + info + bytes([c]), hashlib.sha3_256).digest()
        out += t; c += 1
    return out[:n]
```

### 2.4 ChaCha20-Poly1305

`seal(k, nonce, pt, aad) = ChaCha20Poly1305(k).encrypt(nonce, pt, aad)`. Natija:
`shifrmatn ‖ teg(16)`. `open` teg mos kelmasa istisno tashlaydi. **MUST:**
bitta kalit bilan bitta nonce hech qachon qayta ishlatilmasin (§4.4 da har
kupyuraga alohida kalit va nonce bor).

### 2.5 ML-DSA-65 (FIPS 204)

- Maxfiy kalit **32 baytlik urug'dan** (FIPS 204 KeyGen dagi ξ) hosil qilinadi:
  `MLDSA65PrivateKey.from_seed_bytes(seed)`.
- Ochiq kalit — **1952 bayt** (`public_bytes_raw()`), imzo — **3309 bayt**.
- Rejim: **sof ML-DSA** (pre-hash emas), **kontekst satri bo'sh**.
  `cryptography` ning `sign(msg)` / `verify(sig, msg)` metodlari aynan shunday.
- Imzo **tasodifiy** (hedged): bir xil xabar har safar boshqa imzo beradi.
  Shuning uchun testlarda imzo baytlari solishtirilmaydi, faqat `verify` tekshiriladi.
- **Tasdiqlangan:** `cryptography` imzosini AETHER-Q banki (`aetherq_core.verify`)
  qabul qiladi. Aksincha ham ishlaydi, urug'dan olingan ochiq kalit ham bir xil
  (2026-09-26 da sinalgan).
- `verify` har qanday xatoda `False` qaytarsin (fail-closed), istisno tashlamasin.

### 2.6 Kanonik kodlash — ikki XIL qoida

⚠ Ikkinchi tuzoq. Spec'da ikki xil uzunlik prefiksi bor va ular **aralashtirilmaydi**.

**(a) `lp()` — kichik-endian u64 prefiks.** Kupyura sarlavhasi (§4.1) va
partiya imzo xabari (§6.2) uchun:

```python
def lp(buf: bytearray, d: bytes) -> None:
    buf += len(d).to_bytes(8, "little") + d
u64le = lambda n: n.to_bytes(8, "little")
u128le = lambda n: n.to_bytes(16, "little")
```

**(b) `tagged_hash()` — katta-endian u32 prefiks.** Sertifikat, cheklov va
`mint_auth` uchun:

```python
def tagged_hash(label: bytes, *parts: bytes) -> bytes:
    b = b""
    for p in (label, *parts):
        b += len(p).to_bytes(4, "big") + p
    return sha3(b)
u64be = lambda n: n.to_bytes(8, "big")
```

### 2.7 Kalit izi (fingerprint)

Odam o'qiydigan iz: `sha3(ochiq_kalit).hex().upper()` ning birinchi 24 belgisi,
4 tadan `-` bilan bo'lingan. Masalan: `71AC-43F0-9FBB-1AB7-7EAF-0A74`.
Bank ham shu usulni ishlatadi. Operator izlarni ko'z bilan solishtiradi.

---

## 3. Konstantalar

### 3.1 Domen yorliqlari (ASCII baytlar, aynan shunday)

| Nom | Qiymat |
|---|---|
| `L_HEADER` | `AETHER-Q-CBDC/NOTE-HEADER/v1` |
| `L_ID` | `AETHER-Q-CBDC/NOTE-ID/v1` |
| `L_REST` | `AETHER-Q-CBDC/NOTE-REST/v1` |
| `L_CLAIM` | `AETHER-Q-CBDC/NOTE-CLAIM/v1` |
| `L_ROOT` | `AETHER-Q-CBDC/BATCH-ROOT/v1` |
| `L_CERT` | `AETHER-Q-CBDC/MINT-CERT/v1` |
| `L_CONSTRAINTS` | `AETHER-Q-CBDC/CONSTRAINTS/v1` |
| `L_MINT_AUTH` | `AETHER-Q-BANK/MINT-AUTH/v1` |
| `L_WIRE` | `AETHER-Q-BANK/WIRE/v1` |
| `L_KEYSTORE_AAD` | `AETHER-Q-BANK/KEYSTORE/v1` |
| `L_SRV_ID` | `AETHER-Q-v5.1-SRV-ID` |

### 3.2 Sonlar

| Nom | Qiymat |
|---|---|
| Nominallar (kattadan kichikka) | `5000, 1000, 500, 100, 50, 10, 5, 1` |
| Partiyadagi eng ko'p kupyura | `100 000` (bank ham shuni tekshiradi) |
| Xazina egasi | `"AQ-TREASURY"` |
| Yadro uzunligi | 56 = 32 + 8 + 16 |
| Muhr uzunligi | 72 = 56 + 16 (teg) |
| Partiya id | 16 bayt, tasodifiy |
| Partiya kaliti, master | 32 bayt, tasodifiy, **saqlanmaydi** |
| Sertifikat id | 16 bayt (bank beradi) |
| Onlayn bo'lak | 250 kupyura / `batch_chunk` |
| Bitta protokol xabari | ≤ 1 048 576 bayt (JSON) |

---

## 4. Kupyura

Kupyura qog'oz pulni takrorlaydi. U ikki qismdan iborat:

```
OCHIQ SARLAVHA  — ledger va audit o'qiydi
  note_id, nominal, egasi, seq, partiya_id, cheklov_xeshi
MUHRLANGAN YADRO — faqat egasi ochadi
  nazorat kaliti (32 B), zarb vaqti (u64), sertifikat id (16 B)
```

### 4.1 Sarlavha kodi (MUST, bayt-ma-bayt)

```python
def sarlavha_kodi(note_id, nominal, egasi, seq, partiya_id, cheklov_xeshi) -> bytes:
    b = bytearray()
    lp(b, b"AETHER-Q-CBDC/NOTE-HEADER/v1")
    lp(b, note_id)                  # 32 B
    lp(b, u64le(nominal))
    lp(b, egasi.encode("utf-8"))    # "AQ-TREASURY"
    lp(b, u64le(seq))
    lp(b, partiya_id)               # 16 B
    lp(b, cheklov_xeshi)            # 32 B
    return bytes(b)

sarlavha_xeshi = sha3(sarlavha_kodi(...))
barg           = sha3(b"\x00" + sarlavha_kodi(...))    # Merkle bargi
```

Sarlavha xeshi (AAD uchun) va barg — **ikki xil** qiymat: bargda `0x00` prefiks bor.

### 4.2 Identifikator va nazorat kaliti

```python
note_id        = kmac256(partiya_kaliti, partiya_id + u64le(indeks), L_ID)     # 32 B
nazorat_kaliti = kmac256(partiya_kaliti, note_id, L_CLAIM)                     # 32 B
```

`indeks` — kupyuraning partiyadagi o'rni, 0 dan boshlanadi. `seq` emas!
Nazorat kaliti kupyuraning «mikrochipi»: kimda shu kalit bo'lsa, kupyura o'shaniki.

### 4.3 Yadro

```python
yadro = nazorat_kaliti (32) + u64le(zarb_ms) (8) + sert_id (16)     # 56 B
```

### 4.4 Muhr

```python
km    = hkdf_expand(master, L_REST + note_id, 44)
kalit, nonce = km[:32], km[32:44]
muhr  = chacha20poly1305_seal(kalit, nonce, yadro, aad=sarlavha_xeshi)   # 72 B
```

**AAD = sarlavha xeshi.** Bazada nominal yoki egasi o'zgartirilsa, yadro ochilmaydi.
Shifrlash shu tariqa yaxlitlikni ham ta'minlaydi. Muhrni ochishda xato sababi
aytilmaydi (kalitmi, sarlavhami): shunchaki `None` qaytadi.

---

## 5. Merkle daraxti

```python
def tugun(chap, ong):  return sha3(b"\x01" + chap + ong)

def qavatlar(barglar):
    if not barglar: return [[bytes(32)]]           # bo'sh ildiz = 32 nol bayt
    q = [list(barglar)]
    while len(q[-1]) > 1:
        j = q[-1]
        k = [tugun(j[i], j[i+1]) for i in range(0, len(j) - 1, 2)]
        if len(j) % 2: k.append(j[-1])              # ⚠ toq tugun NUSXALANMAYDI —
        q.append(k)                                  #   o'zgarishsiz ko'tariladi
    return q

ildiz = qavatlar(barglar)[-1][0]
```

**Isbot** — pastdan yuqoriga qo'shni xeshlar ro'yxati. Tomon indeksdan aniqlanadi.
Qo'shnisi bo'lmagan (toq, ko'tarilgan) qavatda isbotga hech narsa qo'shilmaydi:

```python
def isbot(q, i):
    yol = []
    for qavat in q[:-1]:
        s = i + 1 if i % 2 == 0 else i - 1
        if s < len(qavat): yol.append(qavat[s])
        i //= 2
    return yol

def isbot_togri(barg, yol, i, soni, ildiz) -> bool:
    if soni == 0 or not 0 <= i < soni: return False
    x, j, n = barg, 0, soni
    while n > 1:
        s = i + 1 if i % 2 == 0 else i - 1
        if s < n:
            if j >= len(yol): return False
            x = tugun(x, yol[j]) if i % 2 == 0 else tugun(yol[j], x); j += 1
        i //= 2; n = (n + 1) // 2
    return j == len(yol) and x == ildiz
```

Faylda isbot `b"".join(yol)` ko'rinishida saqlanadi. Uzunligi 32 ga karrali bo'ladi.

⚠ **Samaradorlik tuzog'i (v2 da topilgan):** har kupyura uchun `isbot()` ni
butun daraxtni qayta qurib chaqirish O(n²) bo'ladi: 3 000 kupyura 6,5 soniya
oladi. **MUST:** daraxt partiyaga **bir marta** quriladi va barcha isbotlar
shundan olinadi (0,08 s).

---

## 6. Partiya

### 6.1 Zarb algoritmi

```
kirish: nominallar[], sert_id, zaxira_qulfi, birinchi_seq, cheklov_json, egasi="AQ-TREASURY"
tekshir: 1 ≤ soni ≤ 100 000; har nominal ∈ NOMINALLAR; birinchi_seq ≥ 1;
         zaxira_qulfi.strip() bo'sh emas; cheklov_xeshi 32 B

partiya_id     = tasodif(16)
partiya_kaliti = tasodif(32)          # xotirada, diskka YOZILMAYDI
master         = tasodif(32)          # xotirada, diskka YOZILMAYDI
zarb_ms        = int(time.time()*1000)   # partiyaga BITTA vaqt, hamma kupyuraga bir xil
cheklov_xeshi  = §7.2

har i uchun: note_id → sarlavha (seq = birinchi_seq + i) → yadro → muhr → barg
ildiz, isbotlar = §5
imzo = ML-DSA-65.sign(zarbxona_kaliti, imzo_xabari)   # §6.2
```

Test/KAT uchun `partiya_id`, `partiya_kaliti`, `master` va `zarb_ms` tashqaridan
berilishi mumkin bo'lsin. Ishlab chiqarish rejimida ular faqat tasodifdan olinadi.

### 6.2 Imzo xabari (BATCH-ROOT/v1)

```python
def imzo_xabari(ildiz, partiya_id, soni, jami, zaxira_qulfi, zarb_ms) -> bytes:
    b = bytearray()
    lp(b, b"AETHER-Q-CBDC/BATCH-ROOT/v1")
    lp(b, ildiz)                              # 32 B
    lp(b, partiya_id)                         # 16 B
    lp(b, u64le(soni))
    lp(b, u128le(jami))                       # ⚠ summa 128-bitli
    lp(b, zaxira_qulfi.strip().encode("utf-8"))
    lp(b, u64le(zarb_ms))
    return bytes(b)
```

Bank bu xabarni **o'zi** quradi va zarbxona imzosini tekshiradi. Ya'ni sertifikat
id va cheklov imzo xabariga kirmaydi. Ular har kupyuraning bargi orqali ildizga
bog'langan (cheklov xeshi) yoki yadroda muhrlangan (sertifikat id).

### 6.3 Summani nominallarga bo'lish

Ochko'z algoritm, kattadan kichikka:

```python
def nominallarga_bol(summa):
    assert summa > 0
    natija, q = [], summa
    for n in (5000, 1000, 500, 100, 50, 10, 5, 1):
        k, q = divmod(q, n); natija += [n] * k
    return natija
# 1 234 567 → 246×5000, 4×1000, 1×500, 1×50, 1×10, 1×5, 2×1 = 256 kupyura
```

v2 da bitta partiya 100 000 kupyuradan oshsa xato berilardi. v3 da buyurtma
partiyalarga bo'linadi (§15), shuning uchun buyurtma darajasida bu cheklov yo'q.

---

## 7. Cheklov (dasturlanadigan pul)

### 7.1 Kanonik JSON

```python
def cheklov_json(toifalar=(), muddat_ms=None, soliq_bps=0, soliq_hisobi="") -> str:
    t = sorted({x.strip().upper() for x in toifalar if x.strip()})
    # tekshiruvlar:
    #  len(t) ≤ 8; har toifa ≤ 32 belgi va x.replace("_","").isalnum()
    #  0 ≤ soliq_bps < 10000; soliq_bps>0 ⇔ soliq_hisobi bo'sh emas
    #  muddat_ms None yoki > 0
    d = {}
    if t: d["categories"] = t
    if muddat_ms: d["expires_ms"] = int(muddat_ms)
    if soliq_bps: d["tax_bps"] = int(soliq_bps); d["tax_account"] = soliq_hisobi
    if not d: return ""                                    # cheklovsiz — BO'SH SATR
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

### 7.2 Cheklov xeshi

```python
cheklov_xeshi = bytes(32) if json_satr == "" else tagged_hash(L_CONSTRAINTS, json_satr.encode())
```

Xesh **har bir kupyuraning sarlavhasiga** kiradi. Ya'ni imzolangandan keyin qoidani
o'zgartirib bo'lmaydi. Bitta partiyadagi hamma kupyuralarning cheklovi bir xil.

---

## 8. Sertifikat (`.aqcert`)

### 8.1 Fayl formati (JSON, UTF-8)

```json
{
  "format": "AETHER-Q-CBDC-CERT",
  "version": 1,
  "cert_id": "<16 B hex>",
  "bank_public_key": "<1952 B hex>",
  "mint_public_key": "<1952 B hex>",
  "label": "Vakolat nomi",
  "limit_amount": 50000000,
  "valid_from_ms": 1700000000000,
  "valid_until_ms": 1900000000000,
  "signature": "<3309 B hex — bank imzosi>"
}
```

### 8.2 Bank imzolagan xabar (MINT-CERT/v1)

```python
xabar = tagged_hash(L_CERT, mint_public_key, cert_id, label.encode("utf-8"),
                    u64be(limit_amount), u64be(valid_from_ms), u64be(valid_until_ms))
# ⚠ bu yerda u32 BE prefiks va u64 BE sonlar (§2.6-b)
```

Imzo `xabar` ning **o'zi** ustiga qo'yiladi (xabar — 32 baytlik xesh).

### 8.3 Yaroqlilik (tartib muhim, birinchi muammo qaytariladi)

1. `mint_public_key == zarbxona ochiq kaliti`, aks holda «BOSHQA zarbxonaga berilgan»;
2. bank imzosi `bank_public_key` bilan to'g'ri;
3. `limit_amount > 0`;
4. `hozir ≥ valid_from_ms`, aks holda «hali kuchga kirmagan»;
5. `hozir ≤ valid_until_ms`, aks holda «muddati o'tgan».

Sertifikat import qilinganda shu tekshiruvlar bajariladi va fayl profil papkasiga
nusxalanadi. **Bank ochiq kaliti sertifikatdan olinadi**: onlayn ulanishda aynan
shu kalit pinlanadi (§13).

`qolgan_limit = limit_amount − (shu cert_id bo'yicha jurnaldagi jami)`. Bank o'zida
ham hisoblaydi (`minted_total`). Zarbxonaning hisobi faqat erta ogohlantirish uchun.

---

## 9. Kalit ombori (`kalit.json`)

Bank dasturi bilan bir xil format. Eski zarbxona kalitini ham ochadi.

```json
{
  "version": 1,
  "kdf": {"name": "scrypt", "n": 32768, "r": 8, "p": 1, "salt": "<16 B hex>"},
  "nonce": "<12 B hex>",
  "ciphertext": "<(32+16) B hex>",
  "public_key": "<1952 B hex>"
}
```

```python
k    = hashlib.scrypt(parol.encode(), salt=salt, n=n, r=r, p=p, dklen=32, maxmem=256*2**20)
urug = ChaCha20Poly1305(k).decrypt(nonce, ciphertext, b"AETHER-Q-BANK/KEYSTORE/v1")
# ochiq kalitni urug'dan qayta hisoblab, fayldagi "public_key" bilan SOLISHTIRING —
# mos kelmasa: «ombordagi ochiq kalit urug'ga mos emas»
```

- Parol kamida 8 belgi. Noto'g'ri parol uchun xabar bitta: «parol noto'g'ri yoki fayl buzilgan».
- `public_key` ochiq saqlanadi. Kirish ekranida kalit izi (§2.7) parolsiz ko'rsatiladi.
- Yozish atomik: `kalit.json.tmp` ga yoziladi, keyin `os.replace`.
- Testlarda `n = 4096` ishlatish mumkin (tezlik uchun). Ishlab chiqarishda 32768.

---

## 10. Partiya fayli (`.aqbatch`)

SQLite fayli. Sxema **aynan** shunday: ustun nomlari va tartibi ham shu.
Bank uni `aqmint.import_batch` bilan o'qiydi.

```sql
CREATE TABLE header (
    magic        TEXT    NOT NULL,   -- "AETHER-Q-CBDC-BATCH"
    version      INTEGER NOT NULL,   -- 1
    batch_id     BLOB    NOT NULL,   -- 16 B
    cert_id      BLOB    NOT NULL,   -- 16 B
    root         BLOB    NOT NULL,   -- 32 B
    note_count   INTEGER NOT NULL,
    first_seq    INTEGER NOT NULL,
    total        INTEGER NOT NULL,
    reserve_lock TEXT    NOT NULL,
    minted_ms    INTEGER NOT NULL,
    signature    BLOB    NOT NULL,   -- 3309 B
    mint_label   TEXT    NOT NULL,   -- sertifikat "label"
    constraints  TEXT    NOT NULL    -- kanonik cheklov JSON yoki ""
);
CREATE TABLE notes (
    leaf_index       INTEGER PRIMARY KEY,   -- 0..soni-1
    note_id          BLOB    NOT NULL,
    denomination     INTEGER NOT NULL,
    owner            TEXT    NOT NULL,
    seq              INTEGER NOT NULL,
    batch_id         BLOB    NOT NULL,
    constraints_hash BLOB    NOT NULL,
    sealed_core      BLOB    NOT NULL,      -- 72 B
    proof            BLOB    NOT NULL       -- 32·k B
);
```

- Fayl nomi: `partiya-<batch_id hex birinchi 12 belgi>.aqbatch`.
- **Atomik yozish (MUST):** avval `<nom>.aqbatch.yarim` ga yoziladi, `commit`,
  `close`, keyin nomi o'zgartiriladi. Uzilib qolgan yozuv tayyor partiya
  ko'rinishida qolmasin.
- O'qish: `sqlite3.connect("file:<yo'l>?mode=ro", uri=True)`, `magic` va
  `version` tekshiriladi, qatorlar `ORDER BY leaf_index` bilan olinadi.

---

## 11. Bank qabul qoidalari

Bank partiyani faqat quyidagilarning **hammasi** bajarilsa qabul qiladi.
v3 ning o'z tekshiruvchisi (§12) bularni topshirishdan **oldin** takrorlaydi.

1. Sertifikat bankda mavjud, bank imzosi to'g'ri, faol va muddati ichida.
2. `1 ≤ note_count ≤ 100 000`, qatorlar soni = `note_count`.
3. Nominallar yig'indisi = `total`.
4. `total ≤ sertifikatning qolgan limiti`.
5. `batch_id` avval qabul qilinmagan. Takror bo'lsa: «bu partiya allaqachon qabul qilingan».
6. Zaxira qulfi mavjud, bo'shatilmagan va `total ≤ qulfdagi bo'sh summa`.
7. Imzo xabarini (§6.2) bank o'zi quradi, zarbxona imzosi `mint_public_key` bilan to'g'ri.
8. Har kupyura: `batch_id` mos; `owner == "AQ-TREASURY"`; `nominal > 0`;
   `seq == first_seq + index`; `constraints_hash` = e'lon qilingan cheklov xeshi;
   Merkle isboti ildizga olib boradi.

Bank rad etgan partiya bank tomonida hech narsa o'zgartirmaydi.

---

## 12. O'z tekshiruvchisi

Zarbdan keyin, faylga yozishdan **oldin**, partiya noldan qayta hisoblanadi.
Faqat toza bo'lsa yoziladi. Xuddi shu tekshiruvchi «Tekshiruv» sahifasida
istalgan faylga va butun jurnalga qo'llanadi.

**Partiya darajasi.** Har muammo `(qayerda, qoida, izoh)` ko'rinishida yoziladi.

| Qoida | Tekshiruv |
|---|---|
| `bo'sh` | soni > 0 |
| `tartib` | `seq == birinchi_seq + i` |
| `nominal` | NOMINALLAR ichida |
| `partiya-id` | kupyuradagi = sarlavhadagi |
| `cheklov` | kupyura cheklov xeshi = `cheklov_xeshi(header.constraints)` |
| `muhr` | uzunlik 72 |
| `ildiz` | barglardan qayta hisoblangan = fayldagi |
| `isbot` | isbot to'g'ri. Katta partiyada namuna: boshidan, o'rtasidan, oxiridan jami ≤ 2000 ta. Ildiz baribir HAMMA bargdan hisoblanadi |
| `imzo` | ML-DSA imzo to'g'ri (§6.2) |
| `sertifikat` / `vakolat` / `limit` | sert_id mos, sertifikat yaroqli (§8.3), `jami ≤ limit` |

**Jurnal darajasi** (jurnal ↔ fayllar): fayl mavjud; fayldagi summa, soni, ildiz,
seq oralig'i va zaxira qulfi jurnaldagi bilan bir xil; partiyalar seq oraliqlari
**kesishmaydi**; sertifikat bo'yicha jami chiqarilgan ≤ limit.

**Hisobot:** `ok` faqat muammo yo'q bo'lsa. «Tekshirilmadi» hech qachon «toza»
deb ko'rsatilmaydi. Masalan, fayl ochilmasa — bu muammo.

**Buzib ko'rish demosi (SHOULD).** Faylni yoki jurnalni ataylab buzib,
tekshiruv topishini ko'rsatadi. Nominal, egasi, imzoning bitta bayti, jurnal
summasi, faylni o'chirish. «Tiklash» asl holatga qaytaradi. ⚠ **Buzish qiymati
joriy qiymatdan FARQ qilishi shart.** v2 da «nominalni 5000 qilish» demosi
kupyura allaqachon 5000 bo'lgani uchun hech narsani buzmagan. Buni test qulflasin.

---

## 13. Onlayn topshirish protokoli

### 13.1 Qatlamlar

```
MQTT mavzulari            aetherq/bank/<bank_id>/c2b|b2c/<sessiya_id>
  wire (AQW1)             soxta va takroriy paketlarni AEAD'ga QADAR tashlaydi
    AETHER-Q v5.1 sessiya  handshake + AEAD yozuv qatlami (tashqi komponent, §13.3)
      JSON so'rov/javob   {"v":1,"op":…,"id":…}
```

### 13.2 MQTT (kanal)

- Default broker: `broker.hivemq.com:1883` (bepul, ochiq). Sozlanadigan bo'lsin.
- Kutubxona: `paho-mqtt ≥ 2`, `CallbackAPIVersion.VERSION2`, `clean_session=True`,
  `client_id = "zarbxona-" + sessiya_id`, keepalive 60.
- `bank_id = sha3(b"AETHER-Q-v5.1-SRV-ID" + bank_public_key).hex()[:16]`.
- `sessiya_id = tasodif(8).hex()`.
- Zarbxona `…/c2b/<sessiya_id>` ga **nashr qiladi** (qos=1) va
  `…/b2c/<sessiya_id>` ga **obuna bo'ladi** (qos=1).
- ⚠ Obuna **tasdiqlanmaguncha** hech narsa yubormang (`on_connect` → `subscribe` →
  tayyor hodisasi). Aks holda birinchi javob yo'qoladi.
- Yopish tartibi: avval `disconnect()`, keyin `loop_stop()`. Shunda oldingi «bye»
  paketi brokerga yetib boradi.
- Broker ishonchsiz: u paketlarni ko'radi, lekin o'qiy olmaydi va o'zgartira olmaydi.
  QoS1 tufayli paketni **takrorlab** yuborishi mumkin, buni wire hal qiladi.

### 13.3 AETHER-Q sessiyasi — tashqi komponent (adapter)

Handshake va yozuv qatlami — AETHER-Q v5.1 protokoli (gibrid post-kvant
handshake). U `aetherq_core` kutubxonasida (Rust, PyO3). Bu kutubxona PyPI da
yo'q va sizning muhitingizda **mavjud emas**. Uni o'zingiz yozmang.
v3 sessiyani **adapter interfeysi** orqali ishlatadi:

```python
class Handshake(Protocol):
    def start(self) -> bytes: ...                      # birinchi paket (klient → bank)
    def recv(self, paket: bytes) -> bytes | None: ...  # javob paketi yoki None; xato → istisno
    @property
    def is_connected(self) -> bool: ...
    def take_session(self) -> "Sessiya": ...

class Sessiya(Protocol):
    def seal(self, ochiq: bytes) -> bytes: ...
    def open(self, paket: bytes) -> tuple[int, bytes]: ...   # (yozuv turi, ochiq matn); xato → istisno

class SessiyaFabrikasi(Protocol):
    def mijoz(self, bank_ochiq_kaliti: bytes) -> Handshake: ...   # bank kaliti PINLANGAN
```

- **Haqiqiy implementatsiya** (`AetherQFabrika`) foydalanuvchi mashinasida ishlaydi:
  `import aetherq_core as aq`; `aq.ClientHandshake(bank_pk)` — aynan yuqoridagi
  interfeysga ega (`start`, `recv`, `is_connected`, `take_session`; sessiyada
  `seal`, `open`). Adapter shunchaki shu obyektlarni qaytaradi.
- `aetherq_core` import bo'lmasa, onlayn topshirish **o'chiriladi** va aniq xabar
  chiqadi: «onlayn topshirish uchun aetherq_core kerak; fayl orqali topshirish
  ishlaydi». Qolgan barcha funksiyalar usiz ishlaydi.
- **Testlar** uchun `SoxtaFabrika` yoziladi: handshake bitta paket almashadi;
  `seal`/`open` — shifrsiz o'rash va tur baytini tekshirish. Bu faqat protokolning
  yuqori qatlamini sinash uchun. Xavfsizlik uchun emas.
- Handshake: `start()` paketini yuboring; `is_connected` bo'lguncha kelgan har
  paketni `recv()` ga bering va qaytgan javobni yuboring. Umumiy muddat 90 s.

### 13.4 Xabar formati

UTF-8 JSON, `separators=(",", ":")`, `ensure_ascii=False`, ≤ 1 MiB.

- So'rov: `{"v":1, "op":"<amal>", "id":<int>, ...parametrlar}`. `id` har so'rovda
  +1 oshadi, 1 dan boshlanadi.
- Muvaffaqiyatli javob: `{"v":1, "id":<so'rov id>, "ok":true, "data":<...>}`.
- Xato: `{"v":1, "id":<id>, "ok":false, "code":"<kod>", "error":"<matn>"}`.
  Kodlar: `bad_request`, `unauthorized`, `forbidden`, `bank_error`, `internal`.
- `"op":"event"` — bank hodisasi. Javob emas, e'tiborsiz qoldiriladi.
- Javob `id` si so'rovnikiga teng bo'lishi SHART. Teng bo'lmasa — protokol xatosi.

### 13.5 Oqim

```
Zarbxona                                        Bank
   │── handshake (bank kaliti sertifikatdan, PINLANGAN) ──►│
   │◄── {"op":"challenge","id":0,"nonce":<32B hex>,"wire_key":<32B hex>}  (wire'SIZ)
   │   ── shu paytdan boshlab zarbxona HAR paketni wire bilan o'raydi ──
   │── {"op":"mint_auth","id":1,"cert_id":<hex>,"signature":<hex>} ──►│
   │◄── ok: {"cert_id","label","limit","minted_total","remaining","chunk_notes":250}
   │── {"op":"batch_begin","id":2, batch_id, root, note_count, first_seq, total,
   │        reserve_lock, minted_ms, signature, constraints} ──►│
   │◄── ok: {"expect_notes":N,"chunk_notes":250}
   │── {"op":"batch_chunk","id":3,"rows":[...≤250 qator...]} ──►│   × ⌈N/250⌉
   │◄── ok: {"received":<shu paytgacha jami>}
   │── {"op":"batch_commit","id":k} ──►│            ← bank QARORI shu yerda
   │◄── ok: {"batch_id","note_count","total","accepted_ms"}
   │── {"op":"bye","id":0}  (javob kutilmaydi) ──►│
```

- **`mint_auth` imzosi:**
  `sign(zarbxona_kaliti, tagged_hash(L_MINT_AUTH, bank_public_key, nonce, cert_id))`.
  Bank kaliti, chaqiriq va sertifikatga bog'langan: boshqa bankka, sessiyaga yoki
  vakolatga ko'chirib bo'lmaydi. Rad etilsa, bank `unauthorized` qaytaradi va ulanishni yopadi.
- **`batch_begin` parametrlari:** `batch_id`, `root`, `signature` — hex;
  `note_count`, `first_seq`, `total`, `minted_ms` — int; `reserve_lock` — str;
  `constraints` — kanonik cheklov JSON satri (bo'sh bo'lishi mumkin).
- **Qator (`rows` elementi) — 8 maydonli ro'yxat.** Baytlar standart base64 da
  (padding bilan), chunki hex ikki barobar joy oladi:
  `[b64(note_id), nominal, egasi, seq, b64(batch_id), b64(constraints_hash), b64(sealed_core), b64(proof)]`.
- Bir sessiyada bir vaqtda faqat bitta ochiq partiya. Oldingisi tugamasa: `bank_error`.
- **Xato yoki bekor qilish:** `batch_abort` yuboriladi (muddat 5 s, uning xatosi
  asosiy xatoni yashirmasin). Bank yarim yig'ilgan partiyani tashlaydi (`{"aborted":true}`).
- **Muddatlar:** har so'rov javobi 60 s; bank autentifikatsiyani 30 s kutadi;
  bo'sh sessiya bankda 600 s dan keyin yopiladi.
- **Idempotentlik:** bank «bu partiya allaqachon qabul qilingan» desa, partiya
  **topshirilgan** deb belgilanadi. Bu xato emas: oldingi urinishda javob yo'qolgan
  bo'lishi mumkin.
- Bitta qator base64 bilan ~0,4–1 KB. Isbot uzunligi partiya hajmiga bog'liq:
  `32·⌈log₂ soni⌉` bayt. 100 000 kupyurali partiyada 250 qatorli bo'lak ~240 KB,
  ya'ni 1 MiB chegaraga sig'adi.

### 13.6 Wire qatlami (AQW1)

**Nega kerak:** AETHER-Q sessiyasi AEAD tegi mos kelmagan birinchi yozuvdan keyin
«zaharlanadi», ya'ni o'ladi. Ochiq brokerda istalgan odam sessiya mavzusiga
tasodifiy paket tashlab, ulanishni uzishi mumkin. QoS1 dublikati ham shunday qiladi.
Wire ularni AEAD'ga yetkazmay tashlaydi.

```
paket = b"AQW1" ‖ u64_BE(hisoblagich) ‖ teg(16) ‖ yozuv
teg   = sha3(L_WIRE ‖ wire_key ‖ yo'nalish ‖ u64_BE(hisoblagich) ‖ yozuv)[:16]
yo'nalish: klient→bank b"c2b", bank→klient b"b2c"
```

- `wire_key` — `challenge` dagi 32 bayt. U allaqachon shifrlangan kanal ichida keladi.
- `challenge` o'ralmagan keladi. Zarbxonaning **birinchi** o'ralgan paketi
  (`mint_auth`) bankda wire rejimini yoqadi. Shundan keyin bank ham o'raydi.
- Yuborish hisoblagichi 1 dan boshlanadi va har paketda +1 oshadi.
- Qabul: sehr so'zi mos emas, uzunlik < 28, teg mos emas (**constant-time**
  solishtirish: `hmac.compare_digest`) yoki `hisoblagich ≤ oxirgi qabul qilingan`
  bo'lsa, paket jim tashlanadi, `tashlangan` hisoblagichi +1 oshadi va kutish davom
  etadi. Sessiya tirik qoladi.

---

## 14. Konveyer sur'ati (v3 ning asosiy xususiyati)

### 14.1 Nega

Zarbning o'zi tez: bitta kupyura ~0,03 ms, ya'ni 100 000 kupyura bir necha
soniyada tayyor bo'ladi. Bu ikki narsani yo'qotadi: protsessor to'la band bo'ladi va
operator jarayonni ko'rmaydi. v3 da pul **sekin, kam resurs bilan, kuzatuv ostida**
zarb qilinadi. Bu bezak emas, asosiy talab.

### 14.2 Sozlamalar

| Sozlama | Ma'nosi | Default |
|---|---|---|
| rejim | `tezlik` · `davomiylik` · `cheklovsiz` | `tezlik` |
| tezlik | kupyura/soniya (> 0) | 8 |
| davomiylik | buyurtma (yoki partiya) shuncha vaqtda tugasin, daqiqa | 10 |
| protsessor byudjeti | ish ulushi, 0 < b ≤ 1 (duty cycle) | 0,25 |
| sovutish | har `N` kupyuradan keyin `X` soniya tanaffus (N = 0 — o'chiq) | N = 25, X = 2 |

`davomiylik` rejimida tezlik hisoblanadi. Tanaffuslar ham berilgan vaqt ichiga kiradi:

```python
tanaffus = (soni // N) * X if N > 0 else 0
tezlik   = soni / max(davomiylik_s - tanaffus, davomiylik_s * 0.05)
```

Sozlamalar profilda saqlanadi va dastur qayta ochilganda tiklanadi.

### 14.3 Ritm algoritmi (MUST — aynan shu mantiq)

```python
ENG_QISQA_UYQU = 0.004   # bundan qisqa uyqu qilinmaydi; qarz keyingi qadamga o'tadi
BOLAK = 0.10             # uzun kutish shunday bo'laklarga bo'linadi

class Ritm:
    def __init__(self, s, soat=time.perf_counter, uxla=time.sleep,
                 toxtatildi=None, tanaffus=None):
        self.boshlangan = soat(); self.oxirgi = self.boshlangan
        self.ishlagan = 0.0      # sof ish vaqti
        self.uxlagan = 0.0       # jami kutish (tanaffus ham)
        self.tanaffusda = 0.0    # shundan sovutishga ketgani

    def qadam(self, bajarildi):           # har kupyuradan KEYIN chaqiriladi
        hozir = soat(); self.ishlagan += hozir - self.oxirgi
        kerak = 0.0
        if s.byudjet < 1:                 # ish / (ish + uyqu) = byudjet
            kerak = self.ishlagan * (1 - s.byudjet) / s.byudjet - self.uxlagan
        if s.tezlik is not None:          # lenta tezligi
            nishon = self.boshlangan + self.tanaffusda + bajarildi / s.tezlik
            kerak = max(kerak, nishon - hozir)
        if kerak >= ENG_QISQA_UYQU:
            self._kut(kerak)
        if s.N > 0 and s.X > 0 and bajarildi % s.N == 0:
            if tanaffus: tanaffus(s.X)    # monitorga «sovutish rejimi» satri
            self.tanaffusda += s.X
            self._kut(s.X)
        self.oxirgi = soat()

    def _kut(self, t):                    # bo'laklab — TO'XTATISH darhol ishlasin
        qolgan = t
        while qolgan > 0:
            if toxtatildi and toxtatildi(): raise BekorQilindi()
            b = min(qolgan, BOLAK); uxla(b); qolgan -= b
        self.uxlagan += t
```

(`s.N` va `s.X` — §14.2 dagi sovutish parametrlari.)

Uchta muhim qoida:

1. **Ikki chegaradan kattarog'i** tanlanadi: tezlik «qancha tez», byudjet «qancha
   resurs» degan savolga javob beradi.
2. ⚠ **Tanaffus vaqti tezlik nishonidan chegiriladi** (`self.tanaffusda`). v2 da bu
   yo'q edi: 2 soniyalik sovutishdan keyin konveyer «qarzni yopish» uchun 9 ta
   kupyurani bir zumda chiqarib yubordi. Monitor buni ko'rsatdi.
3. `soat` va `uxla` tashqaridan beriladi. Testlar soxta soat bilan ishlaydi va
   haqiqiy vaqt kutmaydi. «6 soatlik zarb» millisekundlarda sinaladi.

**PAUZA (v3 da yangi, SHOULD):** `_kut` va `qadam` pauza bayrog'ini ham tekshiradi.
Pauzada kutilgan vaqt `tanaffusda` ga qo'shiladi, aks holda davomdan keyin konveyer
portlaydi. Pauza qilingan partiyaning `zarb_ms` i o'zgarmaydi.

### 14.4 Zarb halqasiga ulanish

```
har kupyura: yasash → kuzatuv(kupyura, i, soni) → ritm.qadam(i+1)
             → jarayon(i+1, soni) (False → bekor) → bekormi() (True → bekor)
```

- Sur'at cheklangan yoki kuzatuv yoqilgan bo'lsa, bekor qilish **har kupyurada**
  tekshiriladi. Cheklovsiz rejimda har 250 kupyurada.
- **Sur'at natijani o'zgartirmaydi (MUST, test bilan):** bir xil kirishda sekin va
  tez zarbning ildizi, muhrlari va imzo xabari bayt-ma-bayt bir xil.

### 14.5 Taxminiy vaqt

```python
def taxminiy_vaqt(s, soni, kupyura_ms):
    t = soni * kupyura_ms / 1000 / s.byudjet
    if s.tezlik: t = max(t, soni / s.tezlik)
    if s.N and s.X: t += (soni // s.N) * s.X
    return t
```

`kupyura_ms` qat'iy son emas. Uni zarbning birinchi ~50 kupyurasida **o'lchab**
yangilang. Taxminiy va o'lchangan qiymatni interfeysda farqlang.

### 14.6 O'lchangan natijalar (v2, Windows, 3 000 kupyura)

| Sur'at | Tezlik | Protsessor band |
|---|---|---|
| cheklovsiz | 38 700 kupyura/s | 100 % |
| byudjet 20 % | 5 663 kupyura/s | 17,7 % |
| tezlik 50/s | 50,0 kupyura/s | ~0 % |
| tezlik 100/s + byudjet 20 % | 97,3 kupyura/s | ~0 % |

CPU ulushi `process_time / devor_vaqti` bilan o'lchanadi. ⚠ Windows'da
`process_time` granulyarligi ~15,6 ms. Qisqa o'lchovlar ishonchsiz, uzunroq oling.

---

## 15. v3 da yangi: buyurtma, davom ettirish, avto-topshirish

### 15.1 Buyurtma

Operator **buyurtma** beradi: summa, zaxira qulfi, cheklov, sur'at, partiya hajmi.
Buyurtma bir nechta kichik partiyaga bo'lib zarb qilinadi.

```
nominallar = nominallarga_bol(summa)     # deterministik, cheklovsiz uzunlik
partiya_hajmi = K (default 500, 1..100 000)
partiya j: nominallar[j*K : (j+1)*K]
```

Nominallar ro'yxati saqlanmaydi. U summadan har safar **deterministik** qayta
hisoblanadi, shuning uchun `bajarilgan_kupyura` hisobi yetarli.

### 15.2 Nega shunday (xavfsizlik bilan bog'liq)

Partiya kaliti va master **hech qachon diskka yozilmaydi**. Aks holda o'g'irlanishi
mumkin bo'lgan yana bir sir paydo bo'lardi. Demak yarim zarb qilingan partiyani davom
ettirib bo'lmaydi. Sekin zarb esa soatlab davom etadi. Yechim — kichik partiyalar.
Har biri yopilgach darhol imzolanib jurnalga yoziladi. Uzilishda faqat **joriy**
partiya yo'qoladi: u hali imzolanmagan va hech qayerda mavjud emas. Buyurtma keyingi
kupyuradan davom etadi.

### 15.3 Jurnal (v3 sxemasi)

```sql
CREATE TABLE sozlama (kalit TEXT PRIMARY KEY, qiymat TEXT NOT NULL);

CREATE TABLE buyurtmalar (
    buyurtma_id        TEXT PRIMARY KEY,          -- tasodif(8).hex()
    sert_id            TEXT    NOT NULL,
    summa              INTEGER NOT NULL,
    kupyura_soni       INTEGER NOT NULL,          -- len(nominallarga_bol(summa))
    bajarilgan_kupyura INTEGER NOT NULL DEFAULT 0,
    bajarilgan_summa   INTEGER NOT NULL DEFAULT 0,
    partiya_hajmi      INTEGER NOT NULL,
    zaxira_qulfi       TEXT    NOT NULL,
    cheklov            TEXT    NOT NULL,          -- kanonik JSON yoki ""
    surat              TEXT    NOT NULL,          -- sur'at sozlamasi (JSON)
    holat              TEXT    NOT NULL,          -- 'faol' | 'pauza' | 'tugadi' | 'bekor'
    yaratilgan_ms      INTEGER NOT NULL,
    tugagan_ms         INTEGER
);

CREATE TABLE partiyalar (
    partiya_id      TEXT PRIMARY KEY,
    buyurtma_id     TEXT REFERENCES buyurtmalar(buyurtma_id),   -- NULL ham bo'lishi mumkin
    sert_id         TEXT    NOT NULL,
    ildiz           TEXT    NOT NULL,
    soni            INTEGER NOT NULL,
    jami            INTEGER NOT NULL,
    birinchi_seq    INTEGER NOT NULL,
    oxirgi_seq      INTEGER NOT NULL,
    zaxira_qulfi    TEXT    NOT NULL,
    cheklov         TEXT    NOT NULL,
    zarb_ms         INTEGER NOT NULL,
    davomiylik_ms   REAL    NOT NULL DEFAULT 0,
    fayl            TEXT    NOT NULL,
    topshirilgan_ms INTEGER,
    topshirish_xatosi TEXT                          -- oxirgi urinish xatosi (bo'lsa)
);
```

### 15.4 Bitta partiyaning yopilish tartibi (MUST)

```
1. zarb (sur'at bilan)         ← uzilsa: hech narsa yozilmagan, faqat vaqt yo'qoldi
2. imzo
3. o'z tekshiruvi (§12)        ← xato → buyurtma 'pauza' + xabar; fayl yozilmaydi
4. .aqbatch.yarim → rename     ← atomik
5. BITTA SQLite tranzaksiyasi:
     INSERT partiyalar(...)
     UPDATE buyurtmalar SET bajarilgan_kupyura += soni, bajarilgan_summa += jami
5 muvaffaqiyatsiz → faylni o'chir (jurnalda yo'q partiya diskda qolmasin)
```

### 15.5 Ishga tushishda tiklash (MUST)

1. `*.aqbatch.yarim` fayllari o'chiriladi.
2. Jurnalda yo'q `.aqbatch` fayl (4-qadamdan keyin, 5-qadamdan oldin uzilish)
   tekshiruvchidan o'tkaziladi. U toza bo'lsa, `first_seq == keyingi_seq` va
   sertifikat mos bo'lsa, jurnalga **qabul qilinadi** (qaysi buyurtmaga
   tegishliligini summa va seq orqali aniqlang; aniqlanmasa `buyurtma_id = NULL`).
   Aks holda `karantin/` papkasiga ko'chiriladi va operatorga ko'rsatiladi.
   Hech qachon jim o'chirilmaydi.
3. `faol` holatdagi buyurtma operatorga «davom ettirish» taklifi bilan ko'rsatiladi.
   Avtomatik davom etmaydi.

### 15.6 Tartib raqami, limit va yagona yozuvchi

- `keyingi_seq = MAX(oxirgi_seq) + 1` (bo'sh jurnalda 1). Yangi partiyaning
  `birinchi_seq` i aynan shu. Jurnalga yozishda qayta tekshiriladi.
- **Yagona yozuvchi:** profil papkasida qulf fayli (`zarbxona.lock`, OS darajasida
  eksklyuziv qulf). Ikkinchi nusxa zarb qila olmaydi. Aks holda ikki jarayon bir xil
  seq ni olishi mumkin.
- Buyurtma yaratilganda: `summa ≤ qolgan_limit − boshqa faol buyurtmalarning
  qolgan summasi`. Har partiya oldidan limit va sertifikat muddati **qayta**
  tekshiriladi. Sertifikat o'rtada muddati o'tsa, buyurtma `pauza` ga o'tadi.

### 15.7 Avto-topshirish (ixtiyoriy)

- Yoqilgan bo'lsa, fon ishchisi `topshirilgan_ms IS NULL` partiyalarni **seq
  tartibida** bittadan onlayn topshiradi (§13).
- Muvaffaqiyat: `topshirilgan_ms` yoziladi. «Allaqachon qabul qilingan» ham muvaffaqiyat.
- Tarmoq xatosi: eksponensial kutish (5 s → 10 → 20 … ≤ 5 daqiqa), xato matni
  `topshirish_xatosi` ga yoziladi.
- Bank rad etsa (`bank_error`): o'sha partiya to'xtaydi, operatorga ko'rsatiladi,
  keyingilari **yuborilmaydi**. Chunki seq ketma-ketligi buziladi.
- Zarb va topshirish parallel ishlaydi: zarb keyingi partiyani yasaydi, topshiruvchi
  oldingisini yuboradi.
- Fayl orqali topshirish (`.aqbatch` ni qo'lda berish) ham qoladi. «Topshirildi deb
  belgilash» tugmasi bor.

---

## 16. Ilova

### 16.1 Profil papkasi

```
<papka>/kalit.json            zarbxona kaliti (§9)
<papka>/sertifikat.aqcert     vakolat (§8)
<papka>/jurnal.db             jurnal (§15.3)
<papka>/partiyalar/*.aqbatch  partiyalar (§10)
<papka>/karantin/             tiklashda shubhali topilgan fayllar
<papka>/zarbxona.lock         yagona yozuvchi qulfi
```

Default papka: dastur yonidagi `data/`, `--papka` bilan o'zgartiriladi.

### 16.2 Sahifalar (chap menyu)

1. **Boshqaruv paneli** — sertifikat holati, limit, chiqarilgan, qolgan,
   topshirilmagan; faol buyurtma; oxirgi partiyalar.
2. **Zarb** — vakolat kartasi; buyurtma (summa, zaxira qulfi — oxirgi
   ishlatilganlar ro'yxati bilan, cheklov toifalari va muddati, partiya hajmi);
   **Konveyer sur'ati** kartasi (§14.2 + taxminiy vaqt); ZARB / PAUZA / DAVOM /
   TO'XTATISH; **Konveyer** kartasi.
3. **Buyurtmalar** — ro'yxat, holat, progress, davom ettirish/bekor qilish.
4. **Partiyalar** — jadval; fayl orqali eksport; onlayn topshirish (broker, port);
   avto-topshirish yoqish; bitta kupyura Merkle isbotini JSON ga eksport qilish.
5. **Tekshiruv** — faylni yoki butun jurnalni tekshirish; buzib ko'rish demosi.
6. **Kalit va sertifikat** — kalit izi, sertifikatni import qilish, ochiq kalitni
   eksport qilish (bankka berish uchun).
7. **Qanday ishlaydi** — oddiy tilda tushuntirish (o'zbekcha).

Birinchi ochilish: kalit yo'q bo'lsa — yaratish (parol ikki marta); bor bo'lsa —
kalit izi va parol so'rovi.

### 16.3 Konveyer kartasi (jonli monitor)

- Progress: joriy partiya va butun buyurtma bo'yicha (ikki chiziq).
- Holat satri: `bajarildi / jami · haqiqiy tezlik · haqiqiy CPU ulushi · qolgan ~vaqt`.
  Tezlik 1 dan kichik bo'lsa, «~har 6 soniyada 1 kupyura» deb yoziladi. «0 kupyura/s» emas.
- Monitor oqimi (monospace, qora fon, yashil matn, ≤ 600 satr, eskilari tushib ketadi):
  ```
  [10:37:33] #46       5000 so'm   c97bec3e3d28eba7cd51f37c…  muhr 72 B  ✓
  [10:37:35] — sovutish rejimi (2.0 soniya) —
  [10:37:40] partiya yopildi · Merkle ildizi e7750053d871… · imzo qo'yildi · 8 soniya
  [10:37:54] TO'XTATILDI — partiya yozilmadi
  ```
- Ishchi satrlarni to'plab yuboradi: ≥ 0,15 s oraliqda, bir signalda ≤ 40 satr.
  Tez rejimda «… (N satr o'tkazib yuborildi)». Progress signali ≤ 5/s.

### 16.4 Dizayn

Zamonaviy dark tema, klassik OS ko'rinishidagi widgetlar emas. v2 ranglari:

| Token | Rang | | Token | Rang |
|---|---|---|---|---|
| fon | `#0F1115` | | aksent | `#D98A5B` |
| panel | `#171A21` | | aksent-to'q | `#43281A` |
| panel-alt | `#1E222B` | | ok | `#4ADE80` |
| chegara | `#252A36` | | ogohlantirish | `#FBBF24` |
| matn | `#E6E8EE` | | xavf | `#F87171` |
| xira matn | `#98A0B3` | | monospace | Consolas, Cascadia Mono |

- O'chirilgan (disabled) maydon **ko'rinishidan ham** o'chiq bo'lsin (QSS `:disabled`).
- Shrift `QFont.setFamilies()` bilan beriladi, QSS orqali emas.
- Kontent siqilmasin: sahifalar `QScrollArea` ichida bo'lsin.
- Loyihaga xos ikonka (zarb/tanga mavzusi). ICO da bir necha o'lcham bo'lsin.

### 16.5 Qt qoidalari (v2 da topilgan tuzoqlar)

- Fon ishi `QThread` da. Oqim o'z SQLite ulanishini **o'zi ochadi**: ulanish
  oqimlar orasida yurmaydi.
- Signal lambda'ga ulanmaydi. Oynada `@Slot` metodlari bo'ladi.
- `closeEvent`: avval taymer va oqimlarni to'xtatib kuting, **keyin** bazani yoping.
  Aks holda «Cannot operate on a closed database».
- Tugma bosilganda hech narsa qilmasa — bu xato. Har amal javob beradi (holat
  satri yoki dialog). Har boshqaruv bosib sinaladi.

### 16.6 Ishga tushirish

- `python run.py`, `python -m app.main`, `python app/main.py` uchalasi ham
  ishlaydi (test bilan qulflanadi). `--papka`, `--selftest`, `--version`.
- `--selftest`: Qt'siz, vaqtinchalik papkada kalit → o'z-o'zi imzolagan sertifikat
  → kichik buyurtma → tekshiruv. Natija konsolga **va** faylga yoziladi.
- `run.bat` / `run.sh`: kerakli paketlar o'rnatilgan Python'ni o'zi topadi.
  Bir nechta Python bo'lsa `py.exe` eng yangisini tanlaydi, bunga ishonmang.
  `aetherq_core` bor muhit topilsa, o'sha afzal (onlayn topshirish uchun).

### 16.7 Bog'liqliklar

```
PySide6 >= 6.6
cryptography >= 47        # ML-DSA-65, ChaCha20-Poly1305
paho-mqtt >= 2.0
pytest >= 8               # dev
aetherq_core              # IXTIYORIY, faqat onlayn topshirish uchun (§13.3); PyPI da yo'q
```

---

## 17. Arxitektura

```
zarbxona_v3/
  core/                  Qt'siz; hamma mantiq shu yerda va shu yerda sinaladi
    ibtido.py            §2: sha3, aq_kmac256, hkdf, aead, ML-DSA, lp, tagged_hash, iz
    konstanta.py         §3
    kupyura.py           §4
    merkle.py            §5
    partiya.py           §6 + §10 (fayl)
    cheklov.py           §7
    sertifikat.py        §8
    ombor.py             §9
    tekshiruv.py         §12
    surat.py             §14 (Surat, Ritm)
    buyurtma.py          §15 (buyurtma, tiklash, yagona yozuvchi)
    jurnal.py            §15.3
    protokol.py          §13.4–13.6 (xabarlar, mavzular, wire)
    kanal.py             §13.2 (MQTT + testlar uchun xotira kanali)
    sessiya.py           §13.3 (adapter: AetherQFabrika, SoxtaFabrika)
    topshirish.py        §13.5 + §15.7
  app/
    main.py  theme.py  ishchilar.py
    sahifalar/           har sahifa alohida fayl (≤ ~300 qator)
  tests/
  tools/                 broker_smoke.py (haqiqiy broker), kat_tekshir.py
  run.py  run.bat  run.sh  requirements.txt  README.md
```

---

## 18. Testlar va qabul mezonlari

### 18.1 Bulutda (sizning muhitingizda) — MUST

| # | Test |
|---|---|
| T1 | **KAT:** `kat/zarbxona_kat_v1.json` dagi hamma qiymat v3 yadrosi bilan qayta hisoblanadi: ibtidolar, ML-DSA (urug' → ochiq kalit; KAT imzosi tasdiqlanadi), kalit ombori, cheklov, sertifikat xabari va imzosi, 4 ta partiya (ildiz, imzo xabari, har kupyura: id, nazorat, konvert, sarlavha, barg, yadro, muhr, isbot), bank_id, mint_auth, wire |
| T2 | Standart KMAC256 KAT bilan **mos kelmasligi** qulflangan |
| T3 | O'z-o'zi imzolagan sertifikat bilan to'liq sikl: buyurtma → partiyalar → fayl → o'qish → tekshiruv TOZA |
| T4 | Buzish: nominal, egasi, seq, imzo bayti, isbot, cheklov, jurnal summasi, fayl o'chirilgan — har biri **aniq qoida** bilan topiladi. Buzish qiymati eskisidan farq qiladi |
| T5 | Ritm (soxta soat): tezlik; byudjet (ish ulushi ≈ b); ikki chegaradan kattasi; qisqa uyqu yig'iladi; sovutish; **sovutishdan keyin portlash yo'q** (har oraliq = 1/tezlik [+ X]); uzun tanaffus bo'laklab bekor qilinadi; pauza portlash bermaydi |
| T6 | Sur'at baytlarni o'zgartirmaydi (sekin == tez) |
| T7 | Haqiqiy vaqt: 20 kupyura 40/s da ≥ 0,4 s |
| T8 | Buyurtma uzilishi: 3-partiya o'rtasida to'xtatish → qayta ochish → davom → yakunda seq uzluksiz, kesishmaydi, jami = summa, limit oshmaydi |
| T9 | Tiklash: `.yarim` o'chiriladi; jurnalsiz toza fayl qabul qilinadi; buzilgani karantinga tushadi |
| T10 | Yagona yozuvchi: ikkinchi `Zarbxona` zarb qila olmaydi |
| T11 | Protokol `SoxtaFabrika` + soxta bank bilan (§11 qoidalarini xotirada takrorlaydigan): to'liq halqa, bo'laklar, commit; bekor qilishda abort; takroriy topshirish idempotent; noto'g'ri `mint_auth` rad etiladi; `id` mos kelmasligi xato |
| T12 | Wire: soxta, dublikat, eski hisoblagichli, qisqa paket tashlanadi, sessiya tirik |
| T13 | Avto-topshirish: tarmoq xatosida qayta urinadi; bank rad etsa keyingilarini yubormaydi |
| T14 | Kirish nuqtalari uchalasi va `--selftest` (subprocess bilan) |
| T15 | GUI tutun testi `QT_QPA_PLATFORM=offscreen`: oyna ochiladi, har sahifaga o'tiladi, har tugma bosiladi va javob beradi. ⚠ offscreen'da shrift bazasi bo'sh (kvadratchalar chiqadi): ko'rinish sifati faqat haqiqiy ekranda baholanadi |

### 18.2 Foydalanuvchi mashinasida (AETHER-Q muhiti bilan) — qabul

Bularni bulutda bajarib bo'lmaydi. README'da aniq buyruqlar bilan yozing:

| # | Sinov |
|---|---|
| A1 | Rust `aetherq_mint` bilan bayt-ma-bayt solishtirish (v2 dagi `test_moslik.py` kabi, AETHER-Q topilmasa `skip`) |
| A2 | Haqiqiy `aqbank` partiyani **fayl orqali** qabul qiladi, audit OK, takror rad etiladi |
| A3 | `AetherQFabrika` bilan loopback bank serveri: to'liq onlayn halqa |
| A4 | **Haqiqiy broker** (`broker.hivemq.com`) ustida onlayn topshirish: `tools/broker_smoke.py`. ⚠ Loopback test brokerni sinamaydi |
| A5 | Sekin rejimda uzoq buyurtma (masalan 30 daqiqa): CPU ulushi o'lchanadi, o'rtada dastur yopiladi, qayta ochilib davom ettiriladi |
| A6 | Har sahifa va har tugma skrinshot bilan ko'z bilan tekshiriladi |

---

## 19. Tuzoqlar ro'yxati (hammasi amalda uchragan)

1. **AQ-KMAC256 standart emas** (§2.2). Standart kutubxona jim noto'g'ri natija beradi.
2. **Ikki xil prefiks:** sarlavha va imzo xabari — LE u64; sertifikat, cheklov,
   mint_auth — BE u32 (§2.6).
3. **Summa imzo xabarida u128** (§6.2).
4. **Toq Merkle tugun nusxalanmaydi**, o'zgarishsiz ko'tariladi (§5).
5. **Barg ≠ sarlavha xeshi:** bargda `0x00` prefiks bor. AAD uchun prefikssiz xesh olinadi (§4).
6. **`note_id` indeksdan**, seq dan emas (§4.2).
7. **Bitta partiyaga bitta `zarb_ms`** (§6.1), hamma kupyuraga bir xil.
8. **Merkle isbotlari O(n²)** — daraxt bir marta quriladi (§5).
9. **Sovutishdan keyin portlash** — tanaffus nishondan chegiriladi (§14.3).
10. **Buzish demosi hech narsani buzmasligi** — qiymat eskisidan farq qilsin (§12).
11. **Obunadan oldin yuborish** — birinchi javob yo'qoladi (§13.2).
12. **QoS1 dublikati sessiyani o'ldiradi** — wire tashlaydi (§13.6).
13. **Yopilgan bazaga yozish** — `closeEvent` tartibi (§16.5).
14. **Progress signal toshqini** oynani qotiradi — signal cheklanadi (§16.3).
15. **Windows konsoli** UTF-8 bo'lmagan kodlashda yozadi: fayllarni doim
    `encoding="utf-8"` bilan yozing, stdout'ga ishonmang.
16. **Imzo tasodifiy** — testda imzo baytlarini solishtirmang (§2.5).

## 20. Qilma

- Kriptografik algoritm yozma (§2.2 dagi tuzilma bundan mustasno), AETHER-Q sessiyasini qayta yozma (§13.3).
- Partiya kaliti yoki master'ni diskka, logga yoki monitorga chiqarma.
- Sertifikatsiz, zaxira qulfisiz yoki limitdan ortiq zarb qilma.
- Bank kalitini sertifikatdan boshqa joydan olma, pinlashni o'chirma.
- «Tekshirilmadi» ni «toza» deb ko'rsatma. Taxminiy raqamni o'lchangan deb yozma.
- Loopback testni «broker ishlaydi» degan isbot deb hisoblama.
- Hujjat va interfeys matni o'zbek tilida bo'lsin.
