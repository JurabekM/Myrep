# Sandbox test ma'lumotlari

Barcha PAN'lar fiktiv, M-Pay test BIN diapazonidan, Luhn bo'yicha to'g'ri. Haqiqiy tizimlarga
tegishli emas.

## 1. BIN'lar

| Diapazon | Maqsad |
|---|---|
| `990000`–`990049` | FPAN — emitent emulyatori kartalari |
| `990050`–`990099` | DPAN — token PAN'lar (standart token BIN `990077`) |

## 2. Shield stub stsenariylari (`[shield] engine = "stub"`)

`crates/mpay-shield/src/stub.rs`. Standart rejim — `engine` (§3); stub M3/M4 e2e testlarida
va deterministik namoyish uchun saqlanadi.

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

## 3. Shield dvigateli bilan namoyish (`engine = "engine"`, standart)

Qarorlarni PAN raqamlari emas, xatti-harakat belgilaydi (`crates/mpay-shield/rules/default.toml`):

| Harakat | Natija |
|---|---|
| Yangi qurilmada birinchi 1–3 karta | GREEN |
| Shu qurilmada 4–5-karta | YELLOW (OTP) |
| Shu qurilmada 6-karta | RED (`IDV_DEVICE_FARM`) |
| Mavjud kartani boshqa, yangi qurilmaga qo'shish | YELLOW (`IDV_NEW_DEVICE_EXISTING_CARD`) |
| Bir daqiqada 6+ tranzaksiya yoki onlayn kichik summalar seriyasi | `59` (Shield DECLINE) |
| Odatiy xarid | `00` |

Ishlaydigan ketma-ketlik: `scripts/smoke-e2e.sh`.
