; FinTx Windows o'rnatuvchisi (Inno Setup 6).
; Yig'ish:  ISCC /DAppVersion=0.1.0 packaging\windows\fintx.iss
; Kirish:   dist\FinTx\  (PyInstaller natijasi)
; Chiqish:  dist\FinTx-<versiya>-Windows-Setup.exe
;
; Administrator huquqi so'ralmaydi: dastur faqat joriy foydalanuvchi uchun
; %LOCALAPPDATA%\Programs\FinTx papkasiga o'rnatiladi.
; O'chirilganda foydalanuvchi ma'lumotlari (%APPDATA%\FinTx\fintx.db) saqlanib qoladi.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6F3B2D4E-9A51-4C7B-8E2F-1D5A7C9B3E40}
AppName=FinTx
AppVersion={#AppVersion}
AppVerName=FinTx {#AppVersion}
VersionInfoVersion={#AppVersion}
VersionInfoDescription=FinTx o'rnatuvchisi
DefaultDirName={autopf}\FinTx
DefaultGroupName=FinTx
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=..\..\dist
OutputBaseFilename=FinTx-{#AppVersion}-Windows-Setup
SetupIconFile=..\icon.ico
UninstallDisplayIcon={app}\FinTx.exe
UninstallDisplayName=FinTx
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "uz"; MessagesFile: "compiler:Default.isl"

; O'rnatish ustasining asosiy matnlari o'zbekcha (qolganlari standart inglizcha).
[Messages]
SetupAppTitle=O'rnatish
SetupWindowTitle=O'rnatish - %1
ButtonBack=< &Orqaga
ButtonNext=&Keyingi >
ButtonInstall=&O'rnatish
ButtonCancel=Bekor qilish
ButtonFinish=&Tugatish
ButtonBrowse=&Tanlash...
ButtonYes=&Ha
ButtonNo=&Yo'q
WelcomeLabel1=[name] o'rnatish ustasiga xush kelibsiz
WelcomeLabel2=Bu usta kompyuteringizga [name/ver] dasturini o'rnatadi.%n%nDavom etishdan oldin boshqa dasturlarni yopish tavsiya etiladi.
ClickNext=Davom etish uchun "Keyingi", chiqish uchun "Bekor qilish" tugmasini bosing.
WizardSelectDir=O'rnatish papkasi
SelectDirDesc=[name] qayerga o'rnatilsin?
SelectDirLabel3=[name] quyidagi papkaga o'rnatiladi.
SelectDirBrowseLabel=Davom etish uchun "Keyingi" tugmasini bosing. Boshqa papka tanlash uchun "Tanlash" tugmasini bosing.
WizardSelectTasks=Qo'shimcha amallar
SelectTasksDesc=Qaysi qo'shimcha amallar bajarilsin?
SelectTasksLabel2=[name] o'rnatilayotganda bajariladigan qo'shimcha amallarni belgilang, so'ng "Keyingi" tugmasini bosing.
WizardReady=O'rnatishga tayyor
ReadyLabel1=[name] dasturini kompyuteringizga o'rnatish uchun hammasi tayyor.
ReadyLabel2a=O'rnatishni boshlash uchun "O'rnatish" tugmasini bosing. Sozlamalarni o'zgartirish uchun "Orqaga" tugmasini bosing.
ReadyLabel2b=O'rnatishni boshlash uchun "O'rnatish" tugmasini bosing.
WizardInstalling=O'rnatilmoqda
InstallingLabel=[name] kompyuteringizga o'rnatilmoqda, iltimos kuting.
FinishedHeadingLabel=[name] o'rnatildi
FinishedLabelNoIcons=[name] kompyuteringizga o'rnatildi.
FinishedLabel=[name] kompyuteringizga o'rnatildi. Dasturni Boshlash menyusidagi yorliq orqali ishga tushirishingiz mumkin.
ClickFinish=O'rnatishni yakunlash uchun "Tugatish" tugmasini bosing.
ExitSetupTitle=O'rnatishdan chiqish
ExitSetupMessage=O'rnatish tugallanmadi. Hozir chiqsangiz, dastur o'rnatilmaydi.%n%nO'rnatishdan chiqilsinmi?

[Tasks]
Name: "desktopicon"; Description: "Ish stolida yorliq yaratish"; Flags: unchecked

[Files]
Source: "..\..\dist\FinTx\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\FinTx"; Filename: "{app}\FinTx.exe"; Comment: "Moliyaviy tranzaksiyalar (desktop)"
Name: "{autoprograms}\FinTx (terminal)"; Filename: "{app}\fintx-cli.exe"; Comment: "Moliyaviy tranzaksiyalar (terminal)"
Name: "{autodesktop}\FinTx"; Filename: "{app}\FinTx.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\FinTx.exe"; Description: "FinTx dasturini ishga tushirish"; Flags: nowait postinstall skipifsilent
