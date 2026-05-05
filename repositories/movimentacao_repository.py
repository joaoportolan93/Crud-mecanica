"""
Repository de Movimentações de Estoque — somente leitura.

Movimentações são criadas automaticamente pelos métodos de
PecaRepository e NotaServicoRepository. Este repository
existe apenas para consulta e auditoria.
"""

import sqlite3
from database import Database


class MovimentacaoRepository:
    """Consulta do histórico de movimentações de estoque."""

    def __init__(self, db: Database) -> None:
        self.db = db

    @property
    def conn(self) -> sqlite3.Connection:
        return self.db.connection

    def listar_por_peca(
        self, peca_id: int, limit: int = 100
    ) -> list[sqlite3.Row]:
        """Lista movimentações de uma peça (mais recentes primeiro)."""
        return self.conn.execute(
            "SELECT * FROM movimentacoes_estoque "
            "WHERE peca_id = ? ORDER BY created_at DESC LIMIT ?",
            (peca_id, limit),
        ).fetchall()

    def listar_por_nota(self, nota_id: int) -> list[sqlite3.Row]:
        """Lista movimentações vinculadas a uma nota de serviço."""
        return self.conn.execute(
            "SELECT * FROM movimentacoes_estoque "
            "WHERE nota_id = ? ORDER BY created_at",
            (nota_id,),
        ).fetchall()
