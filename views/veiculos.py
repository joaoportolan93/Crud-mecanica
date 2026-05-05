"""Tela de Veículos — lista, busca por placa/modelo, CRUD."""

import customtkinter as ctk
from components.data_table import DataTable
from components.form_modal import FormModal
from components.cards import ConfirmDialog
from components.layout import DETAIL_PADX, DETAIL_PADY, PAGE_BOTTOM_PADY, PAGE_PADX, PAGE_TOP_PADY, SECTION_GAP

VEICULO_FIELDS = [
    {"key": "modelo", "label": "Modelo", "required": True},
    {"key": "marca", "label": "Marca"},
    {"key": "placa", "label": "Placa"},
    {"key": "ano_fabricacao", "label": "Ano Fabricação", "input_mode": "integer"},
    {"key": "ano_modelo", "label": "Ano Modelo", "input_mode": "integer"},
    {"key": "cor", "label": "Cor"},
    {"key": "chassi", "label": "Chassi"},
    {"key": "km_atual", "label": "Km Atual", "default": "0", "input_mode": "integer"},
    {"key": "observacoes", "label": "Observações", "type": "textarea"},
]


class VeiculosView(ctk.CTkFrame):

    def __init__(self, master, repos, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.repos = repos
        self.app = app
        self._search_after = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAGE_PADX, pady=(PAGE_TOP_PADY, SECTION_GAP))
        ctk.CTkLabel(header, text="Veículos", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")

        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=PAGE_PADX, pady=(0, SECTION_GAP))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ctk.CTkEntry(
            filtros, textvariable=self._search_var,
            placeholder_text="🔍 Buscar por placa ou modelo...", width=350,
        ).pack(side="left")

        self.tabela = DataTable(
            self,
            columns=[
                {"key": "placa", "label": "Placa", "width": 100},
                {"key": "marca", "label": "Marca", "width": 100},
                {"key": "modelo", "label": "Modelo", "width": 180},
                {"key": "ano_modelo", "label": "Ano", "width": 60},
                {"key": "cor", "label": "Cor", "width": 80},
                {"key": "km_atual", "label": "Km", "width": 80},
                {"key": "cliente_nome", "label": "Cliente", "width": 200},
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
        busca = self._search_var.get().strip()
        try:
            if busca:
                # Tenta por placa primeiro, depois por modelo
                por_placa = self.repos.veiculos.buscar_por_placa(busca)
                if por_placa:
                    rows = [por_placa]
                else:
                    rows = self.repos.veiculos.buscar_por_modelo(busca)
            else:
                # Listar todos (buscando via SQL direto já que não tem listar_todos)
                rows = self.repos.veiculos.buscar_por_modelo("")

            data = []
            for r in rows:
                d = dict(r)
                cli = self.repos.clientes.buscar_por_id(r["cliente_id"])
                d["cliente_nome"] = cli["nome"] if cli else "—"
                data.append(d)
            self.tabela.set_data(data)
        except Exception as e:
            print(f"Erro ao listar veículos: {e}")

    def _abrir_detalhe(self, row: dict) -> None:
        detail = ctk.CTkToplevel(self)
        detail.title(f"Veículo: {row.get('placa', '')} - {row['modelo']}")
        detail.geometry("500x500")
        detail.transient(self.winfo_toplevel())
        detail.grab_set()

        scroll = ctk.CTkScrollableFrame(detail)
        scroll.pack(fill="both", expand=True, padx=DETAIL_PADX, pady=DETAIL_PADY)

        ctk.CTkLabel(
            scroll, text=f"{row.get('marca', '')} {row['modelo']}",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", pady=(0, 10))

        infos = [
            ("Placa", row.get("placa")), ("Ano", row.get("ano_modelo")),
            ("Cor", row.get("cor")), ("Chassi", row.get("chassi")),
            ("Km Atual", row.get("km_atual")), ("Cliente", row.get("cliente_nome")),
        ]
        for label, valor in infos:
            if valor:
                f = ctk.CTkFrame(scroll, fg_color="transparent")
                f.pack(fill="x", pady=1)
                ctk.CTkLabel(f, text=f"{label}:", font=ctk.CTkFont(weight="bold"), width=100, anchor="w").pack(side="left")
                ctk.CTkLabel(f, text=str(valor)).pack(side="left")

        btns = ctk.CTkFrame(scroll, fg_color="transparent")
        btns.pack(fill="x", pady=DETAIL_PADY)
        ctk.CTkButton(btns, text="✏️ Editar", width=120, command=lambda: self._editar(row, detail)).pack(side="left", padx=5)
        ctk.CTkButton(btns, text="🗑️ Excluir", width=100, fg_color="#ea4335", hover_color="#c62828",
            command=lambda: ConfirmDialog(detail, "Excluir Veículo", "Tem certeza?",
                on_confirm=lambda: (self.repos.veiculos.deletar(row["id"]), detail.destroy(), self._carregar())),
        ).pack(side="right")

        # Histórico OS
        ctk.CTkLabel(scroll, text="Histórico de OS", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(10, 5))
        try:
            notas = self.repos.notas.listar(veiculo_id=row["id"], limit=15)
            for n in notas:
                nf = ctk.CTkFrame(scroll, corner_radius=6)
                nf.pack(fill="x", pady=2)
                ctk.CTkLabel(nf, text=f"#{n['numero']}", font=ctk.CTkFont(weight="bold"), width=60).pack(side="left", padx=8, pady=6)
                ctk.CTkLabel(nf, text=f"R$ {n['valor_total']:.2f}").pack(side="left", padx=5)
                from components.cards import StatusBadge
                StatusBadge(nf, n["status"]).pack(side="right", padx=8, pady=4)
            if not notas:
                ctk.CTkLabel(scroll, text="Nenhuma OS.", text_color="gray50").pack(anchor="w")
        except Exception:
            pass

    def _editar(self, row: dict, parent) -> None:
        FormModal(parent, "Editar Veículo", VEICULO_FIELDS,
            lambda d: (self.repos.veiculos.atualizar(row["id"], **{k: v for k, v in d.items() if v and k != "cliente_id"}), parent.destroy(), self._carregar()),
            initial_data=dict(row))
