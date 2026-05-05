"""Verificador de atualizações via GitHub Releases."""

from __future__ import annotations

import json
from typing import TypedDict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

APP_VERSION: str = "v1.0.0"
GITHUB_USER: str = "joaoportolan93"
GITHUB_REPO: str = "Crud-mecanica"

_API_URL: str = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
_REQUEST_TIMEOUT: int = 5


class ResultadoAtualizacao(TypedDict):
    """Resultado da verificação de atualização."""

    tem_atualizacao: bool
    versao_nova: str | None
    url_download: str | None


def _resultado_padrao() -> ResultadoAtualizacao:
    """Retorna o resultado padrão, sem atualização disponível."""
    return {
        "tem_atualizacao": False,
        "versao_nova": None,
        "url_download": None,
    }


def verificar_atualizacao() -> ResultadoAtualizacao:
    """Verifica a última release do GitHub e compara com a versão atual.

    Returns:
        Um dicionário com `tem_atualizacao`, `versao_nova` e `url_download`.
        Em qualquer erro, retorna o resultado padrão sem propagar exceções.
    """
    try:
        request = Request(
            _API_URL,
            headers={
                "User-Agent": f"MecanicaApp/{APP_VERSION}",
                "Accept": "application/vnd.github+json",
            },
            method="GET",
        )

        with urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))

        tag_name = str(payload.get("tag_name", "")).strip()
        html_url = str(payload.get("html_url", "")).strip()

        if not tag_name:
            return _resultado_padrao()

        if tag_name != APP_VERSION:
            return {
                "tem_atualizacao": True,
                "versao_nova": tag_name,
                "url_download": html_url or None,
            }

        return _resultado_padrao()

    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return _resultado_padrao()
    except Exception:
        return _resultado_padrao()
