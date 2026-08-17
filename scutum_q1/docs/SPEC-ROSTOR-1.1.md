# ROSTOR-1 v1.1 — O'zbekistondagi kiberfiribgarlikka qarshi ishonch va tasdiqlash protokoli

**Holati:** loyiha spetsifikatsiyasi, tashqi kriptografik ko'rikdan keyingi
qayta ishlangan versiya (v1.1-draft)
**Oldingi versiya:** `docs/SPEC-ROSTOR-1.0-pre-review.md` — konseptual
arxitektura darajasida, ishlab chiqarishga tayyor **emas** deb baholangan
**Meros qatlam:** SCUTUM-Q1 v1.1 transport qatlami — quyida §6-§7 da endi
**yanada qattiqroq** bog'langan (§9 IC/IDC modeli tuzatilgandan keyin)
**Normativ so'zlar:** `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, `MAY`

> Bu hujjat mustaqil kriptografik ko'rik natijasida qayta ko'rib chiqildi.
> Har bir topilma **tekshirildi** (aksarият tasdiqlandi, ba'zilari
> aniqlashtirildi/qisman rad etildi — pastda §0.2 da ko'rsatilgan), so'ng
> tuzatildi. Bu — bir martalik "spec yoz" emas, balki **audit → tuzat →
> qayta audit** siklining ikkinchi bosqichi, xuddi SCUTUM-Q1 v1.0 → v1.1
> o'tishidagi kabi.

---

## 0. v1.0 dan v1.1 ga o'zgarishlar

### 0.1. SCUTUM-Q1 transporti haqida — mustaqil tekshiruv natijasi

Tashqi ko'rik "ROSTOR zaif SCUTUM transportini o'zgarishsiz meros qiladi,
oldingi audit fingerprint bypass, pre-auth ratchet mutation, buzilgan
revocation va session collision ko'rsatgan edi" deb da'vo qildi. Bu da'vo
**qisman tekshirildi, qisman rad etildi**:

| Da'vo qilingan zaiflik | Tekshiruv natijasi |
|---|---|
| Fingerprint bypass | ❌ **Rad etildi.** `Y-7` hujumi HARDENED rejimda ijro etildi — SAFE. Fingerprint faqat identity kalitlariga bog'langan, DC muddati o'zgarishi uni o'zgartirmaydi (`selftest.py`, `sim/attacks.py::_atk_fingerprint_churn`) |
| Pre-auth ratchet mutation | ❌ **Rad etildi.** `K-4` (ratchet sarlavhasi AAD ichida) HARDENED'da SAFE — server `pn`/`n`/`dh` ni o'zgartirsa AEAD tegi buziladi |
| Buzilgan revocation | ❌ **Rad etildi.** `Y-8` (monoton `revoke_epoch`, rollback himoyasi) HARDENED'da SAFE |
| **Session collision** | ✅ **TASDIQLANDI — yangi, oldin topilmagan zaiflik.** `session_id` yuboruvchi tomonidan erkin tanlanadi va serverga ochiq ko'rinadi (AAD, shifrlanmaydi); `accept_session` uni tekshirmasdan qabul qilardi. Amaliy isbot: Mallory Alisaning session_id'sini bilib, o'z INIT'ini AYNI shu ID bilan Boburga yuborsa, Alisaning sessiyasi **jimgina** Mallory'nikiga almashtiriladi (Bob buni sezmaydi, Alisa keyingi xabarini yubora olmay qoladi). **Tuzatildi:** `session.py::accept_session` endi `session_id` allaqachon mavjud bo'lsa, `ReplayError` bilan rad etadi (K-6 deb kod-nomlangan, chunki original spec'da bu holat umuman ko'rilmagan). Hujum lab (`session_collision`) va selftest bilan qulflandi, 38/38 test o'tadi. |
| PQ fallback xatolari | ⚠️ **Aniq misol berilmagan, alohida tekshirilmadi.** Mavjud `_atk_*` to'plamida bunday ssenariy yo'q edi; agar ko'rikchida aniq reproduksiya bo'lsa, alohida taqdim etilishi so'raladi — hozircha aniqlanmagan da'vo sifatida ochiq qoldirilmoqda (§20). |

**Xulosa:** transportni "qayta ochish" (butun handshake/ratchet qayta
loyihalash) **kerak emas edi** — u to'g'ri ishlayotgan edi. Lekin
transport atrofidagi **sessiya boshqaruvi** (kim qaysi session_id'ni
egallashi mumkinligi) haqiqatan tekshirilmagan bo'shliq edi va endi
yopildi. Bu — "meros qilib olish xavfli" degan umumiy da'voni emas,
balki **aniq, tekshiriladigan bitta bo'shliqni** tasdiqlaydi. ROSTOR-1
qurilishi transport ustida davom etadi.

### 0.2. ROSTOR-1 spetsifikatsiyasidagi 11 topilma

| # | Topilma | Jiddiylik | Verdikt | Yechim |
|---|---|---|---|---|
| R2 | "Tekshiruv" qo'ng'iroq qilayotgan TOMONNI emas, institutsiya MAVJUDLIGINI tasdiqlaydi | KRITIK | ✅ To'g'ri, aniq zaiflik | §11.3 — `CALL_CONTEXT` push-first modeli + rasmiy raqamlar reestri |
| R3 | Jurnal "yo'qlik"ni isbotlamaydi (inclusion ≠ completeness) | KRITIK | ✅ To'g'ri, fundamental kamchilik | §8.3 — sparse Merkle (verifiable map) + non-inclusion proof + freshness + lokal checkpoint |
| R4 | Gossip faqat `SHOULD`, markazlashmagan emas | YUQORI | ✅ To'g'ri | §8.6 — submission receipt, MMD, witness-cosign `MUST` |
| R5 | Registrator konsorsiumi uchun genesis/epoch/rotatsiya yo'q | YUQORI | ✅ To'g'ri | §4.1 — genesis anchor, `RegistrarRosterUpdate`, domen ajratilgan `RegistrarApproval` |
| R6 | IC modeli SCUTUM handshake bilan mos emas (SPK/OPK yo'q) | YUQORI | ✅ To'g'ri, aniq arxitektura xatosi | §9 — IC (ildiz) / IDC (SCUTUM DC, o'zgarishsiz) ikki qatlamga bo'lindi |
| R7 | `TxnConfirmResponse` to'liq so'rovga bog'lanmagan; WYSIWYS da'vosi haddan tashqari kuchli | YUQORI | ✅ To'g'ri (ikkalasi ham) | §12.2 — `request_hash` bog'lanishi; §12.3 — da'vo aniq chegaralandi |
| R8 | Account/device ishonch modeli yo'q | YUQORI | ✅ To'g'ri | §13 — `AccountAuthState`, `policy_epoch`, atomik bekor qilish |
| R9 | `PaymentIntent` imzosiz; `memo` fishing yo'li | YUQORI | ✅ To'g'ri | §14 — `issuer_sig`, `payee_token` ta'rifi, `memo` cheklovlari |
| R10 | `✓` belgisi vizual taqlid qilinishi mumkin | YUQORI | ✅ To'g'ri, **to'liq yechim yo'q** | §10.4 — halol chegara + Phase 3 asoslash |
| R11 | `FraudReport`/`ReporterProof` normativ qiymatlarsiz | O'RTA/YUQORI | ✅ To'g'ri | §15.2 — aniq konstantalar |
| R12 | APK modeli Android Signature Scheme bilan bog'lanmagan | O'RTA | ✅ To'g'ri | §16 — `ApkManifestAttestation` ko'prigi |

**Barcha 11 topilma qabul qilindi va tuzatildi.** Rad etilgan yagona
da'vo — §0.1 dagi uchta SCUTUM-Q1 zaifligi (fingerprint/ratchet/revocation)
edi, va ular tekshiruv bilan, hujum lab dalili bilan rad etildi, taxmin
bilan emas.

---

*(§1–§7 quyida — asosiy tuzilma v1.0 bilan bir xil: tahdid modeli T1-T6,
dizayn tamoyillari, ishonch rollari, kriptografik profil, envelope
kengaytmasi, identifikatsiya. Ular qisqartirilgan holda takrorlanadi va
faqat o'zgargan joylar to'liq yozilgan — to'liq matn uchun
`SPEC-ROSTOR-1.0-pre-review.md` ga qarang, unda §1-§7 o'zgarishsiz qoladi.)*

## 1-5. Tahdid modeli, dizayn tamoyillari, ishonch rollari, kriptografik profil, envelope — **o'zgarishsiz**

v1.0 §1-§7 to'liq kuchda qoladi: 6 ta tahdid vektori (T1-T6), 7 ta dizayn
tamoyili (P1-P7), rol jadvali, `SCUTUM-Q1` primitivlari, yangi Envelope
turlari. Faqat §4.1 (Registrator konsorsiumi) va §7 (identifikatsiya)
quyida kengaytiriladi.

---

## 4.1. Registrator konsorsiumi — genesis, epoch, rotatsiya (R5 tuzatishi)

v1.0 §4.1 "kim birinchi bo'lib ishonadi" savolini ochiq qoldirgan edi —
faqat "k-of-n imzo kerak" deyilgan, lekin **kimning** kaliti dastlab
ro'yxatga kiritilishi, uni kim o'zgartira olishi ta'riflanmagan edi.

### Genesis trust anchor

```text
GenesisAnchor = {
  v: 1,
  roster_epoch: 0,
  registrars: [ { registrar_id: bytes[16], ed25519_pk, mldsa65_pk,
                  display_name }, ... ],   // dastlabki, tashqi kanalda
                                            // tarqatiladigan tarkib
  published_at: uint64
}
```

`GenesisAnchor` **kod ichida qattiq yozilgan** (ROSTOR mijoz ilovasiga
build vaqtida kiritiladi, xuddi ildiz CA to'plamlari kabi) va rasmiy
gazeta/CERT.uz e'loni orqali tashqi kanalda tasdiqlanadi `MUST`. Bu —
kriptografiya bilan hal qilinmaydigan, tashkiliy/huquqiy qaror (v1.0
§4.1 da ham shunday tan olingan edi); v1.1 faqat uning **texnik
skeletini** aniqlaydi.

### Roster epoch va o'z-o'zini yangilash

```text
RegistrarRosterUpdate = {
  v: 1,
  roster_epoch: uint64,        // qat'iy o'suvchi
  added:   [ RegistrarEntry ],
  removed: [ bytes[16] ],      // registrar_id lar
  effective_at: uint64,
  approvals: [ { registrar_id: bytes[16], sig: HybridSignature } ]
              // kamida k ta, OLDINGI (roster_epoch - 1) tarkibidan
}
```

Roster o'zgarishi **o'z-o'zini kengaytiruvchi** zanjir: har yangi tarkib
oldingi tarkibning k-of-n roziligi bilan tasdiqlanadi, genesis'dan
boshlab. Mijoz eng so'nggi ko'rilgan `roster_epoch`'ni saqlaydi va undan
**kichik** epoch'li rosterni rad etadi `MUST` (SCUTUM-Q1 §8 `revoke_epoch`
naqshi bilan bir xil — yangi tushuncha emas, mavjud naqshning qayta
qo'llanilishi).

### Domen ajratilgan `RegistrarApproval` (R5 ning ikkinchi qismi)

v1.0'dagi `RegistrarApproval` faqat `ic_hash`ga o'xshash qiymatni
imzolardi — kontekst, log ID yoki amal turi yo'q edi (bitta imzoni
boshqa kontekstda qayta ishlatish xavfi). Tuzatilgan:

```text
signed = "ROSTOR-1/registrar-approval" ||
         canonical({
           log_id:       bytes[16],   // qaysi shaffoflik jurnaliga tegishli
           action:       tstr,        // "issue_ic" | "issue_pc" | "revoke"
                                       // | "roster_update"
           roster_epoch: uint64,
           target_hash:  bytes[32]    // SHA3-256(canonical(IC/PC/roster))
         })
```

Har bir `registrar_id -> sig` juftligi shu to'liq strukturani imzolaydi
— endi qaysi log, qaysi amal, qaysi epoch ekanligi imzoning o'zida.

---

## 6-7. Transport bog'lanishi va identifikatsiya — §9 ga havola bilan kuchaytirildi

v1.0 §6 dagi arxitektura qarori ("suite o'zgarmaydi, faqat yangi `type`
qiymatlari qo'shiladi") **kuchda qoladi va endi yanada mustahkam** —
sabab: §9 dagi IC/IDC ajratilishi natijasida institutsional xabarlar
ENDI ANIQ SCUTUM-Q1 sessiyasi ustida yuriladi, "qandaydir alohida
mexanizm" emas (bu aynan R6 topilmasining tuzatilishi, pastda).

---

## 8. Shaffoflik jurnali — verifiable map va isbotlangan yo'qlik (R3, R4 tuzatishi)

### 8.1. Nega v1.0 dagi dizayn yetarli emas edi

v1.0 append-only Merkle jurnal + inclusion proof taklif qilgan edi.
Bu **borliqni** isbotlaydi ("bu yozuv jurnalda bor"), lekin
**yo'qlikni** isbotlamaydi. Amaliy oqibat: yovuz (yoki buzilgan) mirror
operatori:

- bekor qilish (`revocation`) yozuvini muayyan so'rovchidan **yashirishi**;
- "bu xesh zararli emas" deb, aslida zararli-xeshlar ro'yxatida bo'lgan
  narsani **noto'g'ri javob berishi**;
- prefiks-chelak so'roviga (§8.5, v1.0) **to'liq bo'lmagan** ro'yxat
  qaytarishi

mumkin, va mijoz buni **hech qanday tarzda aniqlay olmaydi** — chunki
`derive_badge` (§10.1) va `contains()` kabi funksiyalar oddiy
`lookup`/`bool` natijasiga ishonadi, isbot talab qilmaydi. Bu — jiddiy,
fundamental kamchilik edi.

### 8.2. Ikki tuzilma: tarix uchun jurnal, holat uchun xarita

v1.0'dagi append-only Merkle jurnal (§8.2, o'zgarishsiz) **tarixiy audit
izi** sifatida saqlanadi — kim, qachon, nima yubordi, rebuttal zanjiri.
Bunga qo'shimcha, **yangi** tuzilma kiritiladi:

```text
RegistrySMT — sparse Merkle tree (verifiable map)

  kalit maydoni:  256 bit (SHA3-256 chiqishi bilan bir xil o'lcham)
  chuqurlik:      256 daraja
  bo'sh barg:     EMPTY = SHA3-256("ROSTOR-1/smt-empty")
  band barg:      leaf(key, value) = SHA3-256(0x03 || key || value)
  ichki tugun:    node(L, R) = SHA3-256(0x04 || L || R)
```

Har bir `institution_id`, `apk_hash`, `payment_gateway_domain_hash` va
h.k. uchun **aniq, oldindan belgilangan pozitsiya** bor (kalit = o'sha
qiymatning o'zi yoki uning xeshi). Bu shuni anglatadiki:

- **Borlik isboti (inclusion):** standart Merkle yo'l, `leaf(key, value)`
  dan ildizgacha.
- **Yo'qlik isboti (non-inclusion):** o'sha `key` pozitsiyasida barg
  `EMPTY` ekanligini ko'rsatuvchi, ildizgacha bo'lgan **xuddi shunday**
  Merkle yo'l. Endi "bu institutsiya ro'yxatda yo'q" degan javob ham
  **isbotlanadi**, "ishoning" emas.

`RegistrySMT` snapshoti har epoch'da (masalan har soatda) yangilanadi,
uning ildizi navbatdagi STH ga kiritiladi (§8.4).

### 8.3. STH yangilanishi: `SMT_root` bilan

```text
STH (Signed Tree Head) = {
  tree_size:   uint64,       // append-only jurnal o'lchami
  root_hash:   bytes[32],    // append-only jurnal ildizi
  smt_root:    bytes[32],    // RegistrySMT joriy epoch ildizi   <- YANGI
  smt_epoch:   uint64,                                          <- YANGI
  timestamp:   uint64,
  operator_id: bytes[16],
  operator_sig: HybridSignature
}
```

### 8.4. Freshness va lokal monoton checkpoint

Mijoz:

- STH ni `now - STH.timestamp <= MAX_STH_AGE` (tavsiya: 1 soat) bo'lmasa
  **eskirgan** deb rad etishi `MUST`;
- oxirgi ko'rgan `(tree_size, root_hash)` juftligini **lokal saqlashi**
  `MUST` — bu **lokal monoton checkpoint**;
- yangi STH kelganda, uning `tree_size`si eskisidan katta bo'lsa,
  operator **consistency proof** (§8.3, v1.0'dan meros, RFC 6962 §2.1.2)
  taqdim etishi `MUST` — bu eski holatning **faqat kengaytmasi**
  ekanligini isbotlaydi. Consistency proof bo'lmasa yoki mos kelmasa,
  mijoz yangi STH'ni rad etadi va bu hodisani **ko'rinadigan xato**
  sifatida ko'rsatadi (jimgina eskisini ishlatib qolish emas).

### 8.5. Maxfiylik va to'liqlik o'rtasidagi murosaga aniqlik

v1.0 §8.5 prefiks-asosidagi qidiruvni taklif qilgan edi (maxfiylik
uchun), lekin bu **to'liqlik isbotini** beolmaydi — server "sizga mos
keladigan barcha yozuvlar shular" desa, buni tekshirib bo'lmaydi.
`RegistrySMT` esa aksincha — **aniq kalit** so'ralganda to'liq isbot
beradi, lekin bu server **aynan nima so'ralganini biladi** degani (query
maxfiyligi yo'qoladi). Bu — haqiqiy, olib tashlab bo'lmaydigan murosa;
uni bitta "to'g'ri" yechim bilan yashirish noaniqlik yaratardi. Shuning
uchun ROSTOR-1 **uchta aniq rejimni** taqdim etadi:

| Rejim | Maxfiylik | To'liqlik isboti | Qachon ishlatiladi |
|---|---|---|---|
| **To'liq lokal sinxronizatsiya** (asosiy, `SHOULD`) | Mukammal — server so'rov umuman ko'rmaydi | To'liq — mijoz butun SMT'ni yuklab, consistency proof bilan tekshiradi | Fon rejimida, davriy (Safe Browsing lokal ro'yxat naqshi) |
| **Prefiks-qidiruv** (yengil, `MAY`) | Qisman (k-anonimlik) | **Yo'q** — server "to'liq javob" deganiga ishonish kerak | Tarmoq/xotira cheklangan qurilmalarda, tezkor dastlabki tekshiruv |
| **Aniq-kalit SMT so'rovi** (yuqori-garov, `MAY`) | Yo'q — server so'ralgan kalitni biladi | To'liq | Yirik `TXN_CONFIRM`dan OLDIN, foydalanuvchi aniq tasdiq so'raganda — maxfiylikdan ko'ra ishonchlilik ustun bo'lgan holatda |

Bu **ataylab qilingan, izohlangan tanlov** — soxta "hammasi hal qilindi"
da'vosidan ko'ra halolroq. To'liq maxfiy + to'liq isbotlangan so'rov
(masalan Private Information Retrieval orqali) — §20 da ochiq tadqiqot
savoli sifatida qayd etilgan; hozircha vetting qilingan kutubxonalarda
yo'q (P7).

### 8.6. Markazlashmagan chidamlilik: receipt, MMD, witness-cosign (R4 tuzatishi)

v1.0'da gossip faqat `SHOULD` edi — asosiy sequencer yozuvni qabul
qilmasa, hech kim buni bilmasdi. Tuzatilgan:

- **Submission receipt.** Registrator yangi `LogEntry` yuborganda,
  sequencer imzolangan **qabul dalolatnomasi** qaytarishi `MUST`:
  ```text
  SubmissionReceipt = {
    entry_hash: bytes[32],
    max_merge_delay: uint64,   // MMD, tavsiya: 24 soat
    promised_by: uint64,       // submitted_at + MMD
    sequencer_sig: HybridSignature
  }
  ```
  Agar yozuv `promised_by` vaqtigacha jurnalda (inclusion proof bilan)
  paydo bo'lmasa, `SubmissionReceipt`ning o'zi — sequencer noto'g'ri
  ish tutganining **ommaviy, rad etib bo'lmaydigan isboti** (RFC 6962
  SCT naqshi).
- **Witness-cosigning — `SHOULD` emas, `MUST`.** STH kamida `W=2` ta
  **mustaqil** witness tomonidan qo'shimcha imzolanmaguncha, mijozlar
  uni **kanonik** deb hisoblamasligi `MUST` (RFC 9162/"C2SP witness"
  naqshi). Witness — to'liq mirror emas, faqat consistency proof'ni
  tekshirib, STH'ni cosign qiluvchi yengil rol (§4 rol jadvaliga
  qo'shildi).
- **Cross-logging.** Har bir yozuv kamida ikkita mustaqil jurnal
  nusxasiga yuborilishi `SHOULD` (CT'dagi ko'p-log talabi naqshi) —
  qo'shimcha mudofaa qatlami.

---

## 9. Institutsiya identiteti — ikki qatlamli model (R6 tuzatishi)

### 9.1. Muammo aniq: v1.0 IC'si SCUTUM sessiyasini ocha olmasdi

v1.0'dagi `InstitutionCertificate` statik `x25519_pk`/imzo kalitlarini
berardi, lekin SCUTUM-Q1 handshake'i (§5, meros) `SPK`, `OPK` va
**muddatli** `ML-KEM` prekey'larini talab qiladi — bular IC'da yo'q edi.
Natijada "bank ROSTOR xabar sessiyasini qanday ochadi" degan savol
**javobsiz** qolgan edi. Bu — to'g'ri, aniq topilgan arxitektura xatosi.

### 9.2. Yechim: IC (ildiz) + IDC (SCUTUM qurilmasi)

```text
InstitutionCertificate (IC) — faqat IMZOLASH uchun, sessiya ochmaydi
  v, institution_id, category, display_name,
  ed25519_pk, mldsa65_pk,           // <- x25519/ML-KEM OLIB TASHLANDI
  registered_at, expires_at, revoked_at

InstitutionDeviceCertificate (IDC) — SCUTUM-Q1 DeviceKeys/DC bilan
                                       BAYT-BAYT BIR XIL tuzilma
  = SCUTUM-Q1 §3.1 DC   // o'zgarishsiz — DIK, SPK, OPK, ML-KEM hammasi bor

IDCEndorsement = {
  institution_id: bytes[16],
  dc_hash: SHA3-256( canonical(IDC) ),
  issued_at: uint64,
  expires_at: uint64,       // IDC dan qisqaroq, tez-tez yangilanadi
  ic_sig: HybridSignature   // "ROSTOR-1/idc-endorsement" || canonical(...)
                             // bilan IC_sk orqali imzolangan
}
```

**Oqim:** institutsiya bitta uzoq muddatli `IC` ga ega (registrator
konsorsiumi tomonidan tasdiqlangan, §4.1), lekin haqiqiy xabar
almashinuvi uchun bir yoki bir nechta **oddiy SCUTUM-Q1 qurilmasi**
(`IDC`) ishlatadi — masalan "Bank X ilova-backend #1", "Bank X SMS
shlyuzi". Har bir `IDC` odatdagidek `SPK`/`OPK` rotatsiyasiga ega
(SCUTUM-Q1 §8, o'zgarishsiz). `IC` faqat **vaqti-vaqti bilan**, ushbu
`IDC`larni "bu haqiqatan Bank X" deb tasdiqlab turadi (`IDCEndorsement`).

Handshake **aynan SCUTUM-Q1 §5 bo'yicha, o'zgarishsiz** boradi — mijoz
`IDC`ning oddiy `PreKeyBundle`sini oladi, INIT yuboradi. Yagona qo'shimcha
qadam: mijoz `IDCEndorsement`ni tekshiradi (`ic_sig` → §11 badge orqali
`IC` jurnalda ekanligini tasdiqlaydi) — bu SCUTUM mexanikasidan **butunlay
tashqarida**, faqat "bu DC'ga ishonaymi" degan qo'shimcha qatlam.

**Natija:** §17 (kod qayta ishlatish xaritasi) dagi da'vo — "SCUTUM-Q1
DC/handshake o'zgarishsiz meros qilinadi" — endi **haqiqatan aniq va
to'g'ri**, taxmin emas. Bu R6 tuzatishining eng muhim natijasi.

---

## 10. Tasdiqlangan jo'natuvchi belgisi — yangilangan zanjir va halol chegara

### 10.1. Belgi hosil qilish — IC → IDC zanjiri bilan

```text
derive_badge(message, log_snapshot):
    idc = message.sender_idc                     // SCUTUM DC
    if idc is None: return UNVERIFIED

    endorsement = log_snapshot.lookup_endorsement(idc.device_id)
    if endorsement is None: return UNVERIFIED
    if now > endorsement.expires_at: return UNVERIFIED

    ic = log_snapshot.smt_lookup_institution(endorsement.institution_id)
                                                   // §8.2 SMT — ISBOT bilan
    if ic is None or ic.revoked_at and now >= ic.revoked_at:
        return REVOKED

    if NOT HybridVerify(ic.ed25519_pk, ic.mldsa65_pk,
                        endorsement.ic_sig, endorsement.signed_payload):
        return INVALID_SIGNATURE

    if NOT HybridVerify(idc.ed25519_pk, idc.mldsa65_pk,
                        message.sig, message.signed_payload):
        return INVALID_SIGNATURE

    if log_snapshot.smt_lookup_malicious(message.sender_hash):
        return KNOWN_MALICIOUS
    if log_snapshot.fraud_score(ic.institution_id) >= FLAG_THRESHOLD:
        return FLAGGED
    return VERIFIED(ic.display_name, ic.category)
```

Endi ikki bosqichli tekshiruv (`IC` → `IDC`) va **SMT-asoslangan, isbot
bilan** lookup (§8.2) ishlatiladi — v1.0'dagi oddiy `.contains()` emas.

### 10.4. Halol chegara: belgi UI darajasida taqlid qilinishi mumkin (R10)

Bu — eng qiyin, **to'liq yechimi yo'q** muammo, va buni shunday ochiq
tan olish kerak. Kriptografik imzo `✓` belgisining **hosil bo'lishini**
soxtalashtirib bo'lmaydi (§10.1 imzo tekshiruvi haqiqiy), lekin agar
belgi **ROSTOR nazorat qilmaydigan sirtda** (fishing vebsahifasi, soxta
skrinshot, umumiy SMS ilovasi) chizilsa — u yerda **hech qanday
kriptografiya ishlamaydi**, chunki piksel darajasida bir xil ko'rinadigan
matn/belgi chizish har qanday dasturga ochiq. Bu — parol menejerlari va
autentifikator ilovalari duch keladigan klassik "ishonchli e'tibor
yo'li" (trusted attention path) muammosi.

**Halol javob, ikki qism:**

1. **Qoida (`MUST`, foydalanuvchiga o'rgatiladi):** `✓` belgisi **faqat**
   institutsiyaning RASMIY, ROSTOR SDK integratsiya qilingan ilovasi
   ichida ma'no anglatadi. Boshqa har qanday sirtda (veb-sahifa,
   skrinshot, uchinchi tomon ilovasi) ko'ringan xuddi shunday belgi
   **hech narsani tasdiqlamaydi** va e'tiborga olinmasligi kerak.
2. **Uzoq muddatli yechim (Phase 3, §18):** faqat OS darajasidagi,
   oddiy ilova chiza olmaydigan **ishonchli sirt** (masalan tizim
   bildirishnomasi qatlamidagi maxsus indikator, Play Protect
   uslubidagi imzolangan belgi) to'liq yechim beradi. Bu ROSTOR
   spetsifikatsiyasi doirasidan tashqarida — platforma
   ishlab chiqaruvchisi hamkorligini talab qiladi. §18 Phase 3'ning
   ustuvorligi aynan shu muammo bilan asoslanadi.

§16 (chegaralar jadvali) ga mos yozuv qo'shildi.

---

## 11.2-11.3. Tranzaksiya tasdiqlash — to'liq bog'lanish va halol da'vo (R7 tuzatishi)

### To'liq bog'langan javob

v1.0'dagi `TxnConfirmResponse` faqat `txn_id`/`decision`/`amount_minor`/
`recipient_masked` ni imzolardi — `currency`, `purpose`, `institution_id`,
`expires_at` tashqarida qolgan edi, va bog'lanish kanonik obyekt emas,
xom konkatenatsiya edi. Tuzatilgan:

```text
device_sig = HybridSign( DIK,
    "ROSTOR-1/txn-response" ||
    canonical({
      request_hash: SHA3-256( canonical(TxnConfirmRequest
                                        minus institution_sig) ),
      decision:      tstr,
      account_id:    bytes[16],
      device_id:     bytes[16],
      responded_at:  uint64
    })
)
```

`request_hash` **butun so'rovni** (barcha maydonlarni, jumladan
`currency`/`purpose`/`institution_id`/`expires_at`ni) transitiv ravishda
qamrab oladi — endi hech bir maydonni "sig'dan tashqarida qoldirib"
bo'lmaydi.

### WYSIWYS da'vosi — aniqlashtirilgan chegara

v1.0 "vishingni **imkonsiz** qiladi" degan edi. Bu **haddan tashqari
kuchli** da'vo edi. To'g'ri chegara:

> WYSIWYS **faqat** "ekranda ko'rsatilgan narsa bilan imzolanadigan
> narsa **mos kelmasligi**" turidagi hujumni yo'q qiladi (klassik
> display/sign chalkashligi). U foydalanuvchini **to'g'ri ko'rsatilgan**
> firibgar so'rovni ongli ravishda (bosim, qo'rquv, shoshilish ostida)
> tasdiqlashdan **saqlamaydi** — bu hamon ijtimoiy muhandislik g'alabasi
> bo'lishi mumkin, faqat endi "men bilmasdan tasdiqladim" emas, "meni
> ko'rib turib tasdiqlashga majburladilar" shaklida.

Qo'shimcha yumshatuvchi (yangi, `SHOULD`): yuqori-summali yoki
notanish-qabul-qiluvchi operatsiyalar uchun **sovutish davri**
(cooling-off) — masalan 30 soniyalik majburiy kutish + ikkinchi
tasdiqlash bosqichi, ijtimoiy muhandislik bosimini kamaytirish uchun.
Bu ham to'liq yechim emas, faqat qo'shimcha ishqalanish (friction) —
§16 ga mos yozuv qo'shildi.

---

## 13. Account/device avtorizatsiya holat mashinasi (R8 tuzatishi)

v1.0 §13 (Tiklash kvorumi) faqat "yangi qurilma qo'shish" oqimini
tasvirlagan, lekin **kim** ruxsat berilgan qurilmalar ro'yxatini
boshqarishi, qanday siyosat qo'llanilishi, eski qurilmalar qanday bekor
qilinishi ta'riflanmagan edi. To'liq holat mashinasi:

```text
AccountAuthState = {
  account_id:    bytes[16],
  policy_epoch:  uint64,           // qat'iy o'suvchi
  authorized_devices: [
    { device_id: bytes[16], dc_hash: bytes[32],
      added_at: uint64, added_via: tstr }
  ],
  recovery_policy: {
    method: tstr,                  // "existing_device_cosign"
                                    // | "institutional_quorum"
    k: uint32, n: uint32,
    approver_roster_ref: bytes[32]
  }
}
```

### Qurilma qo'shish/olib tashlash — logланган, epoch oshiruvchi amal

Har qanday qurilma ro'yxati o'zgarishi (a) mavjud ishonchli qurilma
ko'rsatuvidan **yoki** (b) tiklash kvorumidan kelib chiqishi `MUST`, va
har ikkala holatda `policy_epoch` **1 ga oshiriladi**, o'zgarish jurnalga
(§8) yoziladi.

### Tiklash so'rovi — to'liq bog'lanish (R8, avvalgi §13 kengaytmasi)

```text
RecoveryRequest = {
  v: 1, new_device_dc: DC, account_id: bytes[16],
  policy_epoch: uint64,      // JORIY (kutilayotgan) epoch — YANGI maydon
  requested_at: uint64,
  expires_at: uint64,        // qisqa TTL, tavsiya: 10 daqiqa   <- YANGI
  method: tstr
}

QuorumApproval = {
  approver_id: bytes[16],
  request_hash: SHA3-256( canonical(RecoveryRequest) ),   // <- YANGI, aniq bog'lanish
  approval_sig: HybridSignature
}
```

- **Replay/eskirish himoyasi:** `expires_at` va `request_hash` bog'lanishi
  eski, boshqa tiklash so'roviga berilgan tasdiqni qayta ishlatishga
  yo'l qo'ymaydi.
- **Rollback himoyasi:** mijoz oxirgi ko'rgan `policy_epoch`'dan kichik
  har qanday `AccountAuthState`ni rad etadi `MUST` (SCUTUM-Q1 `Y-8`
  naqshi — endi account darajasida ham qo'llanildi).
- **Atomik bekor qilish:** "to'liq almashtirish" siyosatida (masalan
  qurilma yo'qolganda) yangi qurilmani qo'shish **va** eski qurilma(lar)ni
  bekor qilish **bitta, bo'linmas** logланган amal sifatida bajarilishi
  `MUST` — eski va yangi qurilma bir vaqtda ishonchli bo'lib turadigan
  oraliq holat bo'lmasligi kerak, agar siyosat buni aniq ruxsat
  bermasa (masalan ko'p-qurilmali akkountlar uchun).

---

## 14. Pul qabul qilish protokoli — autentifikatsiya qo'shildi (R9 tuzatishi)

v1.0 §12'dagi `PaymentIntent`da imzo yoki emituvchi (issuer) yo'q edi —
istalgan kim o'zini "qabul qiluvchi" sifatida ko'rsatishi mumkin edi.
Bundan tashqari, erkin `memo` maydoni fishing havolasi yoki "CVV kiriting"
ko'rsatmasini olib yurishi mumkin edi — kredensial-maydonni taqiqlashning
o'zi yetarli emas.

```text
PaymentIntent = {
  v: 1, intent_id: bytes[16],
  issuer_id:  bytes[16],            // IDC device_id (§9)          <- YANGI
  payee_token: bytes[32],
  amount_minor: uint64 / null,
  memo: tstr,                       // <=140 UTF-8 bayt, cheklangan
  expires_at: uint64,
  issuer_sig: HybridSignature        // canonical(barcha maydonlar)  <- YANGI
}
```

`payee_token` ta'rifi (v1.0'da aniqlanmagan edi):

```text
payee_token = SHA3-256( "ROSTOR-1/payee-token" || payee_idc_ed25519_pk || nonce )
```

Opaque, DIK-bog'langan; `nonce` qayta ishlatilmasa har bir intent uchun
bog'lanmagan ko'rinadi (maxfiylik), yoki takroriy to'lovlar uchun
barqaror token (`token_mode: "stable"`) tanlanishi `MAY` — savdogar
qulayligi bilan bog'lanmaslik o'rtasidagi murosa aniq bayon qilingan.

**`memo` cheklovlari (`MUST`):**

- 140 UTF-8 baytdan oshmaydi;
- klient uni **inert oddiy matn** sifatida ko'rsatadi — hech qanday
  URL avtomatik havolaga aylantirilmaydi, HTML/markdown render
  qilinmaydi;
- URL-ga o'xshash naqsh (`http://`, `.uz`, `.com` va h.k.) topilsa,
  klient qo'shimcha ogohlantirish ko'rsatadi: *"Bu xabar havola o'z
  ichiga oladi — ehtiyot bo'ling."* Bu **to'liq kafolat emas** (matnli
  ijtimoiy muhandislikni to'xtatmaydi), lekin `memo` orqali bosiladigan
  fishing havolasini oldini oladi.

---

## 15. Firibgarlik hisoboti — aniq normativ qiymatlar (R11 tuzatishi)

v1.0 §14'da `ReporterProof` ta'riflanmagan, `MIN_K`/`SCORE_THRESHOLD`
kabi qiymatlar yo'q edi — bu uni implementatsiya va test qilib
bo'lmaydigan qilardi.

### 15.1. `ReporterProof`

```text
ReporterProof = {
  reporter_device_id: bytes[16],       // DIK-bog'langan
  interaction_ref: bytes[16] / null,   // haqiqiy TXN_CONFIRM/session_id
                                        // ga bog'langan bo'lsa
  device_sig: HybridSignature           // "ROSTOR-1/reporter-proof" ||
                                         // canonical({report_id, ...})
}
```

### 15.2. Normativ konstantalar (v1.0'da yo'q edi)

```text
BASE_WEIGHT        = 1
INTERACTION_WEIGHT = 3      // interaction_ref haqiqiy bo'lsa
MIN_K               = 5     // kamida 5 ta ALOHIDA reporter_device_id
SCORE_THRESHOLD     = 15    // masalan: 5 ta interaction-tasdiqlangan
                             // YOKI 15 ta oddiy hisobot
RATE_LIMIT          = 10 hisobot / DIK / 24 soat
DECAY_WINDOW        = 90 kun
```

Bu qiymatlar **boshlang'ich taxmin** sifatida belgilangan, joriylashtirish
davomida real ma'lumot asosida sozlanishi `SHOULD` — lekin hozir aniq,
testlanadigan raqamlar sifatida mavjud (v1.0'dagi kabi mavhum emas).

DIK-asoslangan tezlik cheklash **to'liq Sybil-qarshilik emas** — bu
haqiqat v1.0 §14.3/§20'da allaqachon ochiq tan olingan edi va shunday
qolmoqda; endi faqat aniq, sinovdan o'tkaziladigan chegara bilan.

---

## 16. Dastur/APK kelib chiqishi — Android imzolash bilan texnik ko'prik (R12 tuzatishi)

v1.0 "APK imzosi PC ga mos" deb hal qilmasdan qoldirgan edi — Android
o'zining **native** imzolash sxemasi (APK Signature Scheme v2/v3,
**SHA-256** — SHA3-256 EMAS, X.509 sertifikat formati, `lineage` orqali
kalit rotatsiyasi) bilan ROSTOR gibrid imzolari orasida hech qanday
ko'rsatilgan bog'lanish yo'q edi.

**Muhim tuzatish:** ROSTOR Android'ning o'z imzolash sxemasini
**almashtirmaydi yoki qayta amalga oshirmaydi** — u tashqaridan Android
tomonidan imzolangan aniq APK'ni **vouch qiladi** (tasdiqlaydi):

```text
ApkManifestAttestation = {
  v: 1,
  package_name: tstr,
  version_code: uint64,
  channel: tstr,                    // "official" | "play_store" | "direct"
  apk_sha256: bytes[32],            // Android'ning o'z digest algoritmi —
                                      // SHA-256, ATAYLAB SHA3 emas, chunki
                                      // bu Android tooling bilan mos
                                      // kelishi kerak
  android_signing_cert_sha256: bytes[32],  // APK'ning o'z Android
                                             // signing sertifikati xeshi
  signing_lineage_ref: bytes[32] / null,   // APK Signature Scheme v3
                                             // kalit-rotatsiya zanjiri
  publisher_id: bytes[16],          // PublisherCertificate'ga havola
  issued_at: uint64,
  expires_at: uint64,
  publisher_sig: HybridSignature
}
```

**Tekshiruv oqimi (yangilangan §15.1):** (1) klient standart Android
vositalari orqali qabul qilingan `.apk` ning haqiqiy SHA-256 va Android
signing sertifikat xeshini hisoblaydi; (2) `RegistrySMT`dan (§8.2) shu
juftlikka mos `ApkManifestAttestation` so'raydi (borlik/yo'qlik isboti
bilan); (3) topilsa, `publisher_sig` `PublisherCertificate` zanjiriga
qadar tekshiriladi. Bu endi **texnik aniq va implementatsiya qilinadigan**
— v1.0'dagi kabi "mos keladi" degan noaniq da'vo emas.

---

## 17. SCUTUM-Q1 bilan munosabat — yangilangan xarita

v1.0 §17 jadvali kuchda qoladi, ikkita aniqlashtirish bilan:

- `protocol/identity.py` endi **ikki** yangi tuzilmani oladi: `IC` (yangi,
  yengil, faqat imzo kalitlari) va `IDCEndorsement` (yangi) — `DC`/
  `DeviceKeys`ning o'zi **hech qanday o'zgarishsiz** `IDC` sifatida
  qayta ishlatiladi (§9.2 — bu R6 tuzatishining to'g'ridan-to'g'ri
  natijasi, oldingi jadvaldagi "kengaytiriladi" so'zi endi aniqroq: DC
  o'zgarmaydi, atrofida yangi kichik obyekt qo'shiladi).
- `protocol/session.py`ga K-6 tuzatishi (§0.1) kiritildi — bu ROSTOR
  ishi emas, lekin ROSTOR shu modul ustiga quriladi, shuning uchun
  bu yerda qayd etiladi: session_id endi mavjudlik tekshiruvidan o'tadi.

---

## 18. Joriylashtirish bosqichlari — o'zgarishsiz, R2/R10 bilan bog'liq ustuvorlik izohi

v1.0 §18 (3 bosqich) kuchda qoladi. Qo'shimcha izoh: **Bosqich 1**
endi nafaqat "SDK qo'shish", balki **`CALL_CONTEXT` push-first
modelini** (§11.3, R2 tuzatishi) joriy etishni ham o'z ichiga oladi —
bu eng yuqori USTUVORLIKKA ega, chunki T2/T3 (vishing) real zarar
ro'yxatida eng katta ulush. **Bosqich 3** endi R10 (§10.4) bilan aniq
bog'langan — OS darajasidagi ishonchli sirt shunchaki "yaxshi bo'lardi"
emas, balki UI-taqlid muammosining **yagona** to'liq yechimi.

---

## 19. Majburiy testlar — kengaytirilgan

v1.0 §19 ro'yxatiga qo'shimcha:

9. `RegistrySMT` non-inclusion proof to'g'riligi — soxta "topilmadi"
   javobini aniqlash testi.
10. STH freshness va lokal checkpoint — eskirgan/nomos STH rad etilishi.
11. `SubmissionReceipt`/MMD — vaqtida ko'rinmagan yozuv ommaviy
    isbotlanadigan xato hisoblanishini tasdiqlovchi test.
12. `AccountAuthState.policy_epoch` rollback himoyasi — SCUTUM-Q1 `Y-8`
    testi bilan bir xil naqsh, account darajasida.
13. `ApkManifestAttestation` — Android SHA-256 va ROSTOR SHA3-256
    ikkalasi ham to'g'ri ishlatilishini tekshiruvchi test (algoritm
    chalkashligiga qarshi regressiya).
14. `IDCEndorsement` zanjiri — `IC` bekor qilinganda unga bog'langan
    barcha `IDC`larning belgisi avtomatik `REVOKED`ga o'tishi.

---

## 20. Ochiq masalalar — yangilangan

v1.0 §20 ro'yxati kuchda qoladi (Sybil-qarshilik, konsorsium tarkibi,
threshold-imzo, guruh hisoblari, huquqiy maqom, telekom hamkorligi),
qo'shimcha bilan:

7. **Maxfiy + to'liq isbotlangan so'rov** (Private Information Retrieval
   yoki unga o'xshash) — §8.5 uch-rejimli murosani bitta yechimga
   birlashtira oladigan yagona nomzod, lekin hozircha vetting qilingan
   kutubxonalarda mavjud emas (P7 bilan ziddiyat).
8. **OS darajasidagi ishonchli UI sirt** (§10.4, §18 Phase 3) —
   platforma ishlab chiqaruvchisi hamkorligisiz texnik jihatdan hal
   qilinmaydigan muammo; ROSTOR faqat foydalanuvchi qoidasi bilan
   yumshatadi.
9. **"PQ fallback xatolari"** (tashqi ko'rikda aytilgan, lekin aniq
   reproduksiyasi berilmagan) — agar konkret ssenariy taqdim etilsa,
   alohida topilma sifatida ko'riladi.

---

## 21. Manbalar

v1.0 §21 ro'yxatiga qo'shimcha:

- IETF, [RFC 9162: Certificate Transparency v2](https://www.rfc-editor.org/rfc/rfc9162)
  — witness cosigning va SCT (submission receipt) naqshi
- Google, [Key Transparency / CONIKS](https://github.com/google/keytransparency)
  — sparse Merkle tree / verifiable map naqshi, non-inclusion isboti
- C2SP, [Static CT / Sunlight](https://c2sp.org/static-ct-api) — zamonaviy
  witness-cosigned log arxitekturasi
