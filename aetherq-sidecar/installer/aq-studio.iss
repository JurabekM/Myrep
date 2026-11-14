; AETHER-Q Sidecar Studio o'rnatuvchisi. Yig'ish: scripts\package-studio.ps1 (testlar o'tsa, dist\studio\ ni
; tayyorlaydi va shu faylni ISCC bilan kompilyatsiya qiladi).
; Administrator huquqi so'ralmaydi: dastur {localappdata}\Programs\AETHER-Q Sidecar Studio ga o'rnatiladi.
; Foydalanuvchi ma'lumoti (profillar, kalitlar, jurnal) %APPDATA%\AETHER-Q\Studio da — o'chirishda saqlanib qoladi
; (maxfiy kalitlarni o'chirib yubormaslik uchun).

#define AppVersion "0.1.0"
#define AppName "AETHER-Q Sidecar Studio"

[Setup]
AppId={{9F3C2B71-5D4E-4A8B-9C61-2E7F0A4B8D13}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=AETHER-Q
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=AETHER-Q-Studio-Setup-{#AppVersion}
SetupIconFile=..\crates\aq-studio\assets\icon.ico
UninstallDisplayIcon={app}\aq-studio.exe
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern dark
WizardImageFile=wizard.bmp,wizard-125.bmp
WizardSmallImageFile=wizard-small.bmp,wizard-small-125.bmp
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "uz"; MessagesFile: "compiler:Default.isl"

[Messages]
uz.SetupAppTitle=O'rnatish
uz.SetupWindowTitle=O'rnatish - %1
uz.ButtonBack=< &Orqaga
uz.ButtonNext=&Keyingi >
uz.ButtonInstall=&O'rnatish
uz.ButtonOK=OK
uz.ButtonCancel=Bekor qilish
uz.ButtonYes=&Ha
uz.ButtonNo=&Yo'q
uz.ButtonFinish=&Tugatish
uz.ButtonBrowse=&Tanlash...
uz.ButtonWizardBrowse=T&anlash...
uz.ButtonNewFolder=&Yangi papka
uz.BrowseDialogTitle=Papkani tanlang
uz.BrowseDialogLabel=Ro'yxatdan papkani tanlang va OK tugmasini bosing.
uz.ExitSetupTitle=O'rnatishdan chiqish
uz.ExitSetupMessage=O'rnatish tugallanmadi. Hozir chiqsangiz, dastur o'rnatilmaydi.%n%nO'rnatishni keyinroq qayta ishga tushirishingiz mumkin.%n%nChiqilsinmi?
uz.WelcomeLabel1=[name] o'rnatish sehrgariga xush kelibsiz
uz.WelcomeLabel2=Kompyuteringizga [name/ver] o'rnatiladi: post-kvant AETHER-Q tunellarini sozlash va boshqarish dasturi.%n%nAdministrator huquqi talab qilinmaydi.
uz.WizardSelectDir=O'rnatish joyini tanlang
uz.SelectDirDesc=[name] qayerga o'rnatilsin?
uz.SelectDirLabel3=[name] quyidagi papkaga o'rnatiladi.
uz.SelectDirBrowseLabel=Davom etish uchun "Keyingi" ni bosing. Boshqa papka tanlash uchun "Tanlash" ni bosing.
uz.DiskSpaceMBLabel=Kamida [mb] MB bo'sh joy kerak.
uz.WizardSelectTasks=Qo'shimcha vazifalar
uz.SelectTasksDesc=Qaysi qo'shimcha vazifalar bajarilsin?
uz.SelectTasksLabel2=[name] o'rnatilayotganda bajariladigan vazifalarni tanlang va "Keyingi" ni bosing.
uz.WizardReady=O'rnatishga tayyor
uz.ReadyLabel1=[name] kompyuteringizga o'rnatilishga tayyor.
uz.ReadyLabel2a=O'rnatishni boshlash uchun "O'rnatish" ni bosing, sozlamalarni o'zgartirish uchun "Orqaga" ni bosing.
uz.ReadyLabel2b=O'rnatishni boshlash uchun "O'rnatish" ni bosing.
uz.ReadyMemoDir=O'rnatish joyi:
uz.ReadyMemoTasks=Qo'shimcha vazifalar:
uz.WizardPreparing=O'rnatishga tayyorlanmoqda
uz.PreparingDesc=[name] o'rnatishga tayyorlanmoqda.
uz.WizardInstalling=O'rnatilmoqda
uz.InstallingLabel=[name] o'rnatilmoqda, kuting...
uz.StatusExtractFiles=Fayllar chiqarilmoqda...
uz.StatusCreateIcons=Yorliqlar yaratilmoqda...
uz.StatusSavingUninstall=O'chirish ma'lumoti saqlanmoqda...
uz.StatusClosingApplications=Ochiq dasturlar yopilmoqda...
uz.FinishedHeadingLabel=[name] o'rnatish yakunlandi
uz.FinishedLabelNoIcons=[name] kompyuteringizga o'rnatildi.
uz.FinishedLabel=[name] kompyuteringizga o'rnatildi. Dasturni Start menyusidagi yorliq orqali ochishingiz mumkin.
uz.ClickFinish=O'rnatishdan chiqish uchun "Tugatish" ni bosing.
uz.SetupAborted=O'rnatish tugallanmadi.%n%nMuammoni bartaraf etib, qayta urinib ko'ring.
uz.ConfirmUninstall=%1 o'chirilsinmi?%n%nProfillar va kalitlar (%APPDATA%\AETHER-Q\Studio) saqlanib qoladi.
uz.UninstallStatusLabel=%1 kompyuterdan o'chirilmoqda, kuting...
uz.UninstalledAll=%1 kompyuterdan o'chirildi.
uz.UninstalledMost=%1 o'chirildi.%n%nAyrim elementlarni qo'lda o'chirishingiz mumkin.
uz.UninstallAppTitle=O'chirish
uz.UninstallAppFullTitle=%1 ni o'chirish
uz.SetupAppRunningError=O'rnatuvchi %1 ishlab turganini aniqladi.%n%nUning barcha oynalarini yoping va davom etish uchun OK ni, chiqish uchun "Bekor qilish" ni bosing.
uz.UninstallAppRunningError=O'chiruvchi %1 ishlab turganini aniqladi.%n%nUning barcha oynalarini yoping va davom etish uchun OK ni, chiqish uchun "Bekor qilish" ni bosing.
uz.WizardLicense=Litsenziya shartnomasi
uz.PrepareToInstallNeedsRestart=Kompyuterni qayta yuklash kerak.
uz.ApplicationsFound=Quyidagi dasturlar o'rnatuvchi yangilashi kerak bo'lgan fayllarni ishlatmoqda. O'rnatuvchiga ularni avtomatik yopishga ruxsat bering.
uz.ApplicationsFound2=Quyidagi dasturlar o'rnatuvchi yangilashi kerak bo'lgan fayllarni ishlatmoqda. O'rnatuvchiga ularni avtomatik yopishga ruxsat bering. O'rnatish tugagach, ular qayta ishga tushiriladi.
uz.CloseApplications=Dasturlarni &avtomatik yopish
uz.DontCloseApplications=Dasturlarni &yopmaslik

[CustomMessages]
uz.AdditionalIcons=Qo'shimcha yorliqlar:
uz.CreateDesktopIcon=Ish stolida &yorliq yaratish
uz.LaunchProgram=%1 ni ishga tushirish

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\studio\aq-studio.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\studio\aq-sidecar.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\studio\aqctl.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\studio\aether_new.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\studio\README.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\aq-studio.exe"
Name: "{group}\{#AppName} qo'llanmasi"; Filename: "{app}\README.txt"
Name: "{group}\{#AppName} ni o'chirish"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\aq-studio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\aq-studio.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
