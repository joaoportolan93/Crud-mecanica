"""Tela de Estoque — peças com alerta visual, entrada e ajuste."""

import customtkinter as ctk
from components.data_table import DataTable
from components.form_modal import FormModal
from components.cards import ConfirmDialog
from components.layout import DETAIL_PADX, DETAIL_PADY, PAGE_BOTTOM_PADY, PAGE_PADX, PAGE_TOP_PADY, SECTION_GAP
from components.validation import attach_numeric_validation, normalize_numeric_text

PECA_FIELDS = [
    {"key": "descricao", "label": "Descrição", "required": True},
    {"key": "codigo", "label": "Código"},
    {"key": "unidade", "label": "Unidade", "type": "select", "options": ["UN", "PAR", "JG", "LT", "KG", "MT"]},
    {"key": "preco_venda", "label": "Preço Venda (R$)", "required": True, "input_mode": "decimal"},
    {"key": "preco_custo", "label": "Preço Custo (R$)", "input_mode": "decimal"},
    {"key": "quantidade", "label": "Quantidade Inicial", "default": "0", "input_mode": "integer"},
    {"key": "estoque_minimo", "label": "Estoque Mínimo", "default": "0", "input_mode": "integer"},
    {"key": "localizacao", "label": "Localização"},
    {"key": "observacoes", "label": "Observações", "type": "textarea"},
]


class EstoqueView(ctk.CTkFrame):

    def __init__(self, master, repos, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.repos = repos
        self.app = app
        self._search_after = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAGE_PADX, pady=(PAGE_TOP_PADY, SECTION_GAP))
        ctk.CTkLabel(header, text="Estoque de Peças", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="+ Nova Peça", width=130, command=self._nova_peca).pack(side="right")
        ctk.CTkButton(header, text="📦 Entrada", width=130, fg_color=("gray80", "gray30"), text_color=("gray10", "gray90"), hover_color=("gray70", "gray40"),
            command=self._entrada_estoque).pack(side="right", padx=10)

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=PAGE_PADX, pady=(0, SECTION_GAP))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ctk.CTkEntry(filtros, textvariable=self._search_var, placeholder_text="🔍 Buscar por descrição ou código...", width=350).pack(side="left")

        # Alerta de estoque baixo
        self._alerta_frame = ctk.CTkFrame(self, fg_color="transparent", height=0)
        self._alerta_frame.pack(fill="x", padx=PAGE_PADX, pady=(0, 4))

        self.tabela = DataTable(self,
            columns=[
                {"key": "codigo", "label": "Código", "width": 80},
                {"key": "descricao", "label": "Descrição", "width": 250},
                {"key": "unidade", "label": "Un.", "width": 40},
                {"key": "quantidade", "label": "Qtd", "width": 60},
                {"key": "estoque_minimo", "label": "Mín.", "width": 50},
                {"key": "preco_venda", "label": "Preço", "width": 80},
                {"key": "localizacao", "label": "Local", "width": 100},
            ],
            on_row_click=self._abrir_detalhe,
        )
        self.tabela.pack(fill="both", expand=True, padx=PAGE_PADX, pady=(0, PAGE_BOTTOM_PADY))

    def refresh(self) -> None:
        self._carregar()

    def _on_search(self, *_) -> None:
        if self._search_after:
            self.after_cancel(self._search_after)
        self._search_after = self.after(300, self._carregar)

    def _carregar(self) -> None:
        busca = self._search_var.get().strip() or None
        try:
            rows = self.repos.pecas.listar(busca=busca)
            data = []
            for r in rows:
                d = dict(r)
                d["preco_venda"] = f"R$ {r['preco_venda']:.2f}"
                # Marcar visualmente se abaixo do mínimo
                if r["estoque_minimo"] and r["quantidade"] < r["estoque_minimo"]:
                    d["quantidade"] = f"⚠️ {r['quantidade']}"
                data.append(d)
            self.tabela.set_data(data)

            # Alerta global
            for w in self._alerta_frame.winfo_children():
                w.destroy()
            baixos = self.repos.pecas.listar_abaixo_do_minimo()
            if baixos:
                from components.cards import NotificationBanner
                NotificationBanner(
                    self._alerta_frame,
                    f"⚠️ {len(baixos)} peça(s) abaixo do estoque mínimo!",
                    banner_type="warning",
                ).pack(fill="x")
        except Exception as e:
            print(f"Erro ao listar peças: {e}")

    def _nova_peca(self) -> None:
        FormModal(self, "Nova Peça", PECA_FIELDS, self._salvar_peca)

    def _salvar_peca(self, dados: dict) -> None:
        limpo = {}
        for k, v in dados.items():
            if not v:
                continue
            if k in ("preco_venda", "preco_custo", "quantidade", "estoque_minimo"):
                limpo[k] = float(v)
            else:
                limpo[k] = v
        self.repos.pecas.criar(**limpo)
        self._carregar()

    def _entrada_estoque(self) -> None:
        """Modal para entrada de mercadoria."""
        modal = ctk.CTkToplevel(self)
        modal.title("Entrada de Estoque")
        modal.geometry("420x390")
        modal.minsize(420, 390)
        modal.transient(self.winfo_toplevel())
        modal.grab_set()

        modal.grid_rowconfigure(0, weight=1)
        modal.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(modal, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(body, text="Entrada de Estoque", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(16, 12))

        # Buscar peça
        ctk.CTkLabel(body, text="Peça:", anchor="w").pack(fill="x", padx=16)
        from components.autocomplete import AutocompleteEntry
        peca_search = AutocompleteEntry(
            body,
            search_fn=lambda t: [dict(r) for r in self.repos.pecas.listar(busca=t)],
            on_select=lambda p: None,
            display_key="descricao",
            placeholder="Buscar peça...",
        )
        peca_search.pack(fill="x", padx=16, pady=(0, 8))
        self._sel_peca = None
        def on_peca(p):
            self._sel_peca = p
        peca_search._on_select = on_peca

        ctk.CTkLabel(body, text="Quantidade:", anchor="w").pack(fill="x", padx=16)
        qtd_entry = ctk.CTkEntry(body, placeholder_text="Ex: 10")
        attach_numeric_validation(qtd_entry, "integer")
        qtd_entry.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(body, text="Motivo:", anchor="w").pack(fill="x", padx=16)
        motivo_entry = ctk.CTkEntry(body, placeholder_text="Ex: Compra fornecedor")
        motivo_entry.pack(fill="x", padx=16, pady=(0, 12))

        err = ctk.CTkLabel(body, text="", text_color="#ea4335")
        err.pack()

        footer = ctk.CTkFrame(modal, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))

        def confirmar():
            if not self._sel_peca:
                err.configure(text="Selecione uma peça.")
                return
            try:
                qtd = int(normalize_numeric_text(qtd_entry.get(), "integer"))
                self.repos.pecas.entrada_estoque(self._sel_peca["id"], qtd, motivo_entry.get() or None)
                modal.destroy()
                self._carregar()
            except Exception as e:
                err.configure(text=str(e))

        ctk.CTkButton(footer, text="Confirmar Entrada", command=confirmar).pack(pady=10)

    def _abrir_detalhe(self, row: dict) -> None:
        peca = self.repos.pecas.buscar_por_id(row["id"])
        if not peca:
            return
        p = dict(peca)

        detail = ctk.CTkToplevel(self)
        detail.title(f"Peça: {p['descricao']}")
        detail.geometry("500x550")
        detail.transient(self.winfo_toplevel())
        detail.grab_set()

        scroll = ctk.CTkScrollableFrame(detail)
        scroll.pack(fill="both", expand=True, padx=DETAIL_PADX, pady=DETAIL_PADY)

        ctk.CTkLabel(scroll, text=p["descricao"], font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 10))

        for label, val in [("Código", p.get("codigo")), ("Unidade", p.get("unidade")),
            ("Quantidade", p.get("quantidade")), ("Preço Venda", f"R$ {p['preco_venda']:.2f}"),
            ("Preço Custo", f"R$ {p['preco_custo']:.2f}"), ("Estoque Mínimo", p.get("estoque_minimo")),
            ("Localização", p.get("localizacao"))]:
            if val is not None:
                f = ctk.CTkFrame(scroll, fg_color="transparent")
                f.pack(fill="x", pady=1)
                ctk.CTkLabel(f, text=f"{label}:", font=ctk.CTkFont(weight="bold"), width=120, anchor="w").pack(side="left")
                ctk.CTkLabel(f, text=str(val)).pack(side="left")

        btns = ctk.CTkFrame(scroll, fg_color="transparent")
        btns.pack(fill="x", pady=10)
        ctk.CTkButton(btns, text="✏️ Editar", width=100, command=lambda: self._editar_peca(p, detail)).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="🗑️ Excluir", width=100, fg_color="#ea4335", hover_color="#c62828",
            command=lambda: ConfirmDialog(detail, "Excluir", "Tem certeza?",
                on_confirm=lambda: (self.repos.pecas.deletar(p["id"]), detail.destroy(), self._carregar()))).pack(side="left", padx=5)

        # Movimentações
        ctk.CTkLabel(scroll, text="Histórico de Movimentações", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(12, 5))
        movs = self.repos.movimentacoes.listar_por_peca(p["id"])
        for m in movs:
            motivo = m["motivo"] if "motivo" in m.keys() and m["motivo"] else ""
            mf = ctk.CTkFrame(scroll, corner_radius=6)
            mf.pack(fill="x", pady=2)
            tipo_cor = {"ENTRADA": "#34a853", "SAIDA": "#ea4335", "AJUSTE": "#f9ab00"}.get(m["tipo"], "gray")
            ctk.CTkLabel(mf, text=m["tipo"], text_color=tipo_cor, font=ctk.CTkFont(weight="bold"), width=70).pack(side="left", padx=8, pady=6)
            ctk.CTkLabel(mf, text=f"{m['quantidade_anterior']} → {m['quantidade_posterior']}").pack(side="left", padx=5)
            ctk.CTkLabel(mf, text=motivo, text_color="gray50", font=ctk.CTkFont(size=11)).pack(side="right", padx=8)
        if not movs:
            ctk.CTkLabel(scroll, text="Nenhuma movimentação.", text_color="gray50").pack(anchor="w")

    def _editar_peca(self, p: dict, parent) -> None:
        fields_edit = [f for f in PECA_FIELDS if f["key"] != "quantidade"]
        FormModal(parent, "Editar Peça", fields_edit,
            lambda d: (self.repos.pecas.atualizar(p["id"], **{k: (float(v) if k in ("preco_venda", "preco_custo", "estoque_minimo") else v) for k, v in d.items() if v}), parent.destroy(), self._carregar()),
            initial_data=p)
