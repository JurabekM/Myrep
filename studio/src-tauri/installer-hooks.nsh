; TAMGA o'rnatuvchi hook'lari: Tauri NSIS shabloni ularni tegishli joyga qo'shadi.
;
; Ikki alohida o'rnatuvchi (docs/SERVICE-DESIGN.md), farq kompilyatsiya vaqtida (`INSTALLMODE`):
;   * currentUser — oddiy rejim: daemon foydalanuvchi huquqida, administrator kerak emas.
;     ("both" ishlatilmaydi: u administrator foydalanuvchidan oddiy o'rnatishda ham UAC so'raydi.)
;   * perMachine (`TAMGA Studio Protected`, administrator) — himoyalangan rejim: daemon
;     `NT SERVICE\tamgad` virtual hisobidagi Windows xizmati, ma'lumotlar %ProgramData%\TAMGA da,
;     oddiy foydalanuvchi ularni faqat o'qiy oladi, kalitlar va vault'ga kira olmaydi.
;
; tamgad.exe ishlab turgan bo'lsa fayl band: yangilab ham, o'chirib ham bo'lmaydi — avval to'xtatiladi.
; Jurnal va kalitlar o'chirilmaydi: bu dalil, uni foydalanuvchi o'zi saqlaydi yoki o'chiradi.

Var TamgaRc
Var TamgaPD

; Eslatma: bu fayl shablonda `INSTALLMODE` aniqlanishidan oldin ulanadi, shuning uchun rejim
; tekshiruvi makrolar ichida (ular keyinroq, aniqlangandan so'ng qo'yiladi).

; ---------------------------------------------------------------- oddiy rejim

; K1: daemon `shutdown` ni faqat agent daraxtidan tashqaridagi boshqaruv dasturidan qabul qiladi.
; O'rnatuvchi agent ichidan ishga tushirilgan bo'lsa `stop` rad etiladi — shunda faqat shu
; o'rnatish papkasidagi tamgad.exe majburan yopiladi (oxirgi checkpoint keyingi ishga tushishda).
!macro TAMGA_STOP_DAEMON
  nsExec::Exec '"$INSTDIR\tamga.exe" stop'
  Pop $TamgaRc
  ${If} $TamgaRc <> 0
    ; Tashqi qo'shtirnoq — backtick (NSIS), ichida PowerShell uchun ' va " ishlatiladi.
    nsExec::Exec `powershell -NoProfile -Command "Get-Process tamgad -ErrorAction SilentlyContinue | Where-Object { $$_.Path -eq '$INSTDIR\tamgad.exe' } | Stop-Process -Force"`
    Pop $TamgaRc
  ${EndIf}
!macroend

; ---------------------------------------------------------------- himoyalangan rejim

!macro TAMGA_SERVICE_STOP
  ; `net stop` xizmat to'xtaguncha kutadi (oxirgi checkpoint yoziladi). Xizmat bo'lmasa — zararsiz.
  nsExec::Exec 'net.exe stop tamgad'
  Pop $TamgaRc
!macroend

!macro TAMGA_SERVICE_INSTALL
  ReadEnvStr $TamgaPD "ProgramData"
  ; %ProgramData% da oddiy foydalanuvchi ham papka yarata oladi. Agar TAMGA papkasi oldindan bor va
  ; uning egasi administratorlar yoki SYSTEM bo'lmasa — u bizniki emas (egasi ACL'ni qayta o'zgartira
  ; olardi, ichiga oldindan fayl qo'yilgan bo'lishi mumkin). Uni chetga olib, yangisini yaratamiz.
  nsExec::Exec `powershell -NoProfile -Command "$$p = Join-Path $$env:ProgramData 'TAMGA'; if (Test-Path $$p) { $$o = (Get-Acl $$p).GetOwner([Security.Principal.SecurityIdentifier]).Value; if ($$o -ne 'S-1-5-32-544' -and $$o -ne 'S-1-5-18') { Rename-Item $$p ('TAMGA.untrusted-' + (Get-Date -Format yyyyMMddHHmmss)) } }"`
  Pop $TamgaRc
  CreateDirectory "$TamgaPD\TAMGA\logs"
  CreateDirectory "$TamgaPD\TAMGA\vault"
  CreateDirectory "$TamgaPD\TAMGA\secrets"
  CreateDirectory "$TamgaPD\TAMGA\spool"
  CreateDirectory "$TamgaPD\TAMGA\policies"

  ; Xizmat: virtual hisob, avto-start. Bor bo'lsa (yangilash) — `config` yo'lni yangilaydi.
  nsExec::Exec 'sc.exe create tamgad binPath= "\"$INSTDIR\tamgad.exe\" --service" start= auto obj= "NT SERVICE\tamgad" DisplayName= "TAMGA daemon"'
  Pop $TamgaRc
  nsExec::Exec 'sc.exe config tamgad binPath= "\"$INSTDIR\tamgad.exe\" --service" start= auto obj= "NT SERVICE\tamgad"'
  Pop $TamgaRc
  nsExec::Exec 'sc.exe description tamgad "TAMGA: AI agentlar uchun qora quti (himoyalangan rejim)"'
  Pop $TamgaRc
  nsExec::Exec 'sc.exe failure tamgad reset= 86400 actions= restart/5000/restart/5000/restart/60000'
  Pop $TamgaRc

  ; Egasi — administratorlar (ACL ni faqat ular o'zgartira oladi).
  nsExec::Exec 'icacls.exe "$TamgaPD\TAMGA" /setowner *S-1-5-32-544 /T /C /Q'
  Pop $TamgaRc
  ; ACL (SID bilan — Windows tiliga bog'liq emas): SYSTEM va administratorlar — to'liq; xizmat —
  ; o'zgartirish; foydalanuvchilar (S-1-5-32-545) — faqat o'qish. Meros uzilib, eskisi almashtiriladi.
  nsExec::Exec 'icacls.exe "$TamgaPD\TAMGA" /inheritance:r /grant:r *S-1-5-18:(OI)(CI)F *S-1-5-32-544:(OI)(CI)F "NT SERVICE\tamgad:(OI)(CI)M" *S-1-5-32-545:(OI)(CI)RX /T /C /Q'
  Pop $TamgaRc
  ; Kalitlar, vault va spool — foydalanuvchilarga umuman yopiq.
  nsExec::Exec 'icacls.exe "$TamgaPD\TAMGA\secrets" /inheritance:r /grant:r *S-1-5-18:(OI)(CI)F *S-1-5-32-544:(OI)(CI)F "NT SERVICE\tamgad:(OI)(CI)M" /T /C /Q'
  Pop $TamgaRc
  nsExec::Exec 'icacls.exe "$TamgaPD\TAMGA\vault" /inheritance:r /grant:r *S-1-5-18:(OI)(CI)F *S-1-5-32-544:(OI)(CI)F "NT SERVICE\tamgad:(OI)(CI)M" /T /C /Q'
  Pop $TamgaRc
  nsExec::Exec 'icacls.exe "$TamgaPD\TAMGA\spool" /inheritance:r /grant:r *S-1-5-18:(OI)(CI)F *S-1-5-32-544:(OI)(CI)F "NT SERVICE\tamgad:(OI)(CI)M" /T /C /Q'
  Pop $TamgaRc

  ; Belgi: mijozlar (hook, CLI, Studio) himoyalangan rejimni shundan biladi. Ildiz ACL'ini meros
  ; oladi — foydalanuvchi o'qiydi, o'zgartira olmaydi. JSON (yo'ldagi `\`) PowerShell bilan to'g'ri ekranlanadi.
  nsExec::Exec `powershell -NoProfile -Command "[IO.File]::WriteAllText('$TamgaPD\TAMGA\service.json', (@{ mode = 'service'; pipe = 'tamga-service'; install_dir = '$INSTDIR' } | ConvertTo-Json))"`
  Pop $TamgaRc

  nsExec::Exec 'sc.exe start tamgad'
  Pop $TamgaRc
!macroend

!macro TAMGA_SERVICE_REMOVE
  !insertmacro TAMGA_SERVICE_STOP
  nsExec::Exec 'sc.exe delete tamgad'
  Pop $TamgaRc
  ; Belgi qolsa, hook'lar mavjud bo'lmagan xizmatni kutib har amalni bloklardi (fail-closed).
  ; Jurnal, checkpoint'lar va ochiq kalit (dalil) saqlanadi.
  ReadEnvStr $TamgaPD "ProgramData"
  Delete "$TamgaPD\TAMGA\service.json"
!macroend

; ---------------------------------------------------------------- Tauri hook'lari

!macro NSIS_HOOK_PREINSTALL
  !if "${INSTALLMODE}" == "perMachine"
    !insertmacro TAMGA_SERVICE_STOP
  !endif
  ; Yangilash: eski nusxa daemon'ini to'xtatamiz (birinchi o'rnatishda fayl yo'q).
  ${If} ${FileExists} "$INSTDIR\tamga.exe"
    !insertmacro TAMGA_STOP_DAEMON
  ${EndIf}
!macroend

!macro NSIS_HOOK_POSTINSTALL
  !if "${INSTALLMODE}" == "perMachine"
    !insertmacro TAMGA_SERVICE_INSTALL
  !endif
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  !if "${INSTALLMODE}" == "perMachine"
    ${If} $UpdateMode = 1
      !insertmacro TAMGA_SERVICE_STOP
    ${Else}
      !insertmacro TAMGA_SERVICE_REMOVE
    ${EndIf}
  !else
    !insertmacro TAMGA_STOP_DAEMON
  !endif
  ; To'liq o'chirishda (yangilash emas) Claude Code sozlamalaridan TAMGA hook'larini olamiz,
  ; aks holda ~/.claude/settings.json yo'q tamga-hook.exe ga ishora qilib qoladi.
  ; Hook ulanmagan bo'lsa buyruq faylga tegmaydi.
  ${If} $UpdateMode <> 1
    nsExec::Exec '"$INSTDIR\tamga.exe" uninstall claude-code --user'
    Pop $TamgaRc
  ${EndIf}
!macroend
