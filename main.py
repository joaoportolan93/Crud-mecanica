"""
Ponto de entrada do Sistema de Gestão de Mecânica.

Inicializa banco, aplica migrations, abre janela CustomTkinter
e verifica atualizações em background.
"""

import sys
import os
import logging
import threading
import webbrowser

import customtkinter as ctk

sys.path.insert(0, os.path.dirname(__file__))

from database import Database
from app_context import Repos
from updater import verificar_atualizacao, APP_VERSION
from components.sidebar import Sidebar
from views import (
    DashboardView, ClientesView, VeiculosView, EstoqueView,
    ServicosView, NotasServicoView, NovaNotaView, ConfiguracoesView,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Tema: segue o SO (dark/light)
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """Janela principal do sistema."""

    def __init__(self, db: Database) -> None:
        super().__init__()
        self.title(f"Gestão de Mecânica — {APP_VERSION}")
        self.geometry("1100x700")
        self.minsize(900, 550)

        self.repos = Repos.from_database(db)
        self._db = db
        self._current_view = "dashboard"

        # Layout: sidebar + conteúdo
        self.sidebar = Sidebar(self, self)
        self.sidebar.pack(side="left", fill="y")

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.pack(side="right", fill="both", expand=True)

        # Criar todas as views (place para empilhar e usar tkraise)
        self.views: dict[str, ctk.CTkFrame] = {}
        view_classes = {
            "dashboard": DashboardView,
            "clientes": ClientesView,
            "veiculos": VeiculosView,
            "estoque": EstoqueView,
            "servicos": ServicosView,
            "notas": NotasServicoView,
            "configuracoes": ConfiguracoesView,
        }
        for key, cls in view_classes.items():
            view = cls(self.content, self.repos, self)
            view.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.views[key] = view

        # View de Nova Nota (separada, empilhada junto)
        self.nova_nota_view = NovaNotaView(self.content, self.repos, self)
        self.nova_nota_view.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Mostrar dashboard
        self.show_view("dashboard")

        # Verificar atualização em background
        threading.Thread(target=self._check_update, daemon=True).start()

        # Fechar conexão ao sair
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def show_view(self, name: str) -> None:
        """Troca para a view especificada."""
        if name not in self.views:
            return
        self._current_view = name
        view = self.views[name]
        view.tkraise()
        view.refresh()
        self.sidebar._set_active(name)

    def abrir_nova_nota(self, nota_id: int | None = None, cliente_id: int | None = None) -> None:
        """Abre a tela de Nova/Editar OS."""
        self.nova_nota_view.tkraise()
        self.nova_nota_view.carregar_nota(nota_id=nota_id, cliente_id=cliente_id)

    def _check_update(self) -> None:
        resultado = verificar_atualizacao()
        if resultado["tem_atualizacao"]:
            self.after(0, lambda: self._mostrar_update(resultado))

    def _mostrar_update(self, resultado: dict) -> None:
        dashboard = self.views.get("dashboard")
        if dashboard and hasattr(dashboard, "mostrar_banner"):
            dashboard.mostrar_banner(
                f"Nova versão disponível: {resultado['versao_nova']}",
                action_text="Ver atualização",
                action_cb=lambda: webbrowser.open(resultado["url_download"]),
            )

    def _on_close(self) -> None:
        self._db.close()
        logger.info("Aplicação encerrada.")
        self.destroy()


def main() -> None:
    logger.info("Iniciando aplicação...")
    try:
        db = Database()
        db.initialize()
        logger.info("Banco de dados pronto.")
    except Exception as e:
        logger.critical(f"Falha ao inicializar banco: {e}")
        sys.exit(1)

    app = App(db)
    app.mainloop()


if __name__ == "__main__":
    main()
