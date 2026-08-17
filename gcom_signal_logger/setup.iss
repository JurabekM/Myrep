; Inno Setup Script for GCOM Signal Logger
; Compiles standalone Windows Setup Executable (.exe)

#define MyAppName "GCOM Signal Logger"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Antigravity Systems"
#define MyAppExeName "GCOM_Signal_Logger.exe"
#define MyCLIExeName "GCOM_Logger_CLI.exe"

[Setup]
AppId={{C82F1E4A-98B6-4A51-B9D1-3343C0E56A21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist_installer
OutputBaseFilename=GCOM_Signal_Logger_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Windows yuklanganda avtomatik fonda ishga tushirish"; GroupDescription: "Avto-ishga tushirish:"; Flags: unchecked

[Files]
; Main Executable files
Source: "dist\GCOM_Signal_Logger.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\GCOM_Logger_CLI.exe"; DestDir: "{app}"; Flags: ignoreversion

; Configuration and documentation files
Source: "config.example.ini"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.ini"; DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} (CLI)"; Filename: "{app}\{#MyCLIExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "GCOMSignalLogger"; ValueData: """{app}\{#MyAppExeName}"" --autostart"; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
