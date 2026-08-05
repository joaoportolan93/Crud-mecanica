"""Constantes centrais do aplicativo e resolução de caminhos.

Este módulo foi pensado para funcionar tanto em desenvolvimento quanto
quando o app estiver empacotado com PyInstaller.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME: str = "Gestão de Mecânica"
APP_VERSION: str = "v1.0.3"

# Nome estável usado em diretórios e instalador (sem acentos/espacos)
APP_SLUG: str = "GestaoDeMecanica"


def _is_frozen() -> bool:
    """Indica se o processo atual está rodando empacotado."""
    return bool(getattr(sys, "frozen", False))


def _project_root() -> Path:
    """Retorna a raiz do projeto em modo desenvolvimento."""
    return Path(__file__).resolve().parent


def _runtime_root() -> Path:
    """Retorna a raiz base de execução (dev ou PyInstaller)."""
    if _is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return _project_root()


def _resolve_app_data_dir() -> Path:
    """Resolve o diretório de dados do usuário por sistema operacional.

    Windows: %LOCALAPPDATA%\\GestaoDeMecanica
    Linux: ~/.local/share/GestaoDeMecanica
    macOS: ~/Library/Application Support/GestaoDeMecanica

    A escolha por "Local" no Windows evita sincronização e backup
    indesejados do perfil roaming, porque os dados do app são locais e
    não precisam acompanhar o usuário entre máquinas.
    """
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APP_SLUG


def _resolve_assets_dir() -> Path:
    """Resolve o diretório de assets para dev e ambiente empacotado."""
    return _runtime_root() / "assets"


APP_DATA_DIR: Path = _resolve_app_data_dir()
DB_PATH: Path = APP_DATA_DIR / "mecanica.db"
BACKUP_DIR: Path = APP_DATA_DIR / "backups"
APP_LOG_DIR: Path = APP_DATA_DIR / "logs"
APP_LOG_FILE: Path = APP_LOG_DIR / f"{APP_SLUG}.log"
ASSETS_DIR: Path = _resolve_assets_dir()


def get_asset_path(*parts: str) -> Path:
    """Monta o caminho de um asset dentro da pasta de recursos."""
    asset_path = ASSETS_DIR.joinpath(*parts)
    if asset_path.exists():
        return asset_path
    return _project_root().joinpath(*parts)


def get_legacy_db_paths() -> list[Path]:
    """Retorna uma lista de caminhos onde um banco de dados legado pode estar localizado."""
    paths: list[Path] = []
    
    # 1. Raiz do projeto (modo dev ou instalação portable antiga na pasta do projeto)
    paths.append(_project_root() / "mecanica.db")
    
    # 2. Pasta do executável (se rodando congelado em pasta personalizada)
    if _is_frozen():
        exe_dir = Path(sys.executable).resolve().parent
        paths.append(exe_dir / "mecanica.db")
    
    # 3. Roaming AppData (se em alguma versão anterior salvava em APPDATA em vez de LOCALAPPDATA)
    if sys.platform.startswith("win"):
        roaming = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        paths.append(roaming / APP_SLUG / "mecanica.db")
        
    return list(dict.fromkeys(paths))  # Remove duplicatas preservando ordem

