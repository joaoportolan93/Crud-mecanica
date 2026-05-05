"""
Repository de Serviços — CRUD do catálogo de serviços.
"""

import sqlite3
from database import Database
from exceptions import ServicoNotFoundError


class ServicoRepository:
    """Acesso a dados da tabela `servicos` (catálogo)."""

    _CAMPOS_EDITAVEIS = frozenset({
        "descricao", "preco_padrao", "observacoes",
    })

    def __init__(self, db: Database) -> None:
        self.db = db

    @property
    def conn(self) -> sqlite3.Connection:
        return self.db.connection

    def criar(
        self,
        descricao: str,
        preco_padrao: float = 0,
        observacoes: str | None = None,
    ) -> int:
        """Cria um serviço no catálogo. Retorna o ID."""
        cursor = self.conn.execute(
            "INSERT INTO servicos (descricao, preco_padrao, observacoes) "
            "VALUES (?, ?, ?)",
            (descricao, round(preco_padrao, 2), observacoes),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def buscar_por_id(self, id: int) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM servicos WHERE id = ? AND deleted_at IS NULL",
            (id,),
        ).fetchone()

    def listar(
        self, busca: str | None = None, limit: int = 200
    ) -> list[sqlite3.Row]:
        """Lista serviços ativos com busca por descrição."""
        query = "SELECT * FROM servicos WHERE deleted_at IS NULL"
        params: list = []
        if busca:
            query += " AND descricao LIKE ?"
            params.append(f"%{busca}%")
        query += " ORDER BY descricao COLLATE NOCASE LIMIT ?"
        params.append(limit)
        return self.conn.execute(query, params).fetchall()

    def atualizar(self, id: int, **campos) -> None:
        """Atualiza dados de um serviço do catálogo."""
        invalidos = set(campos.keys()) - self._CAMPOS_EDITAVEIS
        if invalidos:
            raise ValueError(f"Campos inválidos para serviço: {invalidos}")
        if not campos:
            return
        if self.buscar_por_id(id) is None:
            raise ServicoNotFoundError(f"Serviço ID {id} não encontrado.")

        if "preco_padrao" in campos:
            campos["preco_padrao"] = round(campos["preco_padrao"], 2)

        sets = ", ".join(f"{col} = ?" for col in campos)
        values = list(campos.values()) + [id]
        self.conn.execute(
            f"UPDATE servicos SET {sets} WHERE id = ? AND deleted_at IS NULL",
            values,
        )
        self.conn.commit()

    def deletar(self, id: int) -> None:
        """Soft delete do serviço."""
        if self.buscar_por_id(id) is None:
            raise ServicoNotFoundError(f"Serviço ID {id} não encontrado.")
        self.conn.execute(
            "UPDATE servicos SET deleted_at = datetime('now', 'localtime') "
            "WHERE id = ? AND deleted_at IS NULL",
            (id,),
        )
        self.conn.commit()
