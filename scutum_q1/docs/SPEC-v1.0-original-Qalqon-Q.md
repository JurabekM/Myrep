# Qalqon-Q v1 — Q-MSG va Q-FILE umumiy spetsifikatsiyasi

**Holati:** loyiha spetsifikatsiyasi (auditdan oldingi versiya)  
**Maqsadi:** messenjer, fayl almashinuvi va shifrlangan bulut saqlovi uchun post-kvantga tayyor, uchidan-uchigacha shifrlash yadro protokoli.  
**Normativ so‘zlar:** `MUST`, `MUST NOT`, `SHOULD`, `MAY` so‘zlari majburiyat darajasini bildiradi.

> Xavfsizlik eslatmasi: ushbu hujjat yangi shifrlash algoritmini ixtiro qilmaydi. U tan olingan algoritmlarni aniq, almashtiriladigan va audit qilinadigan protokolga birlashtiradi. Ishlab chiqarish muhitiga chiqarishdan oldin mustaqil kriptografik audit, test vektorlari, fuzzing va kalit boshqaruvi ko‘rigi majburiy.

---

## 1. Maqsad va qo‘llanish sohasi

Qalqon-Q ikki moduldan iborat:

| Modul | Vazifa | Himoyalanadigan obyekt |
|---|---|---|
| `Q-MSG` | ikki yoki ko‘p tomonli xabar almashinuvi | xabar matni, biriktirma, yuboruvchi identifikatori, sessiya oqimi |
| `Q-FILE` | katta faylni saqlash yoki uzatish | fayl tarkibi, fayl nomi/metama’lumoti, bo‘laklar tartibi va yaxlitligi |

Bu spetsifikatsiya serverni ishonchsiz transport va saqlash vositasi deb hisoblaydi. Server shifrlangan paketlarni yetkazishi yoki saqlashi mumkin, biroq ochiq matn yoki maxfiy kalitni olmasligi kerak.

### 1.1. Xavfsizlik xususiyatlari

Tizim quyidagilarni ta’minlashi kerak:

- maxfiylik va o‘zgartirishni aniqlash;
- yuboruvchi qurilmasini autentifikatsiyalash;
- post-kvant tahdidga tayyorgarlik;
- `forward secrecy`: eski sessiya kaliti oshkor bo‘lsa, boshqa sessiyalarni saqlash;
- `break-in recovery`: keyingi ratchet qadamlari bilan buzilgan sessiyadan tiklanish;
- replay, paket almashtirish va paketlarning o‘rnini almashtirishdan himoya;
- faylning qisman yuklanishi va bo‘laklar yaxlitligini tekshirish;
- algoritm va parametrlarni kelajakda almashtirish (`crypto-agility`).

### 1.2. Nimalar kafolatlanmaydi

Protokol endpoint buzilishini, foydalanuvchi ekranidan nusxa olishni, zararli klientni yoki trafik tahlilidan keladigan barcha metama’lumot oqishini yakka o‘zi to‘xtatmaydi. Bular uchun OS himoyasi, minimal loglash, anonim transport va operatsion jarayonlar kerak.

---

## 2. Kriptografik profil: `QQ-1`

| Vazifa | Algoritm | Parametr |
|---|---|---|
| Klassik kalit kelishuvi | X25519 | 256-bit |
| Post-kvant KEM | ML-KEM | ML-KEM-768 |
| Klassik imzo | Ed25519 | 128-bit klassik xavfsizlik |
| Post-kvant imzo | ML-DSA | ML-DSA-65 |
| AEAD | ChaCha20-Poly1305 | 256-bit kalit, 96-bit nonce |
| KDF | HKDF-SHA-512 | kontekstga bog‘langan |
| Xesh | SHA-3-256 | identifikator va Merkle daraxti |
| Parol bilan mahalliy kalit himoyasi | Argon2id | platformaga mos xotira/vaqt profili |

`ML-KEM-768`, `ML-DSA-65` va `SLH-DSA` NIST post-kvant standartlari oilasiga kiradi. `SLH-DSA` uzoq muddatli root/backup imzolar uchun ixtiyoriy ikkilamchi imzo sifatida qo‘llanishi mumkin, lekin har xabar uchun emas.

Implementatsiya yuqoridagi algoritmlarni o‘z qo‘li bilan yozishi **MUST NOT**. Faqat tekshirilgan, constant-time kutubxonadan foydalaniladi.

---

## 3. Identifikatsiya va kalitlar

Har bir qurilmada quyidagi kalitlar bo‘ladi:

```text
Device Identity Key (DIK)
  x25519_sk  / x25519_pk
  ed25519_sk / ed25519_pk
  mldsa_sk   / mldsa_pk

Signed Pre-Key (SPK, muddatli)
  x25519_sk / x25519_pk
  mlkem_sk  / mlkem_pk

One-Time Pre-Key (OPK, bir martalik; tavsiya etiladi)
  x25519_sk / x25519_pk
```

### 3.1. Device Certificate (DC)

Har qurilma uchun quyidagi kanonik obyekt yaratiladi va ikkala identifikatsion imzo bilan imzolanadi:

```json
{
  "v": 1,
  "device_id": "16-byte random",
  "x25519_pk": "bytes",
  "ed25519_pk": "bytes",
  "mldsa65_pk": "bytes",
  "created_at": "unix seconds",
  "expires_at": "unix seconds"
}
```

Identifikator: `device_fingerprint = SHA3-256(canonical_DC)`. Foydalanuvchi yangi qurilmani QR-kod, xavfsizlik raqami yoki mavjud ishonchli qurilmadan tasdiqlashi **SHOULD**.

### 3.2. Kalit saqlovi

Maxfiy kalitlar platforma himoyalangan saqlovida bo‘lishi **MUST**. Agar bunday saqlov bo‘lmasa, ular Argon2id bilan hosil qilingan kalit orqali lokal AEAD konteynerida saqlanadi. Maxfiy kalit, session root key yoki ochiq matn logga yozilishi **MUST NOT**.

---

## 4. Umumiy paket qobig‘i

Barcha tarmoq paketlari kanonik CBOR (tavsiya) yoki qat’iy kanonik JSON sifatida kodlanadi. Imzolangan yoki AEAD AAD tarkibidagi maydonlar byte-for-byte bir xil kodlanishi shart.

```text
Envelope = {
  v: uint,                 // 1
  suite: "QQ-1",
  type: string,
  sender_device_id: bytes[16],
  recipient_device_id: bytes[16] | null,
  session_id: bytes[16] | null,
  message_no: uint64 | null,
  timestamp: uint64,
  body: bytes
}
```

`v`, `suite`, `type`, yuboruvchi/qabul qiluvchi identifikatorlari, `session_id`, `message_no` va `timestamp` **MUST** AEAD `associated_data` (AAD) tarkibiga kiritiladi. Shunday qilib server bu maydonlarni almashtira olmaydi.

---

## 5. Q-MSG: sessiya ochish

### 5.1. Pre-key bundle

Qabul qiluvchi serverga faqat ommaviy materialni beradi:

```text
PreKeyBundle = {
  DC,
  SPK_x25519_pk, SPK_mlkem_pk,
  SPK_expiry,
  sig_ed25519(DC || SPK),
  sig_mldsa65(DC || SPK),
  optional OPK_x25519_pk
}
```

Klient ikkala imzoni tekshirmasdan bundle’ni qabul qilishi **MUST NOT**.

### 5.2. `INIT` xabari

Yuboruvchi yangi ephemeral X25519 kalit juftini yaratadi va qabul qiluvchining ML-KEM ochiq kalitiga `Encaps` bajaradi.

```text
dh1 = X25519(sender_ephemeral_sk, recipient_SPK_x25519_pk)
dh2 = X25519(sender_identity_x25519_sk, recipient_SPK_x25519_pk)
pq  = ML-KEM-768.Encaps(recipient_SPK_mlkem_pk)

ikm = dh1 || dh2 || pq.shared_secret
RK0 = HKDF-SHA-512(ikm,
     salt = SHA3-256("Qalqon-Q/1/INIT" || sender_DC || recipient_DC),
     info = "root-key", L = 64)
```

`INIT.body` yuboruvchining DCsi, ephemeral public key, ML-KEM ciphertext, tanlangan OPK identifikatori va yuboruvchi tomonidan qilingan hybrid imzoni o‘z ichiga oladi. Imzo `Envelope`ning AAD maydonlari hamda `INIT.body`ning shifrlanmagan qismini qamrab oladi.

Qabul qiluvchi `ML-KEM.Decaps` va X25519 orqali ayni `RK0`ni hosil qiladi. OPK ishlatilgan bo‘lsa, u tekshiruvdan keyin atomik tarzda o‘chirilishi **MUST**.

### 5.3. Gibrid imzo qoidasi

`HybridSign(M)` = `Ed25519.Sign(M) || ML-DSA-65.Sign(M)`. Tekshiruv har ikki imzo haqiqiy bo‘lgandagina muvaffaqiyatli. Kelajakdagi migratsiyalar uchun qabul qilinadigan imzo siyosati versiya orqali aniq belgilanadi; “bittasi o‘tsa bo‘ldi” siyosati **MUST NOT**.

---

## 6. Double Ratchet va xabar shifrlashi

Har sessiyada `RK` root key, `CKs` yuborish chain key, `CKr` qabul qilish chain key, DH ratchet kalitlari va hisoblagichlar saqlanadi.

```text
KDF_RK(RK, dh_or_pq_secret) -> (RK_next, CK)
KDF_CK(CK) -> (CK_next, MK)
MK = HKDF-SHA-512(CK, salt="Qalqon-Q/1/MSG", info=session_id || message_no, L=32)
```

Har xabar uchun:

```text
nonce = first_12_bytes(SHA3-256(session_id || direction || message_no))
ciphertext = ChaCha20-Poly1305.Seal(MK, nonce, plaintext, AAD)
```

`message_no` har yo‘nalishda monoton o‘sishi **MUST**. Qabul qiluvchi ishlatilgan xabar kalitini qayta qabul qilsa, uni rad etadi. Tarmoq tartibi buzilganda cheklangan miqdordagi (`MAX_SKIPPED_KEYS`, tavsiya: 1 000) o‘tkazib yuborilgan xabar kalitlari saqlanishi mumkin.

### 6.1. Post-kvant ratchet

Kamida har 100 xabar yoki 10 daqiqada (qaysi biri avval bo‘lsa) tomonlar navbatma-navbat yangi ML-KEM encapsulation xabarini yuborishi **SHOULD**. Olingan PQ secret `KDF_RK`ga qo‘shiladi. Bu sessiyani kelajakdagi kvant hujumiga nisbatan tiklash imkonini beradi.

### 6.2. Xabar turlari

| Type | Vazifa |
|---|---|
| `INIT` | yangi sessiya boshlash |
| `ACK` | `INIT` qabul qilinganini tasdiqlash |
| `MSG` | shifrlangan xabar yoki kichik biriktirma |
| `RATCHET_PQ` | post-kvant root-key yangilanishi |
| `CLOSE` | sessiyani nazoratli yakunlash |
| `DEVICE_REVOKE` | qurilma kalitini bekor qilish |

---

## 7. Q-FILE: faylni shifrlash va uzatish

### 7.1. File manifest

Fayl uchun tasodifiy 32-bayt `FK` (file key) yaratiladi. Fayl 4 MiB bo‘laklarga ajratiladi. Bo‘lak o‘lchami manifestda qat’iy beriladi.

```text
file_id = random(16)
file_salt = random(32)
chunk_key_i = HKDF-SHA-512(FK, salt=file_salt,
  info="Qalqon-Q/1/FILE/CHUNK" || file_id || uint64be(i), L=32)
nonce_i = first_12_bytes(SHA3-256(file_id || uint64be(i)))
AAD_i = canonical({v, file_id, i, total_chunks, plaintext_size})
chunk_ciphertext_i = ChaCha20-Poly1305.Seal(chunk_key_i, nonce_i, chunk_i, AAD_i)
leaf_i = SHA3-256(i || chunk_ciphertext_i)
```

`root_hash` — `leaf_i`lardan qurilgan Merkle daraxtining ildizi. Fayl manifesti quyidagilarni o‘z ichiga oladi:

```json
{
  "v": 1,
  "file_id": "bytes",
  "name_enc": "encrypted optional metadata",
  "mime_enc": "encrypted optional metadata",
  "plaintext_size": 0,
  "chunk_size": 4194304,
  "total_chunks": 0,
  "file_salt": "bytes",
  "root_hash": "bytes",
  "created_at": 0
}
```

Manifest va `FK` Q-MSGning amaldagi sessiya xabarida yuboriladi. `FK` hech qachon serverga alohida ochiq holda berilmaydi.

### 7.2. Fayl qabul qilish

Qabul qiluvchi har bo‘lakning AEAD tegini, indeksini va Merkle isbotini tekshiradi. Bitta bo‘lak noto‘g‘ri bo‘lsa, u qayta so‘raladi; fayl ochiq matnga yig‘ilmasdan avval `root_hash` tekshirilishi **MUST**.

### 7.3. Saqlash va ko‘p qabul qiluvchi

Ko‘p qabul qiluvchi uchun har qabul qiluvchining Q-MSG sessiyasi bilan bir xil `FK` alohida shifrlanadi. Fayl ciphertexti bitta nusxada saqlanishi mumkin. Qabul qiluvchi chiqarib tashlansa, faqat keyingi fayl versiyasi uchun yangi `FK` yaratiladi; avvalgi nusxalarni kriptografik tarzda “orqaga qaytarib” olish mumkin emas.

---

## 8. Qurilmani bekor qilish, backup va rotatsiya

- `DEVICE_REVOKE` amaldagi ishonchli qurilmaning hybrid imzosi bilan yuboriladi.
- Bekor qilingan qurilmaga yangi Q-MSG sessiyasi yoki yangi `FK` yuborilmaydi.
- DIK kamida 12 oyda yoki kompromat shubhasida yangilanadi.
- SPK 7–30 kunda yangilanadi; OPK zaxirasi kamayganda to‘ldiriladi.
- Backup faqat foydalanuvchi paroli va, imkon bo‘lsa, ikkinchi qurilma kaliti bilan shifrlanadi. Recovery kaliti serverda saqlanmaydi.

---

## 9. Server API uchun minimal talablar

Server faqat quyidagilarni bajarishi kerak:

- Device Certificate va pre-key bundlelarni saqlash;
- opaque `Envelope`larni navbatga qo‘yish;
- ciphertext fayl bo‘laklari va manifestlarini saqlash;
- rate limit, spamga qarshi nazorat va o‘chirish so‘rovlarini bajarish.

Server **MUST NOT**:

- shifrlanmagan kontent, maxfiy kalit yoki session root key qabul qilishi;
- klientning signature verification ishini o‘z nomidan almashtirishi;
- protokol versiyasi yoki `suite` qiymatini klient roziligisiz pasaytirishi.

TLS 1.3 transport qatlamida ham qo‘llanadi. TLS Qalqon-Q E2EE o‘rnini bosmaydi; u tarmoq sathidagi himoyani to‘ldiradi.

---

## 10. Majburiy testlar va chiqarish mezoni

Ishlab chiqarishga chiqishdan avval quyidagilar bajariladi:

1. Har kriptografik funksiya uchun rasmiy KAT/test vektorlari.
2. `INIT`, ratchet, noto‘g‘ri imzo, replay, out-of-order va key compromise testlari.
3. Fayl bo‘lagi o‘zgartirilishi, truncation, duplicate chunk va manifest almashtirish testlari.
4. Fuzzing: CBOR/JSON parser, envelope, manifest va barcha network handlerlar.
5. Maxfiy kalit, plaintext va tokenlarning loglarda yo‘qligini tekshirish.
6. Mustaqil kriptografik dizayn auditi hamda implementatsiya auditi.
7. Versiyalararo migratsiya va algoritm almashtirish sinovi.

### 10.1. Taqiqlangan amaliyotlar

- nonce’ni tasodifiy taxmin qilish yoki bir kalit bilan qayta ishlatish;
- faqat shifrlash, autentifikatsiyasiz ishlatish;
- imzoni tekshirish xatosini e’tiborsiz qoldirish;
- home-made crypto yoki norasmiy ML-KEM/ML-DSA implementatsiyasi;
- xato sababi orqali kalit yoki decryption holatini oshkor qiluvchi turli javoblar;
- serverdan kelgan public keyni foydalanuvchi/verifikatsiya mexanizmisiz ko‘r-ko‘rona ishonish.

---

## 11. Keyingi implementatsiya bosqichi

1. Kanonik CBOR sxemasi va barcha xabarlar uchun binar test vektorlarini qat’iylashtirish.
2. Faqat `INIT → ACK → MSG` oqimi uchun reference client yaratish.
3. Keyin Q-FILE chunk upload/download va Merkle tekshiruvi qo‘shish.
4. Mustaqil threat-model workshop va kripto-auditdan so‘ng pilot loyiha.

## Manbalar

- NIST, [FIPS 203: ML-KEM](https://csrc.nist.gov/pubs/fips/203/final)
- NIST, [FIPS 204: ML-DSA](https://csrc.nist.gov/pubs/fips/204/final)
- NIST, [FIPS 205: SLH-DSA](https://csrc.nist.gov/pubs/fips/205/final)
- NIST, [Post-Quantum Cryptography Project](https://csrc.nist.gov/projects/post-quantum-cryptography)
