"""
Repository de Configurações — acesso ao estado global (chave-valor).
"""

import sqlite3
from database import Database


class ConfiguracaoRepository:
    """Acesso à tabela `configuracoes` (chave-valor global)."""

    def __init__(self, db: Database) -> None:
        self.db = db

    @property
    def conn(self) -> sqlite3.Connection:
        return self.db.connection

    def get(self, chave: str) -> str | None:
        """Retorna o valor de uma configuração, ou None se não existir."""
        row = self.conn.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?",
            (chave,),
        ).fetchone()
        return row["valor"] if row else None

    def set(self, chave: str, valor: str) -> None:
        """Define o valor de uma configuração existente."""
        result = self.conn.execute(
            "UPDATE configuracoes SET valor = ? WHERE chave = ?",
            (valor, chave),
        )
        if result.rowcount == 0:
            # Chave não existe: cria
            self.conn.execute(
                "INSERT INTO configuracoes (chave, valor) VALUES (?, ?)",
                (chave, valor),
            )
        self.conn.commit()

    def get_proximo_numero_os(self) -> int:
        """Retorna o próximo número de OS SEM consumir.

        Para consumir, use NotaServicoRepository.criar_rascunho(),
        que lê e incrementa atomicamente dentro de uma transação.
        """
        valor = self.get("proximo_numero_os")
        return int(valor) if valor else 1

    def get_dados_oficina(self) -> dict[str, str]:
        """Retorna os dados da oficina para impressão no PDF."""
        chaves = [
            "nome_oficina", "telefone_oficina",
            "endereco_oficina", "cnpj_oficina",
        ]
        dados = {}
        for chave in chaves:
            dados[chave.replace("_oficina", "")] = self.get(chave) or ""
        return dados
