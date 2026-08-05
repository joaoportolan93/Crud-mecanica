"""Dashboard — tela inicial com métricas e atalhos rápidos."""

import customtkinter as ctk
from components.cards import MetricCard, NotificationBanner
from components.layout import PAGE_BOTTOM_PADY, PAGE_PADX, PAGE_TOP_PADY, SECTION_GAP


class DashboardView(ctk.CTkFrame):

    def __init__(self, master, repos, app) -> None:
        super().__init__(master, fg_color="transparent")
        self.repos = repos
        self.app = app

        # Banner de notificação (preenchido pelo app se houver update)
        self._banner_frame = ctk.CTkFrame(self, fg_color="transparent", height=0)
        self._banner_frame.pack(fill="x")

        # Cabeçalho do Dashboard com botão de alternar tema
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAGE_PADX, pady=(PAGE_TOP_PADY, SECTION_GAP))
        header.grid_columnconfigure(0, weight=1)

        titles = ctk.CTkFrame(header, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            titles, text="Dashboard",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles, text="Visão geral da oficina",
            font=ctk.CTkFont(size=13), text_color="gray50",
        ).pack(anchor="w", pady=(2, 0))

        self._btn_theme = ctk.CTkButton(
            header,
            text="☀️ Modo Claro",
            width=135,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("gray80", "gray25"),
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray35"),
            command=self._toggle_theme,
        )
        self._btn_theme.grid(row=0, column=1, sticky="e")
        self._atualizar_botao_tema()

        # Cards de métricas
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.pack(fill="x", padx=PAGE_PADX, pady=(0, SECTION_GAP + 4))
        cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_os = MetricCard(
            cards_frame, title="OS Abertas", icon="📋",
            accent_color="#1565c0",
        )
        self.card_os.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.card_estoque = MetricCard(
            cards_frame, title="Estoque Baixo", icon="⚠️",
            accent_color="#e65100",
        )
        self.card_estoque.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.card_clientes = MetricCard(
            cards_frame, title="Clientes", icon="👥",
            accent_color="#2e7d32",
        )
        self.card_clientes.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

        self.card_ultima = MetricCard(
            cards_frame, title="Última OS", icon="🔧",
            accent_color="#6a1b9a",
        )
        self.card_ultima.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")

        # Atalhos rápidos
        ctk.CTkLabel(
            self, text="Atalhos Rápidos",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=PAGE_PADX, pady=(SECTION_GAP, 6))

        atalhos = ctk.CTkFrame(self, fg_color="transparent")
        atalhos.pack(fill="x", padx=PAGE_PADX)

        ctk.CTkButton(
            atalhos, text="📋  Nova OS", height=45, width=200,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda: self.app.abrir_nova_nota(),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            atalhos, text="📦  Entrada de Peça", height=45, width=200,
            font=ctk.CTkFont(size=14),
            fg_color=("gray80", "gray30"),
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray40"),
            command=lambda: self.app.show_view("estoque"),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            atalhos, text="👤  Novo Cliente", height=45, width=200,
            font=ctk.CTkFont(size=14),
            fg_color=("gray80", "gray30"),
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray40"),
            command=lambda: self.app.show_view("clientes"),
        ).pack(side="left")

        # Últimas OS
        ctk.CTkLabel(
            self, text="Últimas Notas de Serviço",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=PAGE_PADX, pady=(18, 8))

        self._ultimas_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", height=200,
        )
        self._ultimas_frame.pack(fill="both", expand=True, padx=PAGE_PADX, pady=(0, PAGE_BOTTOM_PADY))

    def mostrar_banner(self, message: str, action_text: str = None, action_cb=None) -> None:
        """Exibe banner de notificação no topo do dashboard."""
        for w in self._banner_frame.winfo_children():
            w.destroy()
        NotificationBanner(
            self._banner_frame, message,
            action_text=action_text, action_callback=action_cb,
        ).pack(fill="x")

    def refresh(self) -> None:
        """Atualiza todas as métricas do dashboard."""
        try:
            # OS abertas
            abertas = self.repos.notas.listar(status="ABERTA")
            em_andamento = self.repos.notas.listar(status="EM_ANDAMENTO")
            self.card_os.set_value(len(abertas) + len(em_andamento))

            # Estoque baixo
            baixo = self.repos.pecas.listar_abaixo_do_minimo()
            self.card_estoque.set_value(len(baixo))
            if len(baixo) > 0:
                self.card_estoque._value_label.configure(text_color="#ea4335")
            else:
                self.card_estoque._value_label.configure(text_color="#e65100")

            # Clientes
            clientes = self.repos.clientes.listar()
            self.card_clientes.set_value(len(clientes))

            # Última OS
            ultimas = self.repos.notas.listar(limit=5)
            if ultimas:
                u = ultimas[0]
                cliente = self.repos.clientes.buscar_por_id(u["cliente_id"])
                nome = cliente["nome"] if cliente else "—"
                self.card_ultima.set_value(f"#{u['numero']}")
            else:
                self.card_ultima.set_value("—")

            # Lista de últimas OS
            for w in self._ultimas_frame.winfo_children():
                w.destroy()

            if not ultimas:
                ctk.CTkLabel(
                    self._ultimas_frame, text="Nenhuma OS registrada.",
                    text_color="gray50",
                ).pack(pady=20)
                return

            for nota in ultimas:
                cli = self.repos.clientes.buscar_por_id(nota["cliente_id"])
                nome_cli = cli["nome"] if cli else "—"
                row = ctk.CTkFrame(self._ultimas_frame, fg_color=("white", "gray18"), corner_radius=6)
                row.pack(fill="x", pady=2, padx=2)
                row.configure(cursor="hand2")

                def abrir_nota(_event=None, nota_id=nota["id"]):
                    self.app.abrir_nova_nota(nota_id=nota_id)

                row.bind("<Button-1>", abrir_nota)

                ctk.CTkLabel(
                    row, text=f"OS #{nota['numero']}",
                    font=ctk.CTkFont(size=13, weight="bold"), width=80,
                ).pack(side="left", padx=10, pady=8)
                ctk.CTkLabel(
                    row, text=nome_cli, font=ctk.CTkFont(size=13), width=200,
                ).pack(side="left", padx=5)
                ctk.CTkLabel(
                    row, text=nota["data_abertura"][:10] if nota["data_abertura"] else "",
                    font=ctk.CTkFont(size=12), text_color="gray50",
                ).pack(side="left", padx=5)
                from components.cards import StatusBadge
                StatusBadge(row, nota["status"]).pack(side="right", padx=10, pady=6)
                ctk.CTkLabel(
                    row, text=f"R$ {nota['valor_total']:.2f}",
                    font=ctk.CTkFont(size=13, weight="bold"),
                ).pack(side="right", padx=10)

                for child in row.winfo_children():
                    child.bind("<Button-1>", abrir_nota)
                    child.configure(cursor="hand2")

        except Exception as e:
            print(f"Erro ao atualizar dashboard: {e}")

        self._atualizar_botao_tema()

    def _toggle_theme(self) -> None:
        """Alterna entre os modos Claro e Escuro do aplicativo."""
        current = ctk.get_appearance_mode().lower()
        novo = "light" if current in ("dark", "system") else "dark"
        ctk.set_appearance_mode(novo)
        self._atualizar_botao_tema()

    def _atualizar_botao_tema(self) -> None:
        """Atualiza a mensagem e ícone do botão de tema conforme a aparência ativa."""
        if not hasattr(self, "_btn_theme") or not self._btn_theme:
            return
        current = ctk.get_appearance_mode().lower()
        if current == "dark":
            self._btn_theme.configure(text="☀️ Modo Claro")
        else:
            self._btn_theme.configure(text="🌙 Modo Escuro")
