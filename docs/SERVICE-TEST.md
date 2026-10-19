# Himoyalangan rejim — qo'lda sinov ro'yxati (administrator kerak)

Bu qadamlarni **foydalanuvchi** bajaradi: xizmat o'rnatish va tizim sozlamalarini o'zgartirish
administrator huquqini talab qiladi. Har bir qadam natijasini (buyruq chiqishi yoki skrinshot)
saqlang va qaytaring.

Belgilar: **[A]** — administrator terminali (Start → «Terminal (Administrator)»), **[U]** — oddiy terminal.

## 0. Tayyorgarlik

- Oddiy rejimdagi TAMGA o'rnatilgan bo'lsa, avval uni o'chiring (Sozlamalar → Ilovalar → TAMGA Studio).
  Ikkalasini birga o'rnatmang.
- `TAMGA Studio Protected_0.1.0_x64-setup.exe` ni ishga tushiring → UAC'ni tasdiqlang.

## 1. Xizmat o'rnatildi

```powershell
sc.exe query tamgad          # [U] STATE: RUNNING
sc.exe qc tamgad             # [U] SERVICE_START_NAME: NT SERVICE\tamgad, BINARY_PATH_NAME: ...tamgad.exe" --service
Get-Content "$env:ProgramData\TAMGA\service.json"      # [U] mode=service, pipe, install_dir
icacls "$env:ProgramData\TAMGA"                        # [U] Users: (RX), NT SERVICE\tamgad: (M)
icacls "$env:ProgramData\TAMGA\secrets"                # [U] Users YO'Q
Get-ChildItem "$env:ProgramData\TAMGA"                 # [U] public-key.json, logs\, config.json
```

## 2. Oddiy foydalanuvchi daemon'ni boshqara olmaydi [U]

```powershell
& "C:\Program Files\TAMGA Studio\tamga.exe" status         # ishlaydi (o'qish)
& "C:\Program Files\TAMGA Studio\tamga.exe" stop           # RAD: "administrator (UAC) tasdig'i bilan"
Stop-Process -Name tamgad -Force                            # RAD: Access is denied
Set-Content "$env:ProgramData\TAMGA\config.json" "{}"       # RAD: Access denied
Get-ChildItem "$env:ProgramData\TAMGA\secrets"              # RAD: Access denied
Remove-Item "$env:ProgramData\TAMGA\service.json"           # RAD: Access denied
```

## 3. Hook'lar xizmatga yozadi [U]

1. TAMGA Studio → Sozlamalar: «O'rnatish rejimi: himoyalangan (Windows xizmati)» ko'rinsin.
2. «Claude Code'ga ulash» ni bosing.
3. Yangi Claude Code sessiyasida biror buyruq bajaring (masalan, `git status`).
4. Studio → Jonli: yozuvlar paydo bo'lsin. Yozuv tafsilotida `actor.user` — sizning SID'ingiz
   (`S-1-5-21-…`), xizmat hisobi nomi emas.
5. `tamga verify` — OK.

## 4. Administrator boshqaruvi

1. Studio → Sozlamalar → «Daemon ishlamasa: Bloklash (strict)» → UAC so'rovi chiqsin → tasdiqlang →
   sozlama o'zgarsin. UAC'ni rad etsangiz — «UAC so'rovi rad etildi».
2. [A] `& "C:\Program Files\TAMGA Studio\tamga.exe" key rotate` — ishlasin.
3. Studio → Yaxlitlik: kalitlar zanjirida yangi kalit.

## 5. Fail-closed

1. [A] `net stop tamgad`
2. Claude Code'da biror buyruq bajaring → **bloklansin** («daemon ishlamayapti»).
3. [A] `net start tamgad` → yana ishlasin.

## 5a. Pipe nomini egallab bo'lmaydi

1. [A] `net stop tamgad`
2. [U] `$env:TAMGA_HOME = "$env:TEMP\tamga-fake"; & "C:\Program Files\TAMGA Studio\tamgad.exe"` →
   **rad**: «himoyalangan rejim o'rnatilgan — daemon faqat Windows xizmati sifatida ishlaydi», exit 2.
3. [U] `& "C:\Program Files\TAMGA Studio\tamga.exe" status` → «xizmati ishlamayapti» yoki ulanish xatosi
   (hech qachon `TAMGA_HOME` dagi soxta jurnal emas).
4. [A] `net start tamgad`.

## 6. Qayta ishga tushish va yiqilish

1. Kompyuterni qayta yoqing → `sc query tamgad` RUNNING (avto-start).
2. `tamga verify` — OK, zanjir uzilmagan.

## 7. O'chirish

1. Sozlamalar → Ilovalar → TAMGA Studio → O'chirish (UAC).
2. `sc.exe query tamgad` → «does not exist».
3. `Test-Path "$env:ProgramData\TAMGA\service.json"` → False.
4. `Get-ChildItem "$env:ProgramData\TAMGA\logs"` → jurnal (dalil) saqlangan.
5. `~/.claude/settings.json` da TAMGA hook'lari yo'q.

## Natija

Har bo'lim uchun: ✅ / ❌ va chiqish. ❌ bo'lsa — to'liq xato matni va
`%ProgramData%\TAMGA\tamgad.log` ning oxirgi 20 qatori (administrator o'qiy oladi).
