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
Var TamgaFail

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

; Muhim qadam natijasini yig'adi. nsExec ishga tusha olmasa "error" qaytaradi — shuning uchun satr
; sifatida solishtiriladi (son sifatida "error" = 0, ya'ni "muvaffaqiyat" bo'lib qolardi).
!macro TAMGA_MUST what
  Pop $TamgaRc
  ${If} $TamgaRc != "0"
    StrCpy $TamgaFail "$TamgaFail ${what}=$TamgaRc"
  ${EndIf}
!macroend

!macro TAMGA_SERVICE_INSTALL
  StrCpy $TamgaFail ""
  ; Xizmat: virtual hisob, avto-start. Bor bo'lsa (yangilash) `create` xato beradi — muhimi `config`.
  ; Xizmat avval yaratiladi: `NT SERVICE\tamgad` SID'i ACL uchun shundan keyin aniqlanadi.
  nsExec::Exec 'sc.exe create tamgad binPath= "\"$INSTDIR\tamgad.exe\" --service" start= auto obj= "NT SERVICE\tamgad" DisplayName= "TAMGA daemon"'
  Pop $TamgaRc
  nsExec::Exec 'sc.exe config tamgad binPath= "\"$INSTDIR\tamgad.exe\" --service" start= auto obj= "NT SERVICE\tamgad"'
  !insertmacro TAMGA_MUST "sc-config"
  nsExec::Exec 'sc.exe description tamgad "TAMGA: AI agentlar uchun qora quti (himoyalangan rejim)"'
  Pop $TamgaRc
  nsExec::Exec 'sc.exe failure tamgad reset= 86400 actions= restart/5000/restart/5000/restart/60000'
  Pop $TamgaRc

  ; %ProgramData%\TAMGA: ishonchsiz oldingi papkani chetga olish, himoyalangan DACL bilan yaratish,
  ; reparse point'larga yurmaslik, yakuniy tekshiruv va belgi (service.json) — service-acl.ps1 da.
  ; Skript $INSTDIR da (Program Files — faqat administratorlar yoza oladi). NSIS satri 1024 belgi bilan
  ; cheklangani uchun bu mantiq buyruq qatorida emas.
  ${If} $TamgaFail == ""
    nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\service-acl.ps1" -InstallDir "$INSTDIR"'
    !insertmacro TAMGA_MUST "data-dir"
  ${EndIf}

  ${If} $TamgaFail == ""
    nsExec::Exec 'sc.exe start tamgad'
    !insertmacro TAMGA_MUST "sc-start"
  ${Else}
    ; Himoya kafolatlanmaydi — xizmat ishga tushirilmaydi.
    nsExec::Exec 'sc.exe config tamgad start= disabled'
    Pop $TamgaRc
  ${EndIf}
  ${If} $TamgaFail != ""
    MessageBox MB_ICONSTOP|MB_OK "TAMGA himoyalangan rejimi to'liq sozlanmadi:$\n$TamgaFail$\n$\nXizmat ishga tushirilmadi. Batafsil: o'rnatuvchi jurnali. O'rnatuvchini administrator sifatida qayta ishga tushiring." /SD IDOK
    SetErrorLevel 2
  ${EndIf}
!macroend

!macro TAMGA_SERVICE_REMOVE
  !insertmacro TAMGA_SERVICE_STOP
  nsExec::Exec 'sc.exe delete tamgad'
  Pop $TamgaRc
  ; Belgi qolsa, hook'lar mavjud bo'lmagan xizmatni kutib har amalni bloklardi (fail-closed).
  ; Jurnal, checkpoint'lar va ochiq kalit (dalil) saqlanadi.
  ; Yo'l muhit o'zgaruvchisidan emas (foydalanuvchi HKCU\Environment orqali uni almashtira oladi).
  nsExec::Exec `powershell -NoProfile -Command "Remove-Item -LiteralPath (Join-Path ([Environment]::GetFolderPath('CommonApplicationData')) 'TAMGA\service.json') -Force -ErrorAction SilentlyContinue"`
  Pop $TamgaRc
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
