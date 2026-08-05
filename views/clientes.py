"""Tela de Clientes — lista, busca, CRUD e detalhe com veículos/OS."""

import customtkinter as ctk
from components.data_table import DataTable
from components.form_modal import FormModal
from components.cards import ConfirmDialog
from components.layout import DETAIL_PADX, DETAIL_PADY, PAGE_BOTTOM_PADY, PAGE_PADX, PAGE_TOP_PADY, SECTION_GAP
from components.validation import attach_numeric_validation


CLIENTE_FIELDS = [
    {"key": "nome", "label": "Nome", "required": True},
    {"key": "tipo", "label": "Tipo", "type": "select", "options": ["PF", "PJ"]},
    {"key": "cpf_cnpj", "label": "CPF / CNPJ", "input_mode": "digits"},
    {"key": "telefone", "label": "Telefone", "input_mode": "digits"},
    {"key": "telefone2", "label": "Telefone 2", "input_mode": "digits"},
    {"key": "email", "label": "E-mail"},
    {"key": "endereco", "label": "Endereço"},
    {"key": "cidade", "label": "Cidade"},
    {"key": "observacoes", "label": "Observações", "type": "textarea"},
]


class ClientesView(ctk.CTkFrame):

    def __init__(self, master, repos, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.repos = repos
        self.app = app
        self._search_after: str | None = None

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAGE_PADX, pady=(PAGE_TOP_PADY, SECTION_GAP))

        ctk.CTkLabel(
            header, text="Clientes",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Novo Cliente", width=150,
            command=self._abrir_novo,
        ).pack(side="right")

        # Filtros
        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=PAGE_PADX, pady=(0, SECTION_GAP))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ctk.CTkEntry(
            filtros, textvariable=self._search_var,
            placeholder_text="🔍 Buscar por nome...",
            width=300,
        ).pack(side="left")

        self._tipo_var = ctk.StringVar(value="Todos")
        ctk.CTkSegmentedButton(
            filtros, values=["Todos", "PF", "PJ"],
            variable=self._tipo_var,
            command=lambda _: self._carregar(),
        ).pack(side="left", padx=SECTION_GAP)

        # Tabela
        self.tabela = DataTable(
            self,
            columns=[
                {"key": "nome", "label": "Nome", "width": 250},
                {"key": "tipo", "label": "Tipo", "width": 60},
                {"key": "cpf_cnpj", "label": "CPF/CNPJ", "width": 150},
                {"key": "telefone", "label": "Telefone", "width": 130},
                {"key": "cidade", "label": "Cidade", "width": 120},
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
        tipo = self._tipo_var.get()
        tipo_filtro = tipo if tipo != "Todos" else None

        try:
            rows = self.repos.clientes.listar(busca=busca, tipo=tipo_filtro)
            data = [dict(r) for r in rows]
            self.tabela.set_data(data)
        except Exception as e:
            print(f"Erro ao listar clientes: {e}")

    def _abrir_novo(self) -> None:
        modal = ctk.CTkToplevel(self)
        modal.title("Novo Cliente")
        modal.geometry("500x620")
        modal.minsize(500, 620)
        modal.transient(self.winfo_toplevel())
        modal.grab_set()

        scroll = ctk.CTkScrollableFrame(modal)
        scroll.pack(fill="both", expand=True, padx=16, pady=(16, 10))

        ctk.CTkLabel(scroll, text="Novo Cliente", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 10))

        cliente_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        cliente_frame.pack(fill="x")

        cliente_widgets: dict[str, object] = {}
        for field in CLIENTE_FIELDS:
            key = field["key"]
            label_text = field["label"] + (" *" if field.get("required") else "")
            ctk.CTkLabel(cliente_frame, text=label_text, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", pady=(8, 2))

            field_type = field.get("type", "text")
            if field_type == "select":
                options = field.get("options", [""])
                var = ctk.StringVar(value=options[0])
                widget = ctk.CTkOptionMenu(cliente_frame, variable=var, values=options)
                widget.pack(fill="x")
                cliente_widgets[key] = var
            elif field_type == "textarea":
                widget = ctk.CTkTextbox(cliente_frame, height=80)
                widget.pack(fill="x")
                cliente_widgets[key] = widget
            else:
                widget = ctk.CTkEntry(cliente_frame, placeholder_text=field.get("placeholder", ""))
                if field.get("input_mode"):
                    attach_numeric_validation(widget, field["input_mode"])
                widget.pack(fill="x")
                cliente_widgets[key] = widget

        vehicle_enabled = ctk.BooleanVar(value=True)
        ctk.CTkLabel(scroll, text="Veículo inicial (opcional)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(16, 4))
        ctk.CTkCheckBox(scroll, text="Cadastrar veículo junto com o cliente", variable=vehicle_enabled).pack(anchor="w", pady=(0, 8))

        vehicle_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        vehicle_frame.pack(fill="x")

        vehicle_widgets: dict[str, object] = {}
        veiculo_fields = [
            {"key": "modelo", "label": "Modelo", "required": True},
            {"key": "placa", "label": "Placa"},
            {"key": "ano_modelo", "label": "Ano Modelo", "input_mode": "integer"},
            {"key": "km_atual", "label": "Km Atual", "default": "0", "input_mode": "integer"},
        ]

        for field in veiculo_fields:
            key = field["key"]
            label_text = field["label"] + (" *" if field.get("required") else "")
            ctk.CTkLabel(vehicle_frame, text=label_text, font=ctk.CTkFont(size=13, weight="bold"), anchor="w").pack(fill="x", pady=(8, 2))

            field_type = field.get("type", "text")
            default = field.get("default", "")
            if field_type == "textarea":
                widget = ctk.CTkTextbox(vehicle_frame, height=80)
                widget.pack(fill="x")
                vehicle_widgets[key] = widget
            else:
                widget = ctk.CTkEntry(vehicle_frame, placeholder_text=field.get("placeholder", ""))
                if field.get("input_mode"):
                    attach_numeric_validation(widget, field["input_mode"])
                widget.pack(fill="x")
                if default:
                    widget.insert(0, str(default))
                vehicle_widgets[key] = widget

        def set_vehicle_state() -> None:
            if vehicle_enabled.get():
                vehicle_frame.pack(fill="x")
            else:
                vehicle_frame.pack_forget()

        def get_value(widget):
            if isinstance(widget, ctk.StringVar):
                return widget.get().strip()
            if isinstance(widget, ctk.CTkTextbox):
                return widget.get("1.0", "end-1c").strip()
            return widget.get().strip()

        def salvar() -> None:
            dados_cliente = {k: get_value(w) for k, w in cliente_widgets.items()}
            if not dados_cliente.get("nome"):
                return
            if not dados_cliente.get("tipo"):
                dados_cliente["tipo"] = "PF"

            if vehicle_enabled.get() and not get_value(vehicle_widgets["modelo"]):
                erro.configure(text="Informe o modelo do veículo ou desmarque a opção de cadastrar veículo.")
                return

            try:
                cliente_id = self.repos.clientes.criar(**{k: v for k, v in dados_cliente.items() if v})
            except Exception as e:
                erro.configure(text=str(e))
                return

            if vehicle_enabled.get():
                try:
                    veiculo_data = {k: get_value(w) for k, w in vehicle_widgets.items()}
                    veiculo_limpo = {k: v for k, v in veiculo_data.items() if v}
                    if "ano_fabricacao" in veiculo_limpo:
                        veiculo_limpo["ano_fabricacao"] = int(veiculo_limpo["ano_fabricacao"])
                    if "ano_modelo" in veiculo_limpo:
                        veiculo_limpo["ano_modelo"] = int(veiculo_limpo["ano_modelo"])
                    if "km_atual" in veiculo_limpo:
                        veiculo_limpo["km_atual"] = int(veiculo_limpo["km_atual"])
                    self.repos.veiculos.criar(cliente_id=cliente_id, **veiculo_limpo)
                except Exception as e:
                    erro.configure(text=f"Cliente salvo. O veículo não foi criado: {e}")
                    self._carregar()
                    modal.destroy()
                    return

            modal.destroy()
            self._carregar()

        vehicle_enabled.trace_add("write", lambda *_: set_vehicle_state())
        set_vehicle_state()

        erro = ctk.CTkLabel(scroll, text="", text_color="#ea4335")
        erro.pack(pady=(10, 0), anchor="w")

        btns = ctk.CTkFrame(modal, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(btns, text="Cancelar", width=110, fg_color="gray50", hover_color="gray40", command=modal.destroy).pack(side="right", padx=(10, 0))
        ctk.CTkButton(btns, text="Salvar", width=110, command=salvar).pack(side="right")

    def _salvar_novo(self, dados: dict) -> None:
        dados = {k: v for k, v in dados.items() if v}
        self.repos.clientes.criar(**dados)
        self._carregar()

    def _abrir_detalhe(self, row: dict) -> None:
        """Abre painel lateral com detalhes do cliente."""
        detail = ctk.CTkToplevel(self)
        detail.title(f"Cliente: {row['nome']}")
        detail.geometry("550x650")
        detail.transient(self.winfo_toplevel())
        detail.grab_set()

        scroll = ctk.CTkScrollableFrame(detail)
        scroll.pack(fill="both", expand=True, padx=DETAIL_PADX, pady=DETAIL_PADY)

        # Dados do cliente
        ctk.CTkLabel(
            scroll, text=row["nome"],
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", pady=(0, 5))

        info_items = [
            ("Tipo", row.get("tipo")),
            ("CPF/CNPJ", row.get("cpf_cnpj")),
            ("Telefone", row.get("telefone")),
            ("Telefone 2", row.get("telefone2")),
            ("E-mail", row.get("email")),
            ("Endereço", row.get("endereco")),
            ("Cidade", row.get("cidade")),
        ]
        for label, valor in info_items:
            if valor:
                f = ctk.CTkFrame(scroll, fg_color="transparent")
                f.pack(fill="x", pady=1)
                ctk.CTkLabel(f, text=f"{label}:", font=ctk.CTkFont(weight="bold"), width=100, anchor="w").pack(side="left")
                ctk.CTkLabel(f, text=str(valor), anchor="w").pack(side="left")

        # Botões
        btns = ctk.CTkFrame(scroll, fg_color="transparent")
        btns.pack(fill="x", pady=DETAIL_PADY)
        ctk.CTkButton(
            btns, text="✏️ Editar", width=120,
            command=lambda: self._editar_cliente(row, detail),
        ).pack(side="left", padx=(0, 5))
        ctk.CTkButton(
            btns, text="🚗 Novo Veículo", width=130,
            fg_color=("gray80", "gray30"), text_color=("gray10", "gray90"), hover_color=("gray70", "gray40"),
            command=lambda: self._novo_veiculo(row["id"]),
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btns, text="📋 Nova OS", width=120,
            fg_color=("gray80", "gray30"), text_color=("gray10", "gray90"), hover_color=("gray70", "gray40"),
            command=lambda: (detail.destroy(), self.app.abrir_nova_nota(cliente_id=row["id"])),
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            btns, text="🗑️ Excluir", width=100,
            fg_color="#ea4335", hover_color="#c62828",
            command=lambda: self._confirmar_exclusao(row["id"], detail),
        ).pack(side="left", padx=5)

        # Veículos
        ctk.CTkLabel(scroll, text="Veículos", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(10, 5))
        try:
            veics = self.repos.veiculos.listar_por_cliente(row["id"])
            if not veics:
                ctk.CTkLabel(scroll, text="Nenhum veículo.", text_color="gray50").pack(anchor="w")
            for v in veics:
                vf = ctk.CTkFrame(scroll, corner_radius=6)
                vf.pack(fill="x", pady=2)
                ctk.CTkLabel(vf, text=f"{v['placa'] or '—'}", font=ctk.CTkFont(weight="bold"), width=100).pack(side="left", padx=8, pady=6)
                ctk.CTkLabel(vf, text=f"{v['marca'] or ''} {v['modelo']}").pack(side="left", padx=5)
                ctk.CTkLabel(vf, text=f"{v['ano_modelo'] or ''}", text_color="gray50").pack(side="left", padx=5)
        except Exception:
            pass

        # Histórico de OS
        ctk.CTkLabel(scroll, text="Histórico de OS", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(15, 5))
        try:
            notas = self.repos.notas.listar(cliente_id=row["id"], limit=20)
            if not notas:
                ctk.CTkLabel(scroll, text="Nenhuma OS.", text_color="gray50").pack(anchor="w")
            for n in notas:
                nf = ctk.CTkFrame(scroll, corner_radius=6)
                nf.pack(fill="x", pady=2)
                ctk.CTkLabel(nf, text=f"#{n['numero']}", font=ctk.CTkFont(weight="bold"), width=60).pack(side="left", padx=8, pady=6)
                ctk.CTkLabel(nf, text=n["data_abertura"][:10] if n["data_abertura"] else "").pack(side="left", padx=5)
                ctk.CTkLabel(nf, text=f"R$ {n['valor_total']:.2f}").pack(side="left", padx=15)
                from components.cards import StatusBadge
                StatusBadge(nf, n["status"]).pack(side="left", padx=15, pady=4)
        except Exception:
            pass

    def _editar_cliente(self, row: dict, parent_window) -> None:
        FormModal(
            parent_window, "Editar Cliente", CLIENTE_FIELDS,
            lambda dados: (
                self.repos.clientes.atualizar(row["id"], **{k: v for k, v in dados.items() if v}),
                parent_window.destroy(),
                self._carregar(),
            ),
            initial_data=dict(row),
        )

    def _novo_veiculo(self, cliente_id: int) -> None:
        from views.veiculos import VEICULO_FIELDS
        FormModal(
            self, "Novo Veículo", VEICULO_FIELDS,
            lambda d: (
                self.repos.veiculos.criar(cliente_id=cliente_id, **{k: v for k, v in d.items() if v}),
                self._carregar(),
            ),
        )

    def _confirmar_exclusao(self, id: int, parent) -> None:
        ConfirmDialog(
            parent, "Excluir Cliente",
            "Tem certeza que deseja excluir este cliente?",
            on_confirm=lambda: (
                self.repos.clientes.deletar(id),
                parent.destroy(),
                self._carregar(),
            ),
        )
