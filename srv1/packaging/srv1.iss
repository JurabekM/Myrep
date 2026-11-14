; SRV_1 o'rnatuvchisi (Inno Setup 6). Yig'ish: packaging\build.ps1
; Faqat ASCII: o'zbekcha matnda oddiy apostrof ishlatiladi.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef StageDir
  #define StageDir "..\dist\SRV_1"
#endif
#ifndef OutputDir
  #define OutputDir "..\release"
#endif
#define PowerShellExe "{sys}\WindowsPowerShell\v1.0\powershell.exe"

[Setup]
AppId={{8C1F3B52-6E0A-4D0B-9A41-5E7D1A0C7B10}
AppName=SRV_1
AppVersion={#AppVersion}
AppVerName=SRV_1 {#AppVersion}
AppPublisher=SRV_1
DefaultDirName={autopf}\SRV_1
DefaultGroupName=SRV_1
DisableProgramGroupPage=yes
; Standart: hamma foydalanuvchilar uchun (administrator). "Faqat men uchun" ham tanlanadi -
; unda UAC so'ralmaydi, lekin Windows xizmati qadami baribir administrator so'raydi.
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=SRV_1-Setup-{#AppVersion}
SetupIconFile=..\shell\srv1_shell\srv1.ico
UninstallDisplayIcon={app}\shell\srv1_shell\srv1.ico
UninstallDisplayName=SRV_1 {#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
; O'zbekcha .isl yo'q: inglizcha asos, ko'rinadigan xabarlar [Messages] da o'girilgan.
Name: "uz"; MessagesFile: "compiler:Default.isl"

[Messages]
uz.SetupAppTitle=O'rnatish
uz.SetupWindowTitle=O'rnatish - %1
uz.UninstallAppTitle=Olib tashlash
uz.UninstallAppFullTitle=%1 ni olib tashlash
uz.InformationTitle=Ma'lumot
uz.ConfirmTitle=Tasdiqlash
uz.ErrorTitle=Xato
uz.WindowsVersionNotSupported=Bu dastur kompyuteringizdagi Windows versiyasida ishlamaydi (Windows 10 yoki yangisi kerak).
uz.OnlyOnTheseArchitectures=Bu dastur faqat quyidagi protsessor arxitekturalari uchun mo'ljallangan Windows'ga o'rnatiladi:%n%n%1
uz.AdminPrivilegesRequired=Bu dasturni o'rnatish uchun administrator sifatida kirgan bo'lishingiz kerak.
uz.PrivilegesRequiredOverrideTitle=O'rnatish turini tanlang
uz.PrivilegesRequiredOverrideInstruction=O'rnatish turini tanlang
uz.PrivilegesRequiredOverrideText1=%1 ni hamma foydalanuvchilar uchun (administrator huquqi kerak) yoki faqat siz uchun o'rnatish mumkin.
uz.PrivilegesRequiredOverrideText2=%1 ni faqat siz uchun yoki hamma foydalanuvchilar uchun (administrator huquqi kerak) o'rnatish mumkin.
uz.PrivilegesRequiredOverrideAllUsers=&Hamma foydalanuvchilar uchun
uz.PrivilegesRequiredOverrideAllUsersRecommended=&Hamma foydalanuvchilar uchun (tavsiya etiladi)
uz.PrivilegesRequiredOverrideCurrentUser=Faqat &men uchun
uz.PrivilegesRequiredOverrideCurrentUserRecommended=Faqat &men uchun (tavsiya etiladi)
uz.ExitSetupTitle=O'rnatishdan chiqish
uz.ExitSetupMessage=O'rnatish tugamadi. Hozir chiqsangiz, dastur o'rnatilmaydi.%n%nO'rnatishni keyin qayta ishga tushirishingiz mumkin.%n%nChiqilsinmi?
uz.ButtonBack=< &Orqaga
uz.ButtonNext=&Keyingi >
uz.ButtonInstall=O'&rnatish
uz.ButtonOK=OK
uz.ButtonCancel=Bekor qilish
uz.ButtonYes=&Ha
uz.ButtonNo=&Yo'q
uz.ButtonFinish=&Tugatish
uz.ButtonBrowse=&Tanlash...
uz.ButtonWizardBrowse=&Tanlash...
uz.ButtonNewFolder=&Yangi papka
uz.ClickNext=Davom etish uchun "Keyingi"ni, chiqish uchun "Bekor qilish"ni bosing.
uz.BrowseDialogTitle=Papkani tanlash
uz.BrowseDialogLabel=Ro'yxatdan papkani tanlang va OK ni bosing.
uz.WizardSelectDir=O'rnatish papkasi
uz.SelectDirDesc=[name] qayerga o'rnatilsin?
uz.SelectDirLabel3=[name] quyidagi papkaga o'rnatiladi.
uz.SelectDirBrowseLabel=Davom etish uchun "Keyingi"ni bosing. Boshqa papka kerak bo'lsa, "Tanlash"ni bosing.
uz.DiskSpaceGBLabel=Kamida [gb] GB bo'sh joy kerak.
uz.DiskSpaceMBLabel=Kamida [mb] MB bo'sh joy kerak.
uz.InvalidPath=Disk harfi bilan to'liq yo'l kiriting, masalan:%n%nC:\APP%n%nyoki tarmoq yo'li:%n%n\\server\share
uz.DiskSpaceWarningTitle=Disk joyi yetarli emas
uz.DiskSpaceWarning=O'rnatish uchun kamida %1 KB bo'sh joy kerak, tanlangan diskda esa %2 KB bor.%n%nBaribir davom etilsinmi?
uz.DirExistsTitle=Papka mavjud
uz.DirExists=Papka:%n%n%1%n%nallaqachon mavjud. Baribir shu papkaga o'rnatilsinmi?
uz.WizardSelectTasks=Qo'shimcha vazifalar
uz.SelectTasksDesc=Qaysi qo'shimcha vazifalar bajarilsin?
uz.SelectTasksLabel2=[name] o'rnatilayotganda bajariladigan qo'shimcha vazifalarni belgilang va "Keyingi"ni bosing.
uz.WizardReady=O'rnatishga tayyor
uz.ReadyLabel1=[name] ni kompyuteringizga o'rnatish uchun hammasi tayyor.
uz.ReadyLabel2a=Boshlash uchun "O'rnatish"ni bosing; sozlamalarni ko'rib chiqish yoki o'zgartirish uchun "Orqaga"ni bosing.
uz.ReadyLabel2b=Boshlash uchun "O'rnatish"ni bosing.
uz.ReadyMemoDir=O'rnatish papkasi:
uz.ReadyMemoTasks=Qo'shimcha vazifalar:
uz.WizardPreparing=O'rnatishga tayyorgarlik
uz.PreparingDesc=[name] ni o'rnatishga tayyorgarlik ko'rilmoqda.
uz.CannotContinue=O'rnatishni davom ettirib bo'lmaydi. Chiqish uchun "Bekor qilish"ni bosing.
uz.ApplicationsFound=Quyidagi dasturlar yangilanishi kerak bo'lgan fayllarni ishlatmoqda. O'rnatuvchiga ularni yopishga ruxsat berish tavsiya etiladi.
uz.ApplicationsFound2=Quyidagi dasturlar yangilanishi kerak bo'lgan fayllarni ishlatmoqda. O'rnatuvchiga ularni yopishga ruxsat berish tavsiya etiladi.
uz.CloseApplications=Dasturlarni &avtomatik yopish
uz.DontCloseApplications=Dasturlarni &yopmaslik
uz.ErrorCloseApplications=Dasturlarning hammasini avtomatik yopib bo'lmadi. Davom etishdan oldin SRV_1 oynasi va yadrosini yoping.
uz.WizardInstalling=O'rnatilmoqda
uz.InstallingLabel=[name] kompyuteringizga o'rnatilmoqda, kuting.
uz.FinishedHeadingLabel=[name] o'rnatildi
uz.FinishedLabelNoIcons=[name] kompyuteringizga o'rnatildi.
uz.FinishedLabel=[name] kompyuteringizga o'rnatildi. Dasturni Bosh menyudagi yorliq orqali ochishingiz mumkin.
uz.ClickFinish=Chiqish uchun "Tugatish"ni bosing.
uz.RunEntryExec=%1 ni ishga tushirish
uz.RunEntryShellExec=%1 ni ko'rish
uz.SetupAborted=O'rnatish tugamadi.%n%nMuammoni bartaraf etib, o'rnatishni qayta ishga tushiring.
uz.StatusClosingApplications=Dasturlar yopilmoqda...
uz.StatusCreateDirs=Papkalar yaratilmoqda...
uz.StatusExtractFiles=Fayllar chiqarilmoqda...
uz.StatusCreateIcons=Yorliqlar yaratilmoqda...
uz.StatusCreateRegistryEntries=Reyestr yozuvlari yaratilmoqda...
uz.StatusSavingUninstall=Olib tashlash ma'lumotlari saqlanmoqda...
uz.StatusRunProgram=O'rnatish yakunlanmoqda...
uz.StatusRollback=O'zgarishlar bekor qilinmoqda...
uz.ConfirmUninstall=%1 butunlay olib tashlansinmi? (Ma'lumotlar papkasiga tegilmaydi.)
uz.UninstallStatusLabel=%1 kompyuteringizdan olib tashlanmoqda, kuting.
uz.UninstalledAll=%1 kompyuteringizdan olib tashlandi.
uz.UninstalledMost=%1 olib tashlandi.%n%nAyrim qismlarni o'chirib bo'lmadi; ularni qo'lda o'chirishingiz mumkin.
uz.WizardUninstalling=Olib tashlash holati
uz.StatusUninstalling=%1 olib tashlanmoqda...
uz.ShutdownBlockReasonInstallingApp=%1 o'rnatilmoqda.
uz.ShutdownBlockReasonUninstallingApp=%1 olib tashlanmoqda.

[CustomMessages]
uz.AdditionalIcons=Qo'shimcha yorliqlar:
uz.CreateDesktopIcon=&Ish stoliga yorliq qo'yish
uz.UninstallProgram=%1 ni olib tashlash
uz.LaunchProgram=%1 ni ochish

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Yangilashdan oldin oynasiz ishlayotgan yadroni to'xtatish uchun (PrepareToInstall).
Source: "{#StageDir}\install\stop-core.ps1"; Flags: dontcopy
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\SRV_1\SRV_1"; Filename: "{app}\python\pythonw.exe"; Parameters: "-m srv1_shell"; WorkingDir: "{app}"; IconFilename: "{app}\shell\srv1_shell\srv1.ico"; Comment: "SRV_1 boshqaruv oynasi"
Name: "{autoprograms}\SRV_1\SRV_1 yadro (konsol)"; Filename: "{app}\python\python.exe"; Parameters: "-m srv1_core"; WorkingDir: "{app}"; IconFilename: "{app}\shell\srv1_shell\srv1.ico"; Comment: "Yadroni oynada ishga tushirish (nosozlikni aniqlash uchun; oyna yopilsa, yadro to'xtaydi)"
Name: "{autoprograms}\SRV_1\Qo'llanma"; Filename: "{app}\docs\qollanma.md"
Name: "{autoprograms}\SRV_1\{cm:UninstallProgram,SRV_1}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\SRV_1"; Filename: "{app}\python\pythonw.exe"; Parameters: "-m srv1_shell"; WorkingDir: "{app}"; IconFilename: "{app}\shell\srv1_shell\srv1.ico"; Comment: "SRV_1 boshqaruv oynasi"; Tasks: desktopicon

[Run]
; Ma'lumotlar papkasi (%PROGRAMDATA%\SRV_1) o'rnatayotgan foydalanuvchi nomidan yaratiladi va
; faqat unga, SYSTEM va administratorlarga ochiladi. Bor bo'lsa, tegilmaydi.
Filename: "{#PowerShellExe}"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\install\install.ps1"" -SkipSync -NoShortcut"; Flags: runhidden runasoriginaluser; StatusMsg: "Ma'lumotlar papkasi tayyorlanmoqda..."
; Windows xizmati: alohida administrator oynasida, parolni Windows'ning o'zi so'raydi.
Filename: "{#PowerShellExe}"; Parameters: "-NoProfile -NoExit -ExecutionPolicy Bypass -File ""{app}\install\service.ps1"" -Action install"; Verb: "runas"; Description: "Windows xizmati sifatida o'rnatish (kompyuter yonganda o'zi ishga tushadi; parol so'raladi)"; Flags: postinstall shellexec nowait skipifsilent unchecked
Filename: "{app}\python\pythonw.exe"; Parameters: "-m srv1_shell"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,SRV_1}"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
; Ishlash paytida paydo bo'lishi mumkin bo'lgan .pyc fayllar (faqat dastur papkasi ichida).
Type: filesandordirs; Name: "{app}\core"
Type: filesandordirs; Name: "{app}\sdk"
Type: filesandordirs; Name: "{app}\shell"
Type: filesandordirs; Name: "{app}\plugins"
Type: filesandordirs; Name: "{app}\python"

[Code]
const
  ServiceName = 'SRV_1';
  ServiceKey = 'SYSTEM\CurrentControlSet\Services\SRV_1\Parameters';

var
  ServiceWasStopped: Boolean;

function RunPowerShell(Command: String): Integer;
var
  Code: Integer;
begin
  if not Exec(ExpandConstant('{#PowerShellExe}'),
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "' + Command + '"',
    '', SW_HIDE, ewWaitUntilTerminated, Code) then
    Code := -1;
  Result := Code;
end;

{ Xizmat aynan SHU o'rnatilgan nusxaga tegishlimi? Boshqa papkadan (masalan, ishlab chiqish
  nusxasidan) o'rnatilgan SRV_1 xizmatiga o'rnatuvchi tegmaydi. }
function ServiceIsOurs(): Boolean;
var
  Application: String;
begin
  Result := RegQueryStringValue(HKLM, ServiceKey, 'Application', Application) and
    (Pos(Lowercase(AddBackslash(ExpandConstant('{app}'))), Lowercase(Application)) = 1);
end;

function ServiceIsRunning(): Boolean;
begin
  Result := RunPowerShell('if ((Get-Service ' + ServiceName +
    ' -ErrorAction SilentlyContinue).Status -eq ''Running'') { exit 7 }; exit 0') = 7;
end;

{ Oynasiz (shell ishga tushirgan) yadroni API orqali tartibli to'xtatadi. Natijaga qaralmaydi:
  yadro ishlamayotgan yoki eski bo'lsa va fayllar band bo'lsa, buni o'rnatuvchining o'zi aytadi. }
procedure StopStandaloneCore(Script: String);
var
  Code: Integer;
begin
  Exec(ExpandConstant('{#PowerShellExe}'),
    '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + Script + '"',
    '', SW_HIDE, ewWaitUntilTerminated, Code);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  ServiceWasStopped := False;
  if not ServiceIsRunning() then
  begin
    ExtractTemporaryFile('stop-core.ps1');
    StopStandaloneCore(ExpandConstant('{tmp}\stop-core.ps1'));
  end;
  if ServiceIsOurs() and ServiceIsRunning() then
  begin
    RunPowerShell('Stop-Service ' + ServiceName + ' -ErrorAction SilentlyContinue');
    if ServiceIsRunning() then
      Result := 'SRV_1 xizmati ishlab turibdi va uni to''xtatib bo''lmadi.' + #13#10 +
        'Administrator oynasida "install\service.ps1 -Action stop" ni bajarib, o''rnatishni qayta boshlang.'
    else
      ServiceWasStopped := True;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and ServiceWasStopped then
    RunPowerShell('Start-Service ' + ServiceName + ' -ErrorAction SilentlyContinue');
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  if ServiceIsOurs() and not IsAdmin() then
  begin
    MsgBox('SRV_1 Windows xizmati sifatida o''rnatilgan.' + #13#10 +
      'Avval administrator oynasida "install\service.ps1 -Action remove" ni bajaring, ' +
      'so''ng olib tashlashni qayta boshlang.', mbError, MB_OK);
    Result := False;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usUninstall) and ServiceIsOurs() then
    RunPowerShell('& ''' + ExpandConstant('{app}') + '\install\service.ps1'' -Action remove');
  if (CurUninstallStep = usUninstall) and not ServiceIsRunning() then
    StopStandaloneCore(ExpandConstant('{app}\install\stop-core.ps1'));
end;
