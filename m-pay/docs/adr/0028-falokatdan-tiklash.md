# ADR-0028: Falokatdan tiklash (host yo'qolishi) va navbatchi runbook'i

* Holat: qabul qilingan (2026-10-27, production checklist JM-11).
* Bog'liq: ADR-0023 (shifrlangan zaxira, PITR), ADR-0026 (Shield HA), ADR-0027 (PostgreSQL replika, VIP).

## Kontekst

Almashinuvlar (Shield, PostgreSQL, nginx) bitta komponent yiqilishini yopadi. Butun host yo'qolishi
(disk, VM, ma'lumotlar markazi) esa zaxiradan tiklashni talab qiladi. `restore.sh` faqat DB'ni
ishlab turgan muhitga tiklardi, `state-hsm.tar.gz.age` esa avtomatik tiklanmasdi. Yangi host'da
hammasini birga tiklash va natija ishlashini (eski kartalar to'lov qila olishini) isbotlash tartibi
yo'q edi. Navbatchi uchun ogohlantirish → harakat qo'llanmasi ham yo'q edi.

## Qaror

### 1. `deploy/dr-restore.sh` — bo'sh muhitga to'liq tiklash

1. `SHA256SUMS` tekshiriladi.
2. Holat (konfiguratsiya, sertifikatlar, ML-DSA blob) va SoftHSM tokeni → `state`, `hsm` hajmlari.
3. Yangi PostgreSQL klasteri (yetakchi + replika + `pg`), `pg_dump` dan tiklash.
4. Barcha xizmatlar — `bootstrap` migratsiyalarni va kalitlarni tekshiradi, kalitlar HSM'da allaqachon
   bor.
5. Audit xesh-zanjiri HSM kaliti bilan tekshiriladi — DB va HSM bir-biriga mosligining isboti.

Qo'shimcha qoidalar:

* Har bosqich vaqti chiqariladi (RTO).
* Ishlab turgan yoki to'liq bo'lmagan muhitga — rad (u holat uchun `restore.sh --replace`).
* **Sirlar zaxirada yo'q:** HSM PIN'i, DB, Shield va SMS parollari alohida saqlanadi. Zaxira va sirlar
  bir joyda yo'qolmasin, zaxira o'g'irlansa ham kalitlarsiz foydasiz.
  `TODO(spec):` bankning sirlar ombori (HSM yoki secrets manager) va kalit marosimi (BK-4).
* RPO — oxirgi zaxira vaqti: WAL arxivi ham yo'qolgan host'da edi.
  `TODO(spec):` WAL'ni boshqa joyga uzluksiz yuborish (BK-13).

### 2. `scripts/dr-drill.sh` — mashq, isbot bilan

1. Toza muhit (alohida compose loyihasi).
2. "Telefon": `mpay-tsim` hamyoni host'dagi vaqtinchalik papkada, ya'ni falokatdan omon qoladi.
   Karta qo'shiladi, to'lov `00`.
3. Zaxira olinadi.
4. **Falokat:** `down -v` — barcha konteyner va hajmlar o'chiriladi (DB, replika, WAL arxivi, HSM
   tokeni, holat; qolgan hajmlar soni 0 ekani tekshiriladi).
5. `dr-restore.sh`.
6. Isbot:
   * **o'sha** token va LUK bilan to'lov `00`, ARPC to'g'ri — HSM'dagi IMK, token va emitent hisobi
     tiklangan;
   * LUK to'ldirish — PQ Link'da hamyon pinlagan server barmoq izi (HSM'dagi identifikator) va qurilma
     reyestri tiklangan;
   * solishtirish toza; loglarda PAN va sir yo'q.
7. Natija `docs/load/dr-drill.json`. CI'da alohida job.

Yuk generatori image'iga `mpay-tsim` qo'shildi (Dockerfile `loadgen` bosqichi).

### 3. `docs/runbook.md` — navbatchi qo'llanmasi

* Har ogohlantirish (21 ta) → ma'nosi → birinchi qadam.
* Hodisalar bo'yicha bosqichma-bosqich harakat: API, PostgreSQL (almashinuv, replika, kechikish,
  hovuz, noto'g'ri amal → PITR), Shield, nginx/VIP, `96`/reversal/solishtirish, kechikish va 5xx,
  karta qo'shish (Integrity, OTP), xavfsizlik va kalit oshkor bo'lishi, HSM, kliring, host yo'qolishi.
* Muntazam ishlar: kunlik kliring/solishtirish/zaxira, haftalik tiklash mashqi (`restore.sh
  --verify`), choraklik DR va almashinuv mashqlari.
* O'lchangan tiklash vaqtlari jadvali.

## Oqibatlar

* Host yo'qolsa tiklash bitta buyruq va bir necha daqiqa (`docs/dr-report.md`). Eski kartalar qayta
  qo'shishsiz ishlaydi.
* Mashq CI'da har push'da — zaxira formati, tiklash skripti va kalitlar mosligi buzilsa darhol bilinadi.
* Zaxiraning qiymati sirlar va maxfiy zaxira kaliti bilan birga: uchalasining saqlanish joyi va
  kimga kirish huquqi — bank jarayoni.
* Runbook compose buyruqlarida. Production infratuzilmasida buyruqlar o'zgaradi, tartib qoladi.

## Ko'rib chiqilgan muqobillar

* **PITR bilan tiklash (asosiy nusxa + WAL):** RPO kichikroq, lekin WAL arxivi o'sha host'da edi —
  host yo'qolsa u ham yo'q. Offsite WAL bo'lganda `pitr-restore.sh` yo'li qo'shiladi.
* **Sirlarni zaxiraga qo'shish:** bitta fayl — bitta tiklash, lekin zaxira o'g'irlansa HSM PIN'i ham
  ketadi. Alohida saqlash xavfsizroq.
* **Faqat DB'ni tekshirish (audit-verify):** kalitlar va token qatlami tekshirilmaydi. Haqiqiy to'lov
  (ARQC/ARPC) va PQ Link ulanishi to'liq zanjirni isbotlaydi.
