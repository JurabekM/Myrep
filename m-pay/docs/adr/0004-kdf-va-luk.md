# ADR-0004: Kalit hosil qilish zanjiri va LUK

* Holat: qabul qilingan (2026-10-23)

## Kontekst

Promptda ikki zanjir bor: "IMK → token master key → ATC → session key" va
"token master key + ketma-ketlik raqami → LUK". Qurilma token master key'ni ushlamasligi shart.

## Qaror

```
MK_tok = KDF(IMK-AC, "MPAY-TOKEN-MK", len ‖ DPAN ‖ PSN)
LUK_i  = KDF(MK_tok, "MPAY-LUK", i)
SK     = KDF(LUK_i, "MPAY-SK-AC", ATC)
ARQC   = AES-CMAC(SK, CDOL)[0..8]
ARPC   = AES-CMAC(SK, ARQC ‖ ARC)[0..4]
```

KDF — NIST SP 800-108r1 counter rejimi, PRF = AES-128-CMAC. IAD ichida LUK indeksi `i`
uzatiladi. Algoritmlar `CryptogramScheme` trait'i orqali almashtiriladi (`MPAY-AES128-CMAC-V1`).

LUK'lar DB'da saqlanmaydi: faqat metama'lumot (indeks, berilgan vaqt, TTL, limit, foydalanishlar
soni). Issuer kerak bo'lganda qayta hosil qiladi.

## Oqibatlar

* Qurilmada faqat LUK'lar; ATC bo'yicha session key qurilmada LUK'dan hosil qilinadi.
* Real sxemaga o'tishda yangi `CryptogramScheme` implementatsiyasi (masalan 3DES yoki sxemaning
  o'z session key metodi) qo'shiladi.
