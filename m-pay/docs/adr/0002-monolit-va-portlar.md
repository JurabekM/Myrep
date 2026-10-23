# ADR-0002: Monolit binar va port trait'lari

* Holat: qabul qilingan (2026-10-23)

## Kontekst

Server tomoni bitta binar (`mpay-server`) bo'lishi shart, modullar esa alohida crate'lar.
Vault ID&V uchun Shield'ga, Issuer detokenizatsiya uchun Vault'ga va risk uchun Shield'ga muhtoj.
Shield M5 da tayyor bo'ladi, lekin M3–M4 testlari unga bog'liq.

## Qaror

`mpay-common::ports` da trait'lar: `IdvDecider`, `RiskScorer`, `Detokenizer`.
Modul crate'lari bir-biriga emas, faqat shu trait'larga bog'liq. `mpay-server` ularni
`Arc<dyn Trait>` sifatida haqiqiy implementatsiyalarga ulaydi. M3–M4 da Shield o'rniga
`mpay-shield::stub` (deterministik, test PAN bo'yicha boshqariladi).

Detokenizatsiya HTTP orqali ochilmaydi: `Detokenizer` obyekti faqat issuer moduliga beriladi.

## Oqibatlar

* Bog'liqlik grafi siklsiz; har modul alohida testlanadi.
* `async-trait` qo'shimcha bog'liqlik (dyn-mos async trait uchun).

## Muqobillar

* Generik parametrlar — tip imzolari juda murakkablashadi.
* Modullararo HTTP — monolit talabiga zid, kechikish qo'shadi.
