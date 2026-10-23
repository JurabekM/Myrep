# M-Pay Test Scheme — kontaktsiz EMV-ga o'xshash profil (v1)

> Holat: **v1 (M4)** — soft-karta (`crates/mpay-terminal-sim/src/card.rs`), terminal yadrosi va
> emitent emulyatori shu profil bo'yicha amalga oshirilgan; KAT — §9.
>
> Bu **o'zimizning fiktiv** sxemamiz. Humo, Uzcard, Visa, Mastercard spetsifikatsiyalariga
> asoslanmagan va ularni takrorlamaydi. Tuzilma umumiy ochiq EMV tamoyillariga (ISO 7816-4 APDU,
> BER-TLV, PPSE) o'xshaydi; algoritmlar va TLV tarkibi `CryptogramScheme` trait'i orqali
> almashtiriladi — real sxema spetsifikatsiyasi olinganda alohida profil sifatida ulanadi.

## 1. Identifikatorlar

| Nomi | Qiymat | Izoh |
|---|---|---|
| PPSE nomi | `2PAY.SYS.DDF01` (`32 50 41 59 2E 53 59 53 2E 44 44 46 30 31`) | ochiq standart nom |
| AID | `F0 4D 50 41 59 01` | `F0` — ro'yxatdan o'tmagan proprietar RID kategoriyasi, `4D504159` = "MPAY", `01` = v1 |
| Ilova yorlig'i (tag `50`) | `M-PAY TEST` | ASCII |
| Test FPAN BIN | `990000`–`990049` | fiktiv emitent kartalari |
| Test DPAN BIN | `990050`–`990099` | token PAN'lar |
| Mamlakat / valyuta | `0860` / `0860` | O'zbekiston / UZS (ISO 3166 / ISO 4217 raqamli) |

PAN uzunligi: 16 raqam, oxirgisi Luhn nazorat raqami. Maska: birinchi 6 + `******` + oxirgi 4.

## 2. APDU oqimi

```
Terminal                                   Karta (HCE / soft-karta)
   │ SELECT PPSE                               │
   │──────────────────────────────────────────►│
   │◄──────────── FCI (AID ro'yxati) 9000 ─────│
   │ SELECT AID F04D50415901                   │
   │──────────────────────────────────────────►│
   │◄──────────── FCI (PDOL) 9000 ─────────────│
   │ GET PROCESSING OPTIONS (PDOL ma'lumoti)   │
   │──────────────────────────────────────────►│  ATC++, LUK tanlash, ARQC
   │◄──── 77 { AIP, Track2, PSN, ATC, ARQC, CID, IAD, muddat } 9000
```

### 2.1 SELECT PPSE

C-APDU: `00 A4 04 00 0E 325041592E5359532E4444463031 00`

R-APDU:
```
6F  FCI shabloni
 ├─ 84  DF nomi = 325041592E5359532E4444463031
 └─ A5  FCI xususiy shabloni
     └─ BF0C  FCI emitent ixtiyoriy ma'lumoti
         └─ 61  ilova shabloni
             ├─ 4F  AID = F04D50415901
             ├─ 50  yorliq = "M-PAY TEST"
             └─ 87  ustuvorlik = 01
9000
```

### 2.2 SELECT AID

C-APDU: `00 A4 04 00 06 F04D50415901 00`

R-APDU:
```
6F
 ├─ 84  F04D50415901
 └─ A5
     ├─ 50    "M-PAY TEST"
     └─ 9F38  PDOL = 9F02 06 9F03 06 9F1A 02 95 05 5F2A 02 9A 03 9C 01 9F37 04
9000
```

### 2.3 PDOL (terminal ma'lumotlari, jami 29 bayt)

| Tag | Nomi | Uzunlik | Format |
|---|---|---|---|
| `9F02` | Summa (tiyin) | 6 | n12 BCD |
| `9F03` | Boshqa summa | 6 | n12 BCD |
| `9F1A` | Terminal mamlakat kodi | 2 | n3 BCD (`0860`) |
| `95` | TVR | 5 | b |
| `5F2A` | Valyuta kodi | 2 | n3 BCD (`0860`) |
| `9A` | Sana | 3 | YYMMDD BCD |
| `9C` | Tranzaksiya turi | 1 | n2 BCD (`00` = xarid) |
| `9F37` | Unpredictable Number | 4 | b, terminal CSPRNG |

### 2.4 GET PROCESSING OPTIONS

C-APDU: `80 A8 00 00 1F 83 1D <29 bayt PDOL ma'lumoti> 00`

R-APDU (format 2):
```
77
 ├─ 82    AIP = 0080
 ├─ 57    Track 2 ekvivalenti = DPAN ‖ D ‖ YYMM ‖ 201 ‖ 0000 ‖ F (BCD, toq bo'lsa F bilan to'ldiriladi)
 ├─ 5F34  PSN = 00
 ├─ 5F24  Ilova amal qilish muddati = YYMMDD (oyning oxirgi kuni)
 ├─ 9F36  ATC (2 bayt, big-endian)
 ├─ 9F26  ARQC (8 bayt)
 ├─ 9F27  CID = 80 (ARQC)
 └─ 9F10  IAD (8 bayt, §4)
9000
```

### 2.5 Holat so'zlari (SW1SW2)

| SW | Ma'nosi |
|---|---|
| `9000` | muvaffaqiyat |
| `6700` | noto'g'ri Lc/uzunlik |
| `6A80` | noto'g'ri ma'lumot (PDOL uzunligi mos emas) |
| `6A82` | AID topilmadi |
| `6985` | shartlar bajarilmagan (SELECT'siz GPO, yaroqli LUK yo'q) |
| `6986` | CDCVM talab qilinadi ("telefonga qarang") |
| `6D00` | INS qo'llab-quvvatlanmaydi |
| `6E00` | CLA qo'llab-quvvatlanmaydi |

## 3. AIP

`82 = 00 80` — M-Pay Test Scheme'da yagona qiymat: bayt 2 bit 8 = "EMV rejimi". Boshqa bitlar RFU.

## 4. IAD (tag `9F10`, 8 bayt)

| Bayt | Maydon | Qiymat |
|---|---|---|
| 0 | IAD format versiyasi | `01` |
| 1 | Kriptogramma sxemasi ID | `01` = `MPAY-AES128-CMAC-V1` |
| 2–5 | LUK ketma-ketlik raqami (u32 BE) | issuer shu orqali LUK'ni qayta hosil qiladi |
| 6 | CVR | bit `80` = CDCVM bajarildi; bit `40` = CDCVM talab qilingan; qolgani RFU |
| 7 | RFU | `00` |

## 5. Kalitlarni hosil qilish (KDF)

KDF — NIST SP 800-108r1 counter rejimi, PRF = AES-128-CMAC, chiqish uzunligi L = 128 bit (bitta blok):

```
KDF(K, Label, Context) = AES-CMAC(K, 0x01 ‖ Label ‖ 0x00 ‖ Context ‖ 0x0080)
```

| Kalit | Ota kalit | Label (ASCII) | Context |
|---|---|---|---|
| `MK_tok` | `IMK-AC` (HSM) | `MPAY-TOKEN-MK` | `len(DPAN)` (1 bayt) ‖ DPAN ASCII raqamlari ‖ PSN (1 bayt) |
| `LUK_i` | `MK_tok` | `MPAY-LUK` | `i` (u32 BE) |
| `SK` | `LUK_i` | `MPAY-SK-AC` | `ATC` (u16 BE) |

## 6. ARQC

CDOL ma'lumoti (41 bayt) — quyidagi qiymatlarning ketma-ket ulanishi (teglarsiz, uzunliklarsiz):

```
9F02(6) ‖ 9F03(6) ‖ 9F1A(2) ‖ 95(5) ‖ 5F2A(2) ‖ 9A(3) ‖ 9C(1) ‖ 9F37(4) ‖ 82(2) ‖ 9F36(2) ‖ 9F10(8)
```

`ARQC = AES-CMAC(SK, CDOL)[0..8]` (CMAC chiqishining chapdagi 8 bayti).

## 7. ARPC

`ARC` — ISO 8583 maydon 39 javob kodining 2 ta ASCII bayti (masalan `"00"` = `30 30`).

`ARPC = AES-CMAC(SK, ARQC ‖ ARC)[0..4]`

`0110` javobining maydon 55 ida: `91` (Issuer Authentication Data) = `ARPC(4) ‖ ARC(2)` va
`8A` = `ARC`. ARQC noto'g'ri bo'lsa yoki token/LUK topilmasa, ARPC qaytarilmaydi.

## 8. LUK siyosati

* Har LUK: `max_uses` (standart 10) va `ttl` (standart 24 soat) — konfiguratsiya qilinadi.
* Muddati o'tgan, limiti tugagan yoki noma'lum LUK bilan kriptogramma — har doim rad (`Q1`).
* LUK foydalanishi faqat ARQC muvaffaqiyatli tekshirilgandan keyin hisoblanadi (D1 tahdidi).
* ATC token bo'yicha qat'iy o'sishi shart (replay → `Q1`, ARPC berilmaydi).

## 8.1 CDCVM (karta tomoni)

* Summa karta siyosatidagi limitdan (sandbox: 1 000 000,00 UZS) yuqori va CDCVM bajarilmagan bo'lsa,
  GPO `6986` ("telefonga qarang") qaytaradi.
* CDCVM bir martalik: muvaffaqiyatli GPO'dan keyin bayroq tushiriladi. IAD CVR: `80` bajarildi,
  `40` talab qilingan edi.
* `TODO(spec):` issuer tomonidagi CVM siyosati (M6, `BiometricPrompt` bilan).

## 9. KAT vektorlari

To'liq to'plam (3 holat: `basic`, `decline-arc`, `max-values`) — `testvectors/emv-kat.json`.
Vektorlarni `scripts/gen_emv_kat.py` **Rust'dan mustaqil** Python implementatsiyasi (Python
`cryptography` AES-CMAC) faqat shu hujjat asosida generatsiya qiladi; Rust testi
`crates/mpay-crypto/tests/emv_kat.rs` har bir oraliq qiymatni solishtiradi. Kotlin SDK (M6) ham
shu fayldan foydalanadi.

`basic` holati (barcha kalitlar fiktiv):

| Qiymat | Hex |
|---|---|
| IMK-AC | `000102030405060708090a0b0c0d0e0f` |
| DPAN / PSN | `9900770000001230` / `00` |
| MK kontekst | `103939303037373030303030303132333000` |
| MK_tok | `c0d8d37caf79397b6f8a5823829b8a49` |
| LUK (i = 1) | `d599af4982970b8d972fa30d63b509f0` |
| SK (ATC = 1) | `d617cfcb552b5ee29ecdc856eb737c3c` |
| PDOL ma'lumoti | `00000125000000000000000008600000000000086026102300a1b2c3d4` |
| IAD | `0101000000018000` |
| CDOL | `00000125000000000000000008600000000000086026102300a1b2c3d4008000010101000000018000` |
| ARQC | `d2cb7091eac8b1a4` |
| ARC / ARPC | `"00"` (`3030`) / `b1a08680` |

Terminal ma'lumoti: summa 1 250 000 tiyin (12 500,00 UZS), mamlakat va valyuta 860, TVR nol,
sana 2026-10-23, xarid (`00`), UN `a1b2c3d4`.

Primitivlar uchun ochiq standart vektorlar (`crates/mpay-crypto/src/keystore/conformance.rs`,
har bir KeyStore backend'ida — memory va SoftHSM2 — bajariladi): RFC 4493 (AES-CMAC),
RFC 4231 #6–#7 (HMAC-SHA256), GCM test case 13/14, RFC 8032 #1–#2 (Ed25519).

## 10. Ochiq savollar

* `TODO(spec):` CVM limiti va CDCVM talabining issuer tomonidagi siyosati (M6).
* `TODO(spec):` Real sxema profili ulanganda IAD formati va ARPC metodi qayta ko'rib chiqiladi.
