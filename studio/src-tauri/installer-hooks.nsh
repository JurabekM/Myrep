; TAMGA o'rnatuvchi hook'lari: Tauri NSIS shabloni ularni tegishli joyga qo'shadi.
;
; tamgad.exe ishlab turgan bo'lsa fayl band: yangilab ham, o'chirib ham bo'lmaydi.
; `tamga stop` kutilayotgan so'rovlarni rad etadi, oxirgi checkpoint'ni yozadi va jarayon
; chiqquncha kutadi. Jurnal va kalitlar (%LOCALAPPDATA%\tamga, imzo kaliti Credential Manager'da)
; o'chirilmaydi: bu dalil, uni foydalanuvchi o'zi saqlaydi yoki o'chiradi.
;
; K1: daemon `shutdown` ni faqat agent daraxtidan tashqaridagi boshqaruv dasturidan qabul qiladi.
; O'rnatuvchi agent ichidan ishga tushirilgan bo'lsa `stop` rad etiladi — shunda faqat shu
; o'rnatish papkasidagi tamgad.exe majburan yopiladi (oxirgi checkpoint keyingi ishga tushishda).

Var TamgaRc

!macro TAMGA_STOP_DAEMON
  nsExec::Exec '"$INSTDIR\tamga.exe" stop'
  Pop $TamgaRc
  ${If} $TamgaRc <> 0
    ; Tashqi qo'shtirnoq — backtick (NSIS), ichida PowerShell uchun ' va " ishlatiladi.
    nsExec::Exec `powershell -NoProfile -Command "Get-Process tamgad -ErrorAction SilentlyContinue | Where-Object { $$_.Path -eq '$INSTDIR\tamgad.exe' } | Stop-Process -Force"`
    Pop $TamgaRc
  ${EndIf}
!macroend

!macro NSIS_HOOK_PREINSTALL
  ; Yangilash: eski nusxa daemon'ini to'xtatamiz (birinchi o'rnatishda fayl yo'q).
  ${If} ${FileExists} "$INSTDIR\tamga.exe"
    !insertmacro TAMGA_STOP_DAEMON
  ${EndIf}
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  !insertmacro TAMGA_STOP_DAEMON
  ; To'liq o'chirishda (yangilash emas) Claude Code sozlamalaridan TAMGA hook'larini olamiz,
  ; aks holda ~/.claude/settings.json yo'q tamga-hook.exe ga ishora qilib qoladi.
  ; Hook ulanmagan bo'lsa buyruq faylga tegmaydi.
  ${If} $UpdateMode <> 1
    nsExec::Exec '"$INSTDIR\tamga.exe" uninstall claude-code --user'
    Pop $TamgaRc
  ${EndIf}
!macroend
