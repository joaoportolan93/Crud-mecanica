; -----------------------------------------------------------------------------
; Inno Setup 6 - Instalador do Gestão de Mecânica
; -----------------------------------------------------------------------------

#define AppName "Gestão de Mecânica"
#define AppVersion "1.0.0"
#define AppPublisher "joaoportolan93"
#define AppExeName "Gestão de Mecânica.exe"
#define AppId "GestaoDeMecanica"
#define AppSourceDir "dist\Gestão de Mecânica"
#define AppIconPath "assets\icon.ico"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\GestaoDeMecanica
DefaultGroupName={#AppName}
DisableProgramGroupPage=no
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=Setup_{#AppName}_{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

#if FileExists(AppIconPath)
SetupIconFile={#AppIconPath}
#endif

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: checkedonce

[Files]
Source: "{#AppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir o programa ao final"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Não remover AppData: o banco do cliente fica em %LOCALAPPDATA%\GestaoDeMecanica\mecanica.db.
; A desinstalação deve apagar apenas os binários do app, preservando os dados do usuário.

[Code]
function InitializeSetup(): Boolean;
var
  InstalledVersion: string;
begin
  Result := True;
  if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + ExpandConstant('{#AppId}') + '_is1', 'DisplayVersion', InstalledVersion)
     or RegQueryStringValue(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + ExpandConstant('{#AppId}') + '_is1', 'DisplayVersion', InstalledVersion) then
  begin
    MsgBox(
      'Já existe uma versão instalada do Gestão de Mecânica (' + InstalledVersion + ').'#13#10 +
      'O instalador vai atualizar os arquivos do programa e manter o banco de dados do cliente.',
      mbInformation,
      MB_OK
    );
  end;
end;
