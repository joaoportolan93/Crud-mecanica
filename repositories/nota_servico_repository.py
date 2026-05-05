"""
Repository de Notas de Serviço — o coração do sistema.

Contém os dois fluxos críticos:
  - fechar_nota(): transação atômica que baixa estoque, registra
    movimentações, atualiza km e consome número da OS.
  - cancelar_nota(): estorna movimentações de estoque se a nota
    já havia sido concluída.
"""

import sqlite3
from database import Database
from exceptions import (
    NotaNotFoundError,
    NotaStatusError,
    NotaSemItensError,
    PecaNotFoundError,
    EstoqueInsuficienteError,
    IntegridadeError,
)


class NotaServicoRepository:
    """Acesso a dados da tabela `notas_servico` e seus itens."""

    def __init__(self, db: Database) -> None:
        self.db = db

    @property
    def conn(self) -> sqlite3.Connection:
        return self.db.connection

    # ════════════════════════════════════════════════════════
    # CRIAÇÃO
    # ════════════════════════════════════════════════════════

    def criar_rascunho(
        self,
        cliente_id: int,
        veiculo_id: int,
        km_entrada: int | None = None,
        observacoes: str | None = None,
    ) -> int:
        """Cria uma nota em status ABERTA e consome o próximo número da OS.

        Operação atômica: lê e incrementa proximo_numero_os na mesma
        transação para evitar números duplicados.

        Returns:
            ID da nota criada.
        """
        with self.conn:
            # Consumir número sequencial atomicamente
            row = self.conn.execute(
                "SELECT valor FROM configuracoes "
                "WHERE chave = 'proximo_numero_os'"
            ).fetchone()
            numero = int(row["valor"])

            self.conn.execute(
                "UPDATE configuracoes SET valor = ? "
                "WHERE chave = 'proximo_numero_os'",
                (str(numero + 1),),
            )

            cursor = self.conn.execute(
                """INSERT INTO notas_servico
                   (numero, cliente_id, veiculo_id, km_entrada, observacoes)
                   VALUES (?, ?, ?, ?, ?)""",
                (numero, cliente_id, veiculo_id, km_entrada, observacoes),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    # ════════════════════════════════════════════════════════
    # ITENS: PEÇAS
    # ════════════════════════════════════════════════════════

    def adicionar_peca(
        self,
        nota_id: int,
        peca_id: int,
        quantidade: float,
        valor_unitario: float | None = None,
    ) -> int:
        """Adiciona uma peça à nota.

        Se valor_unitario não for informado, usa preco_venda da peça.
        A descrição é um snapshot do cadastro no momento da inserção.

        Returns:
            ID do item criado em nota_pecas.
        """
        nota = self._get_nota_ativa(nota_id)
        self._validar_nota_editavel(nota)

        peca = self.conn.execute(
            "SELECT * FROM pecas WHERE id = ? AND deleted_at IS NULL",
            (peca_id,),
        ).fetchone()
        if peca is None:
            raise PecaNotFoundError(f"Peça ID {peca_id} não encontrada.")

        preco = valor_unitario if valor_unitario is not None else peca["preco_venda"]
        total = round(quantidade * preco, 2)

        cursor = self.conn.execute(
            """INSERT INTO nota_pecas
               (nota_id, peca_id, descricao, quantidade,
                valor_unitario, valor_total)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nota_id, peca_id, peca["descricao"],
             round(quantidade, 4), round(preco, 2), total),
        )
        self.conn.commit()
        self._recalcular_totais(nota_id)
        return cursor.lastrowid  # type: ignore[return-value]

    def adicionar_servico(
        self,
        nota_id: int,
        descricao: str | None = None,
        servico_id: int | None = None,
        quantidade: float = 1,
        valor_unitario: float | None = None,
    ) -> int:
        """Adiciona um serviço à nota.

        Pode ser do catálogo (servico_id) ou ad-hoc (descricao + valor).
        Se servico_id for informado, usa descricao e preco_padrao como default.

        Returns:
            ID do item criado em nota_servicos.
        """
        nota = self._get_nota_ativa(nota_id)
        self._validar_nota_editavel(nota)

        if servico_id:
            servico = self.conn.execute(
                "SELECT * FROM servicos WHERE id = ? AND deleted_at IS NULL",
                (servico_id,),
            ).fetchone()
            if servico is None:
                raise IntegridadeError(f"Serviço ID {servico_id} não encontrado.")
            desc = descricao or servico["descricao"]
            preco = valor_unitario if valor_unitario is not None else servico["preco_padrao"]
        else:
            if not descricao:
                raise ValueError("Serviço ad-hoc precisa de descrição.")
            if valor_unitario is None:
                raise ValueError("Serviço ad-hoc precisa de valor_unitario.")
            desc = descricao
            preco = valor_unitario

        total = round(quantidade * preco, 2)

        cursor = self.conn.execute(
            """INSERT INTO nota_servicos
               (nota_id, servico_id, descricao, quantidade,
                valor_unitario, valor_total)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (nota_id, servico_id, desc,
             round(quantidade, 4), round(preco, 2), total),
        )
        self.conn.commit()
        self._recalcular_totais(nota_id)
        return cursor.lastrowid  # type: ignore[return-value]

    def remover_peca(self, item_id: int) -> None:
        """Remove um item de peça da nota."""
        item = self.conn.execute(
            "SELECT nota_id FROM nota_pecas WHERE id = ?", (item_id,)
        ).fetchone()
        if item is None:
            raise NotaNotFoundError(f"Item de peça ID {item_id} não encontrado.")

        nota = self._get_nota_ativa(item["nota_id"])
        self._validar_nota_editavel(nota)

        self.conn.execute("DELETE FROM nota_pecas WHERE id = ?", (item_id,))
        self.conn.commit()
        self._recalcular_totais(item["nota_id"])

    def remover_servico(self, item_id: int) -> None:
        """Remove um item de serviço da nota."""
        item = self.conn.execute(
            "SELECT nota_id FROM nota_servicos WHERE id = ?", (item_id,)
        ).fetchone()
        if item is None:
            raise NotaNotFoundError(f"Item de serviço ID {item_id} não encontrado.")

        nota = self._get_nota_ativa(item["nota_id"])
        self._validar_nota_editavel(nota)

        self.conn.execute("DELETE FROM nota_servicos WHERE id = ?", (item_id,))
        self.conn.commit()
        self._recalcular_totais(item["nota_id"])

    # ════════════════════════════════════════════════════════
    # LEITURA
    # ════════════════════════════════════════════════════════

    def buscar_por_id(self, id: int) -> dict | None:
        """Retorna a nota completa com seus itens (peças e serviços).

        Returns:
            Dict com chaves: 'nota', 'pecas', 'servicos' ou None.
        """
        nota = self.conn.execute(
            "SELECT * FROM notas_servico WHERE id = ? AND deleted_at IS NULL",
            (id,),
        ).fetchone()
        if nota is None:
            return None

        pecas = self.conn.execute(
            "SELECT * FROM nota_pecas WHERE nota_id = ?", (id,)
        ).fetchall()
        servicos = self.conn.execute(
            "SELECT * FROM nota_servicos WHERE nota_id = ?", (id,)
        ).fetchall()

        return {"nota": nota, "pecas": pecas, "servicos": servicos}

    def buscar_por_numero(self, numero: int) -> sqlite3.Row | None:
        """Busca nota pelo número sequencial da OS."""
        return self.conn.execute(
            "SELECT * FROM notas_servico "
            "WHERE numero = ? AND deleted_at IS NULL",
            (numero,),
        ).fetchone()

    def listar(
        self,
        cliente_id: int | None = None,
        veiculo_id: int | None = None,
        data_inicio: str | None = None,
        data_fim: str | None = None,
        status: str | None = None,
        busca: str | None = None,
        limit: int = 200,
    ) -> list[sqlite3.Row]:
        """Lista notas com filtros opcionais.

        Args:
            data_inicio/data_fim: formato 'YYYY-MM-DD'.
            busca: busca por número da OS, nome do cliente ou placa.
        """
        query = (
            "SELECT n.* FROM notas_servico n "
            "LEFT JOIN clientes c ON n.cliente_id = c.id "
            "LEFT JOIN veiculos v ON n.veiculo_id = v.id "
            "WHERE n.deleted_at IS NULL"
        )
        params: list = []

        if cliente_id:
            query += " AND n.cliente_id = ?"
            params.append(cliente_id)
        if veiculo_id:
            query += " AND n.veiculo_id = ?"
            params.append(veiculo_id)
        if data_inicio:
            query += " AND n.data_abertura >= ?"
            params.append(data_inicio)
        if data_fim:
            query += " AND n.data_abertura <= ?"
            params.append(data_fim + " 23:59:59")
        if status:
            query += " AND n.status = ?"
            params.append(status)
        if busca:
            query += (
                " AND (CAST(n.numero AS TEXT) LIKE ?"
                " OR c.nome LIKE ? OR v.placa LIKE ?)"
            )
            params.extend([f"%{busca}%", f"%{busca}%", f"%{busca}%"])

        query += " ORDER BY n.data_abertura DESC LIMIT ?"
        params.append(limit)
        return self.conn.execute(query, params).fetchall()

    # ════════════════════════════════════════════════════════
    # FECHAR NOTA — Transação atômica crítica
    # ════════════════════════════════════════════════════════

    def fechar_nota(
        self,
        nota_id: int,
        forma_pagamento: str,
        desconto: float = 0,
    ) -> None:
        """Fecha uma nota de serviço. Transação atômica que executa:

        1. Valida status (só ABERTA ou EM_ANDAMENTO)
        2. Valida que a nota tem pelo menos 1 item
        3. Para cada peça: verifica estoque, subtrai e registra SAIDA
        4. Recalcula subtotais e valor_total
        5. Atualiza km_atual do veículo (se km_entrada informado)
        6. Marca como CONCLUIDA com data_conclusao

        Qualquer falha = rollback completo, nada é alterado.

        Args:
            nota_id: ID da nota a fechar.
            forma_pagamento: DINHEIRO, PIX, CARTAO_CREDITO, etc.
            desconto: Valor do desconto global (padrão 0).

        Raises:
            NotaNotFoundError: Nota não existe.
            NotaStatusError: Status não permite fechamento.
            NotaSemItensError: Nota sem peças nem serviços.
            EstoqueInsuficienteError: Peça com estoque insuficiente.
        """
        with self.conn:
            # ── 1. Buscar e validar nota ────────────────────
            nota = self.conn.execute(
                "SELECT * FROM notas_servico "
                "WHERE id = ? AND deleted_at IS NULL",
                (nota_id,),
            ).fetchone()

            if nota is None:
                raise NotaNotFoundError(f"Nota ID {nota_id} não encontrada.")

            if nota["status"] not in ("ABERTA", "EM_ANDAMENTO"):
                raise NotaStatusError(
                    f"Nota não pode ser fechada. "
                    f"Status atual: {nota['status']}"
                )

            # ── 2. Buscar itens ─────────────────────────────
            pecas_items = self.conn.execute(
                "SELECT * FROM nota_pecas WHERE nota_id = ?",
                (nota_id,),
            ).fetchall()

            servicos_items = self.conn.execute(
                "SELECT * FROM nota_servicos WHERE nota_id = ?",
                (nota_id,),
            ).fetchall()

            if not pecas_items and not servicos_items:
                raise NotaSemItensError(
                    "Nota precisa de pelo menos 1 item para ser fechada."
                )

            # ── 3. Baixar estoque de cada peça ──────────────
            for item in pecas_items:
                peca = self.conn.execute(
                    "SELECT id, descricao, quantidade FROM pecas WHERE id = ?",
                    (item["peca_id"],),
                ).fetchone()

                if peca is None:
                    raise PecaNotFoundError(
                        f"Peça ID {item['peca_id']} não encontrada no cadastro."
                    )

                qtd_anterior = peca["quantidade"]
                qtd_posterior = round(qtd_anterior - item["quantidade"], 4)

                if qtd_posterior < 0:
                    raise EstoqueInsuficienteError(
                        f"Estoque insuficiente para '{peca['descricao']}': "
                        f"disponível {qtd_anterior}, "
                        f"necessário {item['quantidade']}"
                    )

                # Atualizar estoque
                self.conn.execute(
                    "UPDATE pecas SET quantidade = ? WHERE id = ?",
                    (qtd_posterior, item["peca_id"]),
                )

                # Registrar movimentação de SAÍDA
                self.conn.execute(
                    """INSERT INTO movimentacoes_estoque
                       (peca_id, nota_id, tipo, quantidade,
                        quantidade_anterior, quantidade_posterior, motivo)
                       VALUES (?, ?, 'SAIDA', ?, ?, ?, ?)""",
                    (item["peca_id"], nota_id, item["quantidade"],
                     qtd_anterior, qtd_posterior,
                     f"Baixa automática - OS #{nota['numero']}"),
                )

            # ── 4. Calcular totais ──────────────────────────
            subtotal_pecas = round(
                sum(i["valor_total"] for i in pecas_items), 2
            )
            subtotal_servicos = round(
                sum(i["valor_total"] for i in servicos_items), 2
            )
            desconto = round(desconto, 2)
            valor_total = round(
                subtotal_pecas + subtotal_servicos - desconto, 2
            )

            # Segurança: desconto não pode superar o total
            if valor_total < 0:
                valor_total = 0

            # ── 5. Atualizar km do veículo ──────────────────
            if nota["km_entrada"]:
                self.conn.execute(
                    "UPDATE veiculos SET km_atual = ? "
                    "WHERE id = ? AND (km_atual IS NULL OR km_atual < ?)",
                    (nota["km_entrada"], nota["veiculo_id"],
                     nota["km_entrada"]),
                )

            # ── 6. Marcar nota como CONCLUÍDA ───────────────
            self.conn.execute(
                """UPDATE notas_servico SET
                    status = 'CONCLUIDA',
                    data_conclusao = datetime('now', 'localtime'),
                    subtotal_pecas = ?,
                    subtotal_servicos = ?,
                    desconto = ?,
                    valor_total = ?,
                    forma_pagamento = ?
                   WHERE id = ?""",
                (subtotal_pecas, subtotal_servicos, desconto,
                 valor_total, forma_pagamento, nota_id),
            )
        # Fim do with: commit automático se não houve exceção

    # ════════════════════════════════════════════════════════
    # CANCELAR NOTA — Com estorno de estoque
    # ════════════════════════════════════════════════════════

    def cancelar_nota(
        self, nota_id: int, motivo: str | None = None
    ) -> None:
        """Cancela uma nota de serviço.

        Regras debatidas pelo painel:
          - ABERTA/EM_ANDAMENTO: cancela direto (sem estorno, estoque
            não foi tocado).
          - CONCLUIDA: cancela COM estorno — para cada SAIDA registrada
            nessa nota, cria um AJUSTE de volta e devolve ao estoque.
          - CANCELADA: erro — já está cancelada.

        Args:
            nota_id: ID da nota a cancelar.
            motivo: Motivo do cancelamento (opcional mas recomendado).
        """
        with self.conn:
            nota = self.conn.execute(
                "SELECT * FROM notas_servico "
                "WHERE id = ? AND deleted_at IS NULL",
                (nota_id,),
            ).fetchone()

            if nota is None:
                raise NotaNotFoundError(f"Nota ID {nota_id} não encontrada.")

            if nota["status"] == "CANCELADA":
                raise NotaStatusError("Nota já está cancelada.")

            # Se era CONCLUIDA, precisa estornar o estoque
            if nota["status"] == "CONCLUIDA":
                self._estornar_movimentacoes(nota_id, nota["numero"])

            # Marcar como CANCELADA
            obs_atual = nota["observacoes"] or ""
            obs_cancelamento = (
                f"\n[CANCELADA] {motivo}" if motivo else ""
            )

            self.conn.execute(
                """UPDATE notas_servico SET
                    status = 'CANCELADA',
                    observacoes = ?
                   WHERE id = ?""",
                (obs_atual + obs_cancelamento, nota_id),
            )

    def atualizar_financeiro_concluida(
        self,
        nota_id: int,
        desconto: float = 0,
        forma_pagamento: str | None = None,
    ) -> None:
        """Atualiza campos financeiros de uma OS já concluída.

        Não altera itens nem estoque; só recalcula subtotal/total com base
        nos itens já gravados na nota.
        """
        with self.conn:
            nota = self.conn.execute(
                "SELECT * FROM notas_servico WHERE id = ? AND deleted_at IS NULL",
                (nota_id,),
            ).fetchone()
            if nota is None:
                raise NotaNotFoundError(f"Nota ID {nota_id} não encontrada.")
            if nota["status"] != "CONCLUIDA":
                raise NotaStatusError("Apenas notas concluídas podem receber este tipo de atualização.")

            row_p = self.conn.execute(
                "SELECT COALESCE(SUM(valor_total), 0) as total FROM nota_pecas WHERE nota_id = ?",
                (nota_id,),
            ).fetchone()
            row_s = self.conn.execute(
                "SELECT COALESCE(SUM(valor_total), 0) as total FROM nota_servicos WHERE nota_id = ?",
                (nota_id,),
            ).fetchone()

            subtotal_pecas = round(row_p["total"], 2)
            subtotal_servicos = round(row_s["total"], 2)
            desconto = round(desconto, 2)
            valor_total = round(subtotal_pecas + subtotal_servicos - desconto, 2)
            if valor_total < 0:
                valor_total = 0

            self.conn.execute(
                """UPDATE notas_servico SET
                    subtotal_pecas = ?,
                    subtotal_servicos = ?,
                    desconto = ?,
                    valor_total = ?,
                    forma_pagamento = COALESCE(?, forma_pagamento)
                   WHERE id = ?""",
                (subtotal_pecas, subtotal_servicos, desconto, valor_total, forma_pagamento, nota_id),
            )

    def _estornar_movimentacoes(
        self, nota_id: int, numero_os: int
    ) -> None:
        """Estorna todas as SAIDAs de uma nota concluída.

        Para cada SAIDA, devolve a quantidade ao estoque e registra
        um AJUSTE com motivo de estorno.
        """
        saidas = self.conn.execute(
            "SELECT * FROM movimentacoes_estoque "
            "WHERE nota_id = ? AND tipo = 'SAIDA'",
            (nota_id,),
        ).fetchall()

        for saida in saidas:
            peca = self.conn.execute(
                "SELECT quantidade FROM pecas WHERE id = ?",
                (saida["peca_id"],),
            ).fetchone()

            if peca is None:
                continue  # Peça foi excluída — não tem como estornar

            qtd_anterior = peca["quantidade"]
            qtd_posterior = round(qtd_anterior + saida["quantidade"], 4)

            self.conn.execute(
                "UPDATE pecas SET quantidade = ? WHERE id = ?",
                (qtd_posterior, saida["peca_id"]),
            )

            self.conn.execute(
                """INSERT INTO movimentacoes_estoque
                   (peca_id, nota_id, tipo, quantidade,
                    quantidade_anterior, quantidade_posterior, motivo)
                   VALUES (?, ?, 'AJUSTE', ?, ?, ?, ?)""",
                (saida["peca_id"], nota_id, saida["quantidade"],
                 qtd_anterior, qtd_posterior,
                 f"Estorno - Cancelamento da OS #{numero_os}"),
            )

    # ════════════════════════════════════════════════════════
    # MÉTODOS AUXILIARES INTERNOS
    # ════════════════════════════════════════════════════════

    def _get_nota_ativa(self, nota_id: int) -> sqlite3.Row:
        """Busca nota ativa ou levanta NotaNotFoundError."""
        nota = self.conn.execute(
            "SELECT * FROM notas_servico "
            "WHERE id = ? AND deleted_at IS NULL",
            (nota_id,),
        ).fetchone()
        if nota is None:
            raise NotaNotFoundError(f"Nota ID {nota_id} não encontrada.")
        return nota

    def _validar_nota_editavel(self, nota: sqlite3.Row) -> None:
        """Verifica se a nota pode receber edições (adicionar/remover itens)."""
        if nota["status"] not in ("ABERTA", "EM_ANDAMENTO"):
            raise NotaStatusError(
                f"Nota não pode ser editada. Status: {nota['status']}"
            )

    def _recalcular_totais(self, nota_id: int) -> None:
        """Recalcula subtotais e valor_total da nota a partir dos itens.

        Chamado internamente após adicionar/remover itens.
        """
        row_p = self.conn.execute(
            "SELECT COALESCE(SUM(valor_total), 0) as total "
            "FROM nota_pecas WHERE nota_id = ?",
            (nota_id,),
        ).fetchone()
        row_s = self.conn.execute(
            "SELECT COALESCE(SUM(valor_total), 0) as total "
            "FROM nota_servicos WHERE nota_id = ?",
            (nota_id,),
        ).fetchone()

        sub_p = round(row_p["total"], 2)
        sub_s = round(row_s["total"], 2)

        nota = self.conn.execute(
            "SELECT desconto FROM notas_servico WHERE id = ?",
            (nota_id,),
        ).fetchone()
        desconto = nota["desconto"] if nota else 0
        total = round(sub_p + sub_s - desconto, 2)
        if total < 0:
            total = 0

        self.conn.execute(
            """UPDATE notas_servico SET
                subtotal_pecas = ?,
                subtotal_servicos = ?,
                valor_total = ?
               WHERE id = ?""",
            (sub_p, sub_s, total, nota_id),
        )
        self.conn.commit()

    # ── Soft delete da nota ─────────────────────────────────

    def deletar(self, id: int) -> None:
        """Soft delete da nota (não confundir com cancelar)."""
        if self._get_nota_ativa(id) is None:
            raise NotaNotFoundError(f"Nota ID {id} não encontrada.")
        self.conn.execute(
            "UPDATE notas_servico SET deleted_at = datetime('now', 'localtime') "
            "WHERE id = ? AND deleted_at IS NULL",
            (id,),
        )
        self.conn.commit()
