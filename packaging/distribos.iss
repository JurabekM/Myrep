; DistribOS AI — Windows installer (Inno Setup 6)
;
; Yig'ish:  ISCC.exe /DAppVersion=1.0.0 packaging\distribos.iss
; Odatda `packaging/build_windows.py` orqali chaqiriladi.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#define AppName "DistribOS AI"
#define AppPublisher "DistribOS"
#define ExeName "DistribOS.exe"

[Setup]
AppId={{7B3C4E2A-9D51-4F86-A2C7-DistribOS0001}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\DistribOS
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#ExeName}
UninstallDisplayName={#AppName}
OutputDir=..\dist
OutputBaseFilename=DistribOS-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Administrator huquqi TALAB QILINMAYDI. Savdo nuqtasidagi kompyuterda
; ko'pincha administrator paroli bo'lmaydi, va ma'lumotlar baribir
; foydalanuvchi profilida ({localappdata}) yotadi — ya'ni administrator
; rejimida o'rnatish hech qanday foyda bermaydi.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE

[Languages]
Name: "uz"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Ish stolida yorliq yaratish"; \
    GroupDescription: "Qo'shimcha yorliqlar"; Flags: unchecked

[Files]
Source: "..\dist\DistribOS\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\FOYDALANUVCHI_QOLLANMASI.md"; DestDir: "{app}\docs"; \
    Flags: ignoreversion skipifsourcedoesntexist
Source: "..\docs\ADMINISTRATOR_QOLLANMASI.md"; DestDir: "{app}\docs"; \
    Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{group}\{#AppName} — holat tekshiruvi"; Filename: "{app}\{#ExeName}"; \
    Parameters: "--check"
Name: "{group}\{#AppName} ni o'chirish"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "Dasturni ishga tushirish"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Log fayllari o'chiriladi, LEKIN ma'lumotlar bazasi va zaxira nusxalar
; TEGILMAYDI. Ular {localappdata}\DistribOS da qoladi: dasturni o'chirish
; korxonaning savdo tarixini yo'q qilmasligi kerak.
Type: filesandordirs; Name: "{localappdata}\DistribOS\logs"

[Messages]
uz.WelcomeLabel2=Ushbu dastur kompyuteringizga {#AppName} {#AppVersion} ni o'rnatadi.%n%nDistribOS AI markaziy serversiz ishlaydi: barcha ma'lumot shu kompyuterda saqlanadi va qurilmalar o'zaro to'g'ridan-to'g'ri sinxronlanadi.%n%nDavom etishdan oldin boshqa dasturlarni yopishingiz tavsiya etiladi.
uz.FinishedLabel=O'rnatish tugadi.%n%nMuhim: ma'lumotlar faqat shu kompyuterda saqlanadi. Zaxira nusxa olishni ODAT qiling — dastur ichida «Zaxira nusxa» bo'limi bor.
