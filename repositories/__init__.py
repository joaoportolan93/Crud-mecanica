"""
Repositories — camada de acesso a dados.

Cada repository encapsula as queries SQL de uma entidade,
traduz erros do sqlite3 em exceções semânticas (exceptions.py),
e expõe métodos com type hints para a camada de negócio/UI.
"""

from .cliente_repository import ClienteRepository
from .veiculo_repository import VeiculoRepository
from .peca_repository import PecaRepository
from .servico_repository import ServicoRepository
from .nota_servico_repository import NotaServicoRepository
from .movimentacao_repository import MovimentacaoRepository
from .configuracao_repository import ConfiguracaoRepository

__all__ = [
    "ClienteRepository",
    "VeiculoRepository",
    "PecaRepository",
    "ServicoRepository",
    "NotaServicoRepository",
    "MovimentacaoRepository",
    "ConfiguracaoRepository",
]
