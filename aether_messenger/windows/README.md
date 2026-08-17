# AETHER-Q Messenger — Windows (C# / WPF) versiyasi

`aether_q/` Rust kripto-yadrosi ustidan qurilgan messenger PoC'ning desktop (Windows)
versiyasi. Android (Kotlin/Compose) versiyasi bilan **bir xil protokol** va **bir xil
binary wire format** ishlatadi — ikkala klient bir-biriga xabar yubora oladi (agar
kontaktlar QR/matn karta orqali o'zaro qo'shilgan bo'lsa).

## Arxitektura

```
aether_q/crates/aether-ffi-c/     Rust — qo'lda yozilgan raw C ABI (extern "C",
                                   ptr+len asosidagi ByteBuffer'lar). UniFFI ishlatilmagan —
                                   C# uchun sodda va bashoratli P/Invoke ta'minlaydi.

windows/AetherQMessenger/
  Ffi/            AetherNative.cs (P/Invoke deklaratsiyalari), AetherCrypto.cs (fasad),
                  CompressHandles.cs (ratchet handle wrapper'lari)
  Crypto/         Identity.cs (Windows DPAPI bilan), ContactCard.cs (JSON), SelfTest.cs
  Data/           AppDatabase.cs (Microsoft.Data.Sqlite), SessionManager.cs,
                  MessengerRepository.cs, Records.cs
  Mqtt/           MqttClientWrapper.cs (MQTTnet), MessageEnvelope.cs (Android bilan
                  bayt-baytiga bir xil binary format)
  MainWindow.xaml, AddContactWindow.xaml, MyCardWindow.xaml  — WPF UI
```

## Nima uchun UniFFI emas

Mobil versiya UniFFI orqali Kotlin/Python/Swift bindinglarini avtomatik generatsiya
qildi, lekin UniFFI'ning rasmiy generatorlari orasida C# yo'q. Shu sababli bu versiya
uchun alohida, qo'lda yozilgan minimal C ABI qatlami (`aether-ffi-c`) qo'shildi —
`extern "C"` funksiyalar, oddiy `ptr+len` baytlar va opaque handle pointer'lar orqali.
Bu ikki afzallik beradi: (1) hech qanday qo'shimcha kod-generatsiya vositasi kerak emas,
(2) P/Invoke tomonidagi marshaling juda oddiy va bashoratli.

## Qurish

```sh
# 1. Rust DLL (Windows host uchun, cross-compile shart emas)
cd aether_q
cargo build --release -p aether-ffi-c
cp target/release/aether_ffi_c.dll ../aether_messenger/windows/AetherQMessenger/native/

# 2. C# WPF ilova
cd ../aether_messenger/windows/AetherQMessenger
dotnet build -c Release
# yoki to'liq mustaqil (self-contained) distributiv:
dotnet publish -c Release -r win-x64 --self-contained true -o publish

# 3. Setup.exe (Inno Setup)
cd ../installer
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" AetherQMessenger.iss
# -> installer/output/AetherQMessenger-Setup-<versiya>.exe
```

**Muhim**: bu mashinada faqat **.NET 10 runtime** o'rnatilgan (.NET 8 SDK-only muhit) —
`.csproj`da `<RollForward>LatestMajor</RollForward>` shu sababli qo'shilgan, `net8.0-windows`
TFM eng keng moslikni ta'minlaydi va mavjud runtime'da ishlaydi.

## Setup.exe (o'rnatuvchi)

`windows/installer/AetherQMessenger.iss` — Inno Setup skripti, `publish/` papkasidagi
to'liq mustaqil (self-contained) build'ni oddiy o'rnatuvchi dasturga o'raydi: Start
menyusi yorlig'i, ixtiyoriy Desktop yorlig'i, standart Windows uninstaller
(`unins000.exe`, Boshqarish paneli → Dasturlar orqali ham chaqiriladi). Alohida .NET
runtime o'rnatish shart emas — build o'zi bilan olib yuradi (shuning uchun ~52 MB).

## Tekshirilgan (ushbu sessiyada)

- ✅ `aether-ffi-c` Rust crate'i xatosiz build va test qilindi (`cargo test`), `clippy`da
  ogohlantirish yo'q.
- ✅ Windows host uchun native DLL qurildi (`aether_ffi_c.dll`) — faqat standart Windows
  tizim DLL'lariga bog'liq (mingw runtime statik bog'langan), qo'shimcha tarqatishga hojat yo'q.
- ✅ `dotnet build` — Debug va Release konfiguratsiyalarida **0 ogohlantirish, 0 xato**.
- ✅ **Headless self-test rejimi** (`AetherQMessenger.exe --selftest`): to'liq
  AUTH-AKEM handshake + Compress-KEM ratchet qadami + AEAD record round-trip haqiqiy
  P/Invoke chegarasi orqali ishga tushirildi — natija: **muvaffaqiyatli**, chiqish kodi 0,
  Debug, Release va **self-contained publish** build'larining barchasida.
- ✅ `dotnet publish -r win-x64 --self-contained` — mustaqil ishlaydigan distributiv
  (166 MB, .NET runtime ichida) muvaffaqiyatli yaratildi va sinovdan o'tkazildi.
- ✅ **Setup.exe** (Inno Setup, 52.5 MB): to'liq o'rnatish-ishga tushirish-o'chirish
  aylanasi sinovdan o'tkazildi — `/VERYSILENT` bilan boshqa papkaga o'rnatildi,
  o'rnatilgan `.exe` `--selftest` bilan **muvaffaqiyatli** ishladi, so'ng
  `unins000.exe` orqali toza o'chirildi (papka to'liq olib tashlandi).
- ⚠️ WPF oynasi vizual skrinshot orqali tekshirilmadi — bu mashinadagi computer-use
  avtomatlashtirish vositasi faqat oldindan ro'yxatga olingan (Start menyusidagi)
  ilovalarni boshqara oladi, yangi qurilgan `.exe` fayllar uchun emas. O'rniga headless
  self-test orqali aynan shu kripto mantig'ini (P/Invoke chegarasi bilan birga) haqiqiy
  ishga tushirib tekshirdik — bu vizual skrinshotdan ko'ra kriptografik to'g'rilik
  nuqtai nazaridan qat'iyroq tekshiruv.

## Ma'lum cheklovlar (PoC chegaralari)

- **Faqat matnli xabarlar**, ratchet holati faqat jarayon-ichida saqlanadi — Android
  versiyasi bilan bir xil chegaralar (asosiy README'ga qarang).
- **Baza shifrlanmagan** (oddiy SQLite) — faqat identity maxfiy kalitlari Windows DPAPI
  (`ProtectedData`, CurrentUser scope) bilan himoyalangan. Android'dagi to'liq SQLCipher
  darajasidagi baza shifrlash bu versiyada yo'q (foydalanuvchi tanlovi bilan ataylab
  soddalashtirilgan).
- **Kontakt qo'shish matn orqali** (QR JSON'ni nusxalash/joylashtirish) — webcam orqali
  QR skanerlash yo'q (desktop uchun kamera murakkabligisiz, ishonchli yechim sifatida
  tanlangan).
- Ikki haqiqiy klient (masalan, mobil + desktop) o'rtasidagi haqiqiy MQTT orqali xabar
  almashinuvi ushbu sessiyada avtomatik tekshirilmadi — protokol/wire-format
  muvofiqligi kod darajasida ta'minlangan (bir xil `MessageEnvelope` formati, bir xil
  `ContactCard` JSON maydonlari), lekin end-to-end ikki-klientli sinov keyingi bosqich.
