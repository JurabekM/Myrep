# ADR-0007: Javob kodlari xaritasi

* Holat: qabul qilingan (2026-10-23)

## Qaror

| Kod | Holat |
|---|---|
| `00` | tasdiqlandi |
| `05` | rad: token SUSPENDED/DELETED, noma'lum token, Shield REVIEW (siyosat bo'yicha) |
| `51` | mablag' yetarli emas |
| `54` | token (DPAN) muddati o'tgan (2-faza P2.7, ADR-0022) |
| `59` | Shield: fraud gumoni (DECLINE) |
| `91` | emitent mavjud emas / ishlamayapti |
| `94` | takroriy uzatish: shu terminal + STAN + sana boshqa mazmun bilan ishlatilgan; emitentga yuborilmaydi (1-faza, ADR-0010) |
| `Q1` | kriptogramma noto'g'ri; LUK noma'lum, muddati o'tgan yoki limiti tugagan; ATC replay; CDOL ↔ ISO 8583 nomuvofiqligi |
| `Q2` | karta egasini qurilmada tasdiqlash (CDCVM) kerak: summa CVM chegarasidan yuqori yoki Shield REVIEW + `step_up` siyosati — telefonda tasdiqlab qayta tap (ADR-0022). `Q`-kodlar — M-Pay profilining o'z kodlari |

`55` ishlatilmaydi (ISO 8583 da "PIN noto'g'ri" ma'nosida keng tarqalgan). Aniq sabab ichki
`reason` kodida (`ARQC_MISMATCH`, `LUK_EXPIRED`, `LUK_EXHAUSTED`, `ATC_REPLAY`, ...) va
audit/logda saqlanadi.
