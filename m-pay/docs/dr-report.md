# Falokatdan tiklash mashqi — hisobot

Sana: 2026-10-27. Skript: `scripts/dr-drill.sh` (ADR-0028), natija: `docs/load/dr-drill.json`.
Muhit: Docker Desktop (Windows 10, WSL2), bitta host, compose loyihasi `mpay-dr`. CI'da har push'da
(`dr` job'i, ubuntu-24.04).

## Ssenariy

Host butunlay yo'qoldi: barcha konteynerlar va **hamma hajmlar** o'chirildi — PostgreSQL (yetakchi va
replika), WAL arxivi, SoftHSM tokeni, konfiguratsiya holati (qolgan hajmlar: 0). Saqlanganlari:
shifrlangan zaxira (`backup.sh`), sirlar nusxasi (`deploy/secrets/`), maxfiy zaxira kaliti va
"telefon" (mpay-tsim hamyoni host'da).

## Natija

| Bosqich (`deploy/dr-restore.sh`) | Vaqt |
|---|---|
| 1. holat va HSM tokeni (shifrlangan arxivdan) | 1 s |
| 2. PostgreSQL: yangi klaster (yetakchi + replika + `pg`), `pg_dump` dan | 5 s |
| 3. barcha xizmatlar (API sog'lom) | 17 s |
| 4. audit xesh-zanjiri (HSM kaliti bilan) | 1 s |
| **Jami (RTO, skript)** | **24 s** |

Image'lar host'da tayyor edi; yangi host'da image yig'ish yoki yuklash vaqti qo'shiladi.
RPO — zaxira lahzasi (WAL arxivi ham yo'qolgan host'da edi).

## Isbot (tiklangandan keyin)

* **O'sha** token (`tok_…`, DPAN `990077******4651`), o'sha LUK bilan to'lov: `00 APPROVED`, ARPC to'g'ri
  (ATC 1 → 2). Ya'ni HSM'dagi IMK, token, LUK va emitent hisobi tiklangan.
* LUK to'ldirish (`replenish`): PQ Link ulanishi hamyon falokatdan oldin pinlagan server barmoq izi
  bilan o'tdi (identifikator kalitlari HSM'dan), qurilma reyestri tiklangan; 5 ta yangi LUK.
* Audit xesh-zanjiri to'g'ri; solishtirish: acquirer 2, emitent 2, mos 2 — tafovut yo'q.
* Loglarda ochiq PAN va sirlar yo'q.

## Mashq davomida topilgan va tuzatilgan

* `restore.sh` faqat DB'ni ishlab turgan muhitga tiklardi, `state-hsm.tar.gz.age` qo'lda —
  yangi `dr-restore.sh` hammasini bo'sh muhitga tiklaydi.
* Mashq skriptining o'zida: Windows'da bind mount yo'li (`pwd -W`), mpay-tsim'ning STAN hisoblagichi
  faqat o'qish uchun holat papkasida edi — sandbox nusxasi "telefon"da.

## Ochiq

* Sirlar ombori va kalit marosimi (BK-4), WAL'ni boshqa joyga uzluksiz yuborish — RPO daqiqalarga
  (BK-13), alohida host'lar (BK-16).
