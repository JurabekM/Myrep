# ADR-0023: Shifrlangan zaxira, PITR va ogohlantirishlarni yo'naltirish

* Holat: qabul qilingan (2026-10-26, 3-faza tayyorgarligi; ADR-0020 ni to'ldiradi)

## Kontekst

ADR-0020 dagi zaxira (`pg_dump` + holat arxivi) uchta bo'shliq bilan qolgan edi:

1. **Ochiq ma'lumot.** Dump va holat arxivi shifrlanmagan. Karta ma'lumoti DB'da KEK/DEK bilan
   shifrlangan bo'lsa ham, dump'da audit jurnali, maskalangan PAN'lar, qurilma reyestri, sandbox
   holatida esa API kalitlari va mTLS kalitlari bor edi.
2. **Faqat to'liq nusxa.** Kunlik dump'lar orasida yo'qotish — oxirgi dump'dan keyingi hammasi
   (RPO = zaxira oralig'i). Noto'g'ri operator amali yoki buzilgan yozuvdan "bir daqiqa oldingi"
   holatga qaytib bo'lmasdi.
3. **Ogohlantirish hech kimga yetmasdi.** Prometheus qoidalari ishlardi, lekin natija faqat
   `/api/v1/alerts` da — navbatchiga yuborilmasdi.

## Qaror

1. **Shifrlash — age (X25519), ochiq kalit bilan.** `deploy/backup-keygen.sh` kalit juftini
   yaratadi: ochiq kalit (`secrets/backup_recipient`) serverda, maxfiy kalit (`backup_identity`)
   **oflayn** saqlanadi va faqat tiklash paytida olib kelinadi (`MPAY_BACKUP_IDENTITY`). Shunda server
   to'liq buzilganda ham hujumchi eski zaxiralarni o'qiy olmaydi. Shifrlash oqimda, konteyner ichida
   (`age` runtime image'da) — ochiq ma'lumot diskka yozilmaydi. `SHA256SUMS` shifrlangan fayllar bo'yicha.
   `backup.sh` ochiq kalit bo'lmasa ishlamaydi (shifrlanmagan zaxira yo'li yo'q).
2. **PITR (muayyan lahzaga tiklash).** PostgreSQL `archive_mode = on`, `archive_command` har to'lgan WAL
   segmentini `walarchive` hajmiga ko'chiradi (`archive_timeout = 300` — sokin paytda ham segment ≤ 5
   daqiqada yopiladi). `backup.sh` asosiy nusxa (`pg_basebackup`, tar, kerakli WAL bilan) va WAL arxivini
   ham oladi (joriy segment `pg_switch_wal` bilan yopilib arxivlangani kutiladi). `pitr-restore.sh`
   asosiy nusxa + keyingi zaxiradagi WAL'ni vaqtinchalik PostgreSQL'da `recovery_target_time` gacha
   qayta o'ynaydi, audit xesh-zanjirini HSM kaliti bilan tekshiradi; ishlayotgan muhitga tegmaydi.
3. **Alertmanager.** Prometheus → Alertmanager (`group_by: alertname, instance`, `group_wait: 10s`;
   `critical` — har 30 daqiqada eslatish) → webhook. Sandbox'da qabul qiluvchi — virtual navbatchi
   kanali: `mpay-smsgw` `POST /alerts` (Bearer token, faqat yorliqlar saqlanadi). Bank kanali
   (SMS shlyuzi, Telegram, e-pochta) — faqat `alertmanager.yml` dagi receiver.

## Oqibatlar

* RPO: oxirgi arxivlangan WAL segmentigacha (≤ 5 daqiqa sokin paytda, faol paytda — soniyalar);
  hozircha arxiv shu host'da — host yo'qolsa RPO = oxirgi `backup.sh`. `TODO(spec):` WAL'ni uzluksiz
  boshqa joyga (offsite) yuborish va saqlash muddati, bank talablari bo'yicha.
* Maxfiy kalit yo'qolsa zaxiralar ochilmaydi — kalitni ikki nusxada oflayn saqlash tartibi kerak
  (`TODO(spec)`: bankning kalit saqlash protsedurasi, ehtimol HSM).
* Tekshirilgan (`scripts/compose-test.sh`, CI `deploy` job'i): yukdan oldin asosiy nusxa (B1) → yuk →
  T lahza (audit yozuvlari soni C1) → qo'shimcha faollik (C2 > C1) → zaxira B2 → `restore.sh --verify`
  → `pitr-restore.sh B1 B2 T`: tiklangan audit yozuvlari soni **aynan C1**, zanjir to'g'ri; dump fayli
  shifrlangan (`PGDMP` sarlavhasi yo'q); `api-1` to'xtatilganda `MpayInstanceDown` navbatchi kanaliga
  yetib keladi. `mpay-smsgw` unit testi webhook formatini tekshiradi.

## Ko'rib chiqilgan muqobillar

* **GPG:** og'irroq (kalit halqasi, ko'p rejim); age — bitta ochiq kalit, oddiy CLI, zamonaviy kripto.
* **Simmetrik parol (`openssl enc`):** parol serverda bo'lishi kerak — server buzilsa zaxiralar ham
  ochiladi; ochiq kalitli sxema bu muammoni yo'q qiladi.
* **pgBackRest / WAL-G:** to'liq PITR vositalari (siqish, parallel, S3). Pilot bankning saqlash
  infratuzilmasi ma'lum bo'lganda o'tish oson; hozir qo'shimcha xizmatsiz, ko'rinadigan skriptlar.
* **Streaming replica:** yuqori mavjudlik beradi, lekin noto'g'ri amal ham replikaga o'tadi — PITR
  o'rnini bosmaydi. Replika PITR bilan birga qo'shildi — ADR-0027 (WAL arxivi umumiy, PITR
  almashinuvdan keyingi timeline bo'ylab ham tiklaydi).
