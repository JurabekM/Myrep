# BOOT-1 — qurilmani ulash (bootstrap) wire-format v1

**Versiya:** 1 · **Sana:** 2026-08-23 · **Holat:** loyiha

> ⚠ BOOT-1 ham AETHER-Q spetsifikatsiyasining qismi EMAS — u AETHER-Q
> primitivlari ustidagi DistribOS konstruksiyasi, DES-1 kabi.

## Muammo

DES-1 envelope'ni ochish uchun **epoch kaliti** kerak. Yangi telefonda u
yo'q. Ochish uchun jo'natuvchi **tanilgan** bo'lishi kerak — yangi telefon
tanilmagan. Ya'ni tovuq-tuxum: qurilma qo'shilishi uchun allaqachon
qo'shilgan bo'lishi kerak.

BOOT-1 aynan shu bir marotabalik teshikni yopadi.

## Ishonch manbai

Bir martalik **taklif siri** (32 bayt). U QR kod orqali uzatiladi va
faqat egasi ko'radigan ekranda 10 daqiqa turadi.

QR kodda epoch kaliti, master kalit yoki uzoq muddatli sir **YO'Q** —
faqat shu bitta almashinuv uchun yaroqli teg. Sabab: QR ekranda ko'rinadi,
suratga tushadi, messenjerga yuboriladi.

## Kalit ajratish

```
BOOT1_LABEL = b"DistribOS-BOOT-1/AETHER-Q-v5.1/v1"

prk     = HKDF-Extract(salt=BOOT1_LABEL, ikm=invitation_secret)
k_req   = HKDF-Expand(prk, BOOT1_LABEL + b"/join-request",  32)
k_resp  = HKDF-Expand(prk, BOOT1_LABEL + b"/join-response", 32)
iv_req  = HKDF-Expand(prk, BOOT1_LABEL + b"/iv-request",    12)
iv_resp = HKDF-Expand(prk, BOOT1_LABEL + b"/iv-response",   12)
```

Yo'nalish bo'yicha **alohida** kalit (AETHER-Q N3): ushlab olingan
so'rovni javob sifatida qayta o'ynatib bo'lmaydi.

## Wire-format

```
Boot1Envelope := header ‖ ciphertext

header (23 bayt, AAD):
  offset size  field
  0      2     version       u16 = 0x0001
  2      1     kind          u8  (1 = JOIN_REQUEST, 2 = JOIN_RESPONSE)
  3      8     invitation_id [8]
  11     12    nonce         [12]   (iv_dir XOR tasodifiy)

ciphertext := ChaCha20-Poly1305(k_dir, nonce, CBOR(payload), aad=header)
```

**Imzo yo'q.** Taklif sirining o'zi autentifikator: uni faqat egasining
ekranini ko'rgan odam biladi. Imzo qo'shish hech narsa qo'shmaydi, chunki
telefonning kaliti hali hech kimga ma'lum emas.

## Payload

### JOIN_REQUEST (telefon → desktop)

```
device_id         bytes[16]
sign_public_key   bytes[1952]   ML-DSA-65
kem_public_key    bytes[1184]   ML-KEM-768
platform          text          "android"
display_name      text
proof             bytes[32]     KMAC256(prk, device_id ‖ sign_public_key)
```

`proof` telefon taklif sirini **haqiqatan bilishini** qurilma identitetiga
bog'lab isbotlaydi: tegni ushlab olgan boshqa qurilma uni o'z kaliti bilan
ishlatolmaydi.

### JOIN_RESPONSE (desktop → telefon)

```
tenant_id           bytes[16]
epoch               u32
key_id              u64
epoch_root_secret   bytes[32]
profile_id          u8
role                text
host_device_id      bytes[16]
host_sign_public_key bytes[1952]
```

Bu yagona joy — epoch kaliti tarmoq orqali uzatiladigan. U taklif siri
bilan shifrlangan va bir martalik.

## Oqim

```
1. Egasi desktopda taklif yaratadi          (10 daqiqa, bir martalik)
2. Telefon QR ni o'qiydi
3. Telefon JOIN_REQUEST yuboradi            → protocol-control
4. Desktop taklifni tekshiradi:
     · mavjudmi
     · muddati o'tmaganmi
     · ISHLATILMAGANMI
     · proof to'g'rimi (constant-time)
5. Desktop qurilmani INVITED holatida yozadi
6. Desktop JOIN_RESPONSE yuboradi           → protocol-control
7. Telefon tenant va epoch kalitini o'rnatadi
8. Taklif ISHLATILGAN deb belgilanadi — qayta ishlamaydi
9. Egasi desktopda qurilmani TASDIQLAYDI    → ACTIVE
```

8-qadamdan keyin bir xil QR bilan ikkinchi qurilma qo'sha olmaydi.

9-qadam ataylab qo'lda: tarmoqdagi hujumchi taklifni ushlab olsa ham,
egasi tanimagan qurilma ro'yxatda paydo bo'ladi va u tasdiqlanmaydi.

## Nima himoyalanmagan

* **Taklif sirini ko'rgan har kim** 10 daqiqa ichida qurilma qo'sha
  oladi. Bu ataylab: QR ning butun ma'nosi shu. Himoya — qisqa muddat,
  bir martalik ishlatish va egasining qo'lda tasdig'i.
* **Metama'lumot**: broker qachon va qancha bayt ulanganini ko'radi.
