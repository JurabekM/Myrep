# ADR-0029: Bekor qilish ro'yxati — ilova build'i va mustaqil kanal

* Holat: qabul qilingan (2026-10-27, production checklist JM-6).
* Bog'liq: ADR-0014 (oflayn ildiz imzosi), ADR-0012 (kalit almashtirish), P1.5 (build pinlari).

## Kontekst

ADR-0014 bo'yicha qurilma bekor qilish ro'yxatini faqat PQ Link serverining o'zidan oladi. Kalit
oshkor bo'lsa, hujumchi o'sha kalit bilan o'z serverini ko'taradi va ro'yxatni **bermaydi**. Bu holda:

* ro'yxatni hali olmagan qurilma hujumchiga ulanadi;
* yangi o'rnatilgan ilovada ro'yxat umuman yo'q.

ADR-0014 dagi `TODO(spec)`: ro'yxatni ilova build'iga ham joylash va boshqa kanal orqali tarqatish.

## Qaror

### 1. Uchta manba, bitta qoida

`uz.mpay.core.RevocationSources` ro'yxatni uchta manbadan oladi:

* **ilova build'i** (`WalletConfig.bundledRevocations`);
* **mustaqil kanallar** (`WalletConfig.revocationUrls` — CDN'dagi statik fayl, PQ Link serveridan
  alohida infratuzilma);
* **server** (`GET /v1/pqlink/revocations`).

Qoidalar:

* Manbaga ishonilmaydi: har nusxa oflayn ildiz barmoq izi va gibrid imzo (Ed25519 + ML-DSA-65) bilan
  tekshiriladi.
* Eng katta versiya yutadi. Qurilmada saqlangandan kichigi e'tiborsiz — orqaga qaytarib bo'lmaydi.
* Kanal eski, lekin haqiqiy ro'yxatni bersa — shunchaki yutqazadi. Soxtalashtirilgan nusxa rad
  etiladi, sababi logga yoziladi.
* Ro'yxat server identifikatori tekshirilishidan **oldin** yangilanadi.
* Bekor qilingan barmoq izi build pini, o'rganilgan pin yoki TOFU bo'lsa ham rad etiladi
  (`ServerPinPolicy`, ADR-0014).
* Ildiz barmoq izisiz manbalar berilsa — konfiguratsiya xatosi (jim e'tiborsiz qoldirilmaydi).

### 2. Mustaqil kanal

`RevocationSources.fetch`:

* faqat `https://` (loopback `http://` — sinov uchun);
* yo'naltirishga ergashmaydi;
* 64 KB gacha, 3 s timeout;
* har qanday xato — `null`: ulanish to'xtamaydi, boshqa manbalar va saqlangan ro'yxat ishlatiladi.

TLS tizim ildizlari bilan — CDN sertifikati pinlanmaydi. Fayl imzolangan, kanal faqat yetkazadi.

### 3. Build va nashr

* Demo ilova:
  * `-Pmpay.revocationsFile=<revoke chiqishi>` → asset `mpay-revocations.json`;
  * `-Pmpay.revocationUrls=https://…` (vergul bilan; `https` dan boshqasi build'da rad);
  * `-Pmpay.rootFingerprint=…`.
* Nashrdan oldin: `mpay-server revocations-check --file … --root-fingerprint …` — imzo va ildizni
  tekshiradi, xato bo'lsa chiqish kodi 1. Shundan keyin fayl CDN'ga yuklanadi va keyingi ilova
  build'iga joylanadi.

## Oqibatlar

* Oshkor kalit yangi o'rnatishlarda (build'dagi ro'yxat) va hujumchi serveri ro'yxatni bermaganda
  (CDN) ham rad etiladi.
* Qolgan hujum: tarmoqni to'liq boshqaradigan hujumchi CDN'ni ham to'sadi, qurilmada esa yangi
  ro'yxat hali yo'q. Ro'yxatda vaqt belgisi yo'q (imzo formati — versiya va barmoq izlari), shuning
  uchun "ro'yxat eskirgan" deb ulanishni to'xtatish siyosati qo'yilmadi.
  `TODO(spec):`
  * push-xabar (FCM — bank Google loyihasi) orqali yangi ro'yxat haqida xabar;
  * imzolangan vaqt belgisi va eskirish siyosati (bank xavfsizlik siyosati bo'yicha).
* Formati o'zgarmadi — Rust `revoke` chiqishi va Kotlin tekshiruvi bayt-bir xil (interop).
* Tekshirilgan:
  * Kotlin `RevocationsTest`:
    * uch manbadan eng katta versiya;
    * hujumchi serverining eski ro'yxati yutqazadi;
    * soxta va begona ildizli nusxa rad;
    * lokal HTTP server orqali yuklash — 404, 64 KB dan katta, yo'naltirish, oddiy `http`, yetib
      bo'lmaydigan manzil.
  * `revocations-check`: asl — 0, begona ildiz — 1, versiyasi soxtalashtirilgan — 1.
  * Demo build: asset Rust imzolagan fayl bilan bayt-bir xil; `http://` manzil build'da rad.
  * **Emulyator**:
    * ro'yxatni bermaydigan (404) server, build'dagi ro'yxat (versiya 5) uning barmoq izini bekor
      qilgan → ilova TOFU rejimida ham handshake'dan oldin "server identifikatori bekor qilingan";
    * nazorat (boshqa barmoq izi) → handshake boshlandi.

## Ko'rib chiqilgan muqobillar

* **Faqat ilova yangilanishi:** sekin — hamma yangilanguncha himoya yo'q. Build nusxasi asos,
  CDN — yangilanishlar orasida.
* **CDN sertifikatini pinlash:** ishonchni kuchaytirmaydi (fayl allaqachon imzolangan), lekin CDN
  provayderi sertifikat almashtirsa kanal sinadi.
* **Ro'yxatlarni birlashtirish (union):** xato bekor qilingan kalitni keyingi versiyada qaytarib
  bo'lmasdi. "Eng katta versiya" ADR-0014 bilan bir xil semantika.
