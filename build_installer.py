"""Automatiza a compilação do instalador Inno Setup do Gestão de Mecânica.

Fluxo:
  1. confirma que o bundle onedir do PyInstaller existe e contém _internal;
  2. localiza o ISCC.exe do Inno Setup 6;
  3. compila o installer.iss;
  4. valida o Setup.exe gerado;
  5. mostra o tamanho do instalador e os próximos passos.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from constants import APP_VERSION

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
INSTALLER_OUTPUT_DIR = ROOT / "installer_output"
INSTALLER_SCRIPT = ROOT / "installer.iss"

APP_BUNDLE_CANDIDATES = (
    DIST_DIR / "Gestao de Mecanica",
    DIST_DIR / "Gestão de Mecânica",
)

DOWNLOAD_URL = "https://jrsoftware.org/isdl.php"
SETUP_BASENAME = f"Setup_GestaoDeMecanica_v{APP_VERSION.lstrip('vV')}"
SETUP_FILE = INSTALLER_OUTPUT_DIR / f"{SETUP_BASENAME}.exe"


def _print(mensagem: str) -> None:
    print(mensagem, flush=True)


def _versao_instalador() -> str:
    """Converte APP_VERSION ('v1.0.0') para o formato esperado pelo instalador ('1.0.0')."""
    return APP_VERSION.lstrip("vV")


def _encontrar_bundle() -> Path:
    """Localiza o bundle onedir gerado pelo PyInstaller e valida a pasta _internal."""
    for candidato in APP_BUNDLE_CANDIDATES:
        if candidato.exists() and (candidato / "_internal").exists():
            return candidato

    detalhes = []
    for candidato in APP_BUNDLE_CANDIDATES:
        if candidato.exists() and not (candidato / "_internal").exists():
            detalhes.append(f"{candidato} existe, mas a pasta _internal não foi encontrada.")
        else:
            detalhes.append(f"{candidato} não existe.")

    raise FileNotFoundError(
        "Bundle do PyInstaller não está pronto para empacotamento. "
        + " ".join(detalhes)
    )


def _localizar_iscc() -> Path:
    """Procura o compilador do Inno Setup nos caminhos padrão."""
    caminhos = (
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    )
    for caminho in caminhos:
        if caminho.exists():
            return caminho

    encontrado = shutil.which("ISCC.exe")
    if encontrado:
        return Path(encontrado)

    raise FileNotFoundError(
        "ISCC.exe não encontrado. Baixe o Inno Setup 6 em: "
        f"{DOWNLOAD_URL}"
    )


def _executar_compilacao(iscc: Path) -> None:
    """Executa o compilador do Inno Setup mostrando a saída em tempo real."""
    INSTALLER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    comando = [str(iscc), str(INSTALLER_SCRIPT)]
    _print(f"[INFO] Compilando instalador: {' '.join(comando)}")

    processo = subprocess.Popen(
        comando,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert processo.stdout is not None
    for linha in processo.stdout:
        print(linha, end="")

    codigo = processo.wait()
    if codigo != 0:
        raise RuntimeError(f"O Inno Setup falhou com exit code {codigo}.")


def _formatar_tamanho(arquivo: Path) -> str:
    """Formata o tamanho do arquivo em uma unidade legível."""
    tamanho = arquivo.stat().st_size
    unidades = ("B", "KB", "MB", "GB")
    valor = float(tamanho)

    for unidade in unidades:
        if valor < 1024.0 or unidade == unidades[-1]:
            return f"{valor:.2f} {unidade}"
        valor /= 1024.0

    return f"{tamanho} B"


def main() -> int:
    """Executa o fluxo completo de compilação do instalador."""
    _print("[1/5] Verificando bundle do PyInstaller...")
    bundle = _encontrar_bundle()
    _print(f"[INFO] Bundle localizado em: {bundle}")

    _print("[2/5] Localizando o Inno Setup 6...")
    iscc = _localizar_iscc()
    _print(f"[INFO] ISCC encontrado em: {iscc}")

    _print("[3/5] Compilando o installer.iss...")
    _executar_compilacao(iscc)

    _print("[4/5] Validando o instalador gerado...")
    if not SETUP_FILE.exists():
        raise FileNotFoundError(f"Instalador não encontrado: {SETUP_FILE}")

    _print("[5/5] Resultado final:")
    _print(f"  - Instalador gerado em: {SETUP_FILE}")
    _print(f"  - Tamanho: {_formatar_tamanho(SETUP_FILE)}")
    _print("Instalador gerado! Próximo passo:")
    _print("1. Teste o instalador nesta máquina")
    _print("2. Vá em github.com/joaoportolan93/Crud-mecanica/releases")
    _print("3. Edite o release v1.0.0")
    _print("4. Remova o .exe antigo")
    _print(f"5. Anexe o arquivo: {SETUP_FILE.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        _print(f"[ERRO] {exc}")
        raise SystemExit(1) from exc
