#define MyAppName "ScreenGrab"
#define MyAppVersion "1.2"
#define MyAppPublisher "Nexus Technology Partners"
#define MyAppURL "https://www.nexusfw.com/"
#define MyAppExeName "ScreenGrab.exe"
#define MyINIFile "sharefile_conf.ini"
#define MySourceDir "C:/Users/donnykapic/Documents/Upilio/ScreenGrab/Version History/v1.2/dist"
#define MyInstallerName "ScreenGrab Installer"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{B0195C4E-5B61-4784-8C59-BAE8FD024437}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
SourceDir={#MySourceDir}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputBaseFilename={#MyInstallerName}
DisableProgramGroupPage=yes
; Remove the following line to run in administrative install mode (install for all users.)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "*"; DestDir: "{app}"; Flags: ignoreversion
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Code]
var 
  CustomQueryPage: TInputQueryWizardPage;
  ScreenId: String;

procedure SetScreenName();
begin
  CustomQueryPage := CreateInputQueryPage(
    wpWelcome,
    'ScreenGrab Installer v1.2',
    'Screen Name',
    'Please enter the desired screen name. This will be the name of the file when it is uploaded.');

  { Add items (False means it's not a password edit) }
  {CustomQueryPage.Add('&Username:', False); }
  {CustomQueryPage.Add('&Password:', False);}
  CustomQueryPage.Add('&Screen Name (This will also be the name of the ShareFile folder that screenshots will be sent to):', False);
  CustomQueryPage.Add('&Upload Frequency (in minutes):', False);
  CustomQueryPage.Add('&Username:', False);
  CustomQueryPage.Add('&Password:', False);
end;

procedure InitializeCommand();
var
  A: AnsiString;
  U: String;
begin
  LoadStringFromFile(WizardDirValue + '/ScreenGrab_Schedule.xml', A);
  U := A;
  StringChange(U, '[executablePath]', WizardDirValue + '\screengrab.exe');
  A := U;
  SaveStringToFile(WizardDirValue + '/ScreenGrab_Schedule.xml', A, False);
end;

procedure InitializeStartingLocation();
var
  B: AnsiString;
  V: String;
begin
  LoadStringFromFile(WizardDirValue + '/ScreenGrab_Schedule.xml', B);
  V := B;
  StringChange(V, '[programPath]', WizardDirValue);
  B := V;
  SaveStringToFile(WizardDirValue + '/ScreenGrab_Schedule.xml', B, False);
end;

procedure InitializeFrequency();
var
  C: AnsiString;
  W: String;
begin
  LoadStringFromFile(WizardDirValue + '/ScreenGrab_Schedule.xml', C);
  W := C;
  StringChange(W, '[uploadFrequency]', 'PT' + CustomQueryPage.Values[1] + 'M');
  C := W;
  SaveStringToFile(WizardDirValue + '/ScreenGrab_Schedule.xml', C, False);
end;

function GetName(Param: String): String;
begin
  Result := CustomQueryPage.Values[0]
end;

function GetUsername(Param: String): String;
begin
  Result := CustomQueryPage.Values[2]
end;

function GetPassword(Param: String): String;
begin
  Result := CustomQueryPage.Values[3]
end;

procedure InitializeWizard();
begin                             
  SetScreenName();
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then         
  begin
    { Read custom value }
    InitializeCommand();
    InitializeStartingLocation();
    InitializeFrequency();
  end;
end;

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[INI]
Filename: "{app}\{#MyINIFile}"; Section: "SectionThree"; Key: "localPath"; String: "{app}"
Filename: "{app}\{#MyINIFile}"; Section: "Sharefile API"; Key: "username"; String: "{code:GetUsername|{app}}"
Filename: "{app}\{#MyINIFile}"; Section: "Sharefile API"; Key: "password"; String: "{code:GetPassword|{app}}"
Filename: "{app}\{#MyINIFile}"; Section: "SectionThree"; Key: "screenId"; String: "{code:GetName|{app}}"