# ROSTOR-1 — O'zbekistondagi kiberfiribgarlikka qarshi ishonch va tasdiqlash protokoli

**Holati:** loyiha spetsifikatsiyasi, tasdiqlashga taqdim etilgan (v1.0-draft)
**O'rnini bosadi:** loyihaning markaziy maqsadi sifatida — `SCUTUM-Q1` (`docs/SPEC-SCUTUM-Q1-v1.1.md`)
**Meros qatlam:** SCUTUM-Q1 v1.1 transport qatlami (identity/handshake/ratchet/AEAD/kanonik kodlash) **o'zgarishsiz** meros qilib olinadi — quyida §17 da aniq ko'rsatilgan
**Normativ so'zlar:** `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, `MAY` — RFC 2119 ma'nosida
**Muallif rollari:** kriptografik dizayn — ushbu hujjat; joriylashtirish — keyingi bosqich (foydalanuvchi tasdig'idan keyin)

> **Muhim eslatma.** Bu hujjat "toza" akademik kripto-mashq emas. Har bir bo'lim
> quyidagi tuzilishga amal qiladi: **hujum qanday ishlaydi → nega ishlaydi
> (tizimning qaysi bo'shlig'idan foydalanadi) → protokol qanday to'sadi →
> nima kafolatlanmaydi**. Agar biror mexanizm aniq bir hujum turini to'smasa,
> u ushbu spetsifikatsiyada **yo'q**.

---

## 0. Pivot bayonoti — nima va nega o'zgardi

`SCUTUM-Q1 v1.1` — texnik jihatdan to'g'ri, tuzatilgan post-kvant gibrid
xabar almashinuvi protokoli edi. Lekin u **noto'g'ri savolga** javob berardi:
"ikki halol tomon o'rtasida shifrlangan aloqani qanday tashkil qilamiz?"

O'zbekistonda haqiqatda sodir bo'layotgan zarar bu savoldan kelib chiqmaydi.
2026-yil 1-yarim yilligida Ichki Ishlar Vazirligi ma'lumotlariga ko'ra
(Gazeta.uz orqali) **9 282 kiberjinoyat** qayd etilgan, zarar **120+ milliard
so'm**, aniqlash darajasi **8% dan past**. Group-IB ma'lumotlariga ko'ra,
Telegram orqali tarqaladigan Android SMS-stealer oilasi **100 000+ qurilmani**
zararlagan.

Bu raqamlarning aksariyati **kriptografik protokolni buzish orqali emas**,
balki quyidagilar orqali yuzaga keladi:

- foydalanuvchini **ishontirish** (ijtimoiy muhandislik: qo'rqitish, shoshirish,
  ishonchni suiiste'mol qilish);
- **soxta shaxs** (bank, davlat idorasi, tanish odam) niqobi ostida harakat
  qilish;
- **tekshirib bo'lmaydigan** kanallar (SMS, telefon qo'ng'irog'i, sideload
  qilingan `.apk`) orqali aloqa qilish.

Demak, markaziy muammo — **maxfiylik emas, autentifikatsiya va ishonch**:
foydalanuvchi qabul qilgan xabar/qo'ng'iroq/dastur **haqiqatan da'vo qilingan
manbadan** kelayotganini qanday bilishi mumkin, tezkor, o'qitishsiz va
tushunarli tarzda?

**ROSTOR-1** shu savolga javob beradi. Post-kvant gibrid kriptografiya
(`X25519+ML-KEM-768`, `Ed25519+ML-DSA-65`) **vosita** sifatida saqlanadi —
bank va davlat ma'lumotlarining saqlanish gorizonti o'nlab yillarga cho'zilgani
uchun "hozir yig'ib, keyin ochish" (harvest-now-decrypt-later) xavfi haqiqiy —
lekin endi bu loyihaning **sarlavhasi emas**, balki transport qatlamining
muhandislik gigiyenasi.

### 0.1. Nomlash

**Protokol nomi: ROSTOR.** O'zbekcha "rost" (haqiqiy, chin) o'zagidan olingan,
lekin **lug'at so'zi emas** — bu ataylab qilingan tanlov. `SCUTUM` tajribasi
(auditda topilgan: bu so'z allaqachon xalqaro kiberxavfsizlik kompaniyasi
— Scutum Group, €327 mln aylanma — va npm'dagi OpenPGP vositasi tomonidan
band) shuni ko'rsatdiki, xavfsizlik metaforasi bo'lgan lug'at so'zlari
(qalqon, to'siq, minora) deyarli har doim band. O'ylab topilgan nom
(`Kyber`, `Dilithium`, `WireGuard`, `Noise` naqshi) savdo belgisi nuqtai
nazaridan eng kuchli himoyaga ega va band bo'lish ehtimoli kamroq.

- **Protokol/spetsifikatsiya identifikatori:** `ROSTOR-1`
- **Foydalanuvchiga ko'rinadigan UI matni:** lug'aviy va tavsifiy —
  `✓ Tasdiqlangan bank`, `✓ Rasmiy davlat xabari`, `⚠️ Tasdiqlanmagan manba`
  (bular savdo belgisi emas, oddiy tavsif — huquqiy xavf yo'q)
- Rasmiy chiqarishdan oldin `ROSTOR` nomi uchun ham xuddi shu tekshiruv
  (PyPI/npm/GitHub/domen/IACR/savdo belgisi) bajarilishi `SHOULD` — bu
  hujjat implementatsiya bosqichi emas, shuning uchun hozircha o'tkazilmadi.

---

## 1. Qo'llanish sohasi va maqsad

ROSTOR-1 uchta muammoni hal qiladi:

1. **Kim gapiryapti?** — xabar/qo'ng'iroq/dastur da'vo qilingan shaxsdan
   (bank, davlat idorasi, tanish odam, ma'lum dasturchi) kelganini
   kriptografik tarzda tasdiqlash.
2. **Nima tasdiqlanyapti?** — moliyaviy operatsiyani tasdiqlashda foydalanuvchi
   ko'rgan narsa bilan imzolangan narsa **aynan bir xil** bo'lishini
   kafolatlash (WYSIWYS — *What You See Is What You Sign*).
3. **Kim yolg'on gapirgan edi?** — firibgarlik haqidagi signallarni
   markazlashtirmasdan, o'chirib bo'lmaydigan tarzda to'plash va kelajakdagi
   tekshiruvlar uchun ishlatish.

### 1.1. Nimalar kafolatlanadi

- Institutsional xabarning (bank, davlat idorasi) kriptografik autentikligi;
- tranzaksiya tasdig'ining ko'rsatilgan ma'lumotga bog'langanligi (WYSIWYS);
- foydalanuvchi identitetining SIM-karta egaligidan mustaqilligi;
- dastur/`.apk` manbaining ochiq, o'zgartirib bo'lmaydigan reestrga
  tekshirilishi;
- firibgarlik signalining sensuraga chidamli to'planishi.

### 1.2. Nimalar kafolatlanmaydi (§16 da batafsil)

- ovozli qo'ng'iroqning o'zi (vishing) — faqat undan **keyingi** harakat
  (kod aytish, pul o'tkazish) protokol darajasida ma'nosiz qilinadi;
- karta raqamining o'zini "terib olish" fishingi — bu tokenizatsiya
  masalasi, ROSTOR doirasidan tashqarida;
- telekom operatorining ichki jarayonlari (SIM ko'chirish tartib-qoidasi) —
  ROSTOR faqat **oqibatni** (akkount egallanishini) oldini oladi;
- ROSTOR-integratsiyasiz xizmatlar — himoya faqat ROSTOR-mos institutsiyalar
  uchun ishlaydi (§18 joriylashtirish bosqichlari).

---

## 2. Tahdid modeli — 6 real vektor

Har bir vektor uchun: **qanday ishlaydi**, **nega ishlaydi** (tizimdagi qaysi
bo'shliqdan foydalanadi), va qisqacha **ROSTOR mexanizmiga havola** (to'liq
tavsif tegishli bo'limda).

### T1 — Telegram orqali tarqaladigan Android SMS-stealer/dropper

**Qanday ishlaydi.** Hujumchi o'g'irlangan yoki xarid qilingan Telegram
sessiyasidan foydalanib, qurbonning kontaktlariga ishonchli ko'rinadigan
nom bilan (`soliq.apk`, `MyGov_yangilanish.apk`, "bank ilovasi yangilanishi")
zararli `.apk` yuboradi. O'rnatilgach, dastur SMS/bildirishnoma ruxsatlarini
yoki Accessibility Service'ni so'raydi, OTP SMS va USSD balans/o'tkazma
so'rovlarini ushlab oladi, so'ng qurbonning o'z Telegram sessiyasini
egallab, **o'z-o'zini** uning kontaktlariga tarqatadi (qurt uslubidagi
tarqalish).

**Nega ishlaydi.**
- **Ijtimoiy ishonchning ko'chishi**: fayl "tanish odamdan" kelgani uning
  xavfsiz ekanligini anglatmaydi, lekin odamlar shunday qabul qiladi.
- Sideload qilingan `.apk` uchun **hech qanday nashriyotchi tekshiruvi**
  ko'rinmaydi — oddiy foydalanuvchi buni tekshira olmaydi.
- SMS/USSD — tekshirib bo'lmaydigan, oddiy matnli kanal; OTP raqamining
  o'zi hech qanday operatsiyaga kriptografik bog'lanmagan.

**Variatsiyalar:** soxta "IIV" ogohlantirish ilovasi, soxta koronavirus/
epidemiologik kuzatuv ilovasi, soxta "ish topish" ilovasi, soxta bank
"xavfsizlik yangilanishi".

**ROSTOR mexanizmi:** §9 (Nashriyotchi sertifikati), §11 (Shaffoflik
jurnali — zararli xesh reestri).

### T2 — Bank/to'lov fishingi + vishing orqali OTP so'rash

**Qanday ishlaydi.** (a) Foydalanuvchi Click/Payme/Uzcard-Humo interfeysini
aniq taqlid qiluvchi fishing sahifasiga havola oladi, karta ma'lumotlari va
OTP kiritadi. (b) Hujumchi "bankning xavfsizlik xizmati xodimi" sifatida
qo'ng'iroq qiladi, "shubhali operatsiyani bekor qilish uchun" SMS orqali
kelgan kodni **aytib berishni** so'raydi — aslida bu kod hujumchining O'ZI
boshlagan operatsiyani tasdiqlaydi.

**Nega ishlaydi.**
- 6 xonali OTP kod **hech qanday semantik ma'lumot tashimaydi** — foydalanuvchi
  "bu kod 350 000 so'mni X kartaga o'tkazishni tasdiqlaydi" deb ko'ra olmaydi,
  faqat raqamlarni ko'radi va telefon orqali unga nima qilish aytiladi.
- SMS jo'natuvchi ID'sini soxtalashtirish oddiy — istalgan SMS shlyuzi
  o'zini "Click" deb ko'rsata oladi.
- Fishing sahifalari vizual jihatdan haqiqiy interfeysni aniq nusxalaydi;
  oddiy foydalanuvchi domen/sertifikat farqini payqamaydi.

**ROSTOR mexanizmi:** §10 (Tasdiqlangan jo'natuvchi belgisi), §12
(Tranzaksiya tasdiqlash — **markaziy mexanizm**, kodni butunlay yo'q qiladi).

### T3 — Davlat xizmati/sud/militsiya nomidan qo'rqitish

**Qanday ishlaydi.** Soxta SMS/qo'ng'iroq/vebsayt (mygov.uz taqlidi) "sizga
qarshi jinoiy ish ochilgan", "hujjatlaringiz tasdiqlanishi kerak" kabi
qo'rqitish xabarini yetkazadi, shoshilinch harakat (havolani bosish,
to'lov qilish, shaxsiy ma'lumot berish) talab qiladi.

**Nega ishlaydi.**
- Real davlat xabari bilan soxtasi o'rtasida **hech qanday kriptografik
  farq yo'q** — ikkalasi ham bir xil SMS/qo'ng'iroq ko'rinishida keladi.
- **Qo'rqinch + shoshilish** ratsional tekshiruvni chetlab o'tadi;
  qurbonda tezkor, ishonchli tekshirish vositasi yo'q.

**ROSTOR mexanizmi:** §10 (institutsional belgi, davlat idoralariga ham
qo'llaniladi), §10.3 (ommaviy tezkor tekshiruv vositasi — "Tekshiruv").

### T4 — SIM swap / raqam ko'chirish orqali akkount egallash

**Qanday ishlaydi.** Hujumchi telekom operatori xodimini ijtimoiy
muhandislik yoki poraxo'rlik orqali qurbonning raqamini o'z SIM-kartasiga
"ko'chirishga" majbur qiladi. So'ng bank ilovasi, Telegram, elektron pochta
kabi SMS-OTP asosidagi "parolni tiklash" funksiyasidan foydalanib,
akkountlarni to'liq egallaydi.

**Nega ishlaydi.**
- Telefon raqami **identitetning o'zi emas** — u uchinchi tomon (telekom
  operatori) nazorat qiladigan resurs, va uning ko'chirish jarayoni
  hujumga ochiq.
- Ko'p xizmatlar SMS-OTP'ni **yagona** tiklash faktori sifatida ishlatadi:
  kim SMS quti egasi bo'lsa, akkount ham o'shaniki.

**ROSTOR mexanizmi:** §8 (identifikatsiya qurilma kalitiga bog'langan,
raqamga emas), §13 (Tiklash kvorumi).

### T5 — Classiscam-uslubidagi bozor firibgarligi (OLX va sh.k.)

**Qanday ishlaydi.** Hujumchi OLX'da xaridor yoki sotuvchi niqobida
muloqotni Telegram/WhatsApp'ga ko'chiradi, so'ng soxta "xavfsiz to'lov/
yetkazib berish" sahifasiga havola yuboradi. Qurbon "pul olish uchun
tasdiqlash kerak" deb o'ylab karta ma'lumotlarini kiritadi (aslida bu
pul YECHISH so'rovi) yoki mavjud bo'lmagan "yetkazib berish/kafolat"
uchun oldindan to'lov qiladi.

**Nega ishlaydi.**
- Haqiqiy va soxta to'lov havolasi o'rtasida kriptografik farq yo'q.
- Platformadan tashqi (off-platform) suhbatga ko'chish barcha platforma
  ishonch signallarini yo'qotadi.
- **Noto'g'ri tushuncha**: "pul olish uchun karta ma'lumotini kiritish
  kerak" — bu psixologik ekspluatatsiya, chunki pul qabul qilish
  HECH QACHON CVV/OTP talab qilmaydi.

**ROSTOR mexanizmi:** §10 (Tasdiqlangan to'lov shlyuzi reestri), §12.2
(Pul qabul qilish protokoli — bu psixologik xatoni protokol darajasida
imkonsiz qiladi).

### T6 — Soxta investitsiya/kripto/"oson pul" va ish e'lonlari

**Qanday ishlaydi.** Yuqori daromad va'da qiluvchi reklama/xabar, "cheklangan
joy", "kafolatlangan foyda" kabi shoshiltiruvchi uslubda, "ro'yxatdan o'tish
puli" yoki investitsiya kapitalini shaxsiy karta/hamyonga yuborishni so'raydi.
Biznesning o'zi mavjud emas.

**Nega ishlaydi.**
- Sxemaning haqiqiyligini mustaqil tekshirish imkoni yo'q — istalgan kim
  o'zini "investitsiya platformasi" deb da'vo qilishi mumkin.
- Qurbonlar alohida-alohida tekshiradi; sxema og'izdan-og'izga tarqaladigan
  ogohlantirishdan tezroq harakat qiladi.

**ROSTOR mexanizmi:** §14 (Firibgarlik haqida xabar berish va obro' tizimi).

---

## 3. Dizayn tamoyillari

Har bir tamoyil kamida bitta tahdid vektoriga to'g'ridan-to'g'ri bog'langan
— mavhum "eng yaxshi amaliyot" emas.

| # | Tamoyil | Bog'liq tahdid |
|---|---|---|
| **P1** | Identifikatsiya telefon raqamiga emas, apparat ichida saqlangan kriptografik kalitga bog'lanadi | T4 |
| **P2** | "Tasdiqlangan" belgisi faqat kriptografik tekshiruvdan keyin ko'rinadi; UI matni hech qachon mustaqil ishonch manbai bo'lmaydi | T2, T3 |
| **P3** | Muhim operatsiya og'zaki/matnli kod orqali emas, balki ko'rsatilgan strukturaviy ma'lumotni imzolash orqali tasdiqlanadi (WYSIWYS) | T2 (markaziy) |
| **P4** | Obro'/qora ro'yxat ma'lumoti markazlashtirilmagan, o'zgartirib (yashirib) bo'lmaydigan, ko'p tomonlama ko'zgulangan jurnalda saqlanadi | T1, T3, T5, T6 |
| **P5** | Pul qabul qilish oqimi hech qachon maxfiy ma'lumot (karta, CVV, OTP) so'ramaydi — bu **protokol invarianti**, konvensiya emas | T5 |
| **P6** | Server hech qachon ishonilmaydi; faqat kriptografik dalil ishonchli (SCUTUM-Q1 falsafasi meros) | barchasi |
| **P7** | Har bir yangi kriptografik konstruksiya faqat mavjud, tekshirilgan primitivlar ustida quriladi — yangi threshold-imzo yoki eksperimental sxema kiritilmaydi | barchasi |

---

## 4. Ishonch modeli va rollar

ROSTOR-1 klassik ikki tomonlama (Alisa-Bobur) modeldan farqli, **ko'p
rolli** ishonch tarmog'iga ega:

| Rol | Vazifa | Kalit turi |
|---|---|---|
| **Foydalanuvchi qurilmasi** | shaxsiy identitet egasi | DIK (SCUTUM-Q1 dan meros, §17) |
| **Institutsiya** (bank, davlat idorasi, telekom) | tranzaksiya/xabar imzolaydi | Institutsional Sertifikat (IC, §9) |
| **Nashriyotchi** (dastur ishlab chiquvchi) | `.apk`/dastur imzolaydi | Nashriyotchi Sertifikati (PC, §9) |
| **Registrator konsorsiumi** | IC/PC larni jurnalga qabul qiladi | k-of-n a'zolik (§4.1) |
| **Ko'zgu operatori** (mirror) | jurnalni mustaqil saqlaydi va tarqatadi | operator kaliti (§11.2) |
| **Auditor** | jurnal izchilligini tashqaridan tekshiradi | kalit talab qilinmaydi (faqat o'qish) |

### 4.1. Registrator konsorsiumi — "kim birinchi bo'lib ishonadi?" muammosi

Har qanday ishonch tizimida "ildiz ishonchi" (root of trust) muammosi bor:
kim birinchi marta "bu haqiqatan Click" deb tasdiqlaydi? ROSTOR-1 buni
**yagona markaziy sertifikat organi (CA)** orqali emas, balki **ko'p
tomonlama boshqaruv** orqali hal qiladi:

- Registrator konsorsiumi tarkibiga (taklif etiladi, yakuniy tarkib
  siyosat/huquqiy masala, ushbu hujjat doirasidan tashqarida): Markaziy
  bank, yirik telekom operatorlari, CERT.uz, yirik banklar vakillari kiradi.
- Yangi Institutsional Sertifikat jurnalga qo'shilishi uchun kamida **k ta**
  (masalan, 5 tadan 3 tasi) konsorsium a'zosining mustaqil imzosi kerak.
- **Nega threshold-imzo sxemasi (masalan FROST) emas, k-of-n alohida
  imzolar?** Chunki post-kvant threshold-imzo sxemalari hali yetarlicha
  tekshirilgan, ishlab chiqarishga tayyor kutubxonalarda mavjud emas (P7
  tamoyili). Shu sababli oddiyroq, allaqachon mavjud gibrid imzo
  primitividan foydalaniladi: har bir a'zo **o'z alohida** `HybridSign`
  imzosini qo'yadi, tekshiruvchi kamida `k` ta turli a'zodan haqiqiy imzo
  borligini tasdiqlaydi. Bu murakkabroq emas, faqat ko'proq bayt sarflaydi
  — ishlab chiqarishga tayyor bo'lish ustunroq.
- Konsorsium tarkibi va qarorlari ham **shaffoflik jurnalining o'zida**
  qayd etiladi (§11) — hech bir a'zo "tashqarida" harakat qila olmaydi.

---

## 5. Kriptografik profil

ROSTOR-1 SCUTUM-Q1 v1.1 `HARDENED` profilining primitivlarini **to'liq
meros** qiladi — yangi algoritm kiritilmaydi (P7):

| Vazifa | Algoritm | Manba |
|---|---|---|
| Klassik kalit kelishuvi | X25519 | SCUTUM-Q1 (o'zgarishsiz) |
| Post-kvant KEM | ML-KEM-768 | SCUTUM-Q1 (o'zgarishsiz) |
| Klassik imzo | Ed25519 | SCUTUM-Q1 (o'zgarishsiz) |
| Post-kvant imzo | ML-DSA-65 | SCUTUM-Q1 (o'zgarishsiz) |
| AEAD | ChaCha20-Poly1305 + kalit-majburiyat | SCUTUM-Q1 (o'zgarishsiz) |
| KDF | HKDF-SHA-512 | SCUTUM-Q1 (o'zgarishsiz) |
| Xesh | SHA3-256 | SCUTUM-Q1 (o'zgarishsiz) |
| Kanonik kodlash | RFC 8949 §4.2.1 CBOR | SCUTUM-Q1 (o'zgarishsiz) |
| Shaffoflik daraxti | Merkle (RFC 6962 uslubi) | SCUTUM-Q1 **kengaytirilgan** (§11.1) |

**Yagona yangi talab:** Merkle **izchillik isboti** (consistency proof) —
mavjud `merkle.py` faqat **kiritilganlik isboti** (inclusion proof) beradi.
Bu haqiqiy yangilik, §11.1 da batafsil asoslangan.

---

## 6. Umumiy paket qobig'i — meros va kengaytma

ROSTOR-1 obyektlari ikki toifaga bo'linadi:

1. **Shaxsiy xabarlar** — mavjud SCUTUM-Q1 `Envelope` orqali, mavjud
   Double Ratchet sessiyasi ichida yuboriladi (masalan, `TXN_CONFIRM`
   so'rovi — bank foydalanuvchiga shaxsiy sessiya orqali yuboradi).
2. **Ommaviy obyektlar** — Institutsional Sertifikat, jurnal yozuvlari,
   STH (Signed Tree Head). Bular **shifrlanmaydi** (ular davlat siri emas,
   aksincha — ommaga ochiq bo'lishi kerak) va shaxsiy sessiyadan tashqarida,
   ishonchsiz Katalog Xizmati orqali tarqatiladi.

> **Muhim arxitektura qarori:** ROSTOR-1 SCUTUM-Q1 transport `suite`
> qiymatini (`"SCUTUM-Q1"`) **o'zgartirmaydi**. AEAD/handshake/ratchet
> mexanikasi bayt darajasida bir xil qoladi — faqat `Envelope.type`
> maydoniga yangi qiymatlar qo'shiladi (§6.1) va yangi mustaqil obyektlar
> (IC, LogEntry, STH) ta'riflanadi, ular **o'z domen ajratgichlariga**
> ega (`ROSTOR-1/...`). Bu keraksiz wire-formatini buzuvchi versiyalashdan
> qochadi: transport allaqachon to'g'ri ishlayapti (SCUTUM-Q1 v1.1, 37/37
> test), uni qayta ochish xavf qo'shadi, foyda bermaydi.

### 6.1. Yangi Envelope turlari

```text
INSTITUTION_CERT_ANNOUNCE   — IC ni katalogga e'lon qilish (Registrator -> Log)
TXN_CONFIRM_REQUEST         — tranzaksiya tasdig'i so'rovi (Institutsiya -> Foydalanuvchi)
TXN_CONFIRM_RESPONSE        — foydalanuvchi javobi (Foydalanuvchi -> Institutsiya)
PAYMENT_INTENT              — pul qabul qilish so'rovi (Qabul qiluvchi -> To'lovchi)
FRAUD_REPORT                — firibgarlik signali (Foydalanuvchi -> Log)
RECOVERY_REQUEST            — qurilma tiklash so'rovi (Yangi qurilma -> Kvorum)
QUORUM_APPROVAL             — tiklashni tasdiqlash (Kvorum a'zosi -> Yangi qurilma)
```

---

## 7. Identifikatsiya — SIM-swap chidamliligi (T4 himoyasi)

### 7.1. Asosiy qoida

> **P1.** Foydalanuvchi identitetining yagona ildizi — SCUTUM-Q1 dan meros
> qilingan **DIK** (Device Identity Key), apparat himoyalangan saqlovda
> (StrongBox/Keystore/Secure Enclave/TPM) yaratiladigan va **hech qachon
> qurilmadan chiqmaydigan** kalit juftligi.

Telefon raqami **faqat qulaylik uchun** — dastlabki ro'yxatdan o'tishda
odamlar bir-birini topishi uchun (Signal uslubida) — ishlatilishi `MAY`,
lekin u:

- xavfsizlik-muhim operatsiyalar uchun qayta autentifikatsiya omili
  sifatida ishlatilishi `MUST NOT`;
- akkountni tiklashning **yagona** omili sifatida ishlatilishi `MUST NOT`.

### 7.2. Nega bu SIM swap'ni to'sadi

SIM swap hujumchiga **raqamni** beradi, lekin **DIK maxfiy kalitini
bermaydi** — u asl qurilmaning apparat himoyalangan saqlovida qoladi.
ROSTOR-mos xizmat uchun har qanday qiymatli operatsiya (tranzaksiya
tasdig'i, parolni tiklash) DIK bilan imzolangan javobni talab qiladi.
Natijada SIM swap "to'liq akkount egallash" dan "SMS'ni ko'rish, lekin
hech narsani imzolay olmaslik" holatiga tushiriladi — bu strukturaviy
neytrallashtirish, oqibatni cheklaydi, kirish nuqtasining o'zini yo'q
qilmaydi (telekom jarayoni ROSTOR nazorati tashqarisida — §1.2).

---

## 8. Shaffoflik jurnali (Transparency Log)

Bu — T1, T3, T5, T6 uchun **umumiy infratuzilma**: kim tasdiqlangan, kim
zararli deb belgilangan, degan savolga bitta, markazlashtirilmagan
ishonchli javob manbai.

### 8.1. Nega Merkle transparency, oddiy qora-ro'yxat API emas

Oddiy markazlashtirilgan "zararli xeshlar" API'si ikki yo'l bilan
buzilishi mumkin: (a) hujumchi serverni buzib, zararli yozuvni **yashirsa**,
hech kim buni bilmaydi; (b) hujumchi (yoki noto'g'ri niyatli operator)
raqobatchi/halol dasturni **noto'g'ri bloklasa**, buni ham hech kim
tekshira olmaydi. Ikkala holat ham **sezilmasdan** sodir bo'ladi, chunki
oddiy API o'zining tarixini isbotlamaydi.

Merkle append-only jurnal (Certificate Transparency, RFC 6962 uslubida)
bu ikkalasini ham **isbotlab bo'ladigan** qiladi: har bir yangi holat
(Signed Tree Head) oldingi holatning **kengaytmasi** ekanligini kriptografik
isbotlash mumkin (consistency proof). Yozuvni yashirish yoki o'chirish —
jurnal tuzilishini buzadi va istalgan auditor buni aniqlaydi.

### 8.2. Tuzilma

Mavjud `scutum/protocol/merkle.py` (HARDENED, RFC 6962 domen ajratish
bilan) **to'g'ridan-to'g'ri qayta ishlatiladi**:

```text
leaf_i    = SHA3-256( 0x00 || uint64be(seq) || canonical(LogEntry_i) )
node(L,R) = SHA3-256( 0x01 || L || R )
root      = SHA3-256( 0x02 || uint64be(tree_size) || tree_root )
```

```text
LogEntry = {
  v:            1,
  seq:          uint64,     // qat'iy o'suvchi, uzilishsiz
  type:         tstr,       // "institution" | "publisher" | "malicious_hash"
                             // | "payment_gateway" | "fraud_report"
                             // | "rebuttal" | "revocation"
  payload:      bytes,      // turga bog'liq kanonik tuzilma
  submitted_at: uint64,
  submitter_id: bytes[16],
  submitter_sig: HybridSignature
}
```

```text
STH (Signed Tree Head) = {
  tree_size:   uint64,
  root_hash:   bytes[32],
  timestamp:   uint64,
  operator_id: bytes[16],
  operator_sig: HybridSignature
}
```

### 8.3. Yangi kriptografik komponent: izchillik isboti (consistency proof)

Mavjud `merkle.py` faqat **inclusion proof** beradi ("bu barg shu ildizga
tegishli"). Jurnal uchun bundan ko'ra muhimi — **consistency proof**
("`tree_size=N1` bo'lgan eski ildiz `tree_size=N2 > N1` bo'lgan yangi
ildizning **faqat qo'shimchasi**, hech narsa o'chirilmagan yoki
o'zgartirilmagan"). Bu RFC 6962 §2.1.2 algoritmi asosida qo'shiladi —
mavjud daraxt qurilish qoidalarini o'zgartirmaydi, faqat ikki daraxt
holatini solishtiruvchi yangi funksiya.

**Bu implementatsiya bosqichida qo'shiladigan yagona yangi kriptografik
primitiv** — qolgan hamma narsa mavjud primitivlarning qayta tashkil
etilishi.

### 8.4. Ko'zgu operatorlari va gossip

Bitta jurnal operatori ham nazoratni suiiste'mol qilishi mumkin (masalan,
ikki xil foydalanuvchiga ikki xil "haqiqat" ko'rsatib — split-view hujumi).
Buning oldini olish uchun:

- Jurnal kamida **3 ta mustaqil ko'zgu operatori** (masalan: bitta bank
  konsorsiumi, CERT.uz, mustaqil fuqarolik tashkiloti) tomonidan
  parallel saqlanishi `SHOULD`;
- Klientlar davriy ravishda turli ko'zgulardan olingan STH larni
  solishtirishi (**gossip protokoli**) `SHOULD` — nomuvofiqlik topilsa,
  bu **isbotlanadigan** split-view hujumi hisoblanadi va ochiq e'lon
  qilinishi `MUST`.

### 8.5. Maxfiylik: prefiks-asosidagi qidiruv

Jurnalda telefon raqami/karta xeshi kabi maqsad qiymatlari saqlanishi
(§14) **so'rovchining maxfiyligini** buzmasligi kerak — agar foydalanuvchi
"bu raqam firibgarmi?" deb so'rasa, log operatori "kim, qaysi raqamni
tekshirmoqda" degan bog'lanishni bilmasligi kerak.

```text
target_hash = SHA3-256( "ROSTOR-1/report-target" || target_type || normalized_value )
```

Bu funksiya **ochiq va oshkor** — maxfiylik xeshning o'zida emas (target
qiymat allaqachon sir emas), balki **so'rov usulida**: klient serverdan
to'liq `target_hash` emas, balki uning **prefiksini** (masalan, dastlabki
20 bit, ~1 million chelak) so'raydi, prefiksga mos keluvchi barcha
nomzodlarni oladi va **aniq mosligini mahalliy ravishda** tekshiradi
(Google Safe Browsing / HaveIBeenPwned k-anonimlik naqshi). Server hech
qachon aniq qaysi qiymat so'ralganini bilmaydi.

---

## 9. Nashriyotchi sertifikati va Institutsional sertifikat

Ikkalasi ham bir xil tuzilishning variantlari — DC (Device Certificate,
SCUTUM-Q1 §3.1) ning institutsional versiyasi:

```text
InstitutionCertificate (IC) = {
  v:              1,
  institution_id: bytes[16],
  category:       tstr,   // "bank" | "government" | "marketplace"
                           // | "telecom" | "software_publisher"
  display_name:   tstr,   // <=64 UTF-8 bayt, foydalanuvchiga ko'rinadi
  x25519_pk:      bytes[32],
  ed25519_pk:     bytes[32],
  mldsa65_pk:     bytes[1952],
  registered_at:  uint64,
  expires_at:     uint64,
  revoked_at:     uint64 / null
}

RegistrarApproval = {
  ic_hash:   SHA3-256( canonical(IC) ),
  approvals: [ { registrar_id: bytes[16], sig: HybridSignature }, ... ]
             // kamida k ta TURLI registrator_id kerak (§4.1)
}
```

`PublisherCertificate` (PC) — xuddi shu tuzilma, `category = "software_publisher"`,
qo'shimcha maydon: `known_apk_hashes: [bytes[32]]` (ixtiyoriy, nashriyotchi
tomonidan e'lon qilingan rasmiy `.apk` xeshlari ro'yxati).

Nashriyotchi/institutsiya sertifikati **jurnalga** e'lon qilinadi (§8),
shaxsiy sessiya orqali emas — bu **ommaviy** ma'lumot.

---

## 10. Tasdiqlangan jo'natuvchi belgisi (T2, T3 himoyasi)

### 10.1. Belgi hosil qilish algoritmi

UI'da ko'rinadigan `✓ Tasdiqlangan` belgisi — **deterministik, auditga
ochiq funksiya natijasi**, hech qachon serverning o'z hukmiga tayanmaydi:

```text
derive_badge(message, log_snapshot):
    if message.institution_sig NOT present:
        return UNVERIFIED

    ic = log_snapshot.lookup_institution(message.institution_id)
    if ic is None:
        return UNVERIFIED

    if ic.revoked_at is not None and now >= ic.revoked_at:
        return REVOKED

    if NOT HybridVerify(ic.ed25519_pk, ic.mldsa65_pk,
                        message.sig, message.signed_payload):
        return INVALID_SIGNATURE       // hech qachon neytral ko'rsatilmaydi

    if log_snapshot.malicious_registry.contains(message.sender_hash):
        return KNOWN_MALICIOUS

    if log_snapshot.fraud_score(ic.institution_id) >= FLAG_THRESHOLD:
        return FLAGGED

    return VERIFIED(ic.display_name, ic.category)
```

**Nega bu fishingni to'sadi:** fishing manba **hech qachon** haqiqiy
`institution_id` ga mos `ed25519_sk`/`mldsa65_sk` maxfiy kalitlarini ega
bo'la olmaydi (ular institutsiyaning apparat himoyalangan saqlovida).
Demak, imzoni soxtalashtira olmaydi — `HybridVerify` doim yiqiladi, belgi
hech qachon `VERIFIED` bo'lmaydi. Bu — "fishing manba hech qachon bunday
belgi ololmaydi" talabining aniq bajarilishi, taxmin emas.

### 10.2. Institutsional xabar

```text
InstitutionMessage = {
  v: 1,
  institution_id: bytes[16],
  body: tstr,               // erkin matn, LEKIN §12 dagi WYSIWYS qoidasi
                             // bilan cheklangan turlar uchun (TXN_CONFIRM
                             // kabi) alohida strukturaviy maydonlar bo'ladi
  sent_at: uint64,
  sig: HybridSignature       // AAD = canonical(barcha maydonlar sig'siz)
}
```

### 10.3. "Tekshiruv" — ommaviy tezkor tekshiruv vositasi (T3 uchun)

Vishing/qo'rqitish qo'ng'irog'i paytida qurbonga **darhol, o'qitishsiz**
ishlatiladigan tekshiruv vositasi kerak. ROSTOR-1 quyidagini talab qiladi:

- alohida ilova/vebsahifa shaklida, hisob yaratishni talab qilmasdan;
- foydalanuvchi telefon raqami yoki institutsiya nomini kiritadi;
- javob: "`<institutsiya>` ROSTOR tizimida ro'yxatdan o'tganmi? HA/YO'Q" —
  §8.5 dagi maxfiy prefiks-qidiruv orqali;
- javob **2 soniyadan tez** kelishi `SHOULD` — bu qo'ng'iroq davomida
  ishlatilishi mumkin bo'lgan yagona amaliy chegara.

---

## 11. Tranzaksiya tasdiqlash protokoli — markaziy anti-vishing mexanizmi

Bu — T2 uchun **eng muhim** mexanizm, chunki u vishing ssenariysini
so'zning to'g'ri ma'nosida **imkonsiz** qiladi, kamaytirmaydi.

### 11.1. Muammo: OTP kodning semantik bo'shligi

An'anaviy OTP oqimida foydalanuvchi ko'radigan narsa — 6 xonali raqam.
Hujumchi telefon orqali "kodni ayting" desa, foydalanuvchi rozi bo'lishi
mumkin, chunki kod **hech narsani anglatmaydi** — u qaysi summani, qaysi
qabul qiluvchini tasdiqlashini ko'rsatmaydi.

### 11.2. Yechim: tuzilgan, ko'rsatiladigan ma'lumotni imzolash

```text
TxnConfirmRequest = {
  v:                1,
  txn_id:           bytes[16],
  institution_id:   bytes[16],
  amount_minor:     uint64,     // eng kichik pul birligida (tiyin)
  currency:         tstr,       // "UZS"
  recipient_masked: tstr,       // masalan "****1234"
  purpose:          tstr,
  expires_at:       uint64,     // qisqa TTL, tavsiya: 120 soniya
  institution_sig:  HybridSignature
                     // AAD = canonical(barcha maydonlar sig'dan tashqari)
}

TxnConfirmResponse = {
  v:         1,
  txn_id:    bytes[16],
  decision:  tstr,              // "APPROVE" | "DENY"
  device_sig: HybridSignature
              // AAD = txn_id || decision || amount_minor || recipient_masked
}
```

Foydalanuvchi ekranda ko'radi: **"Bank XYZ: 350 000 so'mni \*\*\*\*1234
kartaga o'tkazishni TASDIQLAYSIZMI?"** — `✓ Tasdiqlangan bank` belgisi
bilan (§10.1). Tasdiqlash — bitta tegish/biometrik amal, natijada DIK
bilan imzolangan javob yuboriladi.

**Muhim: bu oqimda aytiladigan/yoziladigan "kod" umuman yo'q.** Bank
tomonidan "kodni ayting" so'ralishi **strukturaviy jihatdan mumkin emas**
— chunki tasdiqlash uchun mo'ljallangan hech qanday alohida kod yaratilmaydi.
Bu ommaviy xabardorlik uchun sodda, ishonchli qoidaga aylanadi:

> **"Bank sizdan hech qachon kod SO'RAMAYDI. Agar so'rasa — bu firibgar."**

### 11.3. WYSIWYS — ekranda ko'rilgan aynan imzolangan narsa

Klient **faqat** `TxnConfirmRequest` ning tekshirilgan, dekodlangan
maydonlaridan (`amount_minor`, `currency`, `recipient_masked`, `purpose`)
render qilishi `MUST` — alohida, imzo tekshiruvidan tashqarida qolgan
"ko'rinadigan matn" maydonidan **hech qachon** emas. Bu klassik hujumni
to'sadi: server/vositachi "displey matni" bitta narsa, imzolangan
struktura boshqa narsa bo'lgan paketni yuborishi.

`TxnConfirmRequest` sxemasida "displey matni" uchun alohida, imzodan
tashqari maydon **umuman yo'q** — bu ataylab qilingan: WYSIWYS xatosi
konvensiya bilan emas, sxema darajasida oldini olinadi.

### 11.4. Replay va relay himoyasi

- `txn_id` har bir tranzaksiya uchun yagona `MUST`, `TxnConfirmResponse`
  o'z `txn_id` sini AAD ichida takrorlaydi — noto'g'ri tranzaksiyaga
  "ha" javobini biriktirib bo'lmaydi.
- `expires_at` qisqa TTL — eski so'rovni keyinroq qayta ishlatib bo'lmaydi.
- Agar hujumchi kichik, zararsiz ko'rinadigan tranzaksiya (masalan, 1000
  so'm) so'rovini ko'rsatib, aslida katta summa uchun imzo olishni
  so'rasa (klassik "chalkashtirish" hiylasi) — bu §11.3 WYSIWYS qoidasi
  bilan imkonsiz, chunki ko'rsatilgan summa va imzolanadigan summa
  bitta maydon.

---

## 12. Pul qabul qilish protokoli (T5 himoyasi)

### 12.1. Muammo

Classiscam qurbonlari ko'pincha "pul olish uchun" karta ma'lumotini
kiritadi — bu psixologik chalkashlik: haqiqatda pul qabul qilish uchun
CVV/OTP **hech qachon** kerak emas, lekin bu tushunarli emas.

### 12.2. Yechim — protokol darajasidagi invariant

```text
PaymentIntent = {
  v:            1,
  intent_id:    bytes[16],
  payee_token:  bytes[32],    // DIK-bog'langan, MAXFIY EMAS identifikator
  amount_minor: uint64 / null,
  memo:         tstr,
  expires_at:   uint64
}
```

> **Invariant (MUST):** `PaymentIntent` sxemasida karta raqami, CVV yoki
> OTP kabi maydon **mavjud emas** — bu konvensiya emas, sxemaning o'zi.
> Klient `PaymentIntent` deb belgilangan, lekin sxemada yo'q qo'shimcha
> maydonni (masalan, `"karta_raqami"`) o'z ichiga olgan xabarni **rad
> etishi va foydalanuvchiga ochiq ogohlantirish ko'rsatishi** `MUST`:
> *"Bu so'rov pul olish uchun kerak bo'lmagan ma'lumot so'ramoqda —
> ehtimol firibgarlik."*

`payee_token` — maxfiy emas, faqat qabul qiluvchini bildiruvchi
identifikator (xuddi bank hisob raqami kabi ochiq bo'lishi mumkin) —
uni bilish hech qanday operatsiyani ruxsatsiz bajarishga imkon bermaydi.

### 12.3. Tasdiqlangan to'lov shlyuzi reestri

Har qanday to'lov havolasi/QR-kod (§8 jurnalidagi alohida `payment_gateway`
turi orqali) faqat rasmiy ro'yxatdagi domenlarga (Click, Payme, Uzcard-Humo
rasmiy shlyuzlari) tegishli bo'lsa `✓ Tasdiqlangan to'lov havolasi`
ko'rsatiladi; aks holda `⚠️ Tasdiqlanmagan to'lov havolasi`.

---

## 13. Tiklash kvorumi (T4 chuqurlashtirish)

SIM yo'qolishi/almashtirilishi **halol** holatlarda ham sodir bo'ladi —
foydalanuvchi haqiqatan yangi qurilma sotib olishi mumkin. ROSTOR-1
buni SMS-OTP'siz, lekin qulay hal qiladi:

```text
RecoveryRequest = {
  v:            1,
  new_device_dc: DC,          // yangi qurilmaning SCUTUM-Q1 uslubidagi DC'i
  account_id:    bytes[16],
  requested_at:  uint64,
  method:        tstr         // "existing_device_cosign" | "institutional_quorum"
}

QuorumApproval = {
  approver_id:   bytes[16],   // mavjud ishonchli qurilma yoki institutsiya vakili
  approval_sig:  HybridSignature   // AAD = canonical(RecoveryRequest)
}
```

- **`existing_device_cosign`**: foydalanuvchining boshqa, hali ishonchli
  qurilmasi (masalan, planshet) yangi qurilmani QR-kod orqali
  ko'rib-tasdiqlaydi — Signal uslubidagi qurilma bog'lash.
- **`institutional_quorum`**: barcha qurilmalar yo'qolganda, xizmat
  siyosati bo'yicha belgilangan `k`-dan-`n` kvorum (masalan, bank filiali
  biometrik tekshiruvi + davlat eID) talab qilinadi.
- **`MUST NOT`**: faqat SMS-OTP asosidagi tiklash, yuqori qiymatli
  ROSTOR-mos xizmatlar uchun.
- Tiklash so'rovi haqida foydalanuvchining **boshqa** faol kanallariga
  (agar mavjud bo'lsa) xabar berilishi `SHOULD` — bu qurbonga
  anomaliyani ko'rish va bekor qilish imkonini beradi.

---

## 14. Firibgarlik haqida xabar berish va obro' tizimi (T6, + hammasi)

### 14.1. Signal tuzilmasi

```text
FraudReport = {
  v:                 1,
  report_id:         bytes[16],
  target_type:       tstr,   // "phone" | "card_hash" | "wallet" | "domain"
                              // | "apk_hash" | "institution_id"
  target_value_hash: bytes[32],   // §8.5 dagi ochiq funksiya
  category:          tstr,   // "T1".."T6"
  evidence_hash:     bytes[32] / null,   // dalilning O'ZI emas, faqat xeshi
  reporter_proof:    ReporterProof,
  submitted_at:      uint64,
  reporter_sig:      HybridSignature
}
```

### 14.2. Suiiste'mol qilishga qarshi — bu eng nozik qism

Ochiq xabar berish tizimi ikki tomonlama xavf tug'diradi: (a) haqiqiy
firibgarlar aniqlanmay qoladi, agar chegara juda yuqori bo'lsa; (b) halol
biznes/shaxs **soxta hisobotlar bilan qoralanishi** mumkin, agar chegara
juda past bo'lsa. ROSTOR-1 buni ikki bosqichli mexanizm bilan hal qiladi:

**1) Signal, hukm emas.** Bitta `FraudReport` — faqat xom signal, avtomatik
"tasdiqlangan firibgar" degani emas.

**2) Og'irlik va chegara:**

```text
weight(report) = base_weight * (interaction_verified ? 3 : 1)

score = sum(weight(r) for r in reports
            where r.reporter_id DISTINCT
            and r.submitted_at within trailing_90_days)

FLAGGED  ⟺  score >= SCORE_THRESHOLD  AND  distinct_reporters >= MIN_K
```

`interaction_verified` — hisobot beruvchi maqsad bilan haqiqiy ROSTOR-mos
tranzaksiya/sessiyaga ega bo'lganini isbotlaydi (yuqori og'irlik);
aks holda past og'irlikdagi anonim signal sifatida hisoblanadi. Ikkala
shart (`score` VA `distinct_reporters`) birgalikda talab qilinadi — bitta
yuqori og'irlikdagi hisobot yagona o'zi hech kimni belgilay olmaydi.

**3) Rad javobi (rebuttal) — jurnalda, o'chirish emas.** Belgilangan
maqsad (agar Institutsional/Nashriyotchi sertifikatga ega bo'lsa, yoki
domen/raqam nazoratini tashqi kanalda isbotlasa) imzolangan rad javobini
yuborishi mumkin — bu **yangi jurnal yozuvi** sifatida qo'shiladi,
asl hisobotlarni **hech qachon o'chirmaydi**, lekin har qanday tekshiruv
vositasida ular yonma-yon ko'rsatiladi. Bu Certificate Transparency'dagi
kabi — jurnal hech qachon "hukm chiqarmaydi", faqat **tekshirib
bo'ladigan tarixni** taqdim etadi; yakuniy baho tashqi auditorlar,
jurnalistlar, CERT.uz tomonidan chiqariladi.

### 14.3. Sybil-qarshilik — halol chegara

To'liq Sybil-qarshilik (bitta shaxs ko'plab soxta "mustaqil" hisobotchi
sifatida ko'rina olmasligi) qat'iy talab qilinsa, real dunyoda tasdiqlangan
noyob shaxsga bog'lash kerak bo'ladi (masalan, telekomlarning real-ism SIM
ro'yxatidan foydalanuvchi ID'sini oshkor qilmasdan tasdiqlovchi ko'r imzo/
anonim hisobot sxemasi). Bu — **kelajakdagi versiya uchun ochiq masala**
(§20), chunki u qo'shimcha huquqiy va institutsional integratsiya talab
qiladi. v1.0 uchun oraliq yechim: DIK-asoslangan tezlik cheklash
(rate-limiting) + `interaction_verified` og'irligi — to'liq emas, lekin
amaliy va halol tan olingan cheklov.

---

## 15. Dastur/`.apk` kelib chiqishi (T1 himoyasi)

### 15.1. Tekshiruv oqimi

Foydalanuvchi `.apk` qabul qilganda (Telegram, boshqa kanal orqali),
"Tekshiruv" vositasi (§10.3, umumiy infratuzilma) yoki kelajakda OS
darajasidagi integratsiya (§18 Bosqich 3):

1. Fayl SHA3-256 xeshi hisoblanadi (lokal, faylning o'zi yuborilmaydi —
   faqat xesh);
2. §8.5 prefiks-qidiruv orqali jurnalda tekshiriladi:
   - **`malicious_hash` reestrida topilsa** → `❌ Bu fayl ZARARLI deb
     tasdiqlangan. O'RNATMANG VA TARQATMANG.` (qattiq blok, o'tkazib
     yuborib bo'lmaydi);
   - **Nashriyotchi Sertifikati orqali imzolangan bo'lsa** (`known_apk_hashes`
     ro'yxatida yoki APK imzosi PC ga mos kelsa) → `✓ Tasdiqlangan
     nashriyotchi: <nom>`;
   - **na yaxshi, na yomon ro'yxatda bo'lsa** (aksariyat holat) →
     neytral, lekin ehtiyotkor ogohlantirish: `⚠️ Noma'lum manba —
     tekshirilmagan dastur. O'rnatishdan oldin ehtiyot bo'ling.`

### 15.2. Chegara — halol tan olish

Bu mexanizm faqat ROSTOR "Tekshiruv" vositasidan **faol foydalanilganda**
ishlaydi; u Telegram yoki Android'ning o'zini o'zgartirmaydi. To'liq
samaradorlik uchun OS darajasidagi integratsiya kerak (§18 Bosqich 3).
v1.0 uchun bu — qo'lda ishga tushiriladigan, lekin tez (bir necha soniya)
tekshiruv vositasi, kelajakda avtomatlashtiriladi.

### 15.3. Qurt uslubidagi o'z-o'zini tarqatishga qarshi

Agar zararli dastur Telegram sessiyasini egallab, o'zini kontaktlarga
yuborsa — bu hujum ROSTOR ekotizimidan **tashqarida** sodir bo'ladi
(Telegram ROSTOR-integratsiyalanmagan). ROSTOR faqat **qabul qiluvchi**
tomonda himoya beradi (§15.1 tekshiruvi orqali). Agar kelajakda banklar/
davlat channels ROSTOR-mos rasmiy tarqatish kanali orqali ishlasa (masalan,
"Bank ilovasi faqat ROSTOR-tasdiqlangan havoladan yuklab olinadi" siyosati),
bu hujum yuzasi butunlay kamayadi — lekin bu ekotizim qabul qilish
masalasi, sof kriptografiya emas.

---

## 16. Nima kafolatlanmaydi — chegaralar

Halollik SCUTUM-Q1 v1.1 an'anasi (Y-3 Merkle topilmasi "STRUCTURAL, BROKEN
emas" deb qayta baholangani kabi) shu yerda ham davom etadi:

| Chegara | Sabab |
|---|---|
| Ovozli qo'ng'iroqning o'zi to'silmaydi | ROSTOR faqat undan **keyingi** kriptografik operatsiyani himoyalaydi; qo'ng'iroqning o'zi hali ham amalga oshadi |
| Karta raqamining "terib olinishi" (raw PAN phishing) | Bu tokenizatsiya/PCI-DSS masalasi, ROSTOR transport/tasdiqlash protokoli, karta tarmog'i emas |
| Telekom SIM-almashtirish jarayonining o'zi | ROSTOR faqat **oqibatni** (akkount egallashni) neytrallaydi, jarayonni o'zgartirmaydi |
| ROSTOR-integratsiyasiz xizmatlar | Himoya faqat ROSTOR-mos institutsiyalar uchun; boshqa barcha joyda foydalanuvchi hali ham himoyasiz |
| To'liq Sybil-qarshilik firibgarlik hisobotlarida | v1.0 da faqat qisman (DIK rate-limit); to'liq yechim huquqiy/institutsional integratsiya talab qiladi (§20) |
| Zararli `.apk` ni **oldindan**, tarqalishdan oldin aniqlash | Jurnal faqat **ma'lum bo'lgan** xeshlarni bloklaydi; nol-kunlik (zero-day) zararli dastur birinchi qurbonlarni zararlagunga qadar noma'lum bo'lib qoladi |
| Insayder tahdidi (registrator konsorsiumi a'zosi) | k-of-n chegara buni qiyinlashtiradi, lekin butun konsorsium buzilsa (k tadan ko'p a'zo), nazariy jihatdan soxta institutsiya tasdiqlanishi mumkin — bu boshqaruv masalasi, kriptografiya emas |
| Endpoint (qurilma) buzilishi | SCUTUM-Q1 §1.2 dan meros — zararli klient DIK ni suiiste'mol qilishi mumkin, bu OS xavfsizligi doirasida |

---

## 17. SCUTUM-Q1 bilan munosabat va kod qayta ishlatish xaritasi

**Faqat rejalashtirish uchun — bu bo'lim kodni o'zgartirmaydi, implementatsiya
bosqichida yo'l xaritasi vazifasini bajaradi.**

| Modul | Holat | Izoh |
|---|---|---|
| `crypto/primitives.py` | **to'liq qayta ishlatiladi** | X25519/Ed25519/ML-KEM/ML-DSA/AEAD/HKDF — o'zgarishsiz |
| `crypto/canonical.py` | **to'liq qayta ishlatiladi** | RFC 8949 kanonik CBOR — o'zgarishsiz |
| `protocol/identity.py` | **qayta ishlatiladi + kengaytiriladi** | `DeviceKeys`/`DC` asos bo'ladi; `InstitutionCertificate`/`PublisherCertificate` shu naqsh asosida qo'shiladi |
| `protocol/envelope.py` | **qayta ishlatiladi** | `MsgType` ga §6.1 dagi yangi turlar qo'shiladi |
| `protocol/handshake.py`, `ratchet.py` | **o'zgarishsiz meros** | Shaxsiy sessiyalar (masalan TXN_CONFIRM yetkazish) uchun transport |
| `protocol/merkle.py` | **kengaytiriladi** | Mavjud inclusion proof qoladi; **consistency proof yangi qo'shiladi** (§8.3) |
| `protocol/sfile.py` | **ixtiyoriy, saqlanadi** | Fayl almashinuvi kelajakda (masalan dalil biriktirmalari) kerak bo'lishi mumkin, lekin markaziy emas |
| `sim/server.py` | **kengaytiriladi** | `UntrustedServer` ga Katalog/Jurnal mirror rolini qo'shish — server hamon ishonilmaydi, faqat yangi ma'lumot turini tarqatadi |
| `sim/attacks.py` | **katta qism yangi yoziladi** | T1-T6 ssenariylari HIMOYASIZ⇄HIMOYALANGAN tarzda; mavjud hujum naqshi (har biri haqiqatan ijro etiladi, natija oldindan yozilmagan) saqlanadi |
| `sim/world.py` | **kengaytiriladi** | Alisa/Bobur/Mallory'dan tashqari: Bank, DavlatIdorasi, Firibgar, RegistratorKonsorsiumi rollari qo'shiladi |
| `selftest.py` + `kat.py` | **kengaytiriladi** | Yangi modul uchun testlar va KAT vektorlari, mavjud naqsh bo'yicha |
| GUI (`gui/panels/`) | **yangi panellar qo'shiladi** | Overview/Devices/Session/Ratchet/S-FILE/Attacks/Inspector/Tests saqlanadi; yangi: Institutsiyalar, Tranzaksiya-tasdiqlash, Jurnal-inspektori, Firibgarlik-hisoboti |

**Umumiy tamoyil:** hech narsa **buzilmaydi** — SCUTUM-Q1 v1.1 ning 37/37
testi implementatsiya bosqichida ham o'tishi kerak. ROSTOR-1 **qo'shimcha
qatlam**, o'rniga o'tuvchi almashtirish emas.

---

## 18. Joriylashtirish bosqichlari

Real dunyoda joriy etish bir martalik "yoq/o'chir" emas — bosqichma-bosqich:

**Bosqich 1 — Institutsiya SDK (eng past to'siq).** Har bir bank/davlat
idorasi o'z ilovasiga ROSTOR SDK qo'shadi: ilova-ichi bildirishnomalar
`✓ Tasdiqlangan` belgisi bilan, `TXN_CONFIRM` oqimi SMS-OTP o'rnini
bosadi. Telekom yoki OS o'zgarishi talab qilinmaydi — har bir institutsiya
mustaqil qaror qabul qilishi mumkin.

**Bosqich 2 — Telekom integratsiyasi.** Alifbo-raqamli SMS jo'natuvchi
ID'lar operatorlar tomonidan faqat ro'yxatdan o'tgan, ROSTOR-tasdiqlangan
institutsiyalarga beriladi — SMS darajasida ham spoofing qiyinlashadi.
Bu regulyator + operator hamkorligini talab qiladi.

**Bosqich 3 — OS darajasidagi integratsiya.** Android bildirishnoma
API'siga kengaytma yoki tizim darajasidagi "Tekshiruv" xizmati — har
qanday ilova, hattoki ROSTOR haqida bilmagan ilova ham, kiruvchi
`.apk`/havolani avtomatik tekshirishi mumkin.

Har bir bosqich avvalgisiga bog'liq emas — ROSTOR foydali bo'lishi uchun
darhol barcha uch bosqich kerak emas, hatto faqat Bosqich 1 (bir nechta
yirik bank + mygov.uz) ham T2/T3 zararini sezilarli kamaytiradi.

---

## 19. Majburiy testlar va chiqarish mezoni

SCUTUM-Q1 §12 naqshi davom ettiriladi, yangi komponentlar uchun kengaytirilgan:

1. Har kriptografik funksiya uchun KAT vektorlari (meros qilinganlar
   allaqachon bor; yangi: consistency proof, IC/PC imzolash, TXN_CONFIRM
   AAD qurilishi).
2. **Har bir T1-T6 ssenariysi hujum laboratoriyasida ijro etilishi
   MUST**: HIMOYASIZ (ROSTOR mexanizmisiz) va HIMOYALANGAN (ROSTOR bilan)
   holatda, natija oldindan yozib qo'yilmasdan.
3. WYSIWYS invarianti: avtomatlashtirilgan test — ko'rsatiladigan har bir
   maydon imzolangan AAD strukturasidan kelib chiqishini tekshiradi (kodni
   statik skanerlash + ijro vaqtidagi tasdiqlash).
4. `PaymentIntent` sxema-qat'iyligi: qo'shimcha kredential-shaklidagi
   maydon (masalan `card_number`) qo'shilgan xabar avtomatik rad
   etilishini tekshiruvchi fuzz test.
5. Jurnal izchilligi: consistency proof va inclusion proof'ning bir-biriga
   zid emasligini, split-view hujumining aniqlanishini tekshiruvchi test.
6. Firibgarlik hisoboti stsenariylari: yolg'on hisobot bombardimoni (spam)
   `FLAGGED` holatiga olib kelmasligini tasdiqlovchi test (chegara
   mantiqi, §14.2).
7. Loglarda maxfiy kalit/foydalanuvchi PII yo'qligini tekshirish (meros
   qilingan gigiyena talabi).
8. Mustaqil audit — kriptografik dizayn **va** ijtimoiy-texnik dizayn
   (fraud-defense mantiqi haqiqiy hujumlarni to'sishini mustaqil
   baholash) — ⬜ bajarilmagan, ishlab chiqarishga chiqishdan oldin talab
   qilinadi.

---

## 20. Ochiq masalalar

1. **To'liq Sybil-qarshilik** firibgarlik hisobotlarida (§14.3) — anonim
   kredensial/ko'r imzo sxemasi orqali, huquqiy-institutsional
   integratsiya talab qiladi.
2. **Registrator konsorsiumi** aniq tarkibi va boshqaruv qoidalari —
   huquqiy/siyosiy masala, texnik spetsifikatsiya doirasidan tashqarida.
3. **Threshold post-kvant imzo** — hozircha k-of-n alohida imzolar bilan
   almashtirilgan (§4.1); vetting qilingan PQ threshold sxemalar
   mavjud bo'lganda qayta ko'rib chiqilishi mumkin.
4. **Guruh/oilaviy hisoblar** — bir nechta DIK bitta "akkount"ga tegishli
   bo'lgan holatlar (masalan oilaviy bank hisobi) hali ta'riflanmagan.
5. **Huquqiy maqom** — firibgarlik hisoboti jurnali qonuniy dalil
   sifatida ishlatilishi mumkinmi, degan masala ROSTOR spetsifikatsiyasi
   doirasidan tashqarida, lekin joriylashtirish uchun muhim.
6. **Telekom/regulyator hamkorligi** (Bosqich 2, §18) — texnik tayyor,
   institutsional amalga oshirish ochiq.

---

## 21. Manbalar

- IIV / Gazeta.uz, 2026-yil 1-yarim yillik kiberjinoyat statistikasi
  (9 282 hodisa, 120+ mlrd so'm zarar, <8% aniqlash)
- Group-IB, Telegram orqali tarqaladigan Android SMS-stealer tahlili
  (100 000+ zararlangan qurilma)
- IETF, [RFC 6962: Certificate Transparency](https://www.rfc-editor.org/rfc/rfc6962)
  — jurnal, STH, consistency proof naqshi
- `docs/SPEC-SCUTUM-Q1-v1.1.md` — meros qilingan transport qatlami
- Signal, [Device linking / multi-device](https://signal.org/docs/) —
  tiklash kvorumi naqshining ilhom manbai
- Google, [Safe Browsing API — k-anonymity design](https://developers.google.com/safe-browsing)
  — prefiks-asosidagi maxfiy qidiruv naqshi
