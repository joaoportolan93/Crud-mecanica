"""
Repository de Peças — CRUD, controle de estoque e movimentações.
"""

import sqlite3
from database import Database
from exceptions import (
    PecaNotFoundError,
    EstoqueInsuficienteError,
    IntegridadeError,
)


class PecaRepository:
    """Acesso a dados da tabela `pecas` com controle de estoque."""

    _CAMPOS_EDITAVEIS = frozenset({
        "codigo", "descricao", "unidade", "preco_custo", "preco_venda",
        "estoque_minimo", "localizacao", "observacoes",
    })

    def __init__(self, db: Database) -> None:
        self.db = db

    @property
    def conn(self) -> sqlite3.Connection:
        return self.db.connection

    # ── CREATE ──────────────────────────────────────────────

    def criar(
        self,
        descricao: str,
        preco_venda: float = 0,
        codigo: str | None = None,
        unidade: str = "UN",
        quantidade: float = 0,
        preco_custo: float = 0,
        estoque_minimo: float = 0,
        localizacao: str | None = None,
        observacoes: str | None = None,
    ) -> int:
        """Cria uma nova peça no estoque. Retorna o ID."""
        cursor = self.conn.execute(
            """INSERT INTO pecas
               (codigo, descricao, unidade, quantidade, preco_custo,
                preco_venda, estoque_minimo, localizacao, observacoes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (codigo, descricao, unidade, round(quantidade, 4),
             round(preco_custo, 2), round(preco_venda, 2),
             round(estoque_minimo, 4), localizacao, observacoes),
        )
        self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    # ── READ ────────────────────────────────────────────────

    def buscar_por_id(self, id: int) -> sqlite3.Row | None:
        """Retorna a peça pelo ID, ou None."""
        return self.conn.execute(
            "SELECT * FROM pecas WHERE id = ? AND deleted_at IS NULL",
            (id,),
        ).fetchone()

    def listar(
        self, busca: str | None = None, limit: int = 200
    ) -> list[sqlite3.Row]:
        """Lista peças ativas, com busca por descrição ou código."""
        query = "SELECT * FROM pecas WHERE deleted_at IS NULL"
        params: list = []

        if busca:
            query += " AND (descricao LIKE ? OR codigo LIKE ?)"
            params.extend([f"%{busca}%", f"%{busca}%"])

        query += " ORDER BY descricao COLLATE NOCASE LIMIT ?"
        params.append(limit)
        return self.conn.execute(query, params).fetchall()

    def listar_abaixo_do_minimo(self) -> list[sqlite3.Row]:
        """Lista peças cujo estoque está abaixo do mínimo configurado."""
        return self.conn.execute(
            "SELECT * FROM pecas "
            "WHERE quantidade < estoque_minimo "
            "AND estoque_minimo > 0 "
            "AND deleted_at IS NULL "
            "ORDER BY descricao COLLATE NOCASE",
        ).fetchall()

    # ── UPDATE ──────────────────────────────────────────────

    def atualizar(self, id: int, **campos) -> None:
        """Atualiza dados cadastrais da peça (NÃO altera quantidade).

        Para alterar quantidade, use entrada_estoque() ou ajustar_quantidade().
        """
        invalidos = set(campos.keys()) - self._CAMPOS_EDITAVEIS
        if invalidos:
            raise ValueError(f"Campos inválidos para peça: {invalidos}")
        if not campos:
            return
        if self.buscar_por_id(id) is None:
            raise PecaNotFoundError(f"Peça ID {id} não encontrada.")

        # Arredondar valores monetários se presentes
        for campo in ("preco_custo", "preco_venda"):
            if campo in campos:
                campos[campo] = round(campos[campo], 2)

        sets = ", ".join(f"{col} = ?" for col in campos)
        values = list(campos.values()) + [id]

        self.conn.execute(
            f"UPDATE pecas SET {sets} WHERE id = ? AND deleted_at IS NULL",
            values,
        )
        self.conn.commit()

    # ── ESTOQUE ─────────────────────────────────────────────

    def entrada_estoque(
        self, peca_id: int, quantidade: float, motivo: str | None = None
    ) -> None:
        """Registra entrada de mercadoria no estoque.

        Atualiza pecas.quantidade e cria movimentacao_estoque (ENTRADA).
        """
        peca = self.buscar_por_id(peca_id)
        if peca is None:
            raise PecaNotFoundError(f"Peça ID {peca_id} não encontrada.")

        if quantidade <= 0:
            raise ValueError("Quantidade de entrada deve ser positiva.")

        qtd_anterior = peca["quantidade"]
        qtd_posterior = round(qtd_anterior + quantidade, 4)

        with self.conn:
            self.conn.execute(
                "UPDATE pecas SET quantidade = ? WHERE id = ?",
                (qtd_posterior, peca_id),
            )
            self.conn.execute(
                """INSERT INTO movimentacoes_estoque
                   (peca_id, nota_id, tipo, quantidade,
                    quantidade_anterior, quantidade_posterior, motivo)
                   VALUES (?, NULL, 'ENTRADA', ?, ?, ?, ?)""",
                (peca_id, round(quantidade, 4),
                 qtd_anterior, qtd_posterior,
                 motivo or "Entrada manual de mercadoria"),
            )

    def ajustar_quantidade(
        self, peca_id: int, nova_quantidade: float, motivo: str
    ) -> None:
        """Ajuste de inventário: define nova quantidade e registra movimentação.

        Usado quando a contagem física difere do sistema.
        Motivo é obrigatório para rastreabilidade.
        """
        peca = self.buscar_por_id(peca_id)
        if peca is None:
            raise PecaNotFoundError(f"Peça ID {peca_id} não encontrada.")

        if nova_quantidade < 0:
            raise ValueError("Quantidade não pode ser negativa.")

        qtd_anterior = peca["quantidade"]
        if qtd_anterior == nova_quantidade:
            return  # Nada a fazer

        with self.conn:
            self.conn.execute(
                "UPDATE pecas SET quantidade = ? WHERE id = ?",
                (round(nova_quantidade, 4), peca_id),
            )
            self.conn.execute(
                """INSERT INTO movimentacoes_estoque
                   (peca_id, nota_id, tipo, quantidade,
                    quantidade_anterior, quantidade_posterior, motivo)
                   VALUES (?, NULL, 'AJUSTE', ?, ?, ?, ?)""",
                (peca_id,
                 round(abs(nova_quantidade - qtd_anterior), 4),
                 qtd_anterior, round(nova_quantidade, 4), motivo),
            )

    # ── DELETE (soft) ───────────────────────────────────────

    def deletar(self, id: int) -> None:
        """Soft delete da peça."""
        if self.buscar_por_id(id) is None:
            raise PecaNotFoundError(f"Peça ID {id} não encontrada.")

        self.conn.execute(
            "UPDATE pecas SET deleted_at = datetime('now', 'localtime') "
            "WHERE id = ? AND deleted_at IS NULL",
            (id,),
        )
        self.conn.commit()
