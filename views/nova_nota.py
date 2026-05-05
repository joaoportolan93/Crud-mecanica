"""Tela de Nova/Editar OS — a mais complexa do sistema."""

import os
from datetime import datetime
from tkinter import filedialog

import customtkinter as ctk
from components.autocomplete import AutocompleteEntry
from components.cards import ConfirmDialog, StatusBadge
from exceptions import EstoqueInsuficienteError
from components.layout import DETAIL_PADX, PAGE_BOTTOM_PADY, PAGE_PADX, PAGE_TOP_PADY, SECTION_GAP, SUBSECTION_GAP
from components.validation import attach_numeric_validation, normalize_numeric_text


class NovaNotaView(ctk.CTkFrame):

    def __init__(self, master, repos, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.repos = repos
        self.app = app
        self._nota_id = None
        self._cliente_id = None
        self._veiculo_id = None
        self._itens_pecas: list[dict] = []
        self._itens_servicos: list[dict] = []
        self._modo_edicao = False
        self._nota_status = None
        self._itens_editaveis = True
        self._btn_add_peca = None
        self._btn_add_servico = None
        self._btn_add_servico_adhoc = None

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Cabeçalho fixo
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAGE_PADX, pady=(PAGE_TOP_PADY, SECTION_GAP))
        header.grid_columnconfigure(0, weight=1)
        self._title = ctk.CTkLabel(header, text="Nova Nota de Serviço", font=ctk.CTkFont(size=22, weight="bold"))
        self._title.grid(row=0, column=0, sticky="w")
        self._status_frame = ctk.CTkFrame(header, fg_color="transparent")
        self._status_frame.grid(row=0, column=1, sticky="e")

        self._erro_label = ctk.CTkLabel(self, text="", text_color="#ea4335", font=ctk.CTkFont(size=12))
        self._erro_label.grid(row=3, column=0, sticky="ew", padx=PAGE_PADX, pady=(2, 0))

        # Área principal com duas colunas e rolagem independente
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=PAGE_PADX)
        body.grid_columnconfigure(0, weight=4)
        body.grid_columnconfigure(1, weight=6)
        body.grid_rowconfigure(0, weight=1)

        left_col = ctk.CTkScrollableFrame(body, fg_color=("gray14", "gray10"), corner_radius=8)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, SECTION_GAP), pady=0)
        right_col = ctk.CTkScrollableFrame(body, fg_color=("gray14", "gray10"), corner_radius=8)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(SECTION_GAP, 0), pady=0)

        def section_label(parent, text):
            ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(0, 6))

        # Cliente
        section_label(left_col, "Dados da OS")
        ctk.CTkLabel(left_col, text="Cliente *", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        self._cliente_search = AutocompleteEntry(
            left_col, search_fn=lambda t: [dict(r) for r in self.repos.clientes.listar(busca=t)],
            on_select=self._on_cliente_select, placeholder="Buscar cliente...",
        )
        self._cliente_search.pack(fill="x", pady=(2, 2))
        self._cliente_label = ctk.CTkLabel(left_col, text="", text_color="gray50", font=ctk.CTkFont(size=12))
        self._cliente_label.pack(anchor="w", pady=(0, SECTION_GAP))

        # Veículo / Km / Observações
        ctk.CTkLabel(left_col, text="Veículo *", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        self._veiculo_var = ctk.StringVar(value="Selecione o cliente primeiro")
        self._veiculo_menu = ctk.CTkOptionMenu(left_col, variable=self._veiculo_var, values=["—"], command=self._on_veiculo_select, state="disabled")
        self._veiculo_menu.pack(fill="x", pady=(2, SECTION_GAP))
        self._veiculos_map = {}

        ctk.CTkLabel(left_col, text="Km Entrada", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        self._km_entry = ctk.CTkEntry(left_col, placeholder_text="Ex: 50000")
        attach_numeric_validation(self._km_entry, "integer")
        self._km_entry.pack(fill="x", pady=(2, SECTION_GAP))

        ctk.CTkLabel(left_col, text="Observações", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        self._obs_text = ctk.CTkTextbox(left_col, height=120)
        self._obs_text.pack(fill="x", pady=(2, 0))

        # Peças
        section_label(right_col, "Itens da Ordem")
        ctk.CTkLabel(right_col, text="Peças", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        add_peca = ctk.CTkFrame(right_col, fg_color="transparent")
        add_peca.pack(fill="x", pady=(2, 4))
        self._peca_search = AutocompleteEntry(
            add_peca, search_fn=lambda t: [dict(r) for r in self.repos.pecas.listar(busca=t)],
            on_select=self._on_peca_select, display_key="descricao", placeholder="Buscar peça...",
        )
        self._peca_search.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._sel_peca = None
        self._peca_qtd = ctk.CTkEntry(add_peca, width=56, placeholder_text="Qtd")
        attach_numeric_validation(self._peca_qtd, "integer")
        self._peca_qtd.pack(side="left", padx=2)
        self._peca_preco = ctk.CTkEntry(add_peca, width=82, placeholder_text="Preço")
        attach_numeric_validation(self._peca_preco, "decimal")
        self._peca_preco.pack(side="left", padx=2)
        self._btn_add_peca = ctk.CTkButton(add_peca, text="+", width=38, font=ctk.CTkFont(weight="bold"), command=self._add_peca)
        self._btn_add_peca.pack(side="left", padx=2)

        self._pecas_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        self._pecas_frame.pack(fill="x", pady=(0, SECTION_GAP))

        # Serviços
        ctk.CTkLabel(right_col, text="Serviços", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
        add_serv = ctk.CTkFrame(right_col, fg_color="transparent")
        add_serv.pack(fill="x", pady=(2, 3))
        self._serv_search = AutocompleteEntry(
            add_serv, search_fn=lambda t: [dict(r) for r in self.repos.servicos.listar(busca=t)],
            on_select=self._on_servico_select, display_key="descricao", placeholder="Buscar serviço...",
        )
        self._serv_search.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._sel_servico = None
        self._serv_preco = ctk.CTkEntry(add_serv, width=82, placeholder_text="Preço")
        attach_numeric_validation(self._serv_preco, "decimal")
        self._serv_preco.pack(side="left", padx=2)
        self._btn_add_servico = ctk.CTkButton(add_serv, text="+", width=38, font=ctk.CTkFont(weight="bold"), command=self._add_servico)
        self._btn_add_servico.pack(side="left", padx=2)

        adhoc = ctk.CTkFrame(right_col, fg_color="transparent")
        adhoc.pack(fill="x", pady=(0, 4))
        self._adhoc_desc = ctk.CTkEntry(adhoc, placeholder_text="Ou digite serviço avulso...")
        self._adhoc_desc.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._adhoc_preco = ctk.CTkEntry(adhoc, width=82, placeholder_text="Preço")
        attach_numeric_validation(self._adhoc_preco, "decimal")
        self._adhoc_preco.pack(side="left", padx=2)
        self._btn_add_servico_adhoc = ctk.CTkButton(adhoc, text="+", width=38, font=ctk.CTkFont(weight="bold"), fg_color=("gray75", "gray30"), command=self._add_servico_adhoc)
        self._btn_add_servico_adhoc.pack(side="left", padx=2)

        self._servicos_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        self._servicos_frame.pack(fill="x", pady=(0, 0))

        # Rodapé fixo com pagamento, totais e ações
        footer = ctk.CTkFrame(self, fg_color=("gray85", "gray15"), corner_radius=8)
        footer.grid(row=2, column=0, sticky="ew", padx=PAGE_PADX, pady=(SECTION_GAP, PAGE_BOTTOM_PADY))
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=1)

        pag_col = ctk.CTkFrame(footer, fg_color="transparent")
        pag_col.grid(row=0, column=0, sticky="w", padx=DETAIL_PADX, pady=(10, 6))
        ctk.CTkLabel(pag_col, text="Forma de Pagamento", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        self._pagamento_var = ctk.StringVar(value="DINHEIRO")
        ctk.CTkOptionMenu(pag_col, variable=self._pagamento_var, values=["DINHEIRO", "PIX", "CARTAO_CREDITO", "CARTAO_DEBITO", "BOLETO", "OUTRO"], width=180).pack(anchor="w", pady=(5, 0))

        tot_col = ctk.CTkFrame(footer, fg_color="transparent")
        tot_col.grid(row=0, column=1, sticky="e", padx=DETAIL_PADX, pady=(10, 6))
        self._lbl_sub_pecas = ctk.CTkLabel(tot_col, text="Subtotal Peças: R$ 0,00", font=ctk.CTkFont(size=13))
        self._lbl_sub_pecas.pack(anchor="e")
        self._lbl_sub_servicos = ctk.CTkLabel(tot_col, text="Subtotal Serviços: R$ 0,00", font=ctk.CTkFont(size=13))
        self._lbl_sub_servicos.pack(anchor="e")
        desc_row = ctk.CTkFrame(tot_col, fg_color="transparent")
        desc_row.pack(anchor="e", pady=5)
        ctk.CTkLabel(desc_row, text="Desconto: R$").pack(side="left")
        self._desconto_entry = ctk.CTkEntry(desc_row, width=90, placeholder_text="0,00")
        attach_numeric_validation(self._desconto_entry, "decimal")
        self._desconto_entry.pack(side="left", padx=5)
        self._desconto_entry.bind("<KeyRelease>", lambda e: self._recalcular_totais())
        ctk.CTkFrame(tot_col, height=1, fg_color="gray40").pack(fill="x", pady=4)
        self._lbl_total = ctk.CTkLabel(tot_col, text="TOTAL: R$ 0,00", font=ctk.CTkFont(size=24, weight="bold"), text_color="#1a73e8")
        self._lbl_total.pack(anchor="e")

        self._btns = ctk.CTkFrame(footer, fg_color="transparent")
        self._btns.grid(row=1, column=0, columnspan=2, sticky="ew", padx=DETAIL_PADX, pady=(0, 10))

    def _rebuild_buttons(self) -> None:
        for w in self._btns.winfo_children():
            w.destroy()

        nota = None
        if self._nota_id:
            try:
                det = self.repos.notas.buscar_por_id(self._nota_id)
                nota = det["nota"] if det else None
            except Exception:
                pass

        status = nota["status"] if nota else "RASCUNHO"
        self._nota_status = status
        self._itens_editaveis = status in ("RASCUNHO", "ABERTA", "EM_ANDAMENTO")

        if status in ("RASCUNHO", "ABERTA", "EM_ANDAMENTO"):
            ctk.CTkButton(self._btns, text="💾 Salvar Rascunho", width=150, fg_color=("gray75","gray30"), hover_color=("gray65","gray40"), command=self._salvar_rascunho).pack(side="left", padx=5)
            ctk.CTkButton(self._btns, text="✅ Concluir OS", width=150, fg_color="#34a853", hover_color="#2e7d32", command=self._concluir).pack(side="left", padx=5)

        if status == "CONCLUIDA":
            ctk.CTkButton(self._btns, text="📄 Exportar PDF", width=140, fg_color="#1a73e8", hover_color="#1558b0", command=self._exportar_pdf).pack(side="left", padx=5)
            ctk.CTkButton(self._btns, text="💾 Salvar Alterações", width=170, fg_color="#1a73e8", hover_color="#1558b0", command=self._salvar_alteracoes_concluida).pack(side="left", padx=5)

        if status in ("RASCUNHO", "ABERTA", "EM_ANDAMENTO", "CONCLUIDA"):
            ctk.CTkButton(self._btns, text="❌ Cancelar OS", width=140, fg_color="#ea4335", hover_color="#c62828", command=self._cancelar).pack(side="right", padx=5)

        ctk.CTkButton(self._btns, text="← Voltar", width=100, fg_color=("gray75","gray30"), hover_color=("gray65","gray40"),
            command=lambda: self.app.show_view("notas")).pack(side="right", padx=5)

    def carregar_nota(self, nota_id: int | None = None, cliente_id: int | None = None) -> None:
        """Configura a view para nova nota ou edição."""
        self._nota_id = nota_id
        self._itens_pecas.clear()
        self._itens_servicos.clear()
        self._sel_peca = None
        self._sel_servico = None
        self._erro_label.configure(text="")

        # Limpar campos
        self._cliente_search.clear()
        self._cliente_label.configure(text="")
        self._veiculo_var.set("Selecione o cliente primeiro")
        self._veiculo_menu.configure(state="disabled")
        self._km_entry.delete(0, "end")
        self._obs_text.delete("1.0", "end")
        self._desconto_entry.delete(0, "end")

        for w in self._status_frame.winfo_children():
            w.destroy()

        if nota_id:
            self._modo_edicao = True
            self._title.configure(text=f"Nota de Serviço #{nota_id}")
            self._carregar_nota_existente(nota_id)
        else:
            self._modo_edicao = False
            self._title.configure(text="Nova Nota de Serviço")
            self._cliente_id = None
            self._veiculo_id = None
            if cliente_id:
                cli = self.repos.clientes.buscar_por_id(cliente_id)
                if cli:
                    self._on_cliente_select(dict(cli))
                    self._cliente_search.set_text(cli["nome"])

        self._rebuild_buttons()
        self._atualizar_listas()
        self._recalcular_totais()

    def _carregar_nota_existente(self, nota_id: int) -> None:
        try:
            det = self.repos.notas.buscar_por_id(nota_id)
            if not det:
                return
            nota = det["nota"]

            StatusBadge(self._status_frame, nota["status"]).pack(side="left", padx=5)
            self._title.configure(text=f"OS #{nota['numero']} — Editar")

            cli = self.repos.clientes.buscar_por_id(nota["cliente_id"])
            if cli:
                self._on_cliente_select(dict(cli))
                self._cliente_search.set_text(cli["nome"])

            veiculo_id = nota["veiculo_id"] if "veiculo_id" in nota.keys() and nota["veiculo_id"] else None
            if veiculo_id:
                veic = self.repos.veiculos.buscar_por_id(veiculo_id)
                if veic:
                    key = f"{veic['placa'] or '—'} - {veic['modelo']}"
                    self._veiculo_var.set(key)
                    self._veiculo_id = veic["id"]

            if "km_entrada" in nota.keys() and nota["km_entrada"]:
                self._km_entry.insert(0, str(nota["km_entrada"]))
            if "observacoes" in nota.keys() and nota["observacoes"]:
                self._obs_text.insert("1.0", nota["observacoes"])
            if "desconto" in nota.keys() and nota["desconto"] and nota["desconto"] > 0:
                self._desconto_entry.insert(0, f"{nota['desconto']:.2f}")
            if "forma_pagamento" in nota.keys() and nota["forma_pagamento"]:
                self._pagamento_var.set(nota["forma_pagamento"])

            for p in det.get("pecas", []):
                self._itens_pecas.append({"id": p.get("peca_id"), "descricao": p["descricao"], "quantidade": p["quantidade"], "valor_unitario": p["valor_unitario"], "item_id": p.get("id")})
            for s in det.get("servicos", []):
                self._itens_servicos.append({"id": s.get("servico_id"), "descricao": s["descricao"], "valor": s["valor"], "item_id": s.get("id")})

            readonly = nota["status"] in ("CONCLUIDA", "CANCELADA")
            if readonly:
                self._cliente_search.entry.configure(state="disabled")
                self._veiculo_menu.configure(state="disabled")
                self._km_entry.configure(state="disabled")
                self._obs_text.configure(state="disabled")
                if self._btn_add_peca:
                    self._btn_add_peca.configure(state="disabled")
                if self._btn_add_servico:
                    self._btn_add_servico.configure(state="disabled")
                if self._btn_add_servico_adhoc:
                    self._btn_add_servico_adhoc.configure(state="disabled")
                self._peca_search.entry.configure(state="disabled")
                self._peca_qtd.configure(state="disabled")
                self._peca_preco.configure(state="disabled")
                self._serv_search.entry.configure(state="disabled")
                self._serv_preco.configure(state="disabled")
                self._adhoc_desc.configure(state="disabled")
                self._adhoc_preco.configure(state="disabled")
        except Exception as e:
            self._erro_label.configure(text=f"Erro ao carregar: {e}")

    def _on_cliente_select(self, cliente: dict) -> None:
        self._cliente_id = cliente["id"]
        self._cliente_label.configure(text=f"CPF/CNPJ: {cliente.get('cpf_cnpj', '—')} | Tel: {cliente.get('telefone', '—')}")
        veiculos = self.repos.veiculos.listar_por_cliente(cliente["id"])
        self._veiculos_map.clear()
        if veiculos:
            vals = []
            for v in veiculos:
                key = f"{v['placa'] or '—'} - {v['modelo']}"
                vals.append(key)
                self._veiculos_map[key] = v["id"]
            self._veiculo_menu.configure(values=vals, state="normal")
            self._veiculo_var.set(vals[0])
            self._veiculo_id = self._veiculos_map[vals[0]]
        else:
            self._veiculo_menu.configure(values=["Nenhum veículo"], state="disabled")
            self._veiculo_var.set("Nenhum veículo")

    def _on_veiculo_select(self, val: str) -> None:
        self._veiculo_id = self._veiculos_map.get(val)

    def _on_peca_select(self, peca: dict) -> None:
        if not self._itens_editaveis:
            return
        self._sel_peca = peca
        self._peca_preco.delete(0, "end")
        self._peca_preco.insert(0, f"{peca['preco_venda']:.2f}")
        self._peca_qtd.delete(0, "end")
        self._peca_qtd.insert(0, "1")

    def _on_servico_select(self, serv: dict) -> None:
        if not self._itens_editaveis:
            return
        self._sel_servico = serv
        self._serv_preco.delete(0, "end")
        self._serv_preco.insert(0, f"{serv['preco_padrao']:.2f}")

    def _add_peca(self) -> None:
        if not self._itens_editaveis:
            self._erro_label.configure(text="OS concluída: itens bloqueados para edição.")
            return
        if not self._sel_peca:
            self._erro_label.configure(text="Selecione uma peça primeiro.")
            return
        try:
            qtd = int(normalize_numeric_text(self._peca_qtd.get() or "1", "integer"))
            preco = float(normalize_numeric_text(self._peca_preco.get() or str(self._sel_peca["preco_venda"]), "decimal"))
        except ValueError:
            self._erro_label.configure(text="Quantidade ou preço inválido.")
            return

        self._itens_pecas.append({"id": self._sel_peca["id"], "descricao": self._sel_peca["descricao"], "quantidade": qtd, "valor_unitario": preco})
        self._sel_peca = None
        self._peca_search.clear()
        self._peca_qtd.delete(0, "end")
        self._peca_preco.delete(0, "end")
        self._erro_label.configure(text="")
        self._atualizar_listas()
        self._recalcular_totais()

    def _add_servico(self) -> None:
        if not self._itens_editaveis:
            self._erro_label.configure(text="OS concluída: itens bloqueados para edição.")
            return
        if not self._sel_servico:
            self._erro_label.configure(text="Selecione um serviço.")
            return
        try:
            preco = float(normalize_numeric_text(self._serv_preco.get() or str(self._sel_servico["preco_padrao"]), "decimal"))
        except ValueError:
            self._erro_label.configure(text="Preço inválido.")
            return
        self._itens_servicos.append({"id": self._sel_servico["id"], "descricao": self._sel_servico["descricao"], "valor": preco})
        self._sel_servico = None
        self._serv_search.clear()
        self._serv_preco.delete(0, "end")
        self._erro_label.configure(text="")
        self._atualizar_listas()
        self._recalcular_totais()

    def _add_servico_adhoc(self) -> None:
        if not self._itens_editaveis:
            self._erro_label.configure(text="OS concluída: itens bloqueados para edição.")
            return
        desc = self._adhoc_desc.get().strip()
        if not desc:
            self._erro_label.configure(text="Informe a descrição do serviço.")
            return
        try:
            preco = float(normalize_numeric_text(self._adhoc_preco.get() or "0", "decimal"))
        except ValueError:
            self._erro_label.configure(text="Preço inválido.")
            return
        self._itens_servicos.append({"id": None, "descricao": desc, "valor": preco})
        self._adhoc_desc.delete(0, "end")
        self._adhoc_preco.delete(0, "end")
        self._erro_label.configure(text="")
        self._atualizar_listas()
        self._recalcular_totais()

    def _atualizar_listas(self) -> None:
        for w in self._pecas_frame.winfo_children():
            w.destroy()
        for w in self._servicos_frame.winfo_children():
            w.destroy()

        if not self._itens_pecas:
            ctk.CTkLabel(self._pecas_frame, text="Nenhuma peça adicionada ainda.", text_color="gray50").pack(anchor="w", pady=(0, 4))

        for i, p in enumerate(self._itens_pecas):
            row = ctk.CTkFrame(self._pecas_frame, corner_radius=4)
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=p["descricao"], width=250, anchor="w").pack(side="left", padx=10, pady=4)
            ctk.CTkLabel(row, text=f"x{p['quantidade']}").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=f"R$ {p['valor_unitario']:.2f}").pack(side="left", padx=5)
            total = p["quantidade"] * p["valor_unitario"]
            ctk.CTkLabel(row, text=f"= R$ {total:.2f}", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
            if self._itens_editaveis:
                ctk.CTkButton(row, text="✕", width=30, height=24, fg_color="#ea4335", hover_color="#c62828",
                    command=lambda idx=i: self._remover_peca(idx)).pack(side="right", padx=5)

        if not self._itens_servicos:
            ctk.CTkLabel(self._servicos_frame, text="Nenhum serviço adicionado ainda.", text_color="gray50").pack(anchor="w", pady=(0, 4))

        for i, s in enumerate(self._itens_servicos):
            row = ctk.CTkFrame(self._servicos_frame, corner_radius=4)
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=s["descricao"], width=300, anchor="w").pack(side="left", padx=10, pady=4)
            ctk.CTkLabel(row, text=f"R$ {s['valor']:.2f}", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
            if self._itens_editaveis:
                ctk.CTkButton(row, text="✕", width=30, height=24, fg_color="#ea4335", hover_color="#c62828",
                    command=lambda idx=i: self._remover_servico(idx)).pack(side="right", padx=5)

    def _remover_peca(self, idx: int) -> None:
        self._itens_pecas.pop(idx)
        self._atualizar_listas()
        self._recalcular_totais()

    def _remover_servico(self, idx: int) -> None:
        self._itens_servicos.pop(idx)
        self._atualizar_listas()
        self._recalcular_totais()

    def _recalcular_totais(self) -> None:
        sub_p = sum(p["quantidade"] * p["valor_unitario"] for p in self._itens_pecas)
        sub_s = sum(s["valor"] for s in self._itens_servicos)
        try:
            desc = float(normalize_numeric_text(self._desconto_entry.get() or "0", "decimal"))
        except ValueError:
            desc = 0
        total = sub_p + sub_s - desc
        self._lbl_sub_pecas.configure(text=f"Subtotal Peças: R$ {sub_p:.2f}")
        self._lbl_sub_servicos.configure(text=f"Subtotal Serviços: R$ {sub_s:.2f}")
        self._lbl_total.configure(text=f"TOTAL: R$ {max(total, 0):.2f}")

    def _validar(self) -> bool:
        if not self._cliente_id:
            self._erro_label.configure(text="Selecione um cliente.")
            return False
        if not self._veiculo_id:
            self._erro_label.configure(text="Selecione um veículo.")
            return False
        if not self._itens_pecas and not self._itens_servicos:
            self._erro_label.configure(text="Adicione pelo menos 1 peça ou serviço.")
            return False
        self._erro_label.configure(text="")
        return True

    def _salvar_rascunho(self) -> None:
        if not self._validar():
            return
        try:
            km = int(self._km_entry.get()) if self._km_entry.get() else None

            if not self._nota_id:
                self._nota_id = self.repos.notas.criar_rascunho(
                    cliente_id=self._cliente_id, veiculo_id=self._veiculo_id,
                    km_entrada=km, observacoes=self._obs_text.get("1.0", "end-1c").strip() or None,
                )
            # Limpar itens antigos e re-adicionar
            det = self.repos.notas.buscar_por_id(self._nota_id)
            if det:
                for p in det.get("pecas", []):
                    try: self.repos.notas.remover_peca(p["id"])
                    except Exception: pass
                for s in det.get("servicos", []):
                    try: self.repos.notas.remover_servico(s["id"])
                    except Exception: pass

            for p in self._itens_pecas:
                self.repos.notas.adicionar_peca(self._nota_id, p["id"], p["quantidade"], p["valor_unitario"])
            for s in self._itens_servicos:
                if s["id"]:
                    self.repos.notas.adicionar_servico(self._nota_id, servico_id=s["id"], valor_unitario=s["valor"])
                else:
                    self.repos.notas.adicionar_servico(self._nota_id, descricao=s["descricao"], valor_unitario=s["valor"])

            self._erro_label.configure(text="")
            self._title.configure(text=f"OS #{self._nota_id} — Rascunho salvo ✓")
            self._rebuild_buttons()
        except Exception as e:
            self._erro_label.configure(text=f"Erro ao salvar: {e}")

    def _salvar_alteracoes_concluida(self) -> None:
        if not self._nota_id:
            return
        try:
            desc = float(self._desconto_entry.get() or "0") if self._desconto_entry.get() else 0
            self.repos.notas.atualizar_financeiro_concluida(
                self._nota_id,
                desconto=desc,
                forma_pagamento=self._pagamento_var.get(),
            )
            self._erro_label.configure(text="")
            self._recalcular_totais()
            self._title.configure(text=f"OS #{self._nota_id} — Concluída ✓")
        except Exception as e:
            self._erro_label.configure(text=f"Erro ao salvar: {e}")

    def _concluir(self) -> None:
        if not self._validar():
            return
        ConfirmDialog(self, "Concluir OS", "Confirma o fechamento desta OS?\nO estoque será atualizado automaticamente.",
            on_confirm=self._do_concluir)

    def _do_concluir(self) -> None:
        try:
            self._salvar_rascunho()
            desc = float(self._desconto_entry.get() or "0") if self._desconto_entry.get() else 0
            self.repos.notas.fechar_nota(self._nota_id, forma_pagamento=self._pagamento_var.get(), desconto=desc)
            self._title.configure(text=f"OS #{self._nota_id} — Concluída ✓")
            self._erro_label.configure(text="")
            self._rebuild_buttons()
            # Feedback visual
            self._lbl_total.configure(text_color="#34a853")
        except EstoqueInsuficienteError as e:
            self._erro_label.configure(text=f"⚠️ {e}")
        except Exception as e:
            self._erro_label.configure(text=f"Erro: {e}")

    def _exportar_pdf(self) -> None:
        if not self._nota_id:
            self._erro_label.configure(text="Erro: nota não encontrada para exportação.")
            return

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ModuleNotFoundError:
            self._erro_label.configure(text="Erro: instale o pacote reportlab para exportar PDF.")
            return

        det = self.repos.notas.buscar_por_id(self._nota_id)
        if not det:
            self._erro_label.configure(text="Erro: não foi possível carregar a OS para exportar.")
            return

        nota = det["nota"]
        cliente = self.repos.clientes.buscar_por_id(nota["cliente_id"])
        veiculo = self.repos.veiculos.buscar_por_id(nota["veiculo_id"])
        oficina = self.repos.config.get_dados_oficina()

        def dinheiro(valor: float) -> str:
            return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        default_name = f"OS_{nota['numero']}_{(cliente['nome'] if cliente else 'cliente').replace(' ', '_')}.pdf"
        caminho = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Salvar OS em PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=default_name,
        )
        if not caminho:
            return

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TitleOS",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1a73e8"),
            spaceAfter=8,
        )
        small = ParagraphStyle("SmallOS", parent=styles["BodyText"], fontSize=9, leading=11)

        story = []
        oficina_nome = oficina.get("nome", "Mecânica") or "Mecânica"
        story.append(Paragraph(oficina_nome, title_style))

        oficina_linhas = []
        if oficina.get("cnpj"):
            oficina_linhas.append(f"CNPJ: {oficina['cnpj']}")
        if oficina.get("telefone"):
            oficina_linhas.append(f"Tel: {oficina['telefone']}")
        if oficina.get("endereco"):
            oficina_linhas.append(oficina["endereco"])
        if oficina_linhas:
            story.append(Paragraph("<br/>".join(oficina_linhas), small))
        story.append(Spacer(1, 6 * mm))

        story.append(Paragraph(f"OS #{nota['numero']} - {nota['status']}", styles["Heading2"]))
        story.append(Spacer(1, 2 * mm))

        dados_os = [
            ["Cliente", cliente["nome"] if cliente else "—"],
            ["CPF/CNPJ", cliente["cpf_cnpj"] if cliente and "cpf_cnpj" in cliente.keys() and cliente["cpf_cnpj"] else "—"],
            ["Telefone", cliente["telefone"] if cliente and "telefone" in cliente.keys() and cliente["telefone"] else "—"],
            ["Veículo", f"{veiculo['placa'] or '—'} - {veiculo['modelo']}" if veiculo else "—"],
            ["Km Entrada", str(nota["km_entrada"]) if nota["km_entrada"] else "—"],
            ["Abertura", nota["data_abertura"][:19] if nota["data_abertura"] else "—"],
            ["Conclusão", nota["data_conclusao"][:19] if nota["data_conclusao"] else "—"],
            ["Forma de Pagamento", nota["forma_pagamento"] or "—"],
        ]
        t_os = Table(dados_os, colWidths=[40 * mm, 125 * mm])
        t_os.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d0d0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEADING", (0, 0), (-1, -1), 11),
        ]))
        story.append(t_os)
        story.append(Spacer(1, 6 * mm))

        itens = [["Tipo", "Descrição", "Qtd", "Vlr. Unit.", "Total"]]
        for p in det["pecas"]:
            itens.append([
                "Peça",
                p["descricao"],
                str(p["quantidade"]),
                dinheiro(float(p["valor_unitario"])),
                dinheiro(float(p["valor_total"])),
            ])
        for s in det["servicos"]:
            itens.append([
                "Serviço",
                s["descricao"],
                str(s["quantidade"]),
                dinheiro(float(s["valor_unitario"])),
                dinheiro(float(s["valor_total"])),
            ])

        t_itens = Table(itens, colWidths=[22 * mm, 78 * mm, 18 * mm, 28 * mm, 28 * mm], repeatRows=1)
        t_itens.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d0d0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(t_itens)
        story.append(Spacer(1, 5 * mm))

        resumo = [
            ["Subtotal Peças", dinheiro(float(nota["subtotal_pecas"] or 0))],
            ["Subtotal Serviços", dinheiro(float(nota["subtotal_servicos"] or 0))],
            ["Desconto", dinheiro(float(nota["desconto"] or 0))],
            ["TOTAL", dinheiro(float(nota["valor_total"] or 0))],
        ]
        t_resumo = Table(resumo, colWidths=[50 * mm, 30 * mm], hAlign="RIGHT")
        t_resumo.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -2), colors.whitesmoke),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0fe")),
            ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d0d0")),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ]))
        story.append(t_resumo)
        if nota["observacoes"]:
            story.append(Spacer(1, 5 * mm))
            story.append(Paragraph("Observações", styles["Heading3"]))
            story.append(Paragraph(nota["observacoes"], styles["BodyText"]))

        doc = SimpleDocTemplate(
            caminho,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=15 * mm,
            bottomMargin=15 * mm,
            title=f"OS {nota['numero']}",
            author=oficina_nome,
        )

        def _cabecalho_rodape(canvas, _doc) -> None:
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.grey)
            canvas.drawRightString(195 * mm, 10 * mm, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            canvas.restoreState()

        try:
            doc.build(story, onFirstPage=_cabecalho_rodape, onLaterPages=_cabecalho_rodape)
            try:
                os.startfile(caminho)
            except Exception:
                pass
        except Exception as e:
            self._erro_label.configure(text=f"Erro ao exportar PDF: {e}")

    def _cancelar(self) -> None:
        ConfirmDialog(self, "Cancelar OS", "Tem certeza que deseja cancelar esta OS?\nSe já concluída, o estoque será estornado.",
            on_confirm=self._do_cancelar)

    def _do_cancelar(self) -> None:
        try:
            if self._nota_id:
                self.repos.notas.cancelar_nota(self._nota_id, motivo="Cancelada pelo usuário")
            self._title.configure(text=f"OS #{self._nota_id} — Cancelada")
            self._rebuild_buttons()
        except Exception as e:
            self._erro_label.configure(text=f"Erro: {e}")

    def refresh(self) -> None:
        pass
