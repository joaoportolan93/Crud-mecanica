# -*- mode: python ; coding: utf-8 -*-
"""Spec do PyInstaller para o app Gestão de Mecânica.

Escolha deliberada: `onedir` em vez de `onefile`.
Motivos:
  - atualização por substituição da pasta fica mais previsível;
  - início mais rápido;
  - debug e suporte mais simples para o cliente;
  - menos chance de o antivírus interferir na extração temporária.
"""

from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

from constants import APP_NAME, ASSETS_DIR

# O spec é executado via exec() pelo PyInstaller; __file__ não está disponível.
# O build.py chama o PyInstaller com cwd na raiz do projeto, então Path.cwd() é seguro aqui.
project_root = Path.cwd()
icon_file = ASSETS_DIR / "icon.ico"

customtkinter_datas, customtkinter_binaries, customtkinter_hiddenimports = collect_all("customtkinter")
reportlab_datas, reportlab_binaries, reportlab_hiddenimports = collect_all("reportlab")

asset_datas = []
if ASSETS_DIR.exists():
    for asset_path in ASSETS_DIR.rglob("*"):
        if asset_path.is_file():
            relative_parent = asset_path.parent.relative_to(ASSETS_DIR)
            destination = "assets" if str(relative_parent) == "." else f"assets/{relative_parent.as_posix()}"
            asset_datas.append((str(asset_path), destination))

hiddenimports = [
    *customtkinter_hiddenimports,
    *reportlab_hiddenimports,
    "sqlite3",
    "_sqlite3",
    "encodings",
    "tkinter",
    "tkinter.ttk",
]

datas = [
    *customtkinter_datas,
    *reportlab_datas,
    *asset_datas,
    (str(project_root / "schema_mecanica.sql"), "assets"),
]

binaries = [
    *customtkinter_binaries,
    *reportlab_binaries,
]

analysis = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "unittest", "pytest", "PIL.tests"],
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=None)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(icon_file) if icon_file.exists() else None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    name=APP_NAME,
)
