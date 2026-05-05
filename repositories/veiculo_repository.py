"""
Repository de Veículos — CRUD com soft delete e buscas por placa/modelo.
"""

import sqlite3
from database import Database
from exceptions import (
    VeiculoNotFoundError,
    RegistroDuplicadoError,
    IntegridadeError,
)


class VeiculoRepository:
    """Acesso a dados da tabela `veiculos`."""

    _CAMPOS_EDITAVEIS = frozenset({
        "cliente_id", "placa", "marca", "modelo", "ano_fabricacao",
        "ano_modelo", "cor", "chassi", "km_atual", "observacoes",
    })

    def __init__(self, db: Database) -> None:
        self.db = db

    @property
    def conn(self) -> sqlite3.Connection:
        return self.db.connection

    # ── CREATE ──────────────────────────────────────────────

    def criar(
        self,
        cliente_id: int,
        modelo: str,
        placa: str | None = None,
        marca: str | None = None,
        ano_fabricacao: int | None = None,
        ano_modelo: int | None = None,
        cor: str | None = None,
        chassi: str | None = None,
        km_atual: int = 0,
        observacoes: str | None = None,
    ) -> int:
        """Cria um novo veículo vinculado a um cliente. Retorna o ID."""
        try:
            cursor = self.conn.execute(
                """INSERT INTO veiculos
                   (cliente_id, placa, marca, modelo, ano_fabricacao,
                    ano_modelo, cor, chassi, km_atual, observacoes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cliente_id, placa, marca, modelo, ano_fabricacao,
                 ano_modelo, cor, chassi, km_atual, observacoes),
            )
            self.conn.commit()
            return cursor.lastrowid  # type: ignore[return-value]
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            if "placa" in str(e).lower():
                raise RegistroDuplicadoError(
                    f"Placa '{placa}' já está cadastrada."
                ) from e
            raise IntegridadeError(str(e)) from e

    # ── READ ────────────────────────────────────────────────

    def buscar_por_id(self, id: int) -> sqlite3.Row | None:
        """Retorna o veículo pelo ID, ou None."""
        return self.conn.execute(
            "SELECT * FROM veiculos WHERE id = ? AND deleted_at IS NULL",
            (id,),
        ).fetchone()

    def listar_por_cliente(self, cliente_id: int) -> list[sqlite3.Row]:
        """Lista todos os veículos ativos de um cliente."""
        return self.conn.execute(
            "SELECT * FROM veiculos "
            "WHERE cliente_id = ? AND deleted_at IS NULL "
            "ORDER BY modelo COLLATE NOCASE",
            (cliente_id,),
        ).fetchall()

    def buscar_por_placa(self, placa: str) -> sqlite3.Row | None:
        """Busca veículo ativo pela placa (case-insensitive)."""
        return self.conn.execute(
            "SELECT * FROM veiculos "
            "WHERE placa = ? COLLATE NOCASE AND deleted_at IS NULL",
            (placa,),
        ).fetchone()

    def buscar_por_modelo(
        self, modelo: str, limit: int = 100
    ) -> list[sqlite3.Row]:
        """Busca veículos ativos por substring do modelo."""
        return self.conn.execute(
            "SELECT * FROM veiculos "
            "WHERE modelo LIKE ? AND deleted_at IS NULL "
            "ORDER BY modelo COLLATE NOCASE LIMIT ?",
            (f"%{modelo}%", limit),
        ).fetchall()

    # ── UPDATE ──────────────────────────────────────────────

    def atualizar(self, id: int, **campos) -> None:
        """Atualiza campos de um veículo existente."""
        invalidos = set(campos.keys()) - self._CAMPOS_EDITAVEIS
        if invalidos:
            raise ValueError(f"Campos inválidos para veículo: {invalidos}")
        if not campos:
            return
        if self.buscar_por_id(id) is None:
            raise VeiculoNotFoundError(f"Veículo ID {id} não encontrado.")

        sets = ", ".join(f"{col} = ?" for col in campos)
        values = list(campos.values()) + [id]

        try:
            self.conn.execute(
                f"UPDATE veiculos SET {sets} "
                "WHERE id = ? AND deleted_at IS NULL",
                values,
            )
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            if "placa" in str(e).lower():
                raise RegistroDuplicadoError(
                    f"Placa '{campos.get('placa')}' já cadastrada."
                ) from e
            raise IntegridadeError(str(e)) from e

    # ── DELETE (soft) ───────────────────────────────────────

    def deletar(self, id: int) -> None:
        """Soft delete do veículo."""
        if self.buscar_por_id(id) is None:
            raise VeiculoNotFoundError(f"Veículo ID {id} não encontrado.")

        self.conn.execute(
            "UPDATE veiculos SET deleted_at = datetime('now', 'localtime') "
            "WHERE id = ? AND deleted_at IS NULL",
            (id,),
        )
        self.conn.commit()
