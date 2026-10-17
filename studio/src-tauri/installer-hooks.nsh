; TAMGA o'rnatuvchi hook'lari: Tauri NSIS shabloni ularni tegishli joyga qo'shadi.
;
; tamgad.exe ishlab turgan bo'lsa fayl band: yangilab ham, o'chirib ham bo'lmaydi.
; `tamga stop` kutilayotgan so'rovlarni rad etadi, oxirgi checkpoint'ni yozadi va jarayon
; chiqquncha kutadi. Jurnal va kalitlar (%LOCALAPPDATA%\tamga, imzo kaliti Credential Manager'da)
; o'chirilmaydi: bu dalil, uni foydalanuvchi o'zi saqlaydi yoki o'chiradi.

Var TamgaRc

!macro NSIS_HOOK_PREINSTALL
  ; Yangilash: eski nusxa daemon'ini to'xtatamiz (birinchi o'rnatishda fayl yo'q).
  IfFileExists "$INSTDIR\tamga.exe" 0 +3
    nsExec::Exec '"$INSTDIR\tamga.exe" stop'
    Pop $TamgaRc
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  nsExec::Exec '"$INSTDIR\tamga.exe" stop'
  Pop $TamgaRc
  ; To'liq o'chirishda (yangilash emas) Claude Code sozlamalaridan TAMGA hook'larini olamiz,
  ; aks holda ~/.claude/settings.json yo'q tamga-hook.exe ga ishora qilib qoladi.
  ; Hook ulanmagan bo'lsa buyruq faylga tegmaydi.
  ${If} $UpdateMode <> 1
    nsExec::Exec '"$INSTDIR\tamga.exe" uninstall claude-code --user'
    Pop $TamgaRc
  ${EndIf}
!macroend
