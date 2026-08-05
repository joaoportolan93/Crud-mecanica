"""Sistema de atualização via GitHub Releases."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Literal, TypedDict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen, urlretrieve

from constants import APP_VERSION

GITHUB_USER: str = "joaoportolan93"
GITHUB_REPO: str = "Crud-mecanica"
GITHUB_RELEASES_URL: str = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases"
_API_URL: str = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
_REQUEST_TIMEOUT: int = 5
_UPDATE_FILE_NAME: str = "GestaoDeMecanica_update.exe"


class ResultadoAtualizacao(TypedDict):
    """Resultado da verificação de atualização."""

    tem_atualizacao: bool
    versao_nova: str | None
    url_download: str | None


class UpdateStatus(TypedDict):
    """Estado cacheado da atualização para a interface."""

    estado: Literal["verificando", "atualizado", "disponivel", "erro"]
    versao_nova: str | None
    url_download: str | None


class UpdateError(Exception):
    """Erro amigável usado pelo sistema de atualização."""


ProgressCallback = Callable[[int], None]

_progress_callback: ProgressCallback | None = None


def registrar_callback_progresso(callback: ProgressCallback | None) -> None:
    """Registra um callback simples para receber o percentual do download."""
    global _progress_callback
    _progress_callback = callback


def _resultado_padrao() -> ResultadoAtualizacao:
    """Retorna o resultado padrão, sem atualização disponível."""
    return {
        "tem_atualizacao": False,
        "versao_nova": None,
        "url_download": None,
    }


def _notificar_progresso(percentual: int) -> None:
    """Encaminha o progresso para a UI, se houver um callback registrado."""
    if _progress_callback is not None:
        try:
            _progress_callback(max(0, min(100, percentual)))
        except Exception:
            # Se a UI já tiver sido fechada, o download continua sem quebrar.
            pass


def _obter_release_mais_recente() -> dict[str, object]:
    """Busca a release mais recente do GitHub pela API oficial."""
    request = Request(
        _API_URL,
        headers={
            "User-Agent": f"MecanicaApp/{APP_VERSION}",
            "Accept": "application/vnd.github+json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            # Repositório ainda não tem releases publicadas — não é um erro de rede.
            raise UpdateError("__sem_releases__") from exc
        raise UpdateError(
            f"GitHub retornou erro {exc.code}. Verifique sua conexão e tente novamente."
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise UpdateError(
            "Não foi possível verificar atualizações. Verifique sua conexão com a internet."
        ) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise UpdateError("A resposta do servidor de atualização está inválida.") from exc

    if not isinstance(payload, dict):
        raise UpdateError("A resposta do GitHub para atualização é inválida.")

    return payload


def _obter_asset_exe(payload: dict[str, object]) -> str:
    """Localiza o asset .exe no release retornado pela API."""
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise UpdateError("O GitHub não retornou os arquivos da release.")

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        nome = str(asset.get("name", "")).strip().lower()
        if not nome.endswith(".exe"):
            continue
        browser_download_url = str(asset.get("browser_download_url", "")).strip()
        if browser_download_url:
            return browser_download_url

    raise UpdateError("A release mais recente não possui um instalador .exe.")


def _baixar_instalador(asset_url: str, destino: Path) -> None:
    """Baixa o instalador para o caminho indicado emitindo os marcos de progresso."""
    marcos = (25, 50, 75)
    marcos_emitidos: set[int] = {0}

    def reporthook(blocknum: int, blocksize: int, totalsize: int) -> None:
        if totalsize <= 0:
            return

        percentual = min(100, int((blocknum * blocksize * 100) / totalsize))
        for marco in marcos:
            if marco in marcos_emitidos:
                continue
            if percentual >= marco:
                marcos_emitidos.add(marco)
                _notificar_progresso(marco)

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.unlink(missing_ok=True)

    try:
        urlretrieve(asset_url, str(destino), reporthook)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise UpdateError("Não foi possível baixar a atualização. Verifique sua conexão e tente novamente.") from exc

    for marco in marcos:
        if marco not in marcos_emitidos:
            marcos_emitidos.add(marco)
            _notificar_progresso(marco)


def _iniciar_instalador_e_fechar(caminho_exe: Path) -> None:
    """Executa o instalador baixado e encerra o processo atual."""
    subprocess.Popen([str(caminho_exe)])
    sys.exit(0)


def _parse_version(v_str: str) -> tuple[int, ...]:
    """Converte 'v1.0.3' ou '1.0.3' em tupla de inteiros (1, 0, 3) para comparação segura."""
    limpo = v_str.strip().lstrip("vV")
    partes = []
    for part in limpo.split("."):
        try:
            partes.append(int(part))
        except ValueError:
            break
    return tuple(partes)


def _is_versao_maior(versao_remota: str, versao_local: str) -> bool:
    """Verifica se a versão remota é estritamente maior que a versão local."""
    return _parse_version(versao_remota) > _parse_version(versao_local)


def verificar_atualizacao() -> ResultadoAtualizacao:
    """Verifica a última release do GitHub e compara com a versão atual."""
    try:
        payload = _obter_release_mais_recente()

        tag_name = str(payload.get("tag_name", "")).strip()
        html_url = str(payload.get("html_url", "")).strip()

        if not tag_name:
            return _resultado_padrao()

        if _is_versao_maior(tag_name, APP_VERSION):
            return {
                "tem_atualizacao": True,
                "versao_nova": tag_name,
                "url_download": html_url or GITHUB_RELEASES_URL,
            }

        return _resultado_padrao()
    except UpdateError as exc:
        # Sem releases publicadas = sem atualização, não é um erro.
        if "__sem_releases__" in str(exc):
            return _resultado_padrao()
        return _resultado_padrao()


def obter_estado_atualizacao() -> UpdateStatus:
    """Retorna o estado detalhado da atualização para a interface."""
    try:
        payload = _obter_release_mais_recente()
    except UpdateError as exc:
        # Repositório sem releases publicadas ainda — tratar como "atualizado".
        if "__sem_releases__" in str(exc):
            return {
                "estado": "atualizado",
                "versao_nova": APP_VERSION,
                "url_download": None,
            }
        return {
            "estado": "erro",
            "versao_nova": None,
            "url_download": None,
        }

    tag_name = str(payload.get("tag_name", "")).strip()
    html_url = str(payload.get("html_url", "")).strip()

    if not tag_name:
        return {
            "estado": "erro",
            "versao_nova": None,
            "url_download": None,
        }

    if _is_versao_maior(tag_name, APP_VERSION):
        return {
            "estado": "disponivel",
            "versao_nova": tag_name,
            "url_download": html_url or GITHUB_RELEASES_URL,
        }

    return {
        "estado": "atualizado",
        "versao_nova": APP_VERSION,
        "url_download": None,
    }


def baixar_e_instalar_atualizacao(url_download: str) -> None:
    """Baixa o instalador mais recente, valida o arquivo e dispara a instalação."""
    pagina_release = url_download.strip()
    if not pagina_release:
        raise UpdateError("Não foi possível localizar a página do release para a atualização.")

    payload = _obter_release_mais_recente()
    asset_url = _obter_asset_exe(payload)
    caminho_instalador = Path(tempfile.gettempdir()) / _UPDATE_FILE_NAME

    try:
        _notificar_progresso(0)
        _baixar_instalador(asset_url, caminho_instalador)

        if not caminho_instalador.exists() or caminho_instalador.stat().st_size <= 0:
            raise UpdateError("O instalador baixado está vazio ou corrompido.")

        _notificar_progresso(100)
    except UpdateError:
        caminho_instalador.unlink(missing_ok=True)
        raise
    except Exception as exc:
        caminho_instalador.unlink(missing_ok=True)
        raise UpdateError(
            "Não foi possível baixar a atualização agora. Verifique sua conexão e tente novamente."
        ) from exc

    _iniciar_instalador_e_fechar(caminho_instalador)
