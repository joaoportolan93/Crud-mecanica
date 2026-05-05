"""Contexto da aplicação — contém todos os repositories."""

from dataclasses import dataclass
from database import Database
from repositories import (
    ClienteRepository,
    VeiculoRepository,
    PecaRepository,
    ServicoRepository,
    NotaServicoRepository,
    MovimentacaoRepository,
    ConfiguracaoRepository,
)


@dataclass
class Repos:
    """Container de todos os repositories, injetado nas views."""
    clientes: ClienteRepository
    veiculos: VeiculoRepository
    pecas: PecaRepository
    servicos: ServicoRepository
    notas: NotaServicoRepository
    movimentacoes: MovimentacaoRepository
    config: ConfiguracaoRepository

    @classmethod
    def from_database(cls, db: Database) -> "Repos":
        """Cria todos os repositories a partir de uma instância do Database."""
        return cls(
            clientes=ClienteRepository(db),
            veiculos=VeiculoRepository(db),
            pecas=PecaRepository(db),
            servicos=ServicoRepository(db),
            notas=NotaServicoRepository(db),
            movimentacoes=MovimentacaoRepository(db),
            config=ConfiguracaoRepository(db),
        )
