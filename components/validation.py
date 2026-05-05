"""Helpers para validação de entrada em campos numéricos."""

from __future__ import annotations

import re


def is_valid_numeric_text(value: str, mode: str) -> bool:
    """Valida texto parcial para uso em `Entry` com `validate='key'`."""
    if value == "":
        return True

    if mode in ("digits", "int", "integer"):
        return value.isdigit()

    if mode in ("decimal", "float"):
        normalized = value.replace(",", ".")
        return re.fullmatch(r"\d*(\.\d*)?", normalized) is not None

    return True


def normalize_numeric_text(value: str, mode: str) -> str:
    """Normaliza o texto antes de salvar os dados do formulário."""
    text = value.strip()
    if mode in ("digits", "int", "integer"):
        return text
    if mode in ("decimal", "float"):
        return text.replace(",", ".")
    return text


def attach_numeric_validation(entry, mode: str) -> None:
    """Anexa validação de teclado a um `CTkEntry`."""
    callback = entry.register(lambda proposed: is_valid_numeric_text(proposed, mode))
    entry.configure(validate="key", validatecommand=(callback, "%P"))
