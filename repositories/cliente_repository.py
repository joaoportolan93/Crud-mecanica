"""
Repository de Clientes — CRUD com soft delete.
"""

import sqlite3
from database import Database
from exceptions import (
    ClienteNotFoundError,
    RegistroDuplicadoError,
    IntegridadeError,
)


class ClienteRepository:
    """Acesso a dados da tabela `clientes`."""

    # Colunas que podem ser atualizadas via atualizar()
    _CAMPOS_EDITAVEIS = frozenset({
        "tipo", "nome", "cpf_cnpj", "telefone", "telefone2",
        "email", "endereco", "cidade", "uf", "cep", "observacoes",
    })

    def __init__(self, db: Database) -> None:
        self.db = db

    @property
    def conn(self) -> sqlite3.Connection:
        return self.db.connection

    # ── CREATE ──────────────────────────────────────────────

    def criar(
        self,
        nome: str,
        tipo: str = "PF",
        cpf_cnpj: str | None = None,
        telefone: str | None = None,
        telefone2: str | None = None,
        email: str | None = None,
        endereco: str | None = None,
        cidade: str | None = None,
        uf: str | None = None,
        cep: str | None = None,
        observacoes: str | None = None,
    ) -> int:
        """Cria um novo cliente e retorna o ID gerado."""
        try:
            cursor = self.conn.execute(
                """INSERT INTO clientes
                   (tipo, nome, cpf_cnpj, telefone, telefone2,
                    email, endereco, cidade, uf, cep, observacoes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (tipo, nome, cpf_cnpj, telefone, telefone2,
                 email, endereco, cidade, uf, cep, observacoes),
            )
            self.conn.commit()
            return cursor.lastrowid  # type: ignore[return-value]
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            if "cpf_cnpj" in str(e).lower():
                raise RegistroDuplicadoError(
                    f"CPF/CNPJ '{cpf_cnpj}' já está cadastrado."
                ) from e
            raise IntegridadeError(str(e)) from e

    # ── READ ────────────────────────────────────────────────

    def buscar_por_id(self, id: int) -> sqlite3.Row | None:
        """Retorna o cliente pelo ID, ou None se não existir/excluído."""
        return self.conn.execute(
            "SELECT * FROM clientes WHERE id = ? AND deleted_at IS NULL",
            (id,),
        ).fetchone()

    def buscar_por_cpf_cnpj(self, cpf_cnpj: str) -> sqlite3.Row | None:
        """Busca cliente ativo pelo CPF ou CNPJ."""
        return self.conn.execute(
            "SELECT * FROM clientes WHERE cpf_cnpj = ? AND deleted_at IS NULL",
            (cpf_cnpj,),
        ).fetchone()

    def listar(
        self,
        busca: str | None = None,
        tipo: str | None = None,
        limit: int = 200,
    ) -> list[sqlite3.Row]:
        """Lista clientes ativos, com filtro opcional por nome e tipo.

        Args:
            busca: Substring do nome (case-insensitive).
            tipo: 'PF' ou 'PJ' para filtrar por tipo.
            limit: Máximo de resultados (padrão 200).
        """
        query = "SELECT * FROM clientes WHERE deleted_at IS NULL"
        params: list = []

        if busca:
            query += " AND nome LIKE ?"
            params.append(f"%{busca}%")
        if tipo:
            query += " AND tipo = ?"
            params.append(tipo)

        query += " ORDER BY nome COLLATE NOCASE LIMIT ?"
        params.append(limit)

        return self.conn.execute(query, params).fetchall()

    # ── UPDATE ──────────────────────────────────────────────

    def atualizar(self, id: int, **campos) -> None:
        """Atualiza campos de um cliente existente.

        Args:
            id: ID do cliente.
            **campos: Campos a atualizar (ex: nome='João', telefone='...')

        Raises:
            ClienteNotFoundError: Cliente não existe ou foi excluído.
            ValueError: Campo inválido passado em **campos.
            RegistroDuplicadoError: CPF/CNPJ duplicado.
        """
        invalidos = set(campos.keys()) - self._CAMPOS_EDITAVEIS
        if invalidos:
            raise ValueError(f"Campos inválidos para cliente: {invalidos}")
        if not campos:
            return

        # Verifica se o cliente existe
        if self.buscar_por_id(id) is None:
            raise ClienteNotFoundError(f"Cliente ID {id} não encontrado.")

        sets = ", ".join(f"{col} = ?" for col in campos)
        values = list(campos.values()) + [id]

        try:
            self.conn.execute(
                f"UPDATE clientes SET {sets} WHERE id = ? AND deleted_at IS NULL",
                values,
            )
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            if "cpf_cnpj" in str(e).lower():
                raise RegistroDuplicadoError(
                    f"CPF/CNPJ '{campos.get('cpf_cnpj')}' já está cadastrado."
                ) from e
            raise IntegridadeError(str(e)) from e

    # ── DELETE (soft) ───────────────────────────────────────

    def deletar(self, id: int) -> None:
        """Soft delete: marca deleted_at no cliente.

        Raises:
            ClienteNotFoundError: Cliente não existe.
            IntegridadeError: Cliente tem veículos ou notas vinculadas.
        """
        if self.buscar_por_id(id) is None:
            raise ClienteNotFoundError(f"Cliente ID {id} não encontrado.")

        self.conn.execute(
            "UPDATE clientes SET deleted_at = datetime('now', 'localtime') "
            "WHERE id = ? AND deleted_at IS NULL",
            (id,),
        )
        self.conn.commit()
