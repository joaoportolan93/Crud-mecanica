; -----------------------------------------------------------------------------
; Instalador Inno Setup 6 do Gestão de Mecânica
; -----------------------------------------------------------------------------

#define MyAppName "Gestão de Mecânica"
#define MyAppVersion "1.0.0"
#define MyAppExeName "Gestão de Mecânica.exe"
#define MyAppPublisher "João Portolan"
#define MySourceDir "dist\Gestão de Mecânica"

[Setup]
; Metadados principais do instalador e comportamento padrão de instalação.
AppId={{5D9C7B5E-0A06-4A2D-8D0D-7B2AA8C0F4B6}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\GestaoDeMecanica
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
PrivilegesRequired=lowest
OutputDir=installer_output
OutputBaseFilename=Setup_GestaoDeMecanica_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Ícone do instalador: usa o arquivo da pasta assets apenas se ele existir.
#if FileExists("assets\icon.ico")
SetupIconFile=assets\icon.ico
#endif

[Languages]
; Idioma principal do assistente de instalação.
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
; Tarefa opcional para criar atalho na área de trabalho, já marcada por padrão.
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: checkedonce

[Files]
; Copia tudo que o PyInstaller gerou no modo onedir, incluindo a pasta _internal.
Source: "{#MySourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Atalhos do menu Iniciar e da Área de Trabalho apontando para o executável instalado.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Ao final da instalação, oferece abrir o programa imediatamente.
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName} agora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; O banco fica em %LOCALAPPDATA%\GestaoDeMecanica\mecanica.db e não deve ser apagado.
; A desinstalação remove apenas os arquivos instalados em Program Files.

