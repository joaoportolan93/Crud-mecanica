"""Tela de Serviços — CRUD do catálogo."""

import customtkinter as ctk
from components.data_table import DataTable
from components.form_modal import FormModal
from components.cards import ConfirmDialog
from components.layout import PAGE_BOTTOM_PADY, PAGE_PADX, PAGE_TOP_PADY, SECTION_GAP

SERVICO_FIELDS = [
    {"key": "descricao", "label": "Descrição", "required": True},
    {"key": "preco_padrao", "label": "Preço Padrão (R$)", "required": True, "input_mode": "decimal"},
    {"key": "observacoes", "label": "Observações", "type": "textarea"},
]


class ServicosView(ctk.CTkFrame):

    def __init__(self, master, repos, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.repos = repos
        self._search_after = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAGE_PADX, pady=(PAGE_TOP_PADY, SECTION_GAP))
        ctk.CTkLabel(header, text="Catálogo de Serviços", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="+ Novo Serviço", width=150, command=self._novo).pack(side="right")

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=PAGE_PADX, pady=(0, SECTION_GAP))
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ctk.CTkEntry(filtros, textvariable=self._search_var, placeholder_text="🔍 Buscar serviço...", width=300).pack(side="left")

        self.tabela = DataTable(self,
            columns=[
                {"key": "descricao", "label": "Descrição", "width": 400},
                {"key": "preco_fmt", "label": "Preço Padrão", "width": 120},
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
            rows = self.repos.servicos.listar(busca=busca)
            data = [dict(r) | {"preco_fmt": f"R$ {r['preco_padrao']:.2f}"} for r in rows]
            self.tabela.set_data(data)
        except Exception as e:
            print(f"Erro: {e}")

    def _novo(self) -> None:
        FormModal(self, "Novo Serviço", SERVICO_FIELDS, self._salvar)

    def _salvar(self, d: dict) -> None:
        self.repos.servicos.criar(descricao=d["descricao"], preco_padrao=float(d["preco_padrao"]), observacoes=d.get("observacoes"))
        self._carregar()

    def _abrir_detalhe(self, row: dict) -> None:
        detail = ctk.CTkToplevel(self)
        detail.title(f"Serviço: {row['descricao']}")
        detail.geometry("450x300")
        detail.transient(self.winfo_toplevel())
        detail.grab_set()

        ctk.CTkLabel(detail, text=row["descricao"], font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(16, 4), padx=16)
        ctk.CTkLabel(detail, text=f"Preço Padrão: {row['preco_fmt']}", font=ctk.CTkFont(size=14)).pack(padx=16)
        if row.get("observacoes"):
            ctk.CTkLabel(detail, text=row["observacoes"], text_color="gray50", wraplength=400).pack(padx=16, pady=8)

        btns = ctk.CTkFrame(detail, fg_color="transparent")
        btns.pack(pady=16)
        ctk.CTkButton(btns, text="✏️ Editar", width=100, command=lambda: FormModal(
            detail, "Editar Serviço", SERVICO_FIELDS,
            lambda d: (self.repos.servicos.atualizar(row["id"], descricao=d["descricao"], preco_padrao=float(d["preco_padrao"]), observacoes=d.get("observacoes")), detail.destroy(), self._carregar()),
            initial_data=dict(row))).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="🗑️ Excluir", width=100, fg_color="#ea4335", hover_color="#c62828",
            command=lambda: ConfirmDialog(detail, "Excluir", "Tem certeza?",
                on_confirm=lambda: (self.repos.servicos.deletar(row["id"]), detail.destroy(), self._carregar()))).pack(side="left", padx=5)
