; Inno Setup installer script for PoseReferenceForge Local
; Requires Inno Setup 6+ (https://jrsoftware.org/isdl.php)

#define MyAppName "PoseReferenceForge Local"
#define MyAppVersion "1.0.0-dev"
#define MyAppPublisher "PoseReferenceForge"
#define MyAppURL "https://github.com/TriggerMinds/PoseReferenceForge-Local"
#define MyAppExeName "PoseReferenceForge.exe"
#define DistDir "..\dist"

[Setup]
AppId={{B8F3C4A1-5D7E-4A2F-9C6B-1D3E5F7A8B9C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=PoseReferenceForge_Setup_{#MyAppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableWelcomePage=no
DisableReadyPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "{#DistDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion 64bit
Source: "{#DistDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs 64bit

[Dirs]
Name: "{app}\models"
Name: "{app}\assets"
Name: "{app}\blender"
Name: "{userappdata}\PoseReferenceForge\projects"
Name: "{userappdata}\PoseReferenceForge\exports"
Name: "{userappdata}\PoseReferenceForge\cache"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\models"
Type: filesandordirs; Name: "{app}\_internal"

[Code]
function InitializeSetup: Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create model download script
    SaveStringToFile(ExpandConstant('{app}\download_models.bat'),
      '@echo off' + #13#10 +
      'echo Downloading pose detection model...' + #13#10 +
      'cd /d "%~dp0"' + #13#10 +
      'mkdir models 2>nul' + #13#10 +
      'echo Place yolov8n-pose.pt in the models folder.' + #13#10 +
      'pause' + #13#10,
      False);
  end;
end;
