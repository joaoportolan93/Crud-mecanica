"""Sidebar de navegação lateral com ícones e highlight do item ativo."""

import customtkinter as ctk

from components.layout import SIDEBAR_WIDTH


class Sidebar(ctk.CTkFrame):
    """Barra lateral de navegação com itens de menu."""

    MENU_ITEMS = [
        ("dashboard",    "📊", "Dashboard"),
        ("clientes",     "👥", "Clientes"),
        ("veiculos",     "🚗", "Veículos"),
        ("estoque",      "📦", "Estoque"),
        ("servicos",     "🔧", "Serviços"),
        ("notas",        "📋", "Notas de Serviço"),
        ("configuracoes","⚙️", "Configurações"),
    ]

    def __init__(self, master, app) -> None:
        super().__init__(master, width=SIDEBAR_WIDTH, corner_radius=0)
        self.app = app
        self.buttons: dict[str, ctk.CTkButton] = {}

        # Impedir que o frame encolha
        self.pack_propagate(False)

        # Logo / Título
        ctk.CTkLabel(
            self, text="🔧 Mecânica",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(20, 4), padx=16)

        ctk.CTkLabel(
            self, text="Sistema de Gestão",
            font=ctk.CTkFont(size=12),
            text_color="gray50",
        ).pack(pady=(0, 18), padx=16)

        # Separador
        ctk.CTkFrame(self, height=1, fg_color="gray40").pack(
            fill="x", padx=12, pady=(0, 8)
        )

        # Itens de menu
        for key, icon, label in self.MENU_ITEMS:
            btn = ctk.CTkButton(
                self,
                text=f"  {icon}  {label}",
                anchor="w",
                height=40,
                corner_radius=8,
                command=lambda k=key: self._navigate(k),
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray28"),
                font=ctk.CTkFont(size=14),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self.buttons[key] = btn

        # Espaçador + versão no rodapé
        ctk.CTkLabel(self, text="").pack(expand=True)
        from updater import APP_VERSION
        ctk.CTkLabel(
            self, text=f"v{APP_VERSION.lstrip('v')}",
            text_color="gray50",
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 15))

        self._set_active("dashboard")

    def _navigate(self, key: str) -> None:
        self._set_active(key)
        self.app.show_view(key)

    def _set_active(self, key: str) -> None:
        """Destaca visualmente o item ativo na sidebar."""
        for k, btn in self.buttons.items():
            if k == key:
                btn.configure(
                    fg_color=("gray75", "gray25"),
                    text_color=("gray10", "gray90"),
                )
            else:
                btn.configure(fg_color="transparent")
