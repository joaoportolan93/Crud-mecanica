"""Build automatizado para o Gestão de Mecânica.

Fluxo:
  1. verifica dependências e recursos;
  2. limpa build/ e dist/ antigos;
  3. executa PyInstaller com o mecanica.spec;
  4. valida o resultado;
    5. gera build_info.json;
    6. compila o instalador Inno Setup;
    7. imprime o resultado final.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from constants import APP_NAME, APP_VERSION, ASSETS_DIR

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
BUNDLE_DIR = DIST_DIR / APP_NAME
SPEC_FILE = ROOT / "mecanica.spec"
INSTALLER_SPEC = ROOT / "installer.iss"
OUTPUT_DIR = ROOT / "output"


def _print(msg: str) -> None:
    print(msg, flush=True)


def _verificar_prerequisitos() -> None:
    if importlib.util.find_spec("PyInstaller") is None:
        raise RuntimeError("PyInstaller não está instalado no ambiente atual.")

    if not SPEC_FILE.exists():
        raise FileNotFoundError(f"Spec não encontrado: {SPEC_FILE}")

    if not INSTALLER_SPEC.exists():
        raise FileNotFoundError(f"Installer spec não encontrado: {INSTALLER_SPEC}")

    if not ASSETS_DIR.exists():
        _print(f"[AVISO] Pasta de assets não encontrada: {ASSETS_DIR}")
    else:
        icon = ASSETS_DIR / "icon.ico"
        if not icon.exists():
            _print("[AVISO] icon.ico não encontrado; o executável será gerado sem ícone personalizado.")


def _localizar_iscc() -> Path:
    candidato_env = os.environ.get("INNO_SETUP_ISCC")
    if candidato_env:
        candidato = Path(candidato_env)
        if candidato.exists():
            return candidato

    candidato_path = shutil.which("ISCC.exe")
    if candidato_path:
        return Path(candidato_path)

    candidatos = [
        Path(r"C:\InnoSetup6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    for candidato in candidatos:
        if candidato.exists():
            return candidato

    raise FileNotFoundError(
        "ISCC.exe não encontrado. Instale o Inno Setup ou defina a variável INNO_SETUP_ISCC."
    )


def _limpar_diretorio(path: Path) -> None:
    if not path.exists():
        return
    try:
        shutil.rmtree(path)
    except PermissionError as exc:
        raise PermissionError(f"Sem permissão para remover {path}. Feche o app/Explorer e tente novamente.") from exc


def _executar_pyinstaller() -> None:
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(SPEC_FILE)]
    _print(f"[INFO] Executando: {' '.join(cmd)}")

    processo = subprocess.Popen(
        cmd,
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
        raise RuntimeError(f"PyInstaller falhou com exit code {codigo}.")


def _executar_inno_setup() -> Path:
    iscc = _localizar_iscc()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [str(iscc), str(INSTALLER_SPEC)]
    _print(f"[INFO] Compilando instalador: {' '.join(cmd)}")

    processo = subprocess.Popen(
        cmd,
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
        raise RuntimeError(f"Inno Setup falhou com exit code {codigo}.")

    setups = sorted(OUTPUT_DIR.glob("Setup_*.exe"), key=lambda arquivo: arquivo.stat().st_mtime, reverse=True)
    if not setups:
        raise FileNotFoundError(f"Nenhum instalador encontrado em {OUTPUT_DIR}.")

    return setups[0]


def _tamanho_total(pasta: Path) -> int:
    total = 0
    for arquivo in pasta.rglob("*"):
        if arquivo.is_file():
            total += arquivo.stat().st_size
    return total


def _formatar_bytes(valor: int) -> str:
    unidades = ["B", "KB", "MB", "GB"]
    tamanho = float(valor)
    for unidade in unidades:
        if tamanho < 1024 or unidade == unidades[-1]:
            return f"{tamanho:.2f} {unidade}"
        tamanho /= 1024
    return f"{valor} B"


def _gerar_build_info() -> None:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    info = {
        "version": APP_VERSION,
        "build_date": datetime.now().isoformat(timespec="seconds"),
        "python_version": platform.python_version(),
        "app_name": APP_NAME,
    }
    with (DIST_DIR / "build_info.json").open("w", encoding="utf-8") as arquivo:
        json.dump(info, arquivo, ensure_ascii=False, indent=2)


def main() -> None:
    _print("[1/6] Verificando pré-requisitos...")
    _verificar_prerequisitos()

    _print("[2/6] Limpando build/ e dist/ antigos...")
    _limpar_diretorio(BUILD_DIR)
    _limpar_diretorio(DIST_DIR)
    _limpar_diretorio(OUTPUT_DIR)

    _print("[3/6] Gerando executável com PyInstaller...")
    _executar_pyinstaller()

    _print("[4/6] Validando artefatos gerados...")
    if not BUNDLE_DIR.exists():
        raise FileNotFoundError(f"Pasta final do build não encontrada: {BUNDLE_DIR}")

    _print("[5/6] Gerando build_info.json...")
    _gerar_build_info()

    _print("[6/6] Compilando instalador Inno Setup...")
    setup_path = _executar_inno_setup()

    tamanho = _formatar_bytes(_tamanho_total(DIST_DIR))
    _print(f"[INFO] Tamanho total de dist/: {tamanho}")
    _print(f"[INFO] Build disponível em: {BUNDLE_DIR}")

    _print("[7/7] Resultado final:")
    _print(f"  - Instalador gerado em: {setup_path}")
    _print("  - Criar/atualizar a Release no GitHub com a nova tag")
    _print("  - Anexar o Setup.exe e publicar as notas da versão")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _print(f"[ERRO] {exc}")
        raise SystemExit(1) from exc
