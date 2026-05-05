"""Tela de Notas de Serviço — lista de OS com filtros."""

import customtkinter as ctk
from components.data_table import DataTable
from components.cards import StatusBadge
from components.layout import PAGE_BOTTOM_PADY, PAGE_PADX, PAGE_TOP_PADY, SECTION_GAP


class NotasServicoView(ctk.CTkFrame):

    def __init__(self, master, repos, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.repos = repos
        self.app = app
        self._search_after = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAGE_PADX, pady=(PAGE_TOP_PADY, SECTION_GAP))
        ctk.CTkLabel(header, text="Notas de Serviço", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="+ Nova OS", width=130, command=lambda: self.app.abrir_nova_nota()).pack(side="right")

        # Filtros
        filtros = ctk.CTkFrame(self, fg_color="transparent")
        filtros.pack(fill="x", padx=PAGE_PADX, pady=(0, SECTION_GAP))

        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ctk.CTkEntry(filtros, textvariable=self._search_var, placeholder_text="🔍 Número, cliente ou placa...", width=280).pack(side="left")

        ctk.CTkLabel(filtros, text="  Status:").pack(side="left", padx=(15, 5))
        self._status_var = ctk.StringVar(value="Todos")
        ctk.CTkSegmentedButton(
            filtros,
            values=["Todos", "Aberta", "Em Andamento", "Concluída", "Cancelada"],
            variable=self._status_var,
            command=lambda _: self._carregar(),
        ).pack(side="left")

        # Tabela
        self.tabela = DataTable(self,
            columns=[
                {"key": "numero", "label": "Nº OS", "width": 70},
                {"key": "data_fmt", "label": "Data", "width": 90},
                {"key": "cliente_nome", "label": "Cliente", "width": 200},
                {"key": "veiculo_info", "label": "Veículo", "width": 180},
                {"key": "status_label", "label": "Status", "width": 110},
                {"key": "valor_fmt", "label": "Valor Total", "width": 100},
            ],
            on_row_click=self._abrir_nota,
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
        status_map = {
            "Todos": None, "Aberta": "ABERTA", "Em Andamento": "EM_ANDAMENTO",
            "Concluída": "CONCLUIDA", "Cancelada": "CANCELADA",
        }
        status = status_map.get(self._status_var.get())

        try:
            rows = self.repos.notas.listar(status=status, busca=busca or None)
            data = []
            for r in rows:
                d = dict(r)
                # Enriquecer com nomes
                cli = self.repos.clientes.buscar_por_id(r["cliente_id"])
                d["cliente_nome"] = cli["nome"] if cli else "—"
                veiculo_id = r["veiculo_id"] if "veiculo_id" in r.keys() and r["veiculo_id"] else None
                veic = self.repos.veiculos.buscar_por_id(veiculo_id) if veiculo_id else None
                d["veiculo_info"] = f"{veic['placa'] or ''} {veic['modelo']}" if veic else "—"
                d["data_fmt"] = r["data_abertura"][:10] if r["data_abertura"] else ""
                d["valor_fmt"] = f"R$ {r['valor_total']:.2f}"
                status_labels = {"ABERTA": "🔵 Aberta", "EM_ANDAMENTO": "🟡 Em Andamento", "CONCLUIDA": "🟢 Concluída", "CANCELADA": "🔴 Cancelada"}
                d["status_label"] = status_labels.get(r["status"], r["status"])
                data.append(d)
            self.tabela.set_data(data)
        except Exception as e:
            print(f"Erro: {e}")

    def _abrir_nota(self, row: dict) -> None:
        """Abre a nota selecionada no modo de edição/visualização."""
        self.app.abrir_nova_nota(nota_id=row["id"])
