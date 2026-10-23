# Sandbox test ma'lumotlari

Barcha PAN'lar fiktiv, M-Pay test BIN diapazonidan, Luhn bo'yicha to'g'ri. Haqiqiy tizimlarga
tegishli emas.

## 1. BIN'lar

| Diapazon | Maqsad |
|---|---|
| `990000`–`990049` | FPAN — emitent emulyatori kartalari |
| `990050`–`990099` | DPAN — token PAN'lar (standart token BIN `990077`) |

## 2. Shield stub stsenariylari (M3–M4)

`crates/mpay-shield/src/stub.rs`. M5 da haqiqiy Shield bilan almashtiriladi.

### 2.1 Provisioning (ID&V) — FPAN'ning 7–8-raqamlari

| PAN prefiksi | Stsenariy kodi | Qaror |
|---|---|---|
| `990012` `00`–`79` … | 00–79 | GREEN — token darhol, LUK'lar beriladi |
| `990012` `80`–`89` … | 80–89 | YELLOW — OTP (`/v1/sandbox/otp/{id}`) |
| `990012` `90`–`99` … | 90–99 | RED — rad |

Qurilma attestatsiyasi StrongBox'dan past bo'lsa GREEN → YELLOW.

Misol: `990012` + `10` + `0001001` + Luhn → GREEN. Generatsiya: `mpay_e2e::test_fpan(10, 1001)`.

### 2.2 Avtorizatsiya risk skori — merchant ID

| Merchant ID | Qaror | Javob kodi (M4) |
|---|---|---|
| `RISKY…` | DECLINE (950) | `59` |
| `REVIEW…` yoki summa ≥ 50 000 000,00 UZS | REVIEW (600) | siyosat bo'yicha |
| boshqa | APPROVE (50) | — |
