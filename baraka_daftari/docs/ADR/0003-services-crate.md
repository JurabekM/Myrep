# ADR 0003 — `services` crate

Spetsifikatsiyadagi tuzilmada `domain` sof (IO yo'q), `src-tauri` commandlari yupqa bo'lishi shart, lekin "daromad + ajratma bitta tranzaksiyada" kabi use-case'lar ikkalasini birlashtiradi. Ularni commandga qo'ysak — biznes mantiq command ichida bo'lib qoladi; `domain` ga qo'ysak — IO kiradi.

Qaror: `crates/services` — `domain` + `storage` ni birlashtiradi, Tauri'ga bog'liq emas, to'liq testlanadi (in-memory SQLCipher). Pul hisobi baribir faqat `money`/`domain` da; `services` ularni chaqiradi.
`Database::transaction` endi `E: From<StorageError>` bilan generik: servis xatolari tranzaksiya ichidan yo'qolmay chiqadi.
Yangi paket yo'q (faqat ichki crate); UI'ga `@radix-ui/react-dialog` qo'shildi: `Ctrl+N` oynasi uchun fokus tuzog'i va `Esc`, qo'lda yozilsa a11y xatolari ehtimoli yuqori.
