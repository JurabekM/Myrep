# SCUTUM-Q1 v1.1 — S-MSG va S-FILE umumiy spetsifikatsiyasi

**Holati:** auditdan keyingi qayta ishlangan spetsifikatsiya
**Oldingi versiya:** Qalqon-Q v1 (`QQ-1` profili) — **eskirgan, ishlatilmasin**
**Maqsadi:** messenjer, fayl almashinuvi va shifrlangan bulut saqlovi uchun post-kvantga tayyor, uchidan-uchigacha shifrlash yadro protokoli
**Normativ so'zlar:** `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, `MAY` — RFC 2119 ma'nosida
**Referens implementatsiya:** `scutum/` (HARDENED profili), 37/37 test o'tadi
**Test vektorlari:** `kat/scutum-q1-kat.json` — ushbu hujjatning normativ qismi

> **Xavfsizlik eslatmasi.** Ushbu hujjat yangi shifrlash algoritmini ixtiro
> qilmaydi. U tan olingan algoritmlarni aniq, almashtiriladigan va audit
> qilinadigan protokolga birlashtiradi. v1.1 auditda topilgan 16 ta kamchilikni
> tuzatadi, ammo **mustaqil kriptografik audit hali o'tkazilmagan**. Ishlab
> chiqarish muhitiga chiqarishdan oldin §12 dagi barcha mezonlar bajarilishi
> `MUST`.

---

## 0. v1.0 dan v1.1 ga o'zgarishlar

Har bir o'zgarish auditda topilgan aniq kamchilikka javob beradi. `SPEC` ustuni —
kamchilik simulyatorda ijro etilgan hujum bilan tasdiqlanganini bildiradi.

| # | Kamchilik (v1.0) | Isbot | v1.1 dagi yechim | § |
|---|---|---|---|---|
| **K-1** | INIT'da qabul qiluvchining identity kaliti umuman qatnashmaydi; barcha sirlar faqat `SPK` ga bog'langan | BROKEN — faqat SPK sirlari bilan `RK0` aynan tiklandi | `dh3 = X25519(EK_A, IK_B)` qo'shildi | §5.2 |
| **K-2** | `OPK` e'lon qilinadi va o'chiriladi, lekin KDF'ga kirmaydi → dekorativ; INIT replay ochiq | BROKEN — ayni INIT ikkinchi marta qabul qilindi | `dh4 = X25519(EK_A, OPK_B)` + majburiy replay keshi va vaqt oynasi | §5.2, §5.3 |
| **K-3** | `CK` oldinga siljimaydi → chain ichida forward secrecy yo'q | BROKEN — o'g'irlangan `CK` 0-xabarni ochdi | Bir tomonlama zanjir: `MK = HMAC(CK,0x01)`, `CK' = HMAC(CK,0x02)` | §6.2 |
| **K-4** | Ratchet ochiq kaliti va `PN` Envelope sxemasida yo'q → ratchet amalga oshirilmaydi | BROKEN — server `pn` ni o'zgartirdi, sezilmadi | `hdr` maydoni rasmiylashtirildi va AAD ichiga kiritildi | §4.2, §4.3 |
| **K-5** | Mustaqil `RATCHET_PQ` xabari DH ratchet bilan sinxron bo'la olmaydi; holat mashinasi ta'riflanmagan | Implementatsiyada aniqlandi — zanjirlar ajralib ketdi | PQ siri ratchet qadamiga biriktirildi (`hdr.pq_ct`); to'liq holat mashinasi | §6.3, §6.4 |
| **Y-1** | ML-KEM ciphertext, ephemeral pk va KEM pk KDF transkriptiga bog'lanmagan | STRUCTURAL — turli transkript, ayni `RK0` | To'liq transkript xeshi `info` ga kiritildi | §5.2 |
| **Y-2** | AEAD kalitga majburiyat bermaydi → parol bilan shifrlangan backup'ga partitioning-oracle | STRUCTURAL | Har AEAD blokiga 32-baytli kalit-majburiyat tegi | §4.5 |
| **Y-3** | Merkle: barg/tugun domen ajratilmagan, toq tugun dublikat qilinadi | STRUCTURAL — `[A,B,C]` va `[A,B,C,C]` bir xil ildiz | RFC 6962 uslubi + `total_chunks` ildizga bog'landi | §7.3 |
| **Y-4** | `name_enc`/`mime_enc` uchun kalit, nonce va AAD umuman ta'riflanmagan | BROKEN — kalitsiz, XOR bilan fayl nomi tiklandi | Alohida `meta_key` va maydonga bog'langan nonce | §7.5 |
| **Y-5** | «kanonik CBOR yoki kanonik JSON» — AAD ning byte-for-byte mosligi bilan ziddiyat | STRUCTURAL — ikki mos implementatsiya gaplasha olmadi | Yagona majburiy profil: RFC 8949 §4.2.1 | §4.1 |
| **Y-6** | `sig(DC ‖ SPK)` — `SPK_expiry` imzo tashqarisida | BROKEN — muddat +10 yil o'zgartirildi, imzo haqiqiy qoldi | Butun kanonik bundle domen prefiksi bilan imzolanadi | §5.1 |
| **Y-7** | `fingerprint = SHA3-256(canonical_DC)` — `created_at`/`expires_at` ham kiradi | BROKEN — kalitlar o'zgarmasa ham fingerprint o'zgardi | Fingerprint faqat identity ochiq kalitlaridan | §3.2 |
| **Y-8** | Bekor qilish tartibi yo'q → server eski bundle'ni tiriltiradi | BROKEN — `epoch=5` dan keyin `epoch=0` qabul qilindi | Monoton `revoke_epoch` + klientda pinlash | §8 |
| **O-3** | `MAX_SKIPPED_KEYS` faqat chain uchun; chainlar soni cheklanmagan | — | Global limit, TTL va chain cheklovi | §6.5 |
| **O-8** | Metama'lumot oqishi to'liq tan olinmagan | INFO — server ijtimoiy grafni to'liq ko'radi | §11 da halol bayon + padding tavsiyalari | §11 |
| **O-9** | Parser xom kutubxona istisnolarini chiqaradi | 500 fuzz kirishdan 395 tasida oqib chiqdi | Qat'iy validatsiya + yagona xato modeli | §10 |

**Buzuvchi o'zgarishlar.** v1.1 v1.0 bilan **mos emas va mos bo'lishga urinmaydi**:
domen ajratgichlari `Qalqon-Q/1/…` dan `SCUTUM-Q1/…` ga o'zgardi (barcha derivatsiya
qilingan kalitlar boshqacha), `suite` qiymati `"QQ-1"` dan `"SCUTUM-Q1"` ga o'tdi,
`Envelope` sxemasi `hdr` maydoni bilan kengaydi. v1.0 implementatsiyasi bilan
muzokara qilishga urinish `MUST NOT`.

---

## 1. Maqsad va qo'llanish sohasi

SCUTUM ikki moduldan iborat:

| Modul | Vazifa | Himoyalanadigan obyekt |
|---|---|---|
| `S-MSG` | ikki yoki ko'p tomonli xabar almashinuvi | xabar matni, biriktirma, yuboruvchi identifikatori, sessiya oqimi |
| `S-FILE` | katta faylni saqlash yoki uzatish | fayl tarkibi, fayl nomi/metama'lumoti, bo'laklar tartibi va yaxlitligi |

Server ishonchsiz transport va saqlash vositasi deb hisoblanadi. Server shifrlangan
paketlarni yetkazishi yoki saqlashi mumkin, biroq ochiq matn yoki maxfiy kalitni
olmasligi `MUST`.

### 1.1. Xavfsizlik xususiyatlari

Tizim quyidagilarni ta'minlashi `MUST`:

- maxfiylik va o'zgartirishni aniqlash;
- yuboruvchi qurilmasini autentifikatsiyalash;
- post-kvant tahdidga tayyorgarlik (gibrid klassik + PQ);
- **forward secrecy** — har xabar darajasida (v1.0 da buzilgan edi, K-3);
- **break-in recovery** — DH va PQ ratchet qadamlari orqali;
- replay, paket almashtirish va paketlarning o'rnini almashtirishdan himoya;
- faylning qisman yuklanishi va bo'laklar yaxlitligini tekshirish;
- algoritm va parametrlarni kelajakda almashtirish (`crypto-agility`).

### 1.2. Nimalar kafolatlanmaydi

Protokol yakka o'zi quyidagilarni to'xtatmaydi:

- endpoint (qurilma) buzilishi, zararli klient, ekrandan nusxa olish;
- **trafik tahlili va metama'lumot oqishi** — §11 da batafsil va halol bayon
  qilingan. `Envelope` sarlavhasi shifrlanmagan;
- xabar va fayl **uzunligining oshkor bo'lishi** — padding majburiy emas;
- serverning yetkazmaslik orqali qilinadigan senzurasi (mavjudlik);
- kalit tarqatishdagi ishonch — bu §3.2 dagi qo'lda tasdiqlashga tayanadi
  (key transparency §14 da ochiq masala sifatida qayd etilgan).

---

## 2. Kriptografik profil `SCUTUM-Q1`

| Vazifa | Algoritm | Parametr |
|---|---|---|
| Klassik kalit kelishuvi | X25519 | RFC 7748 |
| Post-kvant KEM | ML-KEM-768 | FIPS 203, NIST L3 · pk 1184 B, ct 1088 B, ss 32 B |
| Klassik imzo | Ed25519 | RFC 8032 · pk 32 B, sig 64 B |
| Post-kvant imzo | ML-DSA-65 | FIPS 204, NIST L3 · pk 1952 B, sig 3309 B |
| AEAD | ChaCha20-Poly1305 | RFC 8439 · 256-bit kalit, 96-bit nonce |
| KDF | HKDF-SHA-512 | RFC 5869 |
| MAC / chain KDF | HMAC-SHA-512 | chain key zanjiri uchun |
| Kalit-majburiyat | HMAC-SHA-256 | 32-baytli teg |
| Xesh | SHA3-256 | identifikator, nonce, Merkle |
| Parol KDF | Argon2id | **minimal:** m=64 MiB, t=3, p=1 |
| Kodlash | Kanonik CBOR | RFC 8949 §4.2.1 |

`SLH-DSA` (FIPS 205) uzoq muddatli root/backup imzolar uchun ixtiyoriy ikkilamchi
imzo sifatida qo'llanishi `MAY`, lekin har xabar uchun emas.

Implementatsiya yuqoridagi algoritmlarni o'z qo'li bilan yozishi **`MUST NOT`**.
Faqat tekshirilgan, constant-time kutubxonadan foydalaniladi.

### 2.1. Tasodifiylik

> v1.0 da bu talab **umuman yo'q edi**.

Barcha maxfiy kalitlar, ephemeral kalitlar, `device_id`, `session_id`, `file_id`,
`file_salt`, `FK` va OPK'lar operatsion tizimning kriptografik xavfsiz tasodifiy
manbasidan (`getrandom(2)`, `BCryptGenRandom`, `/dev/urandom`) olinishi `MUST`.
Foydalanuvchi darajasidagi PRNG yoki `rand()` ishlatilishi `MUST NOT`.

### 2.2. Implementatsiya gigiyenasi

- Barcha sir bilan bog'liq solishtirishlar constant-time bo'lishi `MUST`
  (AEAD teglari, kalit-majburiyat teglari, fingerprintlar).
- Maxfiy kalitlar va chain kalitlari ishlatilgandan keyin xotirada zeroize
  qilinishi `SHOULD`; swap'ga tushmasligi uchun `mlock`/`VirtualLock` `SHOULD`.
- Maxfiy kalit, `RK`, `CK`, `MK`, `FK` yoki ochiq matn logga yozilishi `MUST NOT`.

---

## 3. Identifikatsiya va kalitlar

Har bir qurilmada:

```text
Device Identity Key (DIK) — uzoq muddatli
  x25519_sk  / x25519_pk        (32 / 32 B)
  ed25519_sk / ed25519_pk       (32 / 32 B)
  mldsa65_sk / mldsa65_pk       (— / 1952 B)

Signed Pre-Key (SPK) — 7–30 kun
  x25519_sk / x25519_pk         (32 / 32 B)
  mlkem_sk  / mlkem_pk          (— / 1184 B)

One-Time Pre-Key (OPK) — bir martalik, MAJBURIY (v1.0 da "tavsiya etiladi" edi)
  x25519_sk / x25519_pk         (32 / 32 B)
```

### 3.1. Device Certificate (DC)

```text
DC = {
  "v":          1,
  "device_id":  bytes[16],
  "x25519_pk":  bytes[32],
  "ed25519_pk": bytes[32],
  "mldsa65_pk": bytes[1952],
  "created_at": uint64,      // unix sekund
  "expires_at": uint64
}
```

`canonical_DC` — §4.1 bo'yicha kodlangan baytlar.

### 3.2. Qurilma barmoq izi

> **Y-7 tuzatishi.** v1.0 da fingerprint butun `DC` dan olinar edi, ya'ni `DC`
> muddati yangilanganda ham o'zgarardi. Foydalanuvchilar takroriy «xavfsizlik
> raqami o'zgardi» ogohlantirishlariga ko'nikib, haqiqiy MITM ni e'tiborsiz
> qoldirishi mumkin edi.

```text
device_fingerprint =
    SHA3-256( "SCUTUM-Q1/fp" || x25519_pk || ed25519_pk || mldsa65_pk )
```

Fingerprint faqat **identity ochiq kalitlariga** bog'langan, shuning uchun `DC`
muddatini uzaytirish yoki `SPK`/`OPK` rotatsiyasi uni **o'zgartirmaydi** `MUST`.
Fingerprint faqat DIK rotatsiyasida o'zgaradi.

Foydalanuvchi yangi qurilmani QR-kod, xavfsizlik raqami yoki mavjud ishonchli
qurilmadan tasdiqlashi `SHOULD`. Klient tasdiqlangan fingerprintni saqlashi va
o'zgarganda **aniq ogohlantirish ko'rsatishi** `MUST`.

### 3.3. Kalit saqlovi

Maxfiy kalitlar platforma himoyalangan saqlovida (Keychain, TPM, StrongBox,
Keystore) bo'lishi `MUST`. Bunday saqlov bo'lmasa, ular Argon2id bilan hosil
qilingan kalit orqali lokal AEAD konteynerida saqlanadi; **Argon2id parametrlari
m ≥ 64 MiB, t ≥ 3, p ≥ 1 bo'lishi `MUST`** (v1.0 da hech qanday pol yo'q edi).
Lokal konteyner §4.5 dagi kalit-majburiyat tegini ishlatishi `MUST`.

---

## 4. Kodlash, paket qobig'i va AEAD

### 4.1. Kanonik kodlash

> **Y-5 tuzatishi.** v1.0 CBOR va JSON'ni muqobil qilib, ayni paytda AAD'ning
> byte-for-byte mosligini talab qilardi — bu bajarilmas ziddiyat edi.

Barcha imzolangan yoki AAD tarkibiga kiruvchi tuzilmalar **RFC 8949 §4.2.1 Core
Deterministic Encoding** bo'yicha kodlanishi `MUST`. JSON yoki boshqa kodlash
`MUST NOT`.

Amaliy oqibatlari:
- xarita kalitlari **avval uzunligi**, so'ng leksikografik tartibda joylashadi;
- butun sonlar eng qisqa shaklda; suzuvchi nuqta ishlatilmaydi;
- noaniq uzunlikdagi (indefinite-length) elementlar `MUST NOT`.

Qabul qiluvchi kelgan baytlarni dekodlab **qayta kodlashi va natijani asl baytlar
bilan solishtirishi `MUST`**; mos kelmasa paket rad etiladi. Bu server tomonidan
qayta-serializatsiya orqali qilinadigan hujumlarni to'sadi.

### 4.2. Envelope

> **K-4 tuzatishi.** `hdr` maydoni v1.0 sxemasida yo'q edi; usiz Double Ratchet
> amalga oshirilmaydi.

```text
Envelope = {
  v:      uint,                    // 1
  suite:  tstr,                    // "SCUTUM-Q1"
  type:   tstr,                    // §6.7
  snd:    bytes[16],               // yuboruvchi device_id
  rcv:    bytes[16] / null,
  sid:    bytes[16] / null,        // session_id
  no:     uint64 / null,           // message_no — yo'nalish bo'yicha MONOTON
  ts:     uint64,                  // unix sekund
  hdr:    RatchetHeader / null,
  body:   bytes
}

RatchetHeader = {
  dh:     bytes[32],               // yuboruvchining joriy ratchet ochiq kaliti
  pn:     uint32,                  // oldingi yuborish chain uzunligi
  n:      uint32,                  // SHU chain ichidagi tartib
  pq_ct:  bytes[1088] / null,      // ratchet kalitiga biriktirilgan ML-KEM ct
  pq_pk:  bytes[1184] / null       // yuboruvchining yangi ML-KEM ochiq kaliti
}
```

**`no` va `n` farqi (v1.0 dagi ziddiyat).** `no` — sessiya davomida yo'nalish
bo'yicha **monoton o'suvchi** global hisoblagich; u nonce va replay uchun
ishlatiladi. `n` — joriy ratchet chain ichidagi tartib bo'lib, **har ratchet
qadamida 0 ga qaytadi**; u kalit derivatsiyasi va skipped-key hisobi uchun
ishlatiladi. Bularni bitta maydon bilan almashtirish `MUST NOT`.

### 4.3. Associated Data

```text
AAD = canonical({ v, suite, type, snd, rcv, sid, no, ts, hdr })
```

`hdr` **AAD ichiga kiritilishi `MUST`** — aks holda hujumchi ratchet holatini
sezilmasdan buzadi (K-4). `body` AAD ga kirmaydi (u AEAD ning o'zi tomonidan
himoyalanadi).

### 4.4. Nonce

```text
message_nonce = SHA3-256( sid || direction || uint64be(no) )[0:12]

direction: 0x00 — sessiya tashabbuskori (initiator)
           0x01 — javob beruvchi (responder)
```

`direction` baytining aniq qiymatlari v1.0 da **ta'riflanmagan edi**. Har bir
`MK` yagona bo'lgani va `no` monoton o'sgani uchun nonce takrorlanmaydi.

### 4.5. AEAD va kalit-majburiyat

> **Y-2 tuzatishi.** ChaCha20-Poly1305 key-committing emas. §8 dagi backup
> parol bilan shifrlanadi, ya'ni partitioning-oracle hujumi amaliy.

Har bir AEAD chiqishi oldiga kalit-majburiyat tegi qo'yiladi:

```text
commit(K)  = HMAC-SHA-256( K, "SCUTUM-Q1/commit" )        // 32 bayt
body       = commit(K) || ChaCha20-Poly1305.Seal(K, nonce, plaintext, AAD)
```

Deshifrlashda `commit(K)` **AEAD ochishdan oldin** constant-time solishtiriladi
`MUST`. Mos kelmasa paket rad etiladi va AEAD umuman chaqirilmaydi.

---

## 5. S-MSG: sessiya ochish

### 5.1. PreKeyBundle

> **Y-6 tuzatishi.** v1.0 da `sig(DC ‖ SPK)` edi — `SPK_expiry` imzo tashqarisida
> qolardi va server buzilgan `SPK` ni cheksiz «tiriltira» olardi.

```text
PreKeyBundle = {
  dc:            DC,
  spk_x_pk:      bytes[32],
  spk_mlkem_pk:  bytes[1184],
  spk_expiry:    uint64,
  opk_id:        bytes[8] / null,
  opk_pk:        bytes[32] / null,
  revoke_epoch:  uint64,
  sig_ed25519:   bytes[64],
  sig_mldsa65:   bytes[3309]
}
```

Imzo ostiga tushadigan baytlar:

```text
M_bundle = "SCUTUM-Q1/prekey" ||
           canonical({ dc, spk_x, spk_mlkem, spk_expiry, opk_id, opk_pk })
```

Ya'ni **butun bundle**, jumladan muddat, OPK va DC. Xom konkatenatsiya
(`DC || SPK`) `MUST NOT` — u uzunlik prefiksisiz va kanonizatsiya noaniqligiga
ochiq.

Klient quyidagilarning **hammasini** bajarmasdan bundle'ni qabul qilishi
`MUST NOT`:

1. `HybridVerify(DC.ed25519_pk, DC.mldsa65_pk, sig, M_bundle)` — §5.4;
2. `now ≤ DC.expires_at`;
3. `now ≤ spk_expiry`;
4. `revoke_epoch ≥` shu qurilma uchun oxirgi ko'rilgan epoch (§8);
5. kodlash kanonikligi (§4.1);
6. `DC.device_id` bilan bog'langan fingerprint ishonch ro'yxatiga mos (§3.2).

### 5.2. `INIT` — root key derivatsiyasi

> **K-1, K-2, Y-1 tuzatishlari.** v1.0 da uchala sir ham faqat `SPK` ga
> bog'langan edi (`dh3` yo'q), `OPK` KDF'ga kirmasdi (`dh4` yo'q), va KEM
> ciphertext transkriptga bog'lanmagan edi.

Yuboruvchi (A) yangi ephemeral X25519 juftini yaratadi va qabul qiluvchining (B)
ML-KEM ochiq kalitiga `Encaps` bajaradi:

```text
dh1 = X25519( EK_A_sk,      SPK_B_x_pk )
dh2 = X25519( IK_A_x_sk,    SPK_B_x_pk )
dh3 = X25519( EK_A_sk,      IK_B_x_pk   )     ← K-1 tuzatishi
dh4 = X25519( EK_A_sk,      OPK_B_pk    )     ← K-2 tuzatishi
(ss, ct) = ML-KEM-768.Encaps( SPK_B_mlkem_pk )

ikm = dh1 || dh2 || dh3 || dh4 || ss          // aynan shu tartibda
```

`OPK` **majburiy** `MUST`. Agar server OPK'siz bundle qaytarsa, klient sessiyani
ochishni rad etishi `MUST` (v1.0 da OPK ixtiyoriy va ta'sirsiz edi).

Transkript va salt:

```text
transcript = SHA3-256( "SCUTUM-Q1/transcript" ||
             canonical({ suite, ek, spk_x, kem_pk, kem_ct, opk, dc_a, dc_b }) )

salt       = SHA3-256( "SCUTUM-Q1/INIT" || canonical(DC_A) || canonical(DC_B) )

RK0        = HKDF-SHA-512( ikm,
                           salt = salt,
                           info = "root-key" || transcript,
                           L    = 64 )
```

Transkript ML-KEM `ct` va `pk` ni ham qamrab olishi `MUST` — ML-KEM binding
kafolatlari cheklangan (MAL-BIND-K-CT), shuning uchun bog'lash KDF darajasida
bajariladi.

**`INIT.body`:**

```text
core = { dc: DC_A, ek: EK_A_pk, kem_ct: ct, opk_id: opk_id }
sig  = HybridSign( IK_A, AAD || canonical(core) || transcript )
body = canonical({ ...core, sig })
```

Qabul qiluvchi `ML-KEM.Decaps` va uchta X25519 orqali ayni `RK0` ni hosil qiladi.
Ishlatilgan `OPK` tekshiruvdan keyin **atomik tarzda** o'chirilishi `MUST`;
o'chirish muvaffaqiyatsiz bo'lsa sessiya ochilmasligi `MUST`.

### 5.3. INIT replay himoyasi

> **K-2 tuzatishi.** v1.0 da replay oynasi ham, kesh ham ta'riflanmagan edi.

Qabul qiluvchi quyidagilarni bajarishi `MUST`:

```text
init_id = SHA3-256( "SCUTUM-Q1/init-id" || kem_ct )
```

1. `|now − Envelope.ts| ≤ 120 sekund` — aks holda rad etiladi;
2. `init_id` keshda bo'lsa — rad etiladi;
3. aks holda `init_id` keshga `ts` bilan qo'shiladi.

Kesh `SPK` amal qilish muddati davomida saqlanadi va undan eski yozuvlar
tozalanadi. Kesh hajmi cheklangan o'sadi, chunki har `SPK` uchun OPK zaxirasi
chekli.

`dh4` majburiy bo'lgani uchun replay ikki qatlamda to'siladi: takroriy `INIT` da
ko'rsatilgan `OPK` allaqachon o'chirilgan bo'ladi va derivatsiya bajarilmaydi.

### 5.4. Gibrid imzo

```text
HybridSign(M)   = ( Ed25519.Sign(M), ML-DSA-65.Sign(M) )
HybridVerify(M) = Ed25519.Verify(M) AND ML-DSA-65.Verify(M)
```

Tekshiruv **har ikki imzo haqiqiy bo'lgandagina** muvaffaqiyatli `MUST`.
«Bittasi o'tsa bo'ldi» siyosati `MUST NOT`. Ikkala tekshiruv ham har doim
bajarilishi `SHOULD` (short-circuit qilinmasin — vaqt kanali kamayadi).

Ikki imzo alohida maydonlarda uzatiladi (`sig_ed25519`, `sig_mldsa65`); xom
konkatenatsiya `SHOULD NOT`.

### 5.5. `ACK`

```text
core = { sid, ok: true }
sig  = HybridSign( IK_B, AAD || canonical(core) )
body = canonical({ ...core, sig })
```

Tashabbuskor `ACK` imzosini tekshirmasdan sessiyani tasdiqlangan deb hisoblashi
`MUST NOT`.

---

## 6. Double Ratchet

### 6.1. Sessiya holati

```text
RK         root key (64 B)
DHs_sk/pk  bizning joriy ratchet X25519 juftimiz
DHr_pk     peer ratchet ochiq kaliti
CKs, CKr   yuborish / qabul chain kalitlari (32 B)
Ns, Nr     joriy chain ichidagi tartiblar
PN         oldingi yuborish chain uzunligi
send_no    global monoton message_no (yo'nalish bo'yicha)
seen_recv  qabul qilingan message_no lar to'plami (replay)
skipped    { (DHr_pk, n) -> MK }
PQ_sk      bizning joriy ML-KEM maxfiy kalitimiz
PQ_sk_prev oldingisi (peer hali eskisiga Encaps qilgan bo'lishi mumkin)
PQ_peer_pk peer ning ML-KEM ochiq kaliti
PQ_pending PQ qadam so'ralganini bildiruvchi bayroq
```

### 6.2. Kalit derivatsiyasi

> **K-3 tuzatishi.** v1.0 dagi yagona konkret formula `MK` ni **statik** `CK` dan
> chiqarardi; `KDF_CK` ta'riflanmagan edi. Natijada chain ichida forward secrecy
> umuman yo'q edi.

```text
KDF_RK(RK, secret):
    out = HKDF-SHA-512( ikm  = secret,
                        salt = RK,
                        info = "SCUTUM-Q1/RK",
                        L    = 96 )
    return ( out[0:64], out[64:96] )          // (RK_next, CK)

KDF_CK(CK):
    MK      = HMAC-SHA-512( CK, 0x01 )[0:32]
    CK_next = HMAC-SHA-512( CK, 0x02 )[0:32]
    return ( CK_next, MK )
```

`message_no` yoki `session_id` `MK` derivatsiyasiga kirishi `MUST NOT` — ular
faqat AAD va nonce uchun. `CK` har xabardan keyin **almashtirilishi** va eskisi
zeroize qilinishi `MUST`.

### 6.3. Ratchet qadami — holat mashinasi

> **K-4, K-5 tuzatishlari.** v1.0 da holat mashinasi umuman yozilmagan edi.

**Muhim invariant:** tomon yangi ratchet kalitini **faqat xabar qabul
qilganda** yaratadi. Yuboruvchi tomonidan o'z-o'zidan bajarilgan ratchet qadami
qabul qiluvchida takrorlanmaydi va zanjirlarni ajratib yuboradi. Bu qoida buzilishi
`MUST NOT`.

**Bootstrap.**

- Tashabbuskor (A): `DHr_pk := SPK_B_x_pk`, `PQ_peer_pk := SPK_B_mlkem_pk`,
  so'ng darhol `NewSendingRatchet()`.
- Javob beruvchi (B): `DHs := SPK_B_x` (ayni juft), `DHr_pk := null`,
  `PQ_sk := SPK_B_mlkem`, `CKs := null` — B faqat birinchi xabarni qabul
  qilgandan keyin yubora oladi.

**`NewSendingRatchet()`** — yangi yuborish zanjirini ochadi:

```text
PN := Ns ;  Ns := 0
DHs := yangi X25519 juft

extra := ""
if PQ_pending and PQ_peer_pk ≠ null:
    (ss, ct) := ML-KEM-768.Encaps( PQ_peer_pk )
    PQ_sk_prev := PQ_sk ;  PQ_sk := yangi ML-KEM juft
    hdr.pq_ct := ct ;  hdr.pq_pk := PQ_sk.pk
    extra := ss ;  PQ_pending := false
else:
    hdr.pq_ct := null ;  hdr.pq_pk := null

(RK, CKs) := KDF_RK( RK, X25519(DHs_sk, DHr_pk) || extra )
```

`hdr.pq_ct` va `hdr.pq_pk` **shu ratchet kaliti bilan yuborilgan har bir
xabarda** takrorlanadi.

**`DHRatchet(hdr)`** — yangi `hdr.dh` ko'rilganda:

```text
Nr := 0
DHr_pk := hdr.dh

extra := ""
if hdr.pq_ct ≠ null:
    extra := ML-KEM-768.Decaps( PQ_sk yoki PQ_sk_prev, hdr.pq_ct )
if hdr.pq_pk ≠ null:
    PQ_peer_pk := hdr.pq_pk

(RK, CKr) := KDF_RK( RK, X25519(DHs_sk, DHr_pk) || extra )
NewSendingRatchet()
```

Ikki ML-KEM kalitini (`PQ_sk`, `PQ_sk_prev`) saqlash zarur, chunki peer
yangilanishni ko'rishdan oldin eskisiga `Encaps` qilgan bo'lishi mumkin.

### 6.4. Post-kvant ratchet

> **K-5 tuzatishi.** v1.0 mustaqil `RATCHET_PQ` xabarini talab qilardi — bu
> §6.3 dagi invariantni buzadi va holatlarni ajratib yuboradi.

Tomonlar kamida **har 100 xabar yoki 10 daqiqada** (qaysi biri avval bo'lsa)
`PQ_pending := true` qo'yishi `SHOULD`. PQ siri keyingi `NewSendingRatchet()`
qadamiga avtomatik biriktiriladi.

Bu shuni anglatadiki, PQ qadam faqat tomon **xabar qabul qilgandan keyin**
bajariladi. Agar bir tomon uzoq vaqt faqat yuborayotgan bo'lsa, PQ yangilanishi
kechikadi — bu qabul qilinadigan holat, chunki bir tomonlama oqimda DH ratchet
ham yangilanmaydi.

`RATCHET_PQ` turi §6.7 da saqlanib qolgan, lekin endi u **faqat peer'dan javob
so'rovchi bo'sh xabar** (keepalive) sifatida ishlatiladi; u o'z-o'zidan `RK` ni
o'zgartirmaydi `MUST`.

### 6.5. O'tkazib yuborilgan kalitlar

> **O-3 tuzatishi.**

```text
MAX_SKIPPED_PER_CHAIN  = 1000
MAX_SKIPPED_CHAINS     = 8
MAX_SKIPPED_TOTAL      = 8000
SKIPPED_TTL            = 7 kun
```

Bitta ratchet qadamida `MAX_SKIPPED_PER_CHAIN` dan ortiq kalit hosil qilish
so'ralsa, xabar rad etilishi `MUST`. Umumiy saqlangan kalitlar soni
`MAX_SKIPPED_TOTAL` dan oshsa, eng eskisi o'chirilishi `MUST`. TTL o'tgan
kalitlar zeroize qilinib o'chiriladi `MUST`.

Har bir saqlangan yozuv `(MK, saqlangan_vaqt)` juftligi bo'lishi `MUST` — vaqt
belgisisiz TTL qo'llab bo'lmaydi.

Saqlangan `MK` lar o'z muddati davomida forward secrecy'ni kamaytiradi — bu
ongli murosа va foydalanuvchiga sozlanadigan bo'lishi `SHOULD`.

### 6.6. Xabar shifrlash

```text
(CKs, MK) := KDF_CK(CKs)
hdr       := { dh: DHs_pk, pn: PN, n: Ns, pq_ct, pq_pk }
nonce     := SHA3-256( sid || direction || uint64be(no) )[0:12]
body      := commit(MK) || ChaCha20-Poly1305.Seal( MK, nonce, plaintext, AAD )
Ns := Ns + 1 ;  no := no + 1
```

Qabul qiluvchi:

1. `no ∈ seen_recv` bo'lsa — rad etadi (replay);
2. `(hdr.dh, hdr.n)` saqlangan kalitlar orasida bo'lsa — o'shani ishlatadi;
3. `hdr.dh ≠ DHr_pk` bo'lsa — `hdr.pn` gacha kalitlarni saqlaydi, so'ng
   `DHRatchet(hdr)`;
4. `hdr.n` gacha kalitlarni saqlaydi va `KDF_CK(CKr)` bilan `MK` ni oladi;
5. `commit(MK)` ni tekshiradi, so'ng AEAD ni ochadi;
6. `no` ni `seen_recv` ga qo'shadi.

### 6.7. Xabar turlari

| Type | Vazifa |
|---|---|
| `INIT` | yangi sessiya boshlash |
| `ACK` | `INIT` qabul qilinganini tasdiqlash |
| `MSG` | shifrlangan xabar yoki kichik biriktirma |
| `RATCHET_PQ` | peer'dan ratchet qadamini so'rovchi bo'sh xabar (§6.4) |
| `CLOSE` | sessiyani nazoratli yakunlash (imzolangan `MUST`) |
| `DEVICE_REVOKE` | qurilma kalitini bekor qilish (§8) |
| `FILE_MANIFEST` | S-FILE manifesti va `FK` (sessiya ichida) |

---

## 7. S-FILE

### 7.1. Kalitlar

```text
FK          = random(32)          // fayl kaliti
file_id     = random(16)
file_salt   = random(32)
chunk_size  = 4 MiB (default), manifestda qat'iy beriladi

chunk_key_i = HKDF-SHA-512( ikm  = FK,
                            salt = file_salt,
                            info = "SCUTUM-Q1/FILE/CHUNK" || file_id || uint64be(i),
                            L    = 32 )
```

### 7.2. Bo'laklar

```text
nonce_i = SHA3-256( file_id || uint64be(i) )[0:12]
AAD_i   = canonical({ v, file_id, i, total_chunks, plaintext_size })
ct_i    = commit(chunk_key_i) ||
          ChaCha20-Poly1305.Seal( chunk_key_i, nonce_i, chunk_i, AAD_i )
```

`AAD_i` ichidagi `i` va `total_chunks` bo'laklarning o'rnini almashtirish va
truncation'ni to'sadi.

### 7.3. Merkle daraxti

> **Y-3 tuzatishi.** v1.0 da barg va ichki tugun bir xil xesh bilan hisoblanardi,
> toq tugun dublikat qilinardi va `total_chunks` ildizga bog'lanmagan edi.
> Natijada `[A,B,C]` va `[A,B,C,C]` **ayni ildizni** berardi.

```text
leaf_i    = SHA3-256( 0x00 || uint64be(i) || ct_i )
node(L,R) = SHA3-256( 0x01 || L || R )
```

Daraxt qurilishi:

- har darajada juftliklar chapdan o'ngga birlashtiriladi;
- toq qolgan tugun **yuqoriga ko'chiriladi** (dublikat qilinishi `MUST NOT`);
- yagona barg holatida `tree_root = leaf_0`.

```text
root_hash = SHA3-256( 0x02 || uint64be(total_chunks) || tree_root )
```

`total_chunks` ildizga bog'langani uchun daraxt o'lchamini o'zgartirish
aniqlanadi.

### 7.4. Manifest

```text
Manifest = {
  v:               1,
  file_id:         bytes[16],
  name_enc:        bytes / null,
  mime_enc:        bytes / null,
  plaintext_size:  uint64,
  chunk_size:      uint32,
  total_chunks:    uint32,
  file_salt:       bytes[32],
  root_hash:       bytes[32],
  created_at:      uint64
}
```

Manifest va `FK` **faqat amaldagi S-MSG sessiyasi ichida** `FILE_MANIFEST`
xabari sifatida yuborilishi `MUST`. Serverdan olingan manifestga ishonish
`MUST NOT` — u faqat sessiya ichida olingan nusxa bilan solishtirish uchun
ishlatilishi `MAY`. `FK` serverga hech qachon berilmaydi `MUST NOT`.

### 7.5. Fayl metama'lumoti

> **Y-4 tuzatishi.** v1.0 `name_enc`/`mime_enc` uchun kalitni ham, nonce'ni ham,
> AAD ni ham ta'riflamagandi. Amaliyotda `FK` va sobit nonce ishlatilib,
> `name_enc XOR mime_enc` orqali fayl nomi **kalitsiz** tiklanardi.

```text
meta_key   = HKDF-SHA-512( ikm  = FK,
                           salt = file_salt,
                           info = "SCUTUM-Q1/FILE/META" || file_id,
                           L    = 32 )

meta_nonce(f) = SHA3-256( "SCUTUM-Q1/FILE/META" || file_id || f )[0:12]
meta_aad(f)   = canonical({ file_id, f })

name_enc = Seal( meta_key, meta_nonce("name"), name, meta_aad("name") )
mime_enc = Seal( meta_key, meta_nonce("mime"), mime, meta_aad("mime") )
```

Har maydon **o'z nonce'siga** ega `MUST`. Fayl nomi uzunligining oshkor
bo'lishini kamaytirish uchun nom 64 baytga to'ldirilishi (padding) `SHOULD`.

### 7.6. Faylni qabul qilish

Quyidagi tartib majburiy `MUST`:

1. bo'laklar soni `total_chunks` ga teng, indekslar `0..total−1` va takrorlanmagan;
2. barcha `leaf_i` qayta hisoblanadi va `root_hash` **ochiq matnga yig'ishdan
   oldin** tekshiriladi;
3. har bo'lak uchun `commit(chunk_key_i)` tekshiriladi, so'ng AEAD ochiladi;
4. yig'ilgan uzunlik `plaintext_size` ga teng.

Bitta bosqich yiqilsa, fayl **butunlay** rad etiladi va qisman ochiq matn
foydalanuvchiga berilmaydi `MUST`.

### 7.7. Ko'p qabul qiluvchi

Har qabul qiluvchining S-MSG sessiyasi bilan bir xil `FK` alohida shifrlanadi;
fayl ciphertexti bitta nusxada saqlanishi `MAY`.

**Cheklov ochiq e'lon qilinadi:** qabul qiluvchi chiqarib tashlansa, faqat
keyingi fayl versiyasi uchun yangi `FK` yaratiladi. Avvalgi nusxalarni
kriptografik tarzda «orqaga qaytarib» olish **mumkin emas** — bu protokol
cheklovi, xato emas.

---

## 8. Bekor qilish, backup va rotatsiya

> **Y-8 tuzatishi.** v1.0 da bekor qilish tartibi kuzatilmasdi.

```text
DEVICE_REVOKE.core = { target: device_id, epoch: uint64, at: uint64 }
sig = HybridSign( IK_revoker, AAD || canonical(core) )
```

- `revoke_epoch` har rotatsiya va bekor qilishda **monoton o'sadi** `MUST`.
- Klient har qurilma uchun oxirgi ko'rilgan `revoke_epoch` ni saqlaydi va
  undan **kichik** epoch'li bundle'ni rad etadi `MUST` (rollback himoyasi).
- Bekor qilingan qurilmaga yangi sessiya yoki yangi `FK` yuborilmaydi `MUST`.
- Bitta buzilgan qurilma barcha halol qurilmalarni bekor qila olmasligi uchun
  bekor qilish foydalanuvchi tasdig'ini talab qilishi `SHOULD`.
- `DIK` kamida 12 oyda yoki kompromat shubhasida yangilanadi.
- `SPK` 7–30 kunda yangilanadi; `OPK` zaxirasi kamayganda to'ldiriladi.
- Backup faqat foydalanuvchi paroli (Argon2id, §3.3) va imkon bo'lsa ikkinchi
  qurilma kaliti bilan shifrlanadi; kalit-majburiyat tegi majburiy `MUST`
  (§4.5). Recovery kaliti serverda saqlanmaydi `MUST NOT`.

---

## 9. Server uchun talablar

Server faqat quyidagilarni bajaradi:

- Device Certificate va pre-key bundlelarni saqlash va berish;
- opaque `Envelope` larni navbatga qo'yish va yetkazish;
- ciphertext fayl bo'laklari va manifestlarini saqlash;
- rate limit, spamga qarshi nazorat va o'chirish so'rovlarini bajarish;
- `OPK` zaxirasini har `INIT` da kamaytirish va tugaganda xato qaytarish.

Server **`MUST NOT`**:

- shifrlanmagan kontent, maxfiy kalit yoki `RK` qabul qilish;
- klientning imzo tekshiruvini o'z nomidan bajarish;
- protokol versiyasi yoki `suite` qiymatini klient roziligisiz pasaytirish;
- `revoke_epoch` i kichikroq eski bundle'ni qaytarish.

TLS 1.3 transport qatlamida qo'llanadi `MUST`. TLS uchidan-uchigacha shifrlash
o'rnini bosmaydi — u faqat tarmoq sathidagi himoyani to'ldiradi.

---

## 10. Xato modeli

> **O-9 tuzatishi.** v1.0 da parser xom kutubxona istisnolarini chiqarardi
> (fuzzingda 500 kirishdan 395 tasi).

Tarmoqqa chiqadigan javob **yagona, ma'lumot bermaydigan kod** bo'lishi `MUST`.
Xatoning sababi (imzo, AEAD, replay, parsing, muddat) tashqi kuzatuvchi uchun
farqlanmasligi `MUST` — na kod, na matn, na javob vaqti orqali.

Parser har qanday kirish uchun quyidagilarni bajarishi `MUST`:

- barcha maydon turlarini va uzunliklarini qat'iy tekshirish
  (`snd`/`rcv`/`sid` — 16 B, `hdr.dh` — 32 B, `pq_ct` — 1088 B, `pq_pk` — 1184 B);
- `body` uchun yuqori chegara (default 16 MiB);
- barcha ichki istisnolarni yagona protokol xatosiga aylantirish;
- rekursiya chuqurligi va ajratilgan xotira uchun chegaralar.

---

## 11. Metama'lumot: nima oshkor bo'ladi

> **O-8.** Bu bo'lim v1.0 da yetarlicha halol emas edi.

Server ochiq matnni ko'rmaydi, ammo **har paketda** quyidagilarni to'liq ko'radi:

| Maydon | Oqibati |
|---|---|
| `snd`, `rcv` | to'liq ijtimoiy graf |
| `sid` | suhbatlarni bir-biriga bog'lash |
| `no` | almashilgan xabarlar soni |
| `ts` | suhbat vaqti va ritmi |
| paket uzunligi | xabar uzunligi (padding yo'q) |
| `type` | handshake / xabar / fayl farqi |

Kamaytirish choralari (`SHOULD`, v1.2 da majburiy bo'lishi mumkin):

- xabarlarni sobit chelaklarga to'ldirish (masalan 256 / 1024 / 4096 bayt);
- `Envelope` sarlavhasini alohida header-kalit bilan shifrlash;
- sealed sender uslubidagi yuboruvchini yashirish;
- anonim transport (Tor, mixnet) va minimal server loglash.

---

## 12. Majburiy testlar va chiqarish mezoni

Ishlab chiqarishga chiqishdan avval quyidagilar bajarilishi `MUST`:

1. Har kriptografik funksiya uchun KAT/test vektorlari — §13 va
   `kat/scutum-q1-kat.json`. ✅ *bajarilgan*
2. `INIT`, ratchet, noto'g'ri imzo, replay, out-of-order, key compromise
   testlari. ✅ *bajarilgan*
3. Fayl bo'lagi o'zgartirilishi, truncation, duplicate chunk va manifest
   almashtirish testlari. ✅ *bajarilgan*
4. Fuzzing: CBOR parser, envelope, manifest va barcha network handlerlar —
   faqat protokol xatosi chiqishi tekshiriladi. ✅ *bajarilgan (2400 kirish)*
5. Maxfiy kalit, plaintext va tokenlarning loglarda yo'qligini tekshirish.
   ✅ *bajarilgan*
6. **Mustaqil kriptografik dizayn auditi va implementatsiya auditi.**
   ⬜ *bajarilmagan*
7. **Formal verifikatsiya** — `INIT` va ratchet uchun Tamarin yoki ProVerif
   modeli. ⬜ *bajarilmagan*
8. **Constant-time va yon kanal tahlili**, zeroization tekshiruvi.
   ⬜ *bajarilmagan*
9. Versiyalararo migratsiya va algoritm almashtirish sinovi. ⬜ *bajarilmagan*

### 12.1. Taqiqlangan amaliyotlar

- nonce'ni tasodifiy taxmin qilish yoki bir kalit bilan qayta ishlatish;
- faqat shifrlash, autentifikatsiyasiz ishlatish;
- imzoni tekshirish xatosini e'tiborsiz qoldirish;
- home-made crypto yoki norasmiy ML-KEM/ML-DSA implementatsiyasi;
- xato sababi yoki javob vaqti orqali holatni oshkor qilish;
- serverdan kelgan ochiq kalitga verifikatsiyasiz ishonish;
- `MK` ni saqlab qo'yish (skipped kalitlardan tashqari, §6.5);
- kalit-majburiyat tegini o'tkazib yuborish.

---

## 13. Test vektorlari (KAT)

To'liq to'plam: **`kat/scutum-q1-kat.json`** — ushbu hujjatning normativ qismi.
Barcha kalitlar qat'iy urug'lardan chiqariladi, natija har ishga tushirishda bir xil.

```bash
python -m scutum.kat
```

Ikki qiymat tabiatan tasodifiy (`ML-KEM.Encaps` va `ML-DSA.Sign`); ular faylga
qotirilgan va `Decaps` / `Verify` orqali tekshiriladi. Ed25519 (RFC 8032)
deterministik, shuning uchun imzo to'g'ridan-to'g'ri solishtiriladi.

### 13.1. Nazorat qiymatlari

Quyidagilar to'liq to'plamdan olingan asosiy nazorat nuqtalari:

```text
# Identifikatsiya (§3.2)
fingerprint(A)  = b8690525f9cbe7568a734edb06e9c8797c43fc2fd7cc999424f3afd68829155b
fingerprint(B)  = 815740ff25b148d5803e771bc6950af655fe1f4e7350ee948c066fea707f8824

# Handshake (§5.2)
init_salt       = b84d836cc037999e58b7bbb36ceff3c4a7a3674d7a9b93a25e5ad73c4d0be0d8
transcript      = 63b85f75bbc18b52cfb051d1badc41d00a1e466b39b5eb47391bd5ea487e3ed3
RK0             = dc334d96e4805665c0f75bb5c8404d813d205f5f24f88a6cbbc9e1799797837e
                  f9c9e1244bd111d6e0af2e4f629328abf83cd6a2746feb0cc85fdd46a7899dd9

# Ratchet (§6.2)
KDF_RK -> RK1   = 67d0685d8f7e2767d698b125c78255961d7e73ae1a474929655653e7f7bcab22
                  62f8215ebad0ac2be0b13d27246eebdf1589ede44039be9fb6b0ebc7edb36978
KDF_RK -> CK0   = cecf84ed303a71327ac52f64db3e64336455efd27d02b4e3ac9a19d172a05aeb
KDF_CK -> MK0   = 9877c0baf0bc35f8b69ef42300531dbb666ba5f5b7baf3ca20bb064937ccc784
KDF_CK -> CK1   = 77246666b35109ec6f4708364604a6dd63102ceaebc6ac28e81f8c98d7be66a9
KDF_CK -> MK1   = 48d3c2df44a2c5161ef76cf625db1cd4c5217a2a9a38e49877453bc73c51e4df

# Xabar (§6.6) — plaintext "salom", no=0, direction=0x00
nonce           = 104e6c4c3df21db189709d52
wire uzunligi   = 227 bayt

# S-FILE (§7) — 145 bayt, chunk_size=64 -> 3 bo'lak
chunk_key_0     = 13c37690c833119864040a4481b0708b707511ecf09547be47c5c7adf1a8c658
nonce_0         = cd0308806f684097c79fd41b
leaf_0          = 03743c4fd8257541151ac4d6923b3173e0badbfe9dc8911884ca209a6ae93ac2
tree_root       = 5f3ea539f3a7b932b790fda28a6fb10df36709a4db346841e6c1e9a5caca64c5
root_hash       = 7ded0082b974f9eca7b38bb2599cbeefb08a360a642e865bf3e6abe0ffc34d20
meta_key        = ac62cff80ec84c1d04c202dcc05db264c770df9190577b2105f2a375240788b5
```

### 13.2. Domen ajratgichlari — to'liq ro'yxat

```text
SCUTUM-Q1/INIT           §5.2  init_salt
SCUTUM-Q1/transcript     §5.2  handshake transkripti
SCUTUM-Q1/init-id        §5.3  replay keshi kaliti
SCUTUM-Q1/RK             §6.2  KDF_RK
SCUTUM-Q1/MSG            —     v1.0 dagi buzilgan KDF_CK; v1.1 da ISHLATILMAYDI.
                               Referens implementatsiyada faqat v1.0 xatti-
                               harakatini qayta tiklash (SPEC rejimi) uchun saqlangan.
SCUTUM-Q1/commit         §4.5  kalit-majburiyat tegi
SCUTUM-Q1/prekey         §5.1  bundle imzosi
SCUTUM-Q1/fp             §3.2  device_fingerprint
SCUTUM-Q1/FILE/CHUNK     §7.1  chunk_key_i
SCUTUM-Q1/FILE/META      §7.5  meta_key va meta_nonce
```

Implementatsiya bu ro'yxatdan tashqari domen ajratgichini ishlatishi `MUST NOT`.
Referens implementatsiyada bu avtomatik test bilan qulflangan.

---

## 14. Ochiq masalalar

Quyidagilar v1.1 da **hal qilinmagan** va keyingi versiyaga qoldirilgan:

1. **Key transparency.** §3.2 qo'lda tasdiqlashga tayanadi. Server ochiq
   kalitlarni almashtirsa, buni faqat foydalanuvchi aniqlaydi. CONIKS/Parakeet
   uslubidagi append-only log kerak.
2. **Header encryption va padding** — §11 da tavsiya darajasida.
3. **Downgrade himoyasi** — `suite` AAD ichida, lekin muzokara transkripti yo'q;
   `Q2` chiqqanda pasaytirish hujumini kriptografik aniqlash mexanizmi kerak.
4. **Guruh sessiyalari** — hozircha faqat juftlik. MLS bilan integratsiya
   o'rganilishi kerak.
5. **Ko'p qurilmali sinxronizatsiya** — bir foydalanuvchining bir nechta
   qurilmasi o'rtasidagi holat almashinuvi ta'riflanmagan.
6. **Formal model** — §12 p.7.

---

## 15. Manbalar

- NIST, [FIPS 203: ML-KEM](https://csrc.nist.gov/pubs/fips/203/final)
- NIST, [FIPS 204: ML-DSA](https://csrc.nist.gov/pubs/fips/204/final)
- NIST, [FIPS 205: SLH-DSA](https://csrc.nist.gov/pubs/fips/205/final)
- IETF, [RFC 8949: CBOR](https://www.rfc-editor.org/rfc/rfc8949) — §4.2.1
- IETF, [RFC 8439: ChaCha20-Poly1305](https://www.rfc-editor.org/rfc/rfc8439)
- IETF, [RFC 5869: HKDF](https://www.rfc-editor.org/rfc/rfc5869)
- IETF, [RFC 7748: X25519](https://www.rfc-editor.org/rfc/rfc7748)
- IETF, [RFC 8032: Ed25519](https://www.rfc-editor.org/rfc/rfc8032)
- IETF, [RFC 6962: Certificate Transparency](https://www.rfc-editor.org/rfc/rfc6962) — Merkle qoidalari
- Signal, [The Double Ratchet Algorithm](https://signal.org/docs/specifications/doubleratchet/)
- Signal, [X3DH](https://signal.org/docs/specifications/x3dh/)
- Signal, [PQXDH](https://signal.org/docs/specifications/pqxdh/)
